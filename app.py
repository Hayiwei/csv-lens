"""Run with: python -m streamlit run app.py."""

from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st

from csv_lens.core import CSVError, finite_numeric, inspect_frame, load_csv, report_json

ROOT = Path(__file__).resolve().parent
TEAL = "#117C83"
NAVY = "#19334A"

st.set_page_config(page_title="CSV Lens", page_icon="◫", layout="wide")
st.markdown("""
<style>
.block-container {max-width:1180px; padding-top:2.8rem; padding-bottom:3rem}
[data-testid="stMetric"] {background:#F2F6F8; border:1px solid #E2EAF0;
 border-radius:12px; padding:1rem 1.25rem}
[data-testid="stMetricLabel"] {color:#526778}
[data-testid="stMetricValue"] {color:#19334A}
.eyebrow {font-size:.75rem; font-weight:650; letter-spacing:.18em; color:#117C83}
.intro {font-size:1.1rem; color:#526778; margin-bottom:1.7rem}
h1, h2, h3 {letter-spacing:-.025em}
</style>
""", unsafe_allow_html=True)


def style_chart(fig, *, height=360):
    fig.update_layout(
        height=height, paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family="Arial, sans-serif", color=NAVY),
        margin=dict(l=15, r=15, t=25, b=15),
        colorway=[TEAL, NAVY, "#D18B47"], bargap=0.18,
    )
    fig.update_xaxes(showgrid=False)
    fig.update_yaxes(gridcolor="#E5EDF1", zeroline=False)
    return fig


with st.sidebar:
    st.markdown("### ◫ CSV Lens")
    st.caption("A closer look at your data.")
    st.divider()
    source = st.radio("Data source", ["Sample dataset", "Upload a CSV"])
    encoding_label = st.selectbox("File encoding", ["UTF-8", "GB18030", "Latin-1"], key="encoding")
    separator_label = st.selectbox("Delimiter", ["Auto", "Comma", "Semicolon", "Tab", "Pipe"], key="delimiter")
    st.caption("Up to 20 MiB · 100,000 rows · 200 columns")
    st.divider()
    st.markdown("**How to use**")
    st.caption("Start with the sample, check the overview, then explore individual columns.")
    st.caption("Files are processed by the running app server. This app does not save uploads to disk.")

st.markdown('<div class="eyebrow">SMALL TOOLS / CLEARER DATA</div>', unsafe_allow_html=True)
st.title("CSV Lens")
st.markdown('<div class="intro">Understand a CSV before you work with it.</div>', unsafe_allow_html=True)

encoding = {"UTF-8": "utf-8-sig", "GB18030": "gb18030", "Latin-1": "latin-1"}[encoding_label]
delimiter = {"Auto": None, "Comma": ",", "Semicolon": ";", "Tab": "\t", "Pipe": "|"}[separator_label]
if source == "Upload a CSV":
    uploaded = st.file_uploader("Choose a CSV file", type=["csv", "tsv", "txt"])
    if uploaded is None:
        st.info("Choose a file to begin, or switch to the sample dataset in the sidebar.")
        st.stop()
    content, filename = uploaded.getvalue(), uploaded.name
else:
    content = (ROOT / "data" / "sample_orders.csv").read_bytes()
    filename = "sample_orders.csv"
    # The bundled sample has a known format; sidebar parsing options apply to uploads.
    encoding, delimiter = "utf-8-sig", ","

try:
    loaded = load_csv(content, encoding=encoding, delimiter=delimiter)
except CSVError as exc:
    st.error(str(exc))
    st.stop()

frame = loaded.frame
report = inspect_frame(frame)
separator_name = {"\t": "tab", ",": "comma", ";": "semicolon", "|": "pipe"}[loaded.delimiter]
st.caption(f"{filename} · {separator_name}-separated · {loaded.encoding}")
if source == "Sample dataset":
    st.caption("Synthetic shop orders with intentional gaps and duplicates. No real customer records.")

metrics = st.columns(4)
for column, label, value, detail in [
    (metrics[0], "Rows", f"{report['rows']:,}", "All loaded rows"),
    (metrics[1], "Columns", str(report["columns"]), "Fields in this file"),
    (metrics[2], "Missing cells", f"{report['missing_pct']:.1f}%", f"{report['missing_cells']:,} cells"),
    (metrics[3], "Duplicate rows", str(report["duplicate_rows"]), "Extra full-row copies"),
]:
    column.metric(label, value, help=detail)

st.write("")
overview, fields, explore, export = st.tabs(["Overview", "Columns", "Explore", "Export report"])
profiles = pd.DataFrame(report["column_profiles"])
numeric = finite_numeric(frame)

