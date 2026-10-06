"""Cloud Run Job 진입점: 대상 날짜 계산 → 소스별 Open API 수집 → BigQuery 적재.

소스는 순차 실행하고(API 호출 한도 보호), 하나가 실패해도 나머지는 계속한다.
실패한 소스가 있으면 마지막에 exit 1 → Cloud Run이 재시도(--max-retries)한다.
적재는 멱등이라 재시도해도 중복되지 않는다.

사용법:
  python -m src.main                                  # 전체 소스, KST 어제
  python -m src.main --sources scsbid_list_sttus      # 일부 소스만
  python -m src.main --dry-run                        # 수집만 하고 BigQuery에 쓰지 않음
  TARGET_DATE=2026-10-01 python -m src.main           # 특정 날짜(백필)
"""

import argparse
import asyncio
import json
import logging
import sys
from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

from src.client import fetch_all
from src.config import Config, source_url
from src.loader import BigQueryLoader, to_dataframe
from src.sources import SOURCES, SOURCES_BY_NAME, Source, base_params

KST = ZoneInfo("Asia/Seoul")

# LogRecord 기본 속성 이름들. 이것을 뺀 나머지가 logger.info(..., extra={...})로 넘긴 값이다.
_STD_LOG_ATTRS = set(vars(logging.makeLogRecord({}))) | {"message"}

logger = logging.getLogger("ingest")


class CloudLoggingFormatter(logging.Formatter):
    """로그 레코드를 Cloud Logging이 인식하는 JSON 한 줄로 바꾸는 포매터.

    stdout에 JSON을 출력하면 Cloud Logging이 "severity"로 로그 수준을 구분한다.
    extra로 넘긴 값도 필드로 들어가서 콘솔에서 검색할 수 있다.
    출력 예) {"severity": "INFO", "message": "source done", "logger": "ingest", "source": "...", "loaded": 333}
    """

    def format(self, record: logging.LogRecord) -> str:
        """
        Args:
            record (logging.LogRecord): 출력할 로그 레코드.

        Returns:
            str: JSON 한 줄. 한글은 이스케이프하지 않는다.
                예외 정보가 있으면 "exception" 필드에 traceback이 들어간다.
        """
        entry = {
            "severity": record.levelname,
            "message": record.getMessage(),
            "logger": record.name,
        }
        entry.update({k: v for k, v in vars(record).items() if k not in _STD_LOG_ATTRS})
        if record.exc_info:
            entry["exception"] = self.formatException(record.exc_info)
        return json.dumps(entry, ensure_ascii=False, default=str)


def setup_logging() -> None:
    """루트 로거를 stdout + JSON 포맷(INFO 이상)으로 설정한다.

    httpx 로거는 WARNING 이상만 남긴다. httpx는 INFO 수준에서 요청 URL을 찍는데,
    그 URL에 ServiceKey가 들어 있기 때문이다.

    Returns:
        None
    """
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(CloudLoggingFormatter())
    logging.basicConfig(level=logging.INFO, handlers=[handler], force=True)
    logging.getLogger("httpx").setLevel(logging.WARNING)  # 요청 URL(ServiceKey 포함) 로그 방지


def resolve_target_date(override: str | None, now: datetime | None = None) -> date:
    """수집 대상 날짜를 정한다.

    Args:
        override (str | None): TARGET_DATE 값(YYYY-MM-DD). 있으면 그 날짜를 쓴다 (백필용).
        now (datetime | None): 현재 시각. 테스트에서 고정할 때만 넘긴다. None이면 현재 KST 시각.

    Returns:
        date: override가 있으면 그 날짜, 없으면 KST 기준 어제.

    Raises:
        ValueError: override가 YYYY-MM-DD 형식이 아닐 때.
    """
    if override:
        return date.fromisoformat(override)
    now = now or datetime.now(KST)
    return (now.astimezone(KST) - timedelta(days=1)).date()


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    """명령줄 인자를 읽는다.

    Args:
        argv (list[str] | None): 인자 목록. None이면 sys.argv[1:].

    Returns:
        argparse.Namespace:
            - sources (str): 실행할 소스 이름들을 쉼표로 이은 문자열. 기본값은 전체.
            - dry_run (bool): True면 수집만 하고 BigQuery에 쓰지 않는다.

    Raises:
        SystemExit: 알 수 없는 소스 이름이 있을 때 (argparse가 오류 메시지를 찍고 종료).
    """
    parser = argparse.ArgumentParser(description="나라장터 Open API → BigQuery 수집")
    parser.add_argument("--sources", default=",".join(s.name for s in SOURCES),
                        help=f"쉼표로 구분. 선택지: {', '.join(SOURCES_BY_NAME)}")
    parser.add_argument("--dry-run", action="store_true", help="수집만 하고 BigQuery에 쓰지 않음")
    args = parser.parse_args(argv)
    unknown = [n for n in args.sources.split(",") if n not in SOURCES_BY_NAME]
    if unknown:
        parser.error(f"알 수 없는 소스: {unknown}")
    return args


