import asyncio
import json
from datetime import date, datetime
from unittest.mock import MagicMock
from zoneinfo import ZoneInfo

import httpx
import pandas as pd
import pytest
from google.api_core.exceptions import NotFound
from google.cloud import bigquery

from src import main as main_mod
from src.client import OpenApiError, fetch_all
from src.config import Config
from src.loader import INGEST_DATE, BigQueryLoader, to_dataframe
from src.schemas.scsbid_list_sttus_service_dto import ScsbidListSttusAPIRes, ScsbidListSttusResItem
from src.sources import SOURCES, SOURCES_BY_NAME, base_params

D = date(2026, 10, 3)
SECRET = "abc+/=SECRET"


def scsbid_item(no: str, **kw) -> dict:
    fields = {k: None for k in ScsbidListSttusResItem.model_fields}
    return {**fields, "bidNtceNo": no, "rgstDt": "2026-10-03 10:00:00", **kw}


def api_page(items, total, rows=2, code="00"):
    return {"response": {"header": {"resultCode": code, "resultMsg": "NORMAL SERVICE."},
                         "body": {"items": items, "numOfRows": rows, "pageNo": 1, "totalCount": total}}}


def mock_transport(handler):
    return httpx.MockTransport(handler)


def run_fetch(handler, **kw):
    params = {"ServiceKey": SECRET, "numOfRows": 2, "type": "json"}
    return asyncio.run(fetch_all("https://api.test/x", params, ScsbidListSttusAPIRes,
                                 transport=mock_transport(handler), backoff=0, **kw))


# ---------- 날짜 ----------

def test_target_date_defaults_to_yesterday_in_kst():
    # UTC 2026-10-03 16:00 == KST 2026-10-04 01:00 → 어제는 10-03
    now = datetime(2026, 10, 3, 16, 0, tzinfo=ZoneInfo("UTC"))
    assert main_mod.resolve_target_date(None, now) == D


def test_target_date_override():
    assert main_mod.resolve_target_date("2026-09-01") == date(2026, 9, 1)


# ---------- 소스별 파라미터 ----------

def test_all_six_sources_registered_with_unique_tables():
    assert len(SOURCES) == 6
    assert len({s.table for s in SOURCES}) == 6


@pytest.mark.parametrize("name, expected", [
    ("bid_pblanc_list_info", {"inqryDiv": 1, "inqryBgnDt": "202610030000", "inqryEndDt": "202610032359"}),
    ("bid_pblanc_bsis_amount_list_info", {"inqryDiv": 1, "inqryBgnDt": "202610030000", "inqryEndDt": "202610032359"}),
    ("scsbid_list_sttus", {"inqryDiv": 1, "inqryBgnDt": "202610030000", "inqryEndDt": "202610032359"}),
    ("data_set_opn_std_bid_pblanc_info", {"bidNtceBgnDt": "202610030000", "bidNtceEndDt": "202610032359"}),
    ("data_set_opn_std_scsbid_info", {"bsnsDivCd": 5, "opengBgnDt": "202610030000", "opengEndDt": "202610032359"}),
    ("indstryty_base_lawrglt_info", {}),
])
def test_source_params(name, expected):
    params = base_params(SOURCES_BY_NAME[name], D, "KEY")
    assert params == {"ServiceKey": "KEY", "numOfRows": 999, "type": "json", **expected}


# ---------- API 클라이언트 ----------

def test_fetch_all_paginates_in_page_order():
    pages = {1: [scsbid_item("1"), scsbid_item("2")], 2: [scsbid_item("3"), scsbid_item("4")], 3: [scsbid_item("5")]}

    def handler(request):
        p = int(request.url.params["pageNo"])
        return httpx.Response(200, json=api_page(pages[p], total=5))

    items = run_fetch(handler)
    assert [i.bidNtceNo for i in items] == ["1", "2", "3", "4", "5"]


@pytest.mark.parametrize("items", ["", None, {"item": []}])
def test_fetch_all_empty_items_shapes(items):
    assert run_fetch(lambda r: httpx.Response(200, json=api_page(items, total=0))) == []


