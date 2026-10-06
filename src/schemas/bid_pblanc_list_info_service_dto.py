from datetime import datetime
from pydantic import BaseModel, Field, model_validator
from typing_extensions import Optional
from src.schemas.common_dto import BaseAPIRequest, BaseAPIResponseHeader, BaseAPIResponseBody, BaseAPIResponse, BaseAPIResponseWrapper

# 입찰 공고 목록 정보 DTO
# 용역에 대해서만 조회

# 요청 DTO
class BidPblancListInfoReq(BaseAPIRequest):
    """
    입찰 공고 목록 정보 조회 요청 DTO
    
    조회구분(inqryDiv)에 따른 필수 파라미터:
    - 1 (등록일시): inqryBgnDt, inqryEndDt 필수
    - 2 (입찰공고번호): bidNtceNo 필수  
    - 3 (변경일시): inqryBgnDt, inqryEndDt 필수
    """
    inqryDiv: int = Field(description="조회구분 (1:등록일시, 2:입찰공고번호, 3:변경일시)", examples=[1])
    inqryBgnDt: Optional[str] = Field(default=None, description="조회시작일시 (조회구분 1,3일 때 필수)", examples=["202001010000"])
    inqryEndDt: Optional[str] = Field(default=None, description="조회종료일시 (조회구분 1,3일 때 필수)", examples=["202001312359"])
    bidNtceNo: Optional[str] = Field(default=None, description="입찰공고번호 (조회구분 2일 때 필수)", examples=["20200123183"])


