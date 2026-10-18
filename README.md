# ingest-bids

조달청 나라장터 Open API 6종 → BigQuery(`ipchal-491704.ipchal`) 일 단위 수집 배치.
Cloud Run Job + Cloud Scheduler로 매일 실행하고, GitHub `main` push 시 Cloud Build가 이미지를 다시 빌드·배포한다.

```
git push(main) → Cloud Build(test → build → push → jobs deploy) → Cloud Run Job
Cloud Scheduler(매일) → Cloud Run Job → 나라장터 API 6종 → BigQuery ipchal.* (기존 테이블)
```

## 수집 대상

| 소스 (`--sources` 이름) | 조회 기준 (대상 날짜 00:00~23:59) | 테이블 | 저장 방식 |
|---|---|---|---|
| bid_pblanc_list_info | 등록일시 (inqryDiv=1) | bid_pblanc_list_info | 날짜 교체 |
| bid_pblanc_bsis_amount_list_info | 등록일시 (inqryDiv=1) | bid_pblanc_bsis_amount_list_info | 날짜 교체 |
| scsbid_list_sttus | 등록일시 (inqryDiv=1) | scsbid_list_sttus_info | 날짜 교체 |
| data_set_opn_std_bid_pblanc_info | 입찰공고일시 | data_set_opn_std_bid_pblanc_info | 날짜 교체 |
| data_set_opn_std_scsbid_info | 개찰일시, 용역(bsnsDivCd=5) + 늦게 확정된 결과의 개찰일 | data_set_opn_std_scsbid_info | 날짜 교체 |
| indstryty_base_lawrglt_info | 전체 (마스터 데이터) | indstryty_base_lawrglt_info | 전체 덮어쓰기 |

- **대상 날짜**: 기본은 KST 기준 어제. `TARGET_DATE=YYYY-MM-DD`로 지정할 수 있다.
- **날짜 교체**: 각 테이블에 `ingest_date`(DATE) 컬럼을 추가하고, `DELETE WHERE ingest_date = 대상날짜` 후 APPEND한다. 같은 날짜를 몇 번 다시 실행해도 중복되지 않는다.
- **개방표준 낙찰 다시 조회**: 이 API는 개찰일로만 조회되고, 낙찰여부(`sucsfYn`)·최종낙찰(`fnlSucsf*`)은 개찰 후 며칠~몇 달 뒤에 채워진다. 그래서 대상 날짜에 낙찰현황에 **등록된** 결과들의 실개찰일(`rlOpengDt`)을 모아 그 개찰일들도 하루씩 다시 조회해 교체한다. 실측 하루 약 25개 날짜, API 호출 약 210회, 약 2.5분.
- 노트북(`test.ipynb`)으로 넣은 과거 데이터는 `ingest_date`가 NULL이라 건드리지 않는다.
- 컬럼 구조와 타입 변환(`*Dt`/`*Date` → datetime)은 노트북과 같다. 적재할 때는 기존 테이블 스키마를 그대로 쓴다.
- 소스 하나가 실패해도 나머지는 계속 실행한다. 실패한 소스가 있으면 exit 1로 끝나고 Cloud Run이 재시도한다.

## 구조

| 경로 | 역할 |
|---|---|
| `src/main.py` | 진입점. `--sources`, `--dry-run`, 대상 날짜, 소스별 실행/실패 집계 |
| `src/sources.py` | 6개 API의 URL 환경변수, 요청 파라미터, 테이블, 저장 방식 |
| `src/client.py` | 페이지네이션(httpx async, 동시 3), 재시도, `resultCode != "00"` 오류 처리, 키 마스킹 |
| `src/loader.py` | DataFrame 변환, `replace_day` / `replace_all` |
| `src/schemas/` | IPCHAL `app/schemas`에서 복사한 Pydantic DTO |
| `deploy/env.yaml` | Cloud Run 환경변수 (데이터셋, API URL) |
| `cloudbuild.yaml` | CI/CD 파이프라인 |

## 로컬 실행

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements-dev.txt
pytest -q

gcloud auth application-default login     # BigQuery 접근 (서비스 계정 키 파일 사용 안 함)
cp .env.example .env                         # 값 채우기 (URL은 deploy/env.yaml 참고)
set -a && source .env && set +a

python -m src.main --dry-run                 # API 수집만, BigQuery 쓰기 없음
python -m src.main --sources scsbid_list_sttus
```

> 처음에는 `.env`에서 `BQ_DATASET=ipchal_dev`(테스트 데이터셋)로 두고, 같은 날짜를 두 번 실행해서 행 수가 그대로인지 확인한 뒤 운영 데이터셋에 적용하세요.

## GCP 최초 설정

```bash
PROJECT_ID=ipchal-491704
REGION=asia-northeast3
gcloud config set project $PROJECT_ID