def test_fetch_all_single_item_dict_shape():
    items = run_fetch(lambda r: httpx.Response(200, json=api_page({"item": scsbid_item("9")}, total=1)))
    assert [i.bidNtceNo for i in items] == ["9"]


def test_result_code_error_raises_even_with_http_200():
    with pytest.raises(OpenApiError, match="resultCode=22"):
        run_fetch(lambda r: httpx.Response(200, json=api_page([], total=0, code="22")))


def test_transient_error_is_retried():
    calls = {"n": 0}

    def handler(request):
        calls["n"] += 1
        if calls["n"] == 1:
            return httpx.Response(503)
        return httpx.Response(200, json=api_page([scsbid_item("1")], total=1))

    assert len(run_fetch(handler)) == 1
    assert calls["n"] == 2


def test_error_message_does_not_leak_service_key():
    with pytest.raises(OpenApiError) as exc_info:
        run_fetch(lambda r: httpx.Response(500), retries=2)
    message = str(exc_info.value)
    assert "SECRET" not in message
    assert exc_info.value.__cause__ is None and exc_info.value.__suppress_context__


# ---------- DataFrame 변환 ----------

def test_to_dataframe_matches_notebook_conversion():
    item = ScsbidListSttusResItem.model_validate(scsbid_item("1", fnlSucsfDate="2026-10-03", bidwinnrNm="주식회사"))
    df = to_dataframe([item], D)
    assert pd.api.types.is_datetime64_any_dtype(df["rgstDt"])
    assert pd.api.types.is_datetime64_any_dtype(df["fnlSucsfDate"])  # 노트북처럼 *Date 문자열도 datetime
    assert df.loc[0, "bidwinnrNm"] == "주식회사"
    assert df.loc[0, INGEST_DATE] == D


# ---------- BigQuery 적재 ----------

def make_loader(existing_schema=None):
    client = MagicMock(spec=bigquery.Client)
    client.project = "proj"
    if existing_schema is None:
        client.get_table.side_effect = NotFound("missing")
    else:
        table = bigquery.Table("proj.ds.t", schema=existing_schema)
        client.get_table.return_value = table
        client.update_table.side_effect = lambda t, fields: t
    client.load_table_from_dataframe.return_value.output_rows = 1
    return BigQueryLoader("ds", client=client), client


def sample_df():
    return to_dataframe([ScsbidListSttusResItem.model_validate(scsbid_item("1"))], D)


def test_replace_day_adds_column_deletes_then_appends_with_existing_schema():
    loader, client = make_loader([bigquery.SchemaField("bidNtceNo", "STRING")])
    calls = MagicMock()
    client.query.side_effect = lambda *a, **k: calls.query(*a, **k)
    client.load_table_from_dataframe.side_effect = lambda *a, **k: calls.load(*a, **k)
    calls.load.return_value.output_rows = 1

    assert loader.replace_day("t", sample_df(), D) == 1

    # ingest_date 컬럼 추가
    client.update_table.assert_called_once()
    # DELETE → LOAD 순서
    assert [c[0] for c in calls.mock_calls if c[0] in ("query", "load")] == ["query", "load"]
    sql = calls.query.call_args.args[0]
    assert sql == "DELETE FROM `proj.ds.t` WHERE ingest_date = @d"
    param = calls.query.call_args.kwargs["job_config"].query_parameters[0]
    assert (param.name, param.type_, param.value) == ("d", "DATE", D)
    job_config = calls.load.call_args.kwargs["job_config"]
    assert job_config.write_disposition == "WRITE_APPEND"
    assert [f.name for f in job_config.schema] == ["bidNtceNo", "ingest_date"]


def test_replace_day_on_missing_table_autodetects_without_delete():
    loader, client = make_loader(None)
    loader.replace_day("t", sample_df(), D)
    client.query.assert_not_called()
    assert client.load_table_from_dataframe.call_args.kwargs["job_config"].autodetect is True


def test_replace_day_with_no_items_still_clears_the_day():
    loader, client = make_loader([bigquery.SchemaField("bidNtceNo", "STRING"), bigquery.SchemaField("ingest_date", "DATE")])
    assert loader.replace_day("t", pd.DataFrame(), D) == 0
    client.update_table.assert_not_called()
    client.query.assert_called_once()
    client.load_table_from_dataframe.assert_not_called()


