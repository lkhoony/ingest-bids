from datetime import datetime
from pydantic import BaseModel, Field, model_validator
from typing_extensions import Optional
from src.schemas.common_dto import BaseAPIRequest, BaseAPIResponseHeader, BaseAPIResponseBody, BaseAPIResponse, BaseAPIResponseWrapper

# 입찰 공고 기초금액 목록 정보 DTO

# 요청 DTO
class BidPblancBsisAmountListInfoReq(BaseAPIRequest):
    """
    입찰 공고 기초금액 목록 정보 조회 요청 DTO
    
    조회구분(inqryDiv)에 따른 필수 파라미터:
    - 1 (등록일시): inqryBgnDt, inqryEndDt 필수
    - 2 (입찰공고번호): bidNtceNo 필수  
    - 3 (변경일시): inqryBgnDt, inqryEndDt 필수
    """
    inqryDiv: int = Field(description="조회구분 (1:등록일시, 2:입찰공고번호, 3:변경일시)", examples=[1])
    inqryBgnDt: Optional[str] = Field(default=None, description="조회시작일시 (조회구분 1,3일 때 필수)", examples=["202001010000"])
    inqryEndDt: Optional[str] = Field(default=None, description="조회종료일시 (조회구분 1,3일 때 필수)", examples=["202001312359"])
    bidNtceNo: Optional[str] = Field(default=None, description="입찰공고번호 (조회구분 2일 때 필수)", examples=["20200123183"])


class BidPblancBsisAmountListInfoResItem(BaseModel):
    bidNtceNo: str                             # 입찰공고번호
    bidNtceOrd: Optional[str]                  # 입찰공고차수
    bidClsfcNo: Optional[str]                  # 입찰분류번호
    bidNtceNm: Optional[str]                   # 입찰공고명
    bssamt: Optional[str]                      # 기초금액
    bssamtOpenDt: Optional[datetime]           # 기초금액공개일시
    rsrvtnPrceRngBgnRate: Optional[str]        # 예비가격범위시작률
    rsrvtnPrceRngEndRate: Optional[str]        # 예비가격범위종료율
    evlBssAmt: Optional[str]                   # 평가기준금액
    dfcltydgrCfcnt: Optional[str]              # 난이도계수
    etcGnrlexpnsBssRate: Optional[str]         # 기타경비기준율
    gnrlMngcstBssRate: Optional[str]           # 일반관리비기준율
    prftBssRate: Optional[str]                 # 이윤기준율
    lbrcstBssRate: Optional[str]               # 노무비기준율
    sftyMngcst: Optional[str]                  # 산업안전보건관리비
    sftyChckMngcst: Optional[str]              # 안전관리비
    rtrfundNon: Optional[str]                  # 퇴직공제부금비
    envCnsrvcst: Optional[str]                 # 환경보전비
    scontrctPayprcePayGrntyFee: Optional[str]  # 하도급대금지급보증수수료
    mrfnHealthInsrprm: Optional[str]           # 국민건강보험료
    npnInsrprm: Optional[str]                  # 국민연금보험료
    rmrk1: Optional[str]                       # 비고1
    rmrk2: Optional[str]                       # 비고2
    odsnLngtrmrcprInsrprm: Optional[str]       # 노인장기요양보험료
    usefulAmt: Optional[str]                   # 가용금액
    inptDt: Optional[datetime]                 # 입력일시
    
    @model_validator(mode="before")
    @classmethod
    def convert_empty_dt_strings_to_none(cls, data):
        """
        API 응답에서 'Dt'로 끝나는 필드가 빈 문자열('')인 경우 None으로 변환
        validation 전에 실행되어 빈 문자열이 datetime 파싱을 시도하기 전에 None으로 변환
        """
        if isinstance(data, dict):
            for key in list(data.keys()):
                if (key.endswith("Date") or key.endswith("Dt")) and data[key] == "":
                    data[key] = None
        return data


# 공통 베이스 클래스 사용
class BidPblancBsisAmountListInfoResBody(BaseAPIResponseBody[BidPblancBsisAmountListInfoResItem]):
    pass

class BidPblancBsisAmountListInfoResHeader(BaseAPIResponseHeader):
    pass

class BidPblancBsisAmountListInfoRes(BaseAPIResponse[BidPblancBsisAmountListInfoResItem]):
    pass

class BidPblancBsisAmountListInfoAPIRes(BaseAPIResponseWrapper[BidPblancBsisAmountListInfoResItem]):
    pass