# 1. API 활성화
gcloud services enable run.googleapis.com cloudbuild.googleapis.com artifactregistry.googleapis.com \
  secretmanager.googleapis.com bigquery.googleapis.com cloudscheduler.googleapis.com

# 2. 이미지 저장소, API 키 시크릿 (값: IPCHAL/.env.dev 의 BID_DATA_SERVICE_API_KEY)
gcloud artifacts repositories create ingest --repository-format=docker --location=$REGION
printf '%s' "YOUR_API_KEY" | gcloud secrets create openapi-key --data-file=-

# 3. 서비스 계정
gcloud iam service-accounts create ingest-job-sa   # Job 실행용
gcloud iam service-accounts create cloudbuild-sa   # 빌드/배포용
gcloud iam service-accounts create scheduler-sa    # 스케줄 실행용

JOB_SA=ingest-job-sa@$PROJECT_ID.iam.gserviceaccount.com
BUILD_SA=cloudbuild-sa@$PROJECT_ID.iam.gserviceaccount.com
SCHED_SA=scheduler-sa@$PROJECT_ID.iam.gserviceaccount.com

# Job 실행 SA: ipchal 데이터셋 쓰기 + 쿼리 실행 + 시크릿 읽기
gcloud projects add-iam-policy-binding $PROJECT_ID --member=serviceAccount:$JOB_SA --role=roles/bigquery.jobUser
bq add-iam-policy-binding --member=serviceAccount:$JOB_SA --role=roles/bigquery.dataEditor $PROJECT_ID:ipchal
gcloud secrets add-iam-policy-binding openapi-key --member=serviceAccount:$JOB_SA --role=roles/secretmanager.secretAccessor

# 빌드 SA: 이미지 푸시 + Job 배포 + 로그
for role in roles/run.developer roles/artifactregistry.writer roles/logging.logWriter; do
  gcloud projects add-iam-policy-binding $PROJECT_ID --member=serviceAccount:$BUILD_SA --role=$role
done
gcloud iam service-accounts add-iam-policy-binding $JOB_SA --member=serviceAccount:$BUILD_SA --role=roles/iam.serviceAccountUser
```

### 4. GitHub 연결 + 트리거 (콘솔)

1. Cloud Build → 저장소(2세대) → 호스트 연결 만들기 → GitHub App 설치 → 이 저장소 연결
2. Cloud Build → 트리거 만들기: 브랜치로 푸시 `^main$`, 구성 파일 `cloudbuild.yaml`, 서비스 계정 `cloudbuild-sa`
3. push 후 빌드 성공 확인 → 수동 실행:
   ```bash
   gcloud run jobs execute ingest-bids --region=$REGION --wait
   ```

### 5. Cloud Scheduler (Job 최초 배포 후)

```bash
gcloud run jobs add-iam-policy-binding ingest-bids --region=$REGION \
  --member=serviceAccount:$SCHED_SA --role=roles/run.invoker

gcloud scheduler jobs create http ingest-bids-daily --location=$REGION \
  --schedule="0 6 * * *" --time-zone="Asia/Seoul" \
  --uri="https://run.googleapis.com/v2/projects/$PROJECT_ID/locations/$REGION/jobs/ingest-bids:run" \
  --http-method=POST --oauth-service-account-email=$SCHED_SA
```
> 이미 만든 스케줄러는 URI가 위 `:run` 엔드포인트인지, 인증이 **OAuth**(OIDC 아님)인지 확인하세요.

## 운영

```bash
# 특정 날짜 백필 (그 날짜 분량만 교체)
gcloud run jobs execute ingest-bids --region=$REGION --update-env-vars=TARGET_DATE=2026-10-01

# 특정 소스만 다시 실행
gcloud run jobs execute ingest-bids --region=$REGION --args="--sources,scsbid_list_sttus"

# 실행 기록
gcloud run jobs executions list --job=ingest-bids --region=$REGION
```

```sql
-- 일자별 적재 건수 확인
SELECT ingest_date, COUNT(*) AS n
FROM `ipchal-491704.ipchal.scsbid_list_sttus_info`
WHERE ingest_date IS NOT NULL
GROUP BY 1 ORDER BY 1 DESC;
```

## 보안 메모
- 서비스 계정 키 JSON 파일은 쓰지 않습니다. Cloud Run은 연결된 `ingest-job-sa`로, 로컬은 ADC로 인증합니다. `*.json`은 `.gitignore`에 들어 있습니다.
- API 키는 Secret Manager에만 둡니다. 요청 URL은 모두 https이고, 오류 로그에서는 키를 `***`로 가립니다.
