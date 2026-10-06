from datetime import datetime
from pydantic import BaseModel, Field, model_validator
from typing_extensions import Literal, Optional, List
from src.schemas.common_dto import BaseAPIRequest, BaseAPIResponseHeader, BaseAPIResponseBody, BaseAPIResponse, BaseAPIResponseWrapper

# 데이터셋 개방표준 성공입찰 정보 DTO

# 요청 DTO
class DataSetOpnStdScsbidInfoReq(BaseAPIRequest):
    """
    데이터셋 개방표준 성공입찰 정보 조회 요청 DTO
    
    업무구분코드(bsnsDivCd)에 따른 조회:
    - 1: 물품
    - 2: 외자
    - 3: 공사
    - 5: 용역
    
    개찰일시 범위는 1주일로 제한됩니다.
    """
    bsnsDivCd: int = Field(description="업무구분코드 (1:물품, 2:외자, 3:공사, 5:용역)", examples=[5])
    opengBgnDt: str = Field(description="개찰일시범위 시작 'YYYYMMDDHHMM'", examples=["201712010000"])
    opengEndDt: str = Field(description="개찰일시범위 종료 'YYYYMMDDHHMM'", examples=["201712072359"])

class DataSetOpnStdScsbidInfoResItem(BaseModel):
    bidNtceNo: str                         # 입찰공고번호
    bidNtceOrd: Optional[str]              # 입찰공고차수
    bidNtceNm: Optional[str]               # 입찰공고명
    bsnsDivNm: Optional[str]               # 업무구분명
    cntrctCnclsSttusNm: Optional[str]      # 계약체결형태명
    cntrctCnclsMthdNm: Optional[str]       # 계약체결방법명
    bidwinrDcsnMthdNm: Optional[str]       # 낙찰자결정방법명
    ntceInsttNm: Optional[str]             # 공고기관명
    ntceInsttCd: Optional[str]             # 공고기관코드
    dmndInsttNm: Optional[str]             # 수요기관명
    dmndInsttCd: Optional[str]             # 수요기관코드
    sucsfLwstlmtRt: Optional[str]          # 낙찰하한율
    presmptPrce: Optional[str]             # 추정가격
    rsrvtnPrce: Optional[str]              # 예정가격
    bssAmt: Optional[str]                  # 기초금액
    opengDate: Optional[datetime]          # 개찰일자
    opengTm: Optional[str]                 # 개찰시각
    opengRsltDivNm: Optional[str]          # 개찰결과구분명
    opengRank: Optional[str]               # 개찰순위
    bidprcCorpBizrno: Optional[str]        # 투찰업체사업자등록번호
    bidprcCorpNm: Optional[str]            # 투찰업체명
    bidprcCorpCeoNm: Optional[str]         # 투찰업체대표자명
    bidprcAmt: Optional[str]               # 투찰금액
    bidprcRt: Optional[str]                # 투찰율
    bidprcDate: Optional[datetime]         # 투찰일자
    bidprcTm: Optional[str]                # 투찰시각
    sucsfYn: Optional[str]                 # 낙찰여부
    dqlfctnRsn: Optional[str]              # 부적격사유
    fnlSucsfAmt: Optional[str]             # 최종낙찰금액
    fnlSucsfRt: Optional[str]              # 최종낙찰율
    fnlSucsfDate: Optional[datetime]       # 최종낙찰일자
    fnlSucsfCorpNm: Optional[str]          # 최종낙찰업체명
    fnlSucsfCorpCeoNm: Optional[str]       # 최종낙찰업체대표자명
    fnlSucsfCorpOfclNm: Optional[str]      # 최종낙찰업체담당자명
    fnlSucsfCorpBizrno: Optional[str]      # 최종낙찰업체사업자등록번호
    fnlSucsfCorpAdrs: Optional[str]        # 최종낙찰업체주소
    fnlSucsfCorpContactTel: Optional[str]  # 최종낙찰업체연락전화번호
    dataBssDate: Optional[datetime]        # 데이터기준일자

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
class DataSetOpnStdScsbidInfoResBody(BaseAPIResponseBody[DataSetOpnStdScsbidInfoResItem]):
    pass

class DataSetOpnStdScsbidInfoResHeader(BaseAPIResponseHeader):
    pass

class DataSetOpnStdScsbidInfoRes(BaseAPIResponse[DataSetOpnStdScsbidInfoResItem]):
    pass

class DataSetOpnStdScsbidInfoAPIRes(BaseAPIResponseWrapper[DataSetOpnStdScsbidInfoResItem]):
    pass
