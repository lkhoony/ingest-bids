"""BigQuery 적재 모듈.

기존 ipchal.* 테이블(test.ipynb가 autodetect로 만든 컬럼 구조)을 그대로 쓰고,
ingest_date(DATE) 컬럼 하나만 추가해서 같은 날짜를 다시 실행해도 중복되지 않게 한다.
  - daily 소스: ingest_date 파티션(table$YYYYMMDD)을 WRITE_TRUNCATE로 로드   (replace_day)
  - full 소스 : WRITE_TRUNCATE (테이블 전체 교체)                           (replace_all)
daily 테이블은 ingest_date로 파티션되어 있어야 한다 (README "파티션 전환" 참고).
DELETE(DML)는 파티션 없는 테이블에서 테이블 전체 크기만큼 과금되지만, 파티션 덮어쓰기 로드는 무료이고
하루치 교체가 로드 한 번이라 중간에 실패해도 그 날짜가 비지 않는다.
ingest_date가 NULL인 과거 데이터(노트북으로 넣은 것)는 __NULL__ 파티션에 있으므로 건드리지 않는다.
"""

import logging
from datetime import date
from typing import Any

import pandas as pd
from google.api_core.exceptions import NotFound
from google.cloud import bigquery

logger = logging.getLogger(__name__)

# 멱등 적재 기준이 되는 컬럼
INGEST_DATE = "ingest_date"
INGEST_DATE_FIELD = bigquery.SchemaField(INGEST_DATE, "DATE", mode="NULLABLE", description="수집 대상 날짜(KST)")


def to_dataframe(items: list[Any], ingest_date: date) -> pd.DataFrame:
    """API 응답 아이템 리스트를 BigQuery 적재용 DataFrame으로 바꾼다.

    test.ipynb의 insert_items_to_bigquery와 똑같이 변환한다. 그래야 기존 테이블 타입과 맞는다.
      1. Pydantic 모델 → dict (model_dump)
      2. 이름이 "Dt" 또는 "Date"로 끝나는 컬럼 → datetime (변환 실패 값은 NaT)
    여기에 ingest_date 컬럼을 추가한다.

    Args:
        items (list[Any]): ResItem Pydantic 모델 객체 리스트 (client.fetch_all의 결과).
        ingest_date (date): 수집 대상 날짜. 모든 행의 ingest_date 컬럼 값이 된다.

    Returns:
        pd.DataFrame: 행 = 아이템, 열 = ResItem 필드 + ingest_date.
            items가 비어 있으면 ingest_date 컬럼만 있는 빈 DataFrame (df.empty == True).
    """
    df = pd.DataFrame([item.model_dump() for item in items])
    for col in df.columns:
        if col.endswith("Dt") or col.endswith("Date"):
            df[col] = pd.to_datetime(df[col], errors="coerce")
    df[INGEST_DATE] = ingest_date
    return df


