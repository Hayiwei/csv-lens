import json

import numpy as np
import pandas as pd
import pytest

import csv_lens.core as core
from csv_lens.core import CSVError, inspect_frame, load_csv, report_json


def test_counts_are_computed_after_missing_normalization():
    data = b"name,value\nA,1\nA,1\nB,\n ,3\n"
    report = inspect_frame(load_csv(data).frame)
    assert (report["rows"], report["columns"]) == (4, 2)
    assert report["missing_cells"] == 2
    assert report["missing_pct"] == 25.0
    assert report["duplicate_rows"] == 1
    assert report["column_profiles"][1]["median"] == 1.0


@pytest.mark.parametrize("separator", [",", ";", "\t", "|"])
def test_detects_supported_delimiters_and_quoted_values(separator):
    text = f'name{separator}value\n"Lee, Jo"{separator}2\nSam{separator}3\n'
    loaded = load_csv(text.encode())
    assert loaded.delimiter == separator
    assert loaded.frame.iloc[0, 0] == "Lee, Jo"
    assert loaded.frame.iloc[0, 1] == 2


def test_utf8_bom_and_explicit_chinese_encoding():
    text = "城市,值\n深圳,3\n"
    assert load_csv(text.encode("utf-8-sig")).frame.columns[0] == "城市"
    assert load_csv(text.encode("gb18030"), encoding="gb18030").frame.iloc[0, 0] == "深圳"
    with pytest.raises(CSVError, match="encoding"):
        load_csv(text.encode("gb18030"))


def test_header_only_and_single_column_files():
    empty = inspect_frame(load_csv(b"a,b\n").frame)
    assert empty["rows"] == 0 and empty["missing_pct"] == 0
    assert json.loads(report_json(empty))["rows"] == 0
    assert load_csv(b"name\nAlice\nBob\n").frame.shape == (2, 1)


def test_infinity_does_not_corrupt_json_or_numeric_statistics():
    report = inspect_frame(pd.DataFrame({"x": [1.0, np.inf, -np.inf, np.nan]}))
    assert report["infinite_values"] == 2
    assert report["missing_cells"] == 1
    assert report["column_profiles"][0]["median"] == 1.0
    assert json.loads(report_json(report))["rows"] == 4


@pytest.mark.parametrize("data", [b"", b" \n ", b"a,b\n\"unclosed", b"a\x00b"])
def test_invalid_input_produces_actionable_errors(data):
    with pytest.raises(CSVError):
        load_csv(data)


def test_size_row_and_column_limits(monkeypatch):
    monkeypatch.setattr(core, "MAX_BYTES", 5)
    with pytest.raises(CSVError, match="20 MiB"):
        load_csv(b"a,b\n1,2")
    monkeypatch.setattr(core, "MAX_BYTES", 1000)
    monkeypatch.setattr(core, "MAX_ROWS", 1)
    with pytest.raises(CSVError, match="100,000"):
        load_csv(b"a,b\n1,2\n3,4")
    monkeypatch.setattr(core, "MAX_COLUMNS", 1)
    with pytest.raises(CSVError, match="200-column"):
        load_csv(b"a,b\n1,2")


def test_excess_fields_are_not_silently_discarded():
    with pytest.raises(CSVError, match="parsed"):
        load_csv(b"a,b\n1,2,3\n4,5,6")
