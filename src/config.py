"""환경변수 기반 설정 모듈.

설정값은 모두 환경변수에서 읽는다. 실행 환경별 주입 경로:
  - Cloud Run Job: deploy/env.yaml(--env-vars-file)로 일반 값, Secret Manager(--set-secrets)로 API 키
  - 로컬: .env 파일을 셸에 로드 (`set -a && source .env && set +a`)

사용하는 환경변수:
  GCP_PROJECT   (선택) BigQuery 프로젝트 ID. 비우면 실행 환경의 기본 프로젝트
  BQ_DATASET    (선택) 적재 대상 데이터셋. 기본값 "ipchal"
  OPENAPI_KEY   (필수) 공공데이터포털 서비스 키
  TARGET_DATE   (선택) 수집 대상 날짜 YYYY-MM-DD. 비우면 KST 기준 어제
  *_SERVICE_URL (소스별 필수) 각 API의 요청 URL. 목록은 src/sources.py 참고
"""

import os
from dataclasses import dataclass


def _require(name: str) -> str:
    """필수 환경변수를 읽는다.

    Args:
        name (str): 환경변수 이름.

    Returns:
        str: 환경변수 값 (빈 문자열이 아님).

    Raises:
        RuntimeError: 환경변수가 없거나 빈 문자열일 때.
    """
    value = os.environ.get(name)
    if not value:
        raise RuntimeError(f"필수 환경변수 {name} 가 설정되지 않았습니다.")
    return value


@dataclass(frozen=True)
class Config:
    """실행 전체에 공통으로 쓰는 설정값 (불변 객체).

    Attributes:
        gcp_project (str | None): BigQuery 프로젝트 ID. None이면 클라이언트가 실행 환경에서 자동으로 결정한다.
        bq_dataset (str): 적재 대상 BigQuery 데이터셋 이름.
        api_key (str): 공공데이터포털 서비스 키 (ServiceKey 파라미터로 전송).
        target_date (str | None): 수집 대상 날짜 문자열(YYYY-MM-DD). None이면 KST 기준 어제를 쓴다.
    """

    gcp_project: str | None
    bq_dataset: str
    api_key: str
    target_date: str | None

    @classmethod
    def from_env(cls) -> "Config":
        """환경변수에서 Config를 만든다.

        Returns:
            Config: 환경변수 값을 담은 설정 객체.

        Raises:
            RuntimeError: 필수 환경변수 OPENAPI_KEY가 없을 때.
        """
        return cls(
            # Cloud Run에서는 비워두면 클라이언트가 실행 환경의 프로젝트를 자동으로 사용
            gcp_project=os.environ.get("GCP_PROJECT") or None,
            bq_dataset=os.environ.get("BQ_DATASET", "ipchal"),
            api_key=_require("OPENAPI_KEY"),
            target_date=os.environ.get("TARGET_DATE") or None,
        )


def source_url(env_name: str) -> str:
    """소스별 API URL을 환경변수에서 읽는다.

    전체 설정(Config)과 달리, 해당 소스를 실제로 실행할 때만 요구한다.
    덕분에 `--sources`로 일부 소스만 돌릴 때는 나머지 URL이 없어도 된다.

    Args:
        env_name (str): URL이 담긴 환경변수 이름 (예: "SCSBID_LIST_STTUS_SERVICE_URL").

    Returns:
        str: API 요청 URL.

    Raises:
        RuntimeError: 환경변수가 없거나 빈 문자열일 때.
    """
    return _require(env_name)
