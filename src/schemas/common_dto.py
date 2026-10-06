"""나라장터 Open API 공통 요청/응답 모델 (IPCHAL app/schemas/common_dto.py 복사본).

모든 API 응답(JSON)은 아래 구조를 가진다. 각 API의 *_service_dto.py는 이 제네릭 모델에
자기 ResItem 타입을 넣어서 `XxxAPIRes(BaseAPIResponseWrapper[XxxResItem])`를 정의한다.

    {
      "response": {                         ← BaseAPIResponseWrapper.response
        "header": {"resultCode": "00",      ← BaseAPIResponseHeader ("00" = 정상)
                   "resultMsg": "NORMAL SERVICE."},
        "body": {                           ← BaseAPIResponseBody[T]
          "items": [ {...}, {...} ],        ← List[T] (T = 각 API의 ResItem)
          "numOfRows": 999, "pageNo": 1, "totalCount": 1584
        }
      }
    }

각 *_service_dto.py 의 ResItem 필드 주석은 조달청 OpenAPI 참고자료(Desktop/입찰 API 명세서)의
해당 오퍼레이션 응답 항목 "국문 항목명"이다. 명세서에 없는 필드는 "(명세서 미기재 — IPCHAL 주석)"으로 표시했다.

IPCHAL 원본과 다른 점:ServiceKey 기본값이 IPCHAL settings에 의존하던 것을 빈 문자열로 바꿨다.
(이 프로젝트는 요청 파라미터를 src/sources.py에서 dict로 직접 만들고, 요청 모델은 쓰지 않는다.)
"""

from pydantic import BaseModel, Field
from typing_extensions import Literal, Optional, List, TypeVar, Generic


class BaseAPIRequest(BaseModel):
    """공통 요청 파라미터 (각 API의 XxxReq가 상속). 이 프로젝트에서는 참고용이다."""

    ServiceKey: str = Field(default="", description="서비스키")
    pageNo: int = Field(default=1, description="페이지 번호")
    numOfRows: int = Field(default=100, description="한 페이지 결과 수")
    type: Literal["json", "xml"] = Field(default="json", description="응답 데이터 타입")


class BaseAPIResponseHeader(BaseModel):
    """응답 헤더.

    Attributes:
        resultCode (str): 결과 코드. "00"이면 정상. 그 외(예: 키 오류, 호출 한도 초과)는
            HTTP 200이어도 실패다. client.py가 이 값을 검사한다.
        resultMsg (str): 결과 메시지.
    """

    resultCode: str
    resultMsg: str


# 응답 아이템 타입 변수 (각 API의 ResItem 모델이 들어간다)
T = TypeVar('T')


class BaseAPIResponseBody(BaseModel, Generic[T]):
    """응답 바디 (페이지 단위).

    Attributes:
        items (List[T]): 이 페이지의 데이터 행 목록.
        numOfRows (int): 페이지당 행 수.
        pageNo (int): 현재 페이지 번호.
        totalCount (int): 조회 조건에 맞는 전체 행 수. 전체 페이지 수 계산에 쓴다.
    """

    items: List[T] = Field(default_factory=list)
    numOfRows: int
    pageNo: int
    totalCount: int


class BaseAPIResponse(BaseModel, Generic[T]):
    """response 객체: header + body."""

    header: BaseAPIResponseHeader
    body: BaseAPIResponseBody[T]


class BaseAPIResponseWrapper(BaseModel, Generic[T]):
    """응답 JSON 최상위 객체. client.fetch_all의 response_model로 이 하위 클래스를 넘긴다."""

    response: BaseAPIResponse[T]
