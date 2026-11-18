"""Tests for the GSS StatsBank GDP connector."""

from pathlib import Path
import sys

import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from ghana_banking.data import gss


def pxweb_csv():
    periods = pd.period_range("2023Q1", periods=8, freq="Q").astype(str)
    frame = pd.DataFrame({
        "Quarter": periods,
        "GDP_Series": ["Real GDP (constant 2013 prices)"] * 8,
        "Variable": ["Overall GDP"] * 8,
        "value": [1000 + i * 10 for i in range(8)],
    })
    return frame.to_csv(index=False).encode("utf-8")


def test_gss_query_selects_real_gdp_and_overall_total():
    query = gss.build_gss_gdp_query()
    assert query["query"][0]["code"] == "Quarter"
    assert query["query"][1]["selection"]["values"] == [
        "Real GDP (constant 2013 prices)"
    ]
    assert query["query"][2]["selection"]["values"] == ["Overall GDP"]
    assert query["response"]["format"] == "csv"


def test_parse_pxweb_gdp_csv_normalises_repository_schema():
    result = gss._parse_pxweb_gdp_csv(pxweb_csv())
    assert list(result.columns) == [
        "Name of Series",
        "Gross Domestic Product (GDP), production, real",
    ]
    assert len(result) == 8
    assert result["Name of Series"].iloc[0] == "2023Q1"
    assert result["Name of Series"].iloc[-1] == "2024Q4"
    assert result.iloc[-1, 1] == 1070


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


def test_update_gss_gdp_rejects_older_data_without_replacing_file(tmp_path, monkeypatch):
    destination = tmp_path / "data_first2.csv"
    existing = pd.DataFrame({
        "Name of Series": ["2024Q1", "2024Q2", "2024Q3", "2024Q4"],
        "Gross Domestic Product (GDP), production, real": [1, 2, 3, 4],
    })
    existing.to_csv(destination, index=False)
    original = destination.read_bytes()

    incoming = gss._parse_pxweb_gdp_csv(pxweb_csv())
    monkeypatch.setattr(gss, "fetch_gss_quarterly_gdp", lambda **kwargs: incoming)

    with pytest.raises(ValueError, match="stale"):
        gss.update_gss_quarterly_gdp(raw_data_path=str(tmp_path))

    assert destination.read_bytes() == original
