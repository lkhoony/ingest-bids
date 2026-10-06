"""나라장터 Open API 페이지네이션 클라이언트.

IPCHAL app/utils/pagination_helper.py 를 옮겨왔다. 동작 순서:
  1. 1페이지를 요청해 totalCount(전체 건수)와 numOfRows(페이지당 건수)를 확인한다.
  2. 남은 페이지(2 ~ 마지막)를 concurrency 개씩 동시에 요청한다.
  3. 각 페이지는 실패하면 지수 백오프(0.8초, 1.6초, ...)로 재시도한다.
  4. 응답 header.resultCode가 "00"이 아니면 오류로 본다.
     공공데이터 API는 키 오류, 호출 한도 초과 같은 상황에도 HTTP 200을 주기 때문이다.

추가로, httpx 예외 메시지에는 요청 URL(ServiceKey 포함)이 들어 있으므로
그대로 로그에 남지 않도록 키를 "***"로 가린 OpenApiError로 바꿔서 올린다.
"""

import asyncio
import logging
from math import ceil
from typing import Any
from urllib.parse import quote, quote_plus

import httpx
from pydantic import BaseModel

logger = logging.getLogger(__name__)

# 무한 루프 방지용 안전장치. totalCount가 비정상적으로 커도 이 이상은 요청하지 않는다.
MAX_PAGES = 10_000


class OpenApiError(RuntimeError):
    """Open API 호출 실패 (HTTP 오류, resultCode 오류, 응답 형식 오류 등).

    메시지에는 서비스 키가 가려진 상태로 들어간다.
    """


def _mask(message: str, api_key: str) -> str:
    """문자열 안의 서비스 키를 "***"로 가린다.

    키가 URL 안에서 인코딩된 형태(quote / quote_plus)로 들어갈 수도 있으므로
    원본과 인코딩된 형태를 모두 치환한다.

    Args:
        message (str): 원본 메시지 (예: 예외 메시지).
        api_key (str): 가릴 서비스 키. 빈 문자열이면 아무것도 바꾸지 않는다.

    Returns:
        str: 키가 "***"로 치환된 메시지.
    """
    for secret in {api_key, quote(api_key, safe=""), quote_plus(api_key)}:
        if secret:
            message = message.replace(secret, "***")
    return message


def _normalize_items(payload: Any) -> Any:
    """응답 JSON의 response.body.items 를 항상 리스트로 맞춘다.

    공공데이터 API는 상황에 따라 items를 여러 형태로 돌려준다.
      - 결과 없음: "" 또는 null
      - XML 변환형: {"item": [...]} 또는 단건일 때 {"item": {...}}
    Pydantic 모델(items: List[T])로 검증하기 전에 리스트 형태로 통일한다.
    payload는 제자리(in-place)에서 수정된다.

    Args:
        payload (Any): res.json() 결과. 보통 dict.

    Returns:
        Any: 같은 payload 객체 (items가 list로 정리된 상태).
    """
    body = payload.get("response", {}).get("body") if isinstance(payload, dict) else None
    if isinstance(body, dict):
        items = body.get("items")
        if isinstance(items, dict):
            items = items.get("item", [])
        if isinstance(items, dict):
            items = [items]
        body["items"] = items or []
    return payload


