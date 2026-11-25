from pathlib import Path
from io import BytesIO

import pytest
import streamlit as st

from streamlit.testing.v1 import AppTest


def test_demo_and_exploration_render_without_exceptions():
    app = AppTest.from_file(str(Path(__file__).resolve().parents[1] / "app.py")).run(timeout=30)
    assert not app.exception
    assert len(app.metric) == 4
    assert app.metric[0].value == "248"
    assert app.metric[3].value == "8"
    app.selectbox(key="column").set_value("unit_price").run()
    assert not app.exception
    app.selectbox(key="y_axis").set_value(app.selectbox(key="x_axis").value).run()
    assert not app.exception


def test_upload_mode_has_a_clear_empty_state():
    app = AppTest.from_file(str(Path(__file__).resolve().parents[1] / "app.py")).run(timeout=30)
    app.radio[0].set_value("Upload a CSV").run()
    assert not app.exception
    assert app.info and "Choose a file" in app.info[0].value


@pytest.mark.parametrize("content,rows,has_error", [
    (b"a,b\n1,2\n3,4\n", "2", False),
    (b"a,b\n", "0", False),
    (b"a,b\ninf,2\n-inf,3\n", "2", False),
    (b'name,city\nAlice,London\nBob,Paris\n', "2", False),
    (b'a,b\n"unclosed', None, True),
])
def test_uploaded_file_paths(monkeypatch, content, rows, has_error):
    uploaded = BytesIO(content)
    uploaded.name = "test.csv"
    monkeypatch.setattr(st, "file_uploader", lambda *args, **kwargs: uploaded)
    app = AppTest.from_file(str(Path(__file__).resolve().parents[1] / "app.py")).run(timeout=30)
    app.radio[0].set_value("Upload a CSV").run()
    assert not app.exception
    if has_error:
        assert app.error
    else:
        assert app.metric[0].value == rows
