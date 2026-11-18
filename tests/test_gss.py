"""Tests for the GSS StatsBank GDP connector."""

from pathlib import Path
import json
import sys

import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from ghana_banking.data import gss


def metadata():
    return {
        "variables": [
            {
                "code": "Quarter",
                "text": "Quarter",
                "values": ["2023Q1", "2023Q2"],
                "valueTexts": ["2023 Q1", "2023 Q2"],
                "time": True,
            },
            {
                "code": "GDP_Series",
                "text": "GDP series",
                "values": ["real2013", "nominal"],
                "valueTexts": [
                    "Real GDP (constant 2013 prices)",
                    "Nominal GDP",
                ],
            },
            {
                "code": "Variable",
                "text": "Variable",
                "values": ["total", "agriculture"],
                "valueTexts": ["Total GDP", "Agriculture"],
            },
        ]
    }


def pxweb_csv():
    periods = pd.period_range("2023Q1", periods=8, freq="Q").astype(str).tolist()
    periods[0] += "*"
    periods[1] += "**"
    frame = pd.DataFrame({
        "Quarter": periods,
        "value": [1000 + i * 10 for i in range(8)],
    })
    return frame.to_csv(index=False).encode("utf-8")


def test_gss_query_discovers_dimensions_and_selects_real_total_gdp():
    query = gss.build_gss_gdp_query(metadata())
    selections = {item["code"]: item["selection"] for item in query["query"]}

    assert selections["Quarter"] == {"filter": "all", "values": ["*"]}
    assert selections["GDP_Series"] == {"filter": "item", "values": ["real2013"]}
    assert selections["Variable"] == {"filter": "item", "values": ["total"]}
    assert query["response"]["format"] == "csv"


def test_gss_query_rejects_ambiguous_metadata():
    ambiguous = metadata()
    ambiguous["variables"][1]["values"].append("real_alt")
    ambiguous["variables"][1]["valueTexts"].append(
        "Real GDP (constant 2013 prices), revised"
    )
    with pytest.raises(ValueError, match="unique"):
        gss.build_gss_gdp_query(ambiguous)


def test_parse_pxweb_gdp_csv_normalises_schema_and_keeps_revision_markers():
    result = gss._parse_pxweb_gdp_csv(pxweb_csv())
    assert list(result.columns) == [
        "Name of Series",
        "Gross Domestic Product (GDP), production, real",
        "Observation Status",
    ]
    assert len(result) == 8
    assert result["Name of Series"].iloc[0] == "2023Q1"
    assert result["Name of Series"].iloc[-1] == "2024Q4"
    assert result.iloc[-1, 1] == 1070
    assert result.loc[0, "Observation Status"] == "revised"
    assert result.loc[1, "Observation Status"] == "provisional"


def test_parse_pxweb_gdp_rejects_short_or_invalid_response():
    short = pd.DataFrame({
        "Quarter": ["2024Q1", "2024Q2"],
        "value": [100, 110],
    }).to_csv(index=False).encode("utf-8")
    with pytest.raises(ValueError, match="fewer than eight"):
        gss._parse_pxweb_gdp_csv(short)
    with pytest.raises(ValueError, match="did not contain a GDP data table"):
        gss._parse_pxweb_gdp_csv(b"message\n")


def test_update_gss_gdp_writes_normalised_csv(tmp_path, monkeypatch):
    expected = gss._parse_pxweb_gdp_csv(pxweb_csv())
    monkeypatch.setattr(gss, "fetch_gss_quarterly_gdp", lambda **kwargs: expected)

    result = gss.update_gss_quarterly_gdp(raw_data_path=str(tmp_path))
    saved = pd.read_csv(tmp_path / "data_first2.csv")

    assert result["latest_quarter"] == "2024Q4"
    assert len(saved) == 8
    assert saved["Name of Series"].iloc[0] == "2023Q1"
    assert saved["Observation Status"].iloc[0] == "revised"


def test_update_gss_gdp_rejects_older_data_without_replacing_file(tmp_path, monkeypatch):
    destination = tmp_path / "data_first2.csv"
    existing = pd.DataFrame({
        "Name of Series": ["2025Q1", "2025Q2", "2025Q3", "2025Q4"],
        "Gross Domestic Product (GDP), production, real": [1, 2, 3, 4],
    })
    existing.to_csv(destination, index=False)
    original = destination.read_bytes()

    incoming = gss._parse_pxweb_gdp_csv(pxweb_csv())
    monkeypatch.setattr(gss, "fetch_gss_quarterly_gdp", lambda **kwargs: incoming)

    with pytest.raises(ValueError, match="stale"):
        gss.update_gss_quarterly_gdp(raw_data_path=str(tmp_path))
    assert destination.read_bytes() == original


def test_fetch_gss_gdp_reads_metadata_then_posts_selected_query(monkeypatch):
    metadata_payload = json.dumps(metadata()).encode("utf-8")
    csv_payload = pxweb_csv()
    calls = []

    def fake_request(url, data=None, timeout=60):
        calls.append({"url": url, "data": data, "timeout": timeout})
        return metadata_payload if data is None else csv_payload

    monkeypatch.setattr(gss, "_request_bytes", fake_request)
    result = gss.fetch_gss_quarterly_gdp(
        api_url="https://example.test/table.px", timeout=15
    )

    assert len(calls) == 2
    assert calls[0]["data"] is None
    assert calls[1]["data"] is not None
    assert calls[0]["timeout"] == 15
    assert len(result) == 8


def test_fetch_gss_gdp_requires_https():
    with pytest.raises(ValueError, match="HTTPS"):
        gss.fetch_gss_quarterly_gdp(api_url="http://example.test/table.px")


def test_default_gss_endpoint_uses_documented_pxweb_api_base():
    assert gss.DEFAULT_GSS_GDP_API_URL.startswith(
        "https://statsbank.statsghana.gov.gh:443/api/v1/en/"
    )
    assert "/pxweb/api/" not in gss.DEFAULT_GSS_GDP_API_URL
    assert gss.DEFAULT_GSS_GDP_API_URL.endswith("/qgdp_p_px.px")
