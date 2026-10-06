from datetime import datetime
from pydantic import BaseModel, Field, model_validator
from typing_extensions import Literal, Optional, List
from src.schemas.common_dto import BaseAPIRequest, BaseAPIResponseHeader, BaseAPIResponseBody, BaseAPIResponse, BaseAPIResponseWrapper

# 데이터셋 개방표준에 따른 입찰 공고 정보 DTO

# 요청 DTO
class DataSetOpnStdBidPblancInfoReq(BaseAPIRequest):
    bidNtceBgnDt: str = Field(default="202401010000", description="입찰공고 시작일시", examples=["202401010000"])
    bidNtceEndDt: str = Field(default="202401312359", description="입찰공고 종료일시", examples=["202401312359"])

class DataSetOpnStdBidPblancInfoResItem(BaseModel):
    bidNtceNo: str                                  # 입찰공고번호
    bidNtceOrd: Optional[str]                       # 입찰공고차수
    refNtceNo: Optional[str]                        # 참조공고번호
    refNtceOrd: Optional[str]                       # 참조공고차수
    ppsNtceYn: Optional[str]                        # 나라장터공고여부
    bidNtceNm: Optional[str]                        # 입찰공고명
    bidNtceSttusNm: Optional[str]                   # 입찰공고상태명
    bidNtceDate: Optional[datetime]                 # 입찰공고일자
    bidNtceBgn: Optional[str]                       # 입찰공고시각
    bsnsDivNm: Optional[str]                        # 업무구분명
    intrntnlBidYn: Optional[str]                    # 국제입찰여부
    cmmnCntrctYn: Optional[str]                     # 공동계약여부
    cmmnReciptMethdNm: Optional[str]                # 공동수급방식명
    elctrnBidYn: Optional[str]                      # 전자입찰여부
    cntrctCnclsSttusNm: Optional[str]               # 계약체결형태명
    cntrctCnclsMthdNm: Optional[str]                # 계약체결방법명
    bidwinrDcsnMthdNm: Optional[str]                # 낙찰자결정방법명
    ntceInsttNm: Optional[str]                      # 공고기관명
    ntceInsttCd: Optional[str]                      # 공고기관코드
    ntceInsttOfclDeptNm: Optional[str]              # 공고기관담당자부서명
    ntceInsttOfclNm: Optional[str]                  # 공고기관담당자명
    ntceInsttOfclTel: Optional[str]                 # 공고기관담당자전화번호
    ntceInsttOfclEmailAdrs: Optional[str]           # 공고기관담당자이메일주소
    dmndInsttNm: Optional[str]                      # 수요기관명
    dmndInsttCd: Optional[str]                      # 수요기관코드
    dmndInsttOfclDeptNm: Optional[str]              # 수요기관담당자부서명
    dmndInsttOfclNm: Optional[str]                  # 수요기관담당자명
    dmndInsttOfclTel: Optional[str]                 # 수요기관담당자전화번호
    dmndInsttOfclEmailAdrs: Optional[str]           # 수요기관담당자이메일주소
    presnatnOprtnYn: Optional[str]                  # 설명회실시여부
    presnatnOprtnDate: Optional[datetime]           # 설명회실시일자
    presnatnOprtnTm: Optional[str]                  # 설명회실시시각
    presnatnOprtnPlce: Optional[str]                # 설명회실시장소
    bidPrtcptQlfctRgstClseDate: Optional[datetime]  # 입찰참가자격등록마감일자
    bidPrtcptQlfctRgstClseTm: Optional[str]         # 입찰참가자격등록마감시각
    cmmnReciptAgrmntClseDate: Optional[datetime]    # 공동수급협정마감일자
    cmmnReciptAgrmntClseTm: Optional[str]           # 공동수급협정마감시각
    bidBeginDate: Optional[datetime]                # 입찰개시일자
    bidBeginTm: Optional[str]                       # 입찰개시시각
    bidClseDate: Optional[datetime]                 # 입찰마감일자
    bidClseTm: Optional[str]                        # 입찰마감시각
    opengDate: Optional[datetime]                   # 개찰일자
    opengTm: Optional[str]                          # 개찰시각
    opengPlce: Optional[str]                        # 개찰장소
    asignBdgtAmt: Optional[str]                     # 배정예산금액(설계금액)
    presmptPrce: Optional[str]                      # 추정가격
    rsrvtnPrceDcsnMthdNm: Optional[str]             # 예정가격결정방법명
    rgnLmtYn: Optional[str]                         # 지역제한여부
    prtcptPsblRgnNm: Optional[str]                  # 참가가능지역명
    indstrytyLmtYn: Optional[str]                   # 업종제한여부
    bidprcPsblIndstrytyNm: Optional[str]            # 투찰가능업종명
    bidNtceUrl: Optional[str]                       # 입찰공고URL
    dataBssDate: Optional[datetime]                 # 데이터기준일자

    @model_validator(mode="before")
    @classmethod
    def convert_empty_dt_strings_to_none(cls, data):
        if isinstance(data, dict):
            for key in list(data.keys()):
                if (key.endswith("Date") or key.endswith("Dt")) and data[key] == "":
                    data[key] = None
        return data

# 공통 베이스 클래스 사용
class DataSetOpnStdBidPblancInfoResBody(BaseAPIResponseBody[DataSetOpnStdBidPblancInfoResItem]):
    pass

class DataSetOpnStdBidPblancInfoResHeader(BaseAPIResponseHeader):
    pass

class DataSetOpnStdBidPblancInfoRes(BaseAPIResponse[DataSetOpnStdBidPblancInfoResItem]):
    pass

class DataSetOpnStdBidPblancInfoAPIRes(BaseAPIResponseWrapper[DataSetOpnStdBidPblancInfoResItem]):
    pass