def test_replace_all_truncates_and_refuses_empty():
    loader, client = make_loader([bigquery.SchemaField("bidNtceNo", "STRING")])
    loader.replace_all("t", sample_df())
    assert client.load_table_from_dataframe.call_args.kwargs["job_config"].write_disposition == "WRITE_TRUNCATE"
    with pytest.raises(RuntimeError, match="0건"):
        loader.replace_all("t", pd.DataFrame())


# ---------- main ----------

def config():
    return Config(gcp_project="proj", bq_dataset="ds", api_key=SECRET, target_date="2026-10-03")


def test_run_continues_after_failure_and_reports_failed(monkeypatch):
    seen = []

    async def fake_ingest(source, target_date, cfg, loader):
        seen.append(source.name)
        if source.name == "scsbid_list_sttus":
            raise OpenApiError("boom")
        return 1

    monkeypatch.setattr(main_mod, "ingest_source", fake_ingest)
    names = [s.name for s in SOURCES]
    failed = asyncio.run(main_mod.run(config(), names, loader=MagicMock()))
    assert seen == names
    assert failed == ["scsbid_list_sttus"]


def test_main_exits_1_when_any_source_failed(monkeypatch):
    async def fake_run(*a, **k):
        return ["x"]

    monkeypatch.setattr(main_mod, "run", fake_run)
    monkeypatch.setenv("OPENAPI_KEY", "k")
    with pytest.raises(SystemExit) as e:
        main_mod.main([])
    assert e.value.code == 1


def test_dry_run_does_not_touch_bigquery(monkeypatch):
    monkeypatch.setenv("SCSBID_LIST_STTUS_SERVICE_URL", "https://api.test/x")

    async def fake_fetch(url, params, model):
        return [ScsbidListSttusResItem.model_validate(scsbid_item("1"))]

    monkeypatch.setattr(main_mod, "fetch_all", fake_fetch)
    monkeypatch.setattr(main_mod, "BigQueryLoader", MagicMock(side_effect=AssertionError("BQ used")))
    assert asyncio.run(main_mod.run(config(), ["scsbid_list_sttus"], dry_run=True)) == []


def test_opn_std_scsbid_refetches_opening_dates_of_newly_registered_results(monkeypatch):
    monkeypatch.setenv("SCSBID_LIST_STTUS_SERVICE_URL", "https://api.test/results")
    monkeypatch.setenv("DATA_SET_OPN_STD_SCSBID_INFO_SERVICE_URL", "https://api.test/opnstd")
    results = [scsbid_item("1", rlOpengDt="2026-02-06 11:00:00"), scsbid_item("2", rlOpengDt="2026-02-06 15:00:00"),
               scsbid_item("3", rlOpengDt="2026-10-03 10:00:00"), scsbid_item("4", rlOpengDt="2026-09-30 10:00:00"),
               scsbid_item("5")]
    opened = []

    async def fake_fetch(url, params, model):
        if url.endswith("/results"):
            return [ScsbidListSttusResItem.model_validate(r) for r in results]
        opened.append(params["opengBgnDt"][:8])
        return []

    monkeypatch.setattr(main_mod, "fetch_all", fake_fetch)
    loader = MagicMock()
    loader.replace_day.return_value = 0
    source = SOURCES_BY_NAME["data_set_opn_std_scsbid_info"]
    asyncio.run(main_mod.ingest_source(source, D, config(), loader))

    # 대상 날짜 먼저, 그다음 실개찰일(중복·대상일·빈 값 제외, 오래된 순)
    assert opened == ["20261003", "20260206", "20260930"]
    assert [c.args[2] for c in loader.replace_day.call_args_list] == [D, date(2026, 2, 6), date(2026, 9, 30)]


def test_unknown_source_rejected():
    with pytest.raises(SystemExit):
        main_mod.parse_args(["--sources", "nope"])


def test_log_lines_are_json(capsys):
    main_mod.setup_logging()
    main_mod.logger.info("hello", extra={"source": "s"})
    line = capsys.readouterr().out.strip().splitlines()[-1]
    assert json.loads(line) == {"severity": "INFO", "message": "hello", "logger": "ingest", "source": "s"}
