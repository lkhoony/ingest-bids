from datetime import datetime
from pydantic import BaseModel, Field, field_validator, validator
from typing_extensions import Literal, Optional, List
from src.schemas.common_dto import BaseAPIRequest, BaseAPIResponseHeader, BaseAPIResponseBody, BaseAPIResponse, BaseAPIResponseWrapper

# 나라장터 업종 및 근거법규 서비스 DTO

# 요청 DTO
class IndstrytyBaseLawrgltInfoReq(BaseAPIRequest):
    inqryBgnDt: Optional[str] = Field(default=None, description="조회시작일시", examples=["202401010000"])
    inqryEndDt: Optional[str] = Field(default=None, description="조회종료일시", examples=["202401312359"])
    indstrytyClsfcCd: Optional[str] = Field(default=None, description="업종분류코드")
    indstrytyNm: Optional[str] = Field(default=None, description="업종명")
    indstrytyCd: Optional[str] = Field(default=None, description="업종코드")
    indstrytyUseYn: Optional[Literal["Y", "N"]] = Field(default=None, description="업종사용여부")

class IndstrytyBaseLawrgltInfoResItem(BaseModel):
    indstrytyClsfcCd: Optional[str]         # 업종분류코드
    indstrytyClsfcNm: Optional[str]         # 업종분류명
    indstrytyCd: Optional[str]              # 업종코드
    indstrytyNm: Optional[str]              # 업종명
    baseLawordNm: Optional[str]             # 근거법령명
    baseLawordArtclClauseNm: Optional[str]  # 근거법령조항명
    baseLawordUrl: Optional[str]            # 근거법령URL
    rltnRgltCntnts: Optional[str]           # 관련규정내용
    inclsnLcns: Optional[str]               # 포함면허 (예: "[0002^건축공사업],[0003^토목건축공사업]")
    indstrytyUseYn: Optional[str]           # 업종사용여부
    indstrytyRgstDt: Optional[datetime]     # 업종등록일시
    indstrytyChgDt: Optional[datetime]      # 업종변경일시

# 공통 베이스 클래스 사용
class IndstrytyBaseLawrgltInfoResBody(BaseAPIResponseBody[IndstrytyBaseLawrgltInfoResItem]):
    pass

class IndstrytyBaseLawrgltInfoResHeader(BaseAPIResponseHeader):
    pass

class IndstrytyBaseLawrgltInfoRes(BaseAPIResponse[IndstrytyBaseLawrgltInfoResItem]):
    pass

class IndstrytyBaseLawrgltInfoAPIRes(BaseAPIResponseWrapper[IndstrytyBaseLawrgltInfoResItem]):
    pass
