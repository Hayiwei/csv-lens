"""CSV loading and profiling, independent of the web interface."""

from __future__ import annotations

import csv
import io
import json
import warnings
from dataclasses import dataclass

import numpy as np
import pandas as pd

MAX_BYTES = 20 * 1024 * 1024
MAX_ROWS = 100_000
MAX_COLUMNS = 200


class CSVError(ValueError):
    """A readable input error that the interface can display."""


@dataclass
class LoadedCSV:
    frame: pd.DataFrame
    encoding: str
    delimiter: str


def load_csv(
    content: bytes, *, encoding: str = "utf-8-sig", delimiter: str | None = None
) -> LoadedCSV:
    """Read a bounded CSV. Encoding is explicit; parsing never skips bad rows."""
    if len(content) > MAX_BYTES:
        raise CSVError("This file exceeds the 20 MiB limit. Try a smaller extract.")
    if not content.strip():
        raise CSVError("This file is empty. Choose a CSV with a header row.")
    if encoding not in {"utf-8-sig", "gb18030", "latin-1"}:
        raise CSVError("Unsupported encoding.")
    if delimiter not in {None, ",", ";", "\t", "|"}:
        raise CSVError("Choose comma, semicolon, tab, pipe, or automatic detection.")
    try:
        text = content.decode(encoding)
    except UnicodeDecodeError as exc:
        raise CSVError("Cannot decode this file. Select its encoding in the sidebar.") from exc
    if "\x00" in text:
        raise CSVError("This does not look like a text CSV. Export it as UTF-8 CSV first.")
    if delimiter is None:
        try:
            delimiter = csv.Sniffer().sniff(text[:16_384], delimiters=",;\t|").delimiter
        except csv.Error:
            delimiter = ","
    try:
        header = next(csv.reader(io.StringIO(text), delimiter=delimiter))
        if len(header) > MAX_COLUMNS:
            raise CSVError("This file exceeds the 200-column limit.")
        with warnings.catch_warnings():
            warnings.simplefilter("error", pd.errors.ParserWarning)
            frame = pd.read_csv(
                io.StringIO(text), sep=delimiter, nrows=MAX_ROWS + 1,
                on_bad_lines="error", index_col=False,
            )
    except (pd.errors.EmptyDataError, StopIteration) as exc:
        raise CSVError("No header was found. Choose a CSV with named columns.") from exc
    except (pd.errors.ParserError, pd.errors.ParserWarning, csv.Error) as exc:
        raise CSVError("The CSV could not be parsed. Check its delimiter, quotes, and row lengths.") from exc
    if len(frame) > MAX_ROWS:
        raise CSVError("This file exceeds 100,000 rows. Try a smaller extract.")
    if frame.shape[1] > MAX_COLUMNS:
        raise CSVError("This file exceeds the 200-column limit.")
    # Treat whitespace-only strings as missing; leave other values unchanged.
    frame = frame.replace(r"^\s*$", np.nan, regex=True)
    return LoadedCSV(frame=frame, encoding=encoding, delimiter=delimiter)


def finite_numeric(frame: pd.DataFrame) -> pd.DataFrame:
    """Numeric values usable for plots; infinity remains counted in the report."""
    return frame.select_dtypes(include="number").replace([np.inf, -np.inf], np.nan)


def inspect_frame(frame: pd.DataFrame) -> dict:
    """Return JSON-safe, full-dataset counts and per-column summaries."""
    rows, cols = frame.shape
    cells = rows * cols
    missing = int(frame.isna().sum().sum())
    duplicates = int(frame.duplicated().sum()) if cols else 0
    columns = []
    nonfinite = 0
    for name in frame.columns:
        series = frame[name]
        numeric = pd.api.types.is_numeric_dtype(series) and not pd.api.types.is_bool_dtype(series)
        item = {
            "column": str(name),
            "dtype": str(series.dtype),
            "missing": int(series.isna().sum()),
            "missing_pct": round(float(series.isna().mean() * 100), 2) if rows else 0.0,
            "unique": int(series.nunique(dropna=True)),
            "infinite": 0,
        }
        if numeric:
            values = series.to_numpy(dtype=float, na_value=np.nan)
            item["infinite"] = int(np.isinf(values).sum())
            nonfinite += item["infinite"]
            finite = values[np.isfinite(values)]
            item.update({
                "min": float(finite.min()) if len(finite) else None,
                "median": float(np.median(finite)) if len(finite) else None,
                "max": float(finite.max()) if len(finite) else None,
            })
        columns.append(item)
    return {
        "rows": rows,
        "columns": cols,
        "missing_cells": missing,
        "missing_pct": round(100 * missing / cells, 2) if cells else 0.0,
        "duplicate_rows": duplicates,
        "duplicate_pct": round(100 * duplicates / rows, 2) if rows else 0.0,
        "infinite_values": nonfinite,
        "column_profiles": columns,
        "definitions": {
            "missing": "pandas default NA tokens, empty fields, and whitespace-only strings",
            "duplicates": "exact full-row duplicates after missing-value normalization; first occurrence excluded",
            "numeric_statistics": "finite numeric values only; missing and infinite values excluded",
            "scope": "all loaded rows; no sampling for reported counts",
        },
    }


def report_json(report: dict) -> str:
    return json.dumps(report, ensure_ascii=False, indent=2, allow_nan=False)