class BigQueryLoader:
    """한 데이터셋 안의 테이블들에 DataFrame을 적재한다.

    Attributes:
        client (bigquery.Client): BigQuery 클라이언트.
        dataset (str): 대상 데이터셋 이름 (예: "ipchal").
    """

    def __init__(self, dataset: str, project: str | None = None, client: bigquery.Client | None = None):
        """
        Args:
            dataset (str): 대상 데이터셋 이름.
            project (str | None): GCP 프로젝트 ID. None이면 실행 환경의 기본 프로젝트.
                client를 직접 넘기면 무시된다.
            client (bigquery.Client | None): 이미 만든 클라이언트 (테스트에서 mock 주입용).
                None이면 새로 만든다. 인증은 ADC(Cloud Run 서비스 계정 또는 로컬 gcloud 로그인)를 쓴다.
        """
        self.client = client or bigquery.Client(project=project)
        self.dataset = dataset

    def table_id(self, table: str) -> str:
        """테이블 이름을 전체 ID로 바꾼다.

        Args:
            table (str): 테이블 이름 (예: "scsbid_list_sttus_info").

        Returns:
            str: "프로젝트.데이터셋.테이블" 형식의 전체 ID.
        """
        return f"{self.client.project}.{self.dataset}.{table}"

    def _table_with_ingest_date(self, table_id: str) -> bigquery.Table | None:
        """기존 테이블을 가져온다. ingest_date 컬럼이 없으면 추가한다.

        컬럼 추가는 NULLABLE 컬럼 추가라서 기존 데이터에 영향이 없다.
        기존 행의 ingest_date 값은 NULL이 된다.

        Args:
            table_id (str): 전체 테이블 ID.

        Returns:
            bigquery.Table | None: ingest_date가 포함된 테이블.
                테이블이 없으면 None (첫 적재 때 autodetect로 생성하게 됨).
        """
        try:
            table = self.client.get_table(table_id)
        except NotFound:
            return None
        if all(f.name != INGEST_DATE for f in table.schema):
            table.schema = [*table.schema, INGEST_DATE_FIELD]
            table = self.client.update_table(table, ["schema"])
            logger.info("added ingest_date column", extra={"table": table_id})
        return table

    def _load(self, df: pd.DataFrame, table_id: str, schema: list[bigquery.SchemaField] | None,
              write_disposition: str, partitioned: bool = False) -> int:
        """DataFrame을 BigQuery 로드 작업으로 적재하고 완료를 기다린다.

        Args:
            df (pd.DataFrame): 적재할 데이터.
            table_id (str): 전체 테이블 ID.
            schema (list[bigquery.SchemaField] | None): 적용할 스키마. None이면 autodetect.
            write_disposition (str): bigquery.WriteDisposition 값 (WRITE_APPEND / WRITE_TRUNCATE).
            partitioned (bool): True면 ingest_date 파티션을 지정한다. 테이블이 없을 때
                파티션 테이블로 만들고, 있으면 파티션 설정이 다를 때 로드가 실패한다.

        Returns:
            int: 적재된 행 수.

        Raises:
            google.api_core.exceptions.GoogleAPIError: 로드 작업이 실패했을 때.
        """
        job_config = bigquery.LoadJobConfig(write_disposition=write_disposition)
        if partitioned:
            job_config.time_partitioning = bigquery.TimePartitioning(field=INGEST_DATE)
        if schema is not None:
            # 하루치 데이터에 전부 null인 컬럼이 있어도 타입이 흔들리지 않게 기존 스키마를 그대로 쓴다
            job_config.schema = schema
        else:
            job_config.autodetect = True
        job = self.client.load_table_from_dataframe(df, table_id, job_config=job_config)
        job.result()  # 완료까지 대기. 실패하면 예외
        return job.output_rows or 0

    def replace_day(self, table: str, df: pd.DataFrame, ingest_date: date) -> int:
        """테이블의 해당 날짜(ingest_date) 파티션을 df로 교체한다 (daily 소스용).

        파티션 데코레이터(table$YYYYMMDD)에 WRITE_TRUNCATE로 로드하므로 그 날짜만 바뀌고,
        같은 날짜로 몇 번을 실행해도 결과가 같다(멱등). 로드가 실패하면 기존 파티션이 그대로 남는다.
        df가 비어 있으면 해당 파티션을 지우기만 한다 (그날 데이터가 0건인 것이 최신 상태).

        Args:
            table (str): 테이블 이름 (데이터셋 제외).
            df (pd.DataFrame): to_dataframe()의 결과.
            ingest_date (date): 교체할 날짜.

        Returns:
            int: 새로 적재된 행 수 (df가 비면 0).

        Raises:
            RuntimeError: 기존 테이블이 ingest_date로 파티션되어 있지 않을 때.
                파티션 없는 테이블에 WRITE_TRUNCATE하면 테이블 전체가 지워질 수 있으므로 막는다.
            google.api_core.exceptions.GoogleAPIError: 로드 작업이나 파티션 삭제가 실패했을 때.
        """
        table_id = self.table_id(table)
        existing = self._table_with_ingest_date(table_id)
        if existing is not None and (existing.time_partitioning is None
                                     or existing.time_partitioning.field != INGEST_DATE):
            raise RuntimeError(f"{table_id}: ingest_date 파티션 테이블이 아닙니다 — README의 파티션 전환을 먼저 하세요.")
        partition_id = f"{table_id}${ingest_date:%Y%m%d}"
        if df.empty:
            if existing is not None:
                self.client.delete_table(partition_id, not_found_ok=True)
            return 0
        schema = list(existing.schema) if existing is not None else None
        return self._load(df, partition_id, schema, bigquery.WriteDisposition.WRITE_TRUNCATE, partitioned=True)

    def replace_all(self, table: str, df: pd.DataFrame) -> int:
        """테이블 전체를 df로 덮어쓴다 (full 소스, 마스터 데이터용).

        Args:
            table (str): 테이블 이름 (데이터셋 제외).
            df (pd.DataFrame): to_dataframe()의 결과.

        Returns:
            int: 적재된 행 수.

        Raises:
            RuntimeError: df가 비어 있을 때. 마스터 데이터가 0건이면 API 이상일 가능성이 높으므로
                기존 데이터를 지우지 않고 중단한다.
            google.api_core.exceptions.GoogleAPIError: 로드 작업이 실패했을 때.
        """
        table_id = self.table_id(table)
        if df.empty:
            raise RuntimeError(f"{table_id}: 수집 결과 0건 — 기존 데이터를 지우지 않고 중단합니다.")
        existing = self._table_with_ingest_date(table_id)
        schema = list(existing.schema) if existing is not None else None
        return self._load(df, table_id, schema, bigquery.WriteDisposition.WRITE_TRUNCATE)