async def _fetch_page(
    client: httpx.AsyncClient,
    url: str,
    params: dict[str, Any],
    page_no: int,
    response_model: type[BaseModel],
    retries: int,
    backoff: float,
) -> tuple[list[Any], int, int]:
    """한 페이지를 요청하고 검증한다. 실패하면 재시도한다.

    Args:
        client (httpx.AsyncClient): 연결을 재사용할 비동기 HTTP 클라이언트.
        url (str): API 요청 URL.
        params (dict[str, Any]): 쿼리 파라미터 (pageNo 제외). ServiceKey가 들어 있어야 한다.
        page_no (int): 요청할 페이지 번호 (1부터 시작).
        response_model (type[BaseModel]): 응답 전체를 검증할 Pydantic 모델 클래스.
        retries (int): 최대 시도 횟수 (첫 시도 포함).
        backoff (float): 재시도 대기 기본 시간(초). n번째 재시도 전에 backoff * 2^(n-1)초 기다린다.

    Returns:
        tuple[list[Any], int, int]: (items, numOfRows, totalCount)
            - items: 이 페이지의 ResItem 모델 객체 리스트
            - numOfRows: 페이지당 건수 (응답 기준)
            - totalCount: 조건에 맞는 전체 건수

    Raises:
        OpenApiError: retries 번 모두 실패했을 때. 원인 예외는 연결하지 않는다(from None).
            원인 예외의 메시지에 서비스 키가 들어 있을 수 있기 때문이다.
    """
    api_key = str(params.get("ServiceKey", ""))
    for attempt in range(1, retries + 1):
        try:
            res = await client.get(url, params={**params, "pageNo": page_no})
            res.raise_for_status()  # 4xx/5xx → httpx.HTTPStatusError
            data = response_model.model_validate(_normalize_items(res.json()))
            header = data.response.header
            if header.resultCode != "00":
                raise OpenApiError(f"API 오류 resultCode={header.resultCode}: {header.resultMsg}")
            body = data.response.body
            return list(body.items or []), body.numOfRows, body.totalCount
        except Exception as e:
            if attempt >= retries:
                raise OpenApiError(
                    f"page={page_no} 요청 실패 ({attempt}회 시도): {type(e).__name__}: {_mask(str(e), api_key)}"
                ) from None
            await asyncio.sleep(backoff * (2 ** (attempt - 1)))
    raise AssertionError("unreachable")


async def fetch_all(
    url: str,
    params: dict[str, Any],
    response_model: type[BaseModel],
    *,
    concurrency: int = 3,
    timeout: float = 60.0,
    retries: int = 3,
    backoff: float = 0.8,
    transport: httpx.AsyncBaseTransport | None = None,
) -> list[Any]:
    """조건에 맞는 모든 페이지를 수집해 하나의 리스트로 반환한다.

    1페이지로 전체 건수를 확인한 뒤, 나머지 페이지를 동시에 요청한다.
    결과는 페이지 순서대로 이어 붙인다. 한 페이지라도 끝내 실패하면 전체가 실패한다.
    일부만 저장되는 것을 막기 위해서다.

    Args:
        url (str): API 요청 URL.
        params (dict[str, Any]): 쿼리 파라미터 (pageNo 제외). sources.base_params()의 결과.
        response_model (type[BaseModel]): 응답 전체를 검증할 Pydantic 모델 클래스.
        concurrency (int): 동시에 요청할 최대 페이지 수. 기본 3 (노트북과 동일).
        timeout (float): 요청당 타임아웃(초). 연결 타임아웃은 10초로 따로 둔다.
        retries (int): 페이지당 최대 시도 횟수.
        backoff (float): 재시도 대기 기본 시간(초).
        transport (httpx.AsyncBaseTransport | None): 테스트에서 가짜 응답을 넣을 때 쓴다.
            운영에서는 None(실제 네트워크).

    Returns:
        list[Any]: 모든 페이지의 ResItem 모델 객체 리스트. 결과가 없으면 빈 리스트.

    Raises:
        OpenApiError: 어느 페이지든 재시도 끝에 실패했을 때.
    """
    async with httpx.AsyncClient(
        timeout=httpx.Timeout(timeout, connect=10.0),
        limits=httpx.Limits(max_connections=20, max_keepalive_connections=10),
        transport=transport,
    ) as client:
        # 1) 첫 페이지로 전체 건수 파악
        items, num_of_rows, total_count = await _fetch_page(
            client, url, params, 1, response_model, retries, backoff
        )
        results = list(items)
        if num_of_rows <= 0 or total_count <= len(items):
            return results  # 한 페이지로 끝나는 경우

        # 2) 남은 페이지를 동시에 요청 (Semaphore로 동시 요청 수 제한)
        total_pages = min(ceil(total_count / num_of_rows), MAX_PAGES)
        logger.info("paginating", extra={"total_count": total_count, "total_pages": total_pages})
        sem = asyncio.Semaphore(concurrency)

        async def _task(page_no: int) -> list[Any]:
            """동시 요청 수 제한 안에서 한 페이지를 가져와 items만 반환한다."""
            async with sem:
                page_items, *_ = await _fetch_page(
                    client, url, params, page_no, response_model, retries, backoff
                )
                return page_items

        # gather는 페이지 순서를 유지하고, 하나라도 실패하면 예외를 올린다
        pages = await asyncio.gather(*(_task(p) for p in range(2, total_pages + 1)))
        for page_items in pages:
            results.extend(page_items)
        return results