with overview:
    left, right = st.columns([1.3, 1], gap="large")
    with left:
        st.subheader("Completeness by column")
        shown_profiles = profiles if len(profiles) <= 15 else profiles.sort_values("missing_pct", ascending=False).head(15)
        if len(profiles) > 15:
            st.caption("Showing the 15 columns with the highest missing-value rates. The Columns tab includes every field.")
        missing_fig = px.bar(
            shown_profiles, y="column", x="missing_pct", orientation="h",
            labels={"column": "", "missing_pct": "Missing values (%)"},
            color_discrete_sequence=[TEAL],
        )
        missing_fig.update_layout(yaxis=dict(autorange="reversed"))
        missing_fig.update_xaxes(range=[0, max(10, float(profiles["missing_pct"].max()) * 1.15)])
        st.plotly_chart(style_chart(missing_fig, height=max(300, min(600, 35 * len(shown_profiles)))), width="stretch")
    with right:
        st.subheader("At a glance")
        st.markdown(f"**{len(numeric.columns)} numeric** and **{len(frame.columns) - len(numeric.columns)} other** columns.")
        st.write(f"{int((profiles['missing'] > 0).sum())} columns contain missing values.")
        st.write(f"{report['duplicate_rows']} rows repeat an earlier row exactly.")
        if report["infinite_values"]:
            st.warning(f"{report['infinite_values']} infinite values are excluded from numeric plots and statistics.")
        st.caption("These are inspection signals, not automatic cleaning decisions.")
    st.subheader("First 20 rows")
    st.dataframe(frame.head(20), hide_index=True, width="stretch")

with fields:
    st.subheader("Column profiles")
    st.caption("Unique counts exclude missing values. Numeric summaries exclude missing and infinite values.")
    st.dataframe(profiles, hide_index=True, width="stretch")
    with st.expander("Parsing and counting rules"):
        st.write("The first row is the header. pandas infers types and recognizes its default missing-value tokens; whitespace-only cells are also missing. Date-like strings stay text. Duplicate header names are disambiguated by pandas.")
        st.write("Duplicate rows count additional exact copies after missing-value normalization. No rows are removed or repaired.")

with explore:
    st.subheader("Look inside a column")
    st.caption("Plots use at most 5,000 rows, sampled with a fixed seed. Overview counts use every loaded row.")
    chart_frame = frame.sample(5_000, random_state=42) if len(frame) > 5_000 else frame
    chart_numeric = finite_numeric(chart_frame)
    if frame.empty:
        st.info("This file has headers but no data rows. Upload a file with observations to explore.")
    else:
        selected = st.selectbox("Column", list(frame.columns), key="column")
        if selected in chart_numeric.columns:
            values = chart_numeric[selected].dropna()
            if values.empty:
                st.info("This column has no finite numeric values to plot.")
            else:
                fig = px.histogram(
                    values.to_frame(), x=selected, nbins=25,
                    color_discrete_sequence=[TEAL], labels={"count": "Rows"},
                )
                st.plotly_chart(style_chart(fig), width="stretch")
        else:
            counts = chart_frame[selected].dropna().astype(str).value_counts().head(12)
            if counts.empty:
                st.info("This column has no non-missing values to plot.")
            else:
                counts_frame = counts.rename_axis("Value").reset_index(name="Rows")
                fig = px.bar(counts_frame, x="Rows", y="Value", orientation="h", color_discrete_sequence=[TEAL])
                fig.update_layout(yaxis=dict(autorange="reversed", type="category"))
                st.caption("Up to 12 most frequent non-missing values.")
                st.plotly_chart(style_chart(fig), width="stretch")
        if len(numeric.columns) >= 2:
            st.subheader("Compare two numeric columns")
            x_control, y_control = st.columns(2)
            x_name = x_control.selectbox("X axis", list(numeric.columns), index=0, key="x_axis")
            y_name = y_control.selectbox("Y axis", list(numeric.columns), index=1, key="y_axis")
            pairs = chart_numeric[[x_name, y_name]].dropna() if x_name != y_name else chart_numeric[[x_name]].dropna()
            if pairs.empty:
                st.info("No rows have finite values for both selected columns.")
            else:
                fig = px.scatter(pairs, x=x_name, y=y_name, opacity=0.65, color_discrete_sequence=[TEAL])
                st.plotly_chart(style_chart(fig), width="stretch")

with export:
    st.subheader("Take the summary with you")
    st.write("Download the counts, column profiles, and counting definitions as JSON. Raw rows are not included.")
    st.download_button("Download JSON report", data=report_json(report), file_name="csv-lens-report.json", mime="application/json")
    with st.expander("Preview report"):
        st.json(report)

st.divider()
st.caption("CSV Lens · Built for a useful first look. · github.com/Hayiwei/csv-lens")