async def ingest_source(source: Source, target_date: date, config: Config,
                        loader: BigQueryLoader | None) -> int:
    """소스 하나를 수집하고 적재한다.

    순서: API 전체 페이지 수집 → DataFrame 변환 → 저장 방식(mode)에 따라 적재.

    Args:
        source (Source): 처리할 소스.
        target_date (date): 수집 대상 날짜.
        config (Config): 실행 설정 (API 키 등).
        loader (BigQueryLoader | None): 적재기. None이면 dry-run으로 보고 건수만 로그에 남긴다.

    Returns:
        int: dry-run이면 수집 건수, 아니면 적재된 행 수.

    Raises:
        RuntimeError: URL 환경변수가 없을 때, 또는 full 소스가 0건일 때.
        OpenApiError: API 호출이 실패했을 때.
        google.api_core.exceptions.GoogleAPIError: BigQuery 작업이 실패했을 때.
    """
    started = datetime.now()
    items = await fetch_all(source_url(source.url_env), base_params(source, target_date, config.api_key),
                            source.response_model)
    df = to_dataframe(items, target_date)
    fields = {"source": source.name, "target_date": target_date.isoformat(), "fetched": len(df)}

    if loader is None:
        logger.info("dry-run: fetched", extra=fields)
        return len(df)

    if source.mode == "full":
        rows = loader.replace_all(source.table, df)
    else:
        rows = loader.replace_day(source.table, df, target_date)
    logger.info("source done", extra={**fields, "loaded": rows,
                                      "seconds": round((datetime.now() - started).total_seconds(), 1)})
    return rows


async def run(config: Config, source_names: list[str], dry_run: bool = False,
              loader: BigQueryLoader | None = None) -> list[str]:
    """선택된 소스를 순서대로 처리하고, 실패한 소스 이름 목록을 반환한다.

    한 소스가 실패해도 예외를 로그에 남기고 다음 소스로 넘어간다.

    Args:
        config (Config): 실행 설정.
        source_names (list[str]): 처리할 소스 이름 목록 (SOURCES_BY_NAME의 키).
        dry_run (bool): True면 BigQuery에 쓰지 않는다.
        loader (BigQueryLoader | None): 적재기. None이고 dry_run이 아니면 config로 새로 만든다.
            테스트에서 mock을 넣을 때 쓴다.

    Returns:
        list[str]: 실패한 소스 이름 목록. 모두 성공하면 빈 리스트.

    Raises:
        ValueError: config.target_date 형식이 잘못되었을 때.
    """
    target_date = resolve_target_date(config.target_date)
    logger.info("ingest started", extra={"target_date": target_date.isoformat(),
                                         "sources": source_names, "dry_run": dry_run})
    if not dry_run and loader is None:
        loader = BigQueryLoader(config.bq_dataset, project=config.gcp_project)

    failed = []
    for name in source_names:
        try:
            await ingest_source(SOURCES_BY_NAME[name], target_date, config, None if dry_run else loader)
        except Exception:
            logger.exception("source failed", extra={"source": name, "target_date": target_date.isoformat()})
            failed.append(name)

    logger.info("ingest finished", extra={"target_date": target_date.isoformat(), "failed": failed})
    return failed


def main(argv: list[str] | None = None) -> None:
    """프로그램 진입점. 로깅 설정 → 인자 해석 → 실행 → 종료 코드 결정.

    종료 코드:
        0: 모든 소스 성공
        1: 하나 이상 실패, 또는 설정 오류 (Cloud Run이 실패로 기록하고 재시도한다)
        2: 잘못된 명령줄 인자 (argparse)

    Args:
        argv (list[str] | None): 명령줄 인자. None이면 sys.argv[1:].

    Returns:
        None. 실패 시 sys.exit(1)로 종료한다.
    """
    setup_logging()
    args = parse_args(argv)
    try:
        failed = asyncio.run(run(Config.from_env(), args.sources.split(","), args.dry_run))
    except Exception:
        logger.exception("ingest failed")
        sys.exit(1)
    if failed:
        sys.exit(1)


if __name__ == "__main__":
    main()
