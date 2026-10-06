from datetime import datetime
from pydantic import BaseModel, Field, model_validator
from typing_extensions import Literal, Optional, List
from src.schemas.common_dto import BaseAPIRequest, BaseAPIResponseHeader, BaseAPIResponseBody, BaseAPIResponse, BaseAPIResponseWrapper

# 성공입찰 목록 현황 정보 DTO

# 요청 DTO
class ScsbidListSttusReq(BaseAPIRequest):
    """
    성공입찰 목록 현황 정보 조회 요청 DTO
    
    조회구분(inqryDiv)에 따른 필수 파라미터:
    - 1 (등록일시): inqryBgnDt, inqryEndDt 필수
    - 2 (입찰공고번호): bidNtceNo 필수  
    - 3 (변경일시): inqryBgnDt, inqryEndDt 필수
    """
    inqryDiv: int = Field(description="조회구분 (1:등록일시, 2:입찰공고번호, 3:변경일시)", examples=[1])
    inqryBgnDt: Optional[str] = Field(default=None, description="조회시작일시 (조회구분 1,3일 때 필수)", examples=["202001010000"])
    inqryEndDt: Optional[str] = Field(default=None, description="조회종료일시 (조회구분 1,3일 때 필수)", examples=["202001312359"])
    bidNtceNo: Optional[str] = Field(default=None, description="입찰공고번호 (조회구분 2일 때 필수)", examples=["20160403605"])

class ScsbidListSttusResItem(BaseModel):
    bidNtceNo: str                   # 입찰공고번호
    bidNtceOrd: Optional[str]        # 입찰공고차수
    bidClsfcNo: Optional[str]        # 입찰분류번호
    rbidNo: Optional[str]            # 재입찰번호
    ntceDivCd: Optional[str]         # 공고구분코드
    bidNtceNm: Optional[str]         # 입찰공고명
    prtcptCnum: Optional[str]        # 참가업체수
    bidwinnrNm: Optional[str]        # 최종낙찰업체명
    bidwinnrBizno: Optional[str]     # 최종낙찰업체사업자등록번호
    bidwinnrCeoNm: Optional[str]     # 최종낙찰업체대표자명
    bidwinnrAdrs: Optional[str]      # 최종낙찰업체주소
    bidwinnrTelNo: Optional[str]     # 최종낙찰업체전화번호
    sucsfbidAmt: Optional[str]       # 최종낙찰금액
    sucsfbidRate: Optional[str]      # 최종낙찰률
    rlOpengDt: Optional[datetime]    # 실개찰일시
    dminsttCd: Optional[str]         # 수요기관코드
    dminsttNm: Optional[str]         # 수요기관명
    rgstDt: Optional[datetime]       # 등록일시
    fnlSucsfDate: Optional[str]      # 최종낙찰일자
    fnlSucsfCorpOfcl: Optional[str]  # 최종낙찰업체담당자

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
class ScsbidListSttusResBody(BaseAPIResponseBody[ScsbidListSttusResItem]):
    pass

class ScsbidListSttusResHeader(BaseAPIResponseHeader):
    pass

class ScsbidListSttusRes(BaseAPIResponse[ScsbidListSttusResItem]):
    pass

class ScsbidListSttusAPIRes(BaseAPIResponseWrapper[ScsbidListSttusResItem]):
    pass
