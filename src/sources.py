"""수집 대상 API 레지스트리.

나라장터 Open API 6종을 Source 객체로 정의한다. 각 Source는 다음을 묶어서 가진다:
  - 어느 URL을 호출하는지 (환경변수 이름)
  - 대상 날짜를 어떤 요청 파라미터로 바꾸는지 (API마다 파라미터 이름이 다름)
  - 응답을 어떤 Pydantic 모델로 검증하는지
  - 어느 BigQuery 테이블에, 어떤 방식(daily/full)으로 저장하는지

IPCHAL app/external_services/*_api.py 의 파라미터 구성과 test.ipynb 의 호출 방식을 옮겼다.
새 API를 추가하려면 src/schemas/에 DTO를 넣고 SOURCES 목록에 Source 하나를 추가하면 된다.
"""

from collections.abc import Callable
from dataclasses import dataclass
from datetime import date
from typing import Any, Literal

from pydantic import BaseModel

from src.schemas.bid_pblanc_bsis_amount_list_info_service_dto import BidPblancBsisAmountListInfoAPIRes
from src.schemas.bid_pblanc_list_info_service_dto import BidPblancListInfoAPIRes
from src.schemas.data_set_opn_std_bid_pblanc_info_service_dto import DataSetOpnStdBidPblancInfoAPIRes
from src.schemas.data_set_opn_std_scsbid_info_service_dto import DataSetOpnStdScsbidInfoAPIRes
from src.schemas.indstry_ty_base_lawrglt_info_service_dto import IndstrytyBaseLawrgltInfoAPIRes
from src.schemas.scsbid_list_sttus_service_dto import ScsbidListSttusAPIRes

# 한 페이지에 요청할 행 수. 노트북과 동일하게 API 최대치(999)를 쓴다.
NUM_OF_ROWS = 999

# 저장 방식
#   daily: target_date 하루치를 조회해 테이블의 해당 ingest_date 분량만 교체
#   full : 전체를 조회해 테이블을 통째로 덮어씀 (업종 같은 마스터 데이터)
Mode = Literal["daily", "full"]


@dataclass(frozen=True)
class Source:
    """수집 대상 API 하나의 정의 (불변 객체).

    Attributes:
        name (str): 소스 이름. `--sources` 옵션과 로그에서 쓴다.
        url_env (str): API URL이 담긴 환경변수 이름.
        table (str): 적재할 BigQuery 테이블 이름 (데이터셋 제외).
        response_model (type[BaseModel]): 응답 전체를 검증할 Pydantic 모델 클래스
            (BaseAPIResponseWrapper[ResItem] 하위 클래스).
        mode (Mode): 저장 방식. "daily" 또는 "full".
        build_params (Callable[[date], dict[str, Any]]): 대상 날짜를 받아
            이 API 전용 조회 파라미터(dict)를 돌려주는 함수.
        refetch_by (str | None): 다시 조회할 날짜를 알려주는 소스 이름. 지정하면 대상 날짜에
            그 소스에 등록된 결과들의 실개찰일(rlOpengDt)도 함께 다시 조회해 교체한다.
            개찰일 기준 API에서 나중에 확정된 낙찰 결과(sucsfYn 등)를 반영하기 위해 쓴다.
    """

    name: str
    url_env: str
    table: str
    response_model: type[BaseModel]
    mode: Mode
    build_params: Callable[[date], dict[str, Any]]
    refetch_by: str | None = None


def _day_range(d: date) -> tuple[str, str]:
    """날짜 하루를 API용 시작/종료 일시 문자열로 바꾼다.

    Args:
        d (date): 대상 날짜.

    Returns:
        tuple[str, str]: (시작일시, 종료일시). 형식은 YYYYMMDDHHMM.
            예) date(2026, 10, 3) → ("202610030000", "202610032359")
    """
    day = d.strftime("%Y%m%d")
    return f"{day}0000", f"{day}2359"


def _inqry_div_params(d: date) -> dict[str, Any]:
    """입찰공고/기초금액/낙찰현황 API용 조회 파라미터를 만든다.

    inqryDiv=1은 "등록일시 기준 조회"를 뜻한다.

    Args:
        d (date): 대상 날짜.

    Returns:
        dict[str, Any]: {"inqryDiv": 1, "inqryBgnDt": ..., "inqryEndDt": ...}
    """
    bgn, end = _day_range(d)
    return {"inqryDiv": 1, "inqryBgnDt": bgn, "inqryEndDt": end}