class BidPblancListInfoResItem(BaseModel):
    bidNtceNo: str                               # 입찰공고번호
    bidNtceOrd: Optional[str]                    # 입찰공고차수
    reNtceYn: Optional[str]                      # 재공고여부
    rgstTyNm: Optional[str]                      # 등록유형명
    ntceKindNm: Optional[str]                    # 공고종류명
    intrbidYn: Optional[str]                     # 국제입찰여부
    bidNtceDt: Optional[datetime]                # 입찰공고일시
    refNo: Optional[str]                         # 참조번호
    bidNtceNm: Optional[str]                     # 입찰공고명
    ntceInsttCd: Optional[str]                   # 공고기관코드
    ntceInsttNm: Optional[str]                   # 공고기관명
    dminsttCd: Optional[str]                     # 수요기관코드
    dminsttNm: Optional[str]                     # 수요기관명
    bidMethdNm: Optional[str]                    # 입찰방식명
    cntrctCnclsMthdNm: Optional[str]             # 계약체결방법명
    ntceInsttOfclNm: Optional[str]               # 공고기관담당자명
    ntceInsttOfclTelNo: Optional[str]            # 공고기관담당자전화번호
    ntceInsttOfclEmailAdrs: Optional[str]        # 공고기관담당자이메일주소
    exctvNm: Optional[str]                       # 집행관명
    bidQlfctRgstDt: Optional[datetime]           # 입찰참가자격등록마감일시
    cmmnSpldmdAgrmntRcptdocMethd: Optional[str]  # 공동수급협정서접수방식
    cmmnSpldmdAgrmntClseDt: Optional[datetime]   # 공동수급협정마감일시
    cmmnSpldmdCorpRgnLmtYn: Optional[str]        # 공동수급업체지역제한여부
    bidBeginDt: Optional[datetime]               # 입찰개시일시
    bidClseDt: Optional[datetime]                # 입찰마감일시
    opengDt: Optional[datetime]                  # 개찰일시
    ntceSpecDocUrl1: Optional[str]               # 공고규격서URL1
    ntceSpecDocUrl2: Optional[str]               # 공고규격서URL2
    ntceSpecDocUrl3: Optional[str]               # 공고규격서URL3
    ntceSpecDocUrl4: Optional[str]               # 공고규격서URL4
    ntceSpecDocUrl5: Optional[str]               # 공고규격서URL5
    ntceSpecDocUrl6: Optional[str]               # 공고규격서URL6
    ntceSpecDocUrl7: Optional[str]               # 공고규격서URL7
    ntceSpecDocUrl8: Optional[str]               # 공고규격서URL8
    ntceSpecDocUrl9: Optional[str]               # 공고규격서URL9
    ntceSpecDocUrl10: Optional[str]              # 공고규격서URL10
    ntceSpecFileNm1: Optional[str]               # 공고규격파일명1
    ntceSpecFileNm2: Optional[str]               # 공고규격파일명2
    ntceSpecFileNm3: Optional[str]               # 공고규격파일명3
    ntceSpecFileNm4: Optional[str]               # 공고규격파일명4
    ntceSpecFileNm5: Optional[str]               # 공고규격파일명5
    ntceSpecFileNm6: Optional[str]               # 공고규격파일명6
    ntceSpecFileNm7: Optional[str]               # 공고규격파일명7
    ntceSpecFileNm8: Optional[str]               # 공고규격파일명8
    ntceSpecFileNm9: Optional[str]               # 공고규격파일명9
    ntceSpecFileNm10: Optional[str]              # 공고규격파일명10
    rbidPermsnYn: Optional[str]                  # 재입찰허용여부
    pqApplDocRcptMthdNm: Optional[str]           # PQ신청서접수방법명
    pqApplDocRcptDt: Optional[datetime]          # PQ신청서접수일시
    tpEvalApplMthdNm: Optional[str]              # TP심사신청방법명
    tpEvalApplClseDt: Optional[datetime]         # TP심사신청마감일시
    jntcontrctDutyRgnNm1: Optional[str]          # 공동도급의무지역명1
    jntcontrctDutyRgnNm2: Optional[str]          # 공동도급의무지역명2
    jntcontrctDutyRgnNm3: Optional[str]          # 공동도급의무지역명3
    rgnDutyJntcontrctRt: Optional[str]           # 지역의무공동도급비율
    dtlsBidYn: Optional[str]                     # 내역입찰여부
    bidPrtcptLmtYn: Optional[str]                # 입찰참가제한여부
    prearngPrceDcsnMthdNm: Optional[str]         # 예정가격결정방법명
    totPrdprcNum: Optional[str]                  # 총예가건수
    drwtPrdprcNum: Optional[str]                 # 추첨예가건수
    asignBdgtAmt: Optional[str]                  # 배정예산금액
    presmptPrce: Optional[str]                   # 추정가격
    opengPlce: Optional[str]                     # 개찰장소
    dcmtgOprtnDt: Optional[datetime]             # 설명회실시일시
    dcmtgOprtnPlce: Optional[str]                # 설명회실시장소
    bidNtceDtlUrl: Optional[str]                 # 입찰공고상세URL
    bidNtceUrl: Optional[str]                    # 입찰공고URL
    bidPrtcptFeePaymntYn: Optional[str]          # 입찰참가수수료납부여부
    bidPrtcptFee: Optional[str]                  # 입찰참가수수료
    bidGrntymnyPaymntYn: Optional[str]           # 입찰보증금납부여부
    crdtrNm: Optional[str]                       # 채권자명
    ppswGnrlSrvceYn: Optional[str]               # 조달청일반용역여부
    srvceDivNm: Optional[str]                    # 용역구분명
    prdctClsfcLmtYn: Optional[str]               # 물품분류제한여부
    mnfctYn: Optional[str]                       # 제조여부
    purchsObjPrdctList: Optional[str]            # 구매대상물품목록
    untyNtceNo: Optional[str]                    # 통합공고번호
    cmmnSpldmdMethdCd: Optional[str]             # 공동수급방식코드
    cmmnSpldmdMethdNm: Optional[str]             # 공동수급방식명
    stdNtceDocUrl: Optional[str]                 # 표준공고서URL
    brffcBidprcPermsnYn: Optional[str]           # 지사투찰허용여부
    dsgntCmptYn: Optional[str]                   # 지명경쟁여부
    arsltCmptYn: Optional[str]                   # 실적경쟁여부
    pqEvalYn: Optional[str]                      # PQ심사여부
    tpEvalYn: Optional[str]                      # TP심사여부
    ntceDscrptYn: Optional[str]                  # 공고설명여부
    rsrvtnPrceReMkngMthdNm: Optional[str]        # 예비가격재작성방법명
    arsltApplDocRcptMthdNm: Optional[str]        # 실적신청서접수방법명
    arsltReqstdocRcptDt: Optional[datetime]      # 실적신청서접수일시
    orderPlanUntyNo: Optional[str]               # 발주계획통합번호
    sucsfbidLwltRate: Optional[str]              # 낙찰하한율
    rgstDt: Optional[datetime]                   # 등록일시
    bfSpecRgstNo: Optional[str]                  # 사전규격등록번호
    infoBizYn: Optional[str]                     # 정보화사업여부
    sucsfbidMthdCd: Optional[str]                # 낙찰방법코드
    sucsfbidMthdNm: Optional[str]                # 낙찰방법명
    chgDt: Optional[datetime]                    # 변경일시
    dminsttOfclEmailAdrs: Optional[str]          # 수요기관담당자이메일주소
    indstrytyLmtYn: Optional[str]                # 업종제한여부
    chgNtceRsn: Optional[str]                    # 변경공고사유
    rbidOpengDt: Optional[datetime]              # 재입찰개찰일시
    VAT: Optional[str]                           # 부가가치세
    indutyVAT: Optional[str]                     # 주공종부가가치세
    rgnLmtBidLocplcJdgmBssCd: Optional[str]      # 지역제한입찰장소판단기준코드 (명세서 미기재 — IPCHAL 주석)
    rgnLmtBidLocplcJdgmBssNm: Optional[str]      # 지역제한입찰장소판단기준명 (명세서 미기재 — IPCHAL 주석)
    pubPrcrmntLrgClsfcNm: Optional[str]          # 공공조달대분류명
    pubPrcrmntMidClsfcNm: Optional[str]          # 공공조달중분류명
    pubPrcrmntClsfcNo: Optional[str]             # 공공조달분류번호
    pubPrcrmntClsfcNm: Optional[str]             # 공공조달분류명
    
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
class BidPblancListInfoResBody(BaseAPIResponseBody[BidPblancListInfoResItem]):
    pass

class BidPblancListInfoResHeader(BaseAPIResponseHeader):
    pass

class BidPblancListInfoRes(BaseAPIResponse[BidPblancListInfoResItem]):
    pass

class BidPblancListInfoAPIRes(BaseAPIResponseWrapper[BidPblancListInfoResItem]):
    pass