def _bid_ntce_params(d: date) -> dict[str, Any]:
    """개방표준 입찰공고 API용 조회 파라미터를 만든다 (입찰공고일시 기준).

    Args:
        d (date): 대상 날짜.

    Returns:
        dict[str, Any]: {"bidNtceBgnDt": ..., "bidNtceEndDt": ...}
    """
    bgn, end = _day_range(d)
    return {"bidNtceBgnDt": bgn, "bidNtceEndDt": end}


def _openg_params(d: date) -> dict[str, Any]:
    """개방표준 낙찰 API용 조회 파라미터를 만든다 (개찰일시 기준).

    bsnsDivCd=5는 업무구분 "용역"만 조회한다는 뜻이다 (노트북과 동일).

    Args:
        d (date): 대상 날짜.

    Returns:
        dict[str, Any]: {"bsnsDivCd": 5, "opengBgnDt": ..., "opengEndDt": ...}
    """
    bgn, end = _day_range(d)
    return {"bsnsDivCd": 5, "opengBgnDt": bgn, "opengEndDt": end}


# 수집 대상 목록. main.py는 이 순서대로 하나씩 실행한다.
SOURCES: list[Source] = [
    # 입찰공고 목록 (등록일시 기준)
    Source("bid_pblanc_list_info", "BID_PBLANC_LIST_INFO_SERVICE_URL",
           "bid_pblanc_list_info", BidPblancListInfoAPIRes, "daily", _inqry_div_params),
    # 입찰공고 기초금액 (등록일시 기준)
    Source("bid_pblanc_bsis_amount_list_info", "BID_PBLANC_BSIS_AMOUNT_LIST_INFO_SERVICE_URL",
           "bid_pblanc_bsis_amount_list_info", BidPblancBsisAmountListInfoAPIRes, "daily", _inqry_div_params),
    # 낙찰 현황 (등록일시 기준)
    Source("scsbid_list_sttus", "SCSBID_LIST_STTUS_SERVICE_URL",
           "scsbid_list_sttus_info", ScsbidListSttusAPIRes, "daily", _inqry_div_params),
    # 개방표준 입찰공고 (입찰공고일시 기준)
    Source("data_set_opn_std_bid_pblanc_info", "PUB_DATA_OPN_STD_SERVICE_URL",
           "data_set_opn_std_bid_pblanc_info", DataSetOpnStdBidPblancInfoAPIRes, "daily", _bid_ntce_params),
    # 개방표준 낙찰 - 용역 (개찰일시 기준). 낙찰 결과는 개찰 후 며칠~몇 달 뒤 확정되므로
    # 대상 날짜에 낙찰현황에 등록된 결과들의 개찰일도 다시 조회한다
    Source("data_set_opn_std_scsbid_info", "DATA_SET_OPN_STD_SCSBID_INFO_SERVICE_URL",
           "data_set_opn_std_scsbid_info", DataSetOpnStdScsbidInfoAPIRes, "daily", _openg_params,
           refetch_by="scsbid_list_sttus"),
    # 업종 및 근거법규 (마스터 데이터, 날짜 조건 없이 전체 조회)
    Source("indstryty_base_lawrglt_info", "INDSTRY_BASE_LAWRGLT_INFO_SERVICE_URL",
           "indstryty_base_lawrglt_info", IndstrytyBaseLawrgltInfoAPIRes, "full", lambda d: {}),
]

# 이름으로 Source를 찾기 위한 사전 (예: SOURCES_BY_NAME["scsbid_list_sttus"])
SOURCES_BY_NAME: dict[str, Source] = {s.name: s for s in SOURCES}


def base_params(source: Source, target_date: date, api_key: str) -> dict[str, Any]:
    """API 요청에 보낼 전체 쿼리 파라미터를 만든다 (pageNo 제외).

    공통 파라미터(ServiceKey, numOfRows, type)에 소스별 조회 파라미터를 합친다.
    pageNo는 페이지마다 달라지므로 client.py에서 붙인다.

    Args:
        source (Source): 수집 대상 소스.
        target_date (date): 수집 대상 날짜. full 모드 소스는 무시한다.
        api_key (str): 공공데이터포털 서비스 키.

    Returns:
        dict[str, Any]: 쿼리 파라미터.
            예) {"ServiceKey": "...", "numOfRows": 999, "type": "json",
                 "inqryDiv": 1, "inqryBgnDt": "202610030000", "inqryEndDt": "202610032359"}
    """
    return {
        "ServiceKey": api_key,
        "numOfRows": NUM_OF_ROWS,
        "type": "json",
        **source.build_params(target_date),
    }
