"""
app.py — SEO Tech Audit Tool
Frontend & UI built with Streamlit.
"""

import streamlit as st
import pandas as pd
import io
from backend import load_file, load_sheet, get_sheet_names, analyse, build_pptx

# ─────────────────────────────────────────────
# PAGE CONFIG
# ─────────────────────────────────────────────

st.set_page_config(
    page_title="SEO Tech Audit",
    page_icon="🔍",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ─────────────────────────────────────────────
# CUSTOM CSS
# ─────────────────────────────────────────────

st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=DM+Mono:wght@400;500&family=DM+Sans:wght@300;400;500;600;700&display=swap');

    html, body, [class*="css"] {
        font-family: 'DM Sans', sans-serif;
    }

    /* Dark background */
    .stApp {
        background-color: #0D1B2A;
        color: #E8F4F8;
    }

    /* Sidebar */
    section[data-testid="stSidebar"] {
        background-color: #0A2540;
        border-right: 1px solid #1E3A4A;
    }
    section[data-testid="stSidebar"] * {
        color: #E8F4F8 !important;
    }

    /* Headers */
    h1, h2, h3 { font-family: 'DM Sans', sans-serif; font-weight: 700; color: #00B4D8 !important; }
    h4, h5, h6 { color: #E8F4F8 !important; }

    /* Metric cards */
    div[data-testid="metric-container"] {
        background: #0A2540;
        border: 1px solid #1E3A4A;
        border-radius: 10px;
        padding: 16px;
    }
    div[data-testid="metric-container"] label { color: #00B4D8 !important; font-size: 0.75rem !important; text-transform: uppercase; letter-spacing: 0.08em; }
    div[data-testid="metric-container"] div[data-testid="stMetricValue"] { color: #E8F4F8 !important; font-family: 'DM Mono', monospace; }

    /* Dataframe */
    div[data-testid="stDataFrame"] { border-radius: 8px; overflow: hidden; }

    /* Buttons */
    .stDownloadButton > button, .stButton > button {
        background: linear-gradient(135deg, #00B4D8, #0077B6) !important;
        color: #fff !important;
        border: none !important;
        border-radius: 8px !important;
        font-weight: 600 !important;
        font-family: 'DM Sans', sans-serif !important;
        padding: 0.5rem 1.2rem !important;
        transition: opacity 0.2s;
    }
    .stDownloadButton > button:hover, .stButton > button:hover { opacity: 0.85; }

    /* File uploader */
    div[data-testid="stFileUploader"] {
        background: #0A2540;
        border: 2px dashed #00B4D8;
        border-radius: 12px;
        padding: 10px;
    }

    /* Tabs */
    button[data-baseweb="tab"] { color: #64748B !important; font-weight: 500; }
    button[data-baseweb="tab"][aria-selected="true"] { color: #00B4D8 !important; border-bottom: 2px solid #00B4D8 !important; }

    /* Expander */
    details { background: #0A2540 !important; border: 1px solid #1E3A4A !important; border-radius: 8px; }

    /* Divider */
    hr { border-color: #1E3A4A; }

    /* Badge helpers */
    .badge-critical { color: #EF4444; font-weight: 700; }
    .badge-medium   { color: #F59E0B; font-weight: 700; }
    .badge-low      { color: #22C55E; font-weight: 700; }

    /* Code / mono */
    code { font-family: 'DM Mono', monospace; background: #1E3A4A; padding: 2px 6px; border-radius: 4px; }

    /* Plotly charts transparent bg */
    .js-plotly-plot .plotly .bg { fill: transparent !important; }
</style>
""", unsafe_allow_html=True)


# ─────────────────────────────────────────────
# SIDEBAR
# ─────────────────────────────────────────────

with st.sidebar:
    st.markdown("## 🔍 SEO Tech Audit")
    st.markdown("---")
    st.markdown("### Upload Crawl Data")
    st.markdown("Supports **CSV** and **Excel** files from tools like Screaming Frog, Sitebulb, or custom exports.")

    uploaded_file = st.file_uploader(
        label="Drop your file here",
        type=["csv", "xlsx", "xls"],
        help="Upload a crawl export. Column names are auto-detected.",
        label_visibility="collapsed",
    )

    site_name = st.text_input("Site name (for export)", value="example.com")

    if uploaded_file and uploaded_file.name.endswith((".xlsx", ".xls")):
        st.markdown("---")
        st.markdown("### Sheet Selection")
        uploaded_file.seek(0)
        sheets = get_sheet_names(uploaded_file)
        if sheets:
            selected_sheet = st.selectbox("Select sheet", sheets)
        else:
            selected_sheet = None
    else:
        selected_sheet = None

    st.markdown("---")
    st.markdown("### About")
    st.markdown(
        "This tool analyses SEO technical data **strictly from your file** — "
        "no data is invented or assumed."
    )
    st.markdown("Built for SEO consultants. Export charts and a slide deck for client presentations.")


# ─────────────────────────────────────────────
# MAIN CONTENT
# ─────────────────────────────────────────────

if not uploaded_file:
    # ── Landing state ──
    st.markdown("# Technical SEO Audit Tool")
    st.markdown("### Upload a crawl file to begin your analysis.")
    st.markdown("")

    col1, col2, col3 = st.columns(3)
    with col1:
        st.markdown("#### 📥 Upload")
        st.markdown("Drag in any CSV or Excel crawl export from Screaming Frog, Sitebulb, or similar tools.")
    with col2:
        st.markdown("#### 📊 Analyse")
        st.markdown("Auto-detects columns and surfaces prioritised issues with charts and summaries.")
    with col3:
        st.markdown("#### 📤 Export")
        st.markdown("Download a prioritised action table (CSV) and a client-ready PowerPoint deck.")

    st.markdown("---")
    st.markdown("##### Supported column types (auto-detected by name):")
    supported = [
        "URL / Address", "HTTP Status Code", "Title Tag", "Title Length",
        "Meta Description", "Meta Description Length", "H1 Tag", "H1 Count",
        "Canonical URL", "Indexable", "Word Count", "Response Time",
        "Page Size", "Crawl Depth", "Inlinks / Outlinks", "Images Missing Alt",
    ]
    cols = st.columns(4)
    for i, item in enumerate(supported):
        cols[i % 4].markdown(f"• {item}")

    st.stop()

# ── Load data ──
uploaded_file.seek(0)
if selected_sheet:
    uploaded_file.seek(0)
    df, err = load_sheet(uploaded_file, selected_sheet)
else:
    df, err = load_file(uploaded_file)

if err:
    st.error(f"❌ {err}")
    st.stop()

if df is None or df.empty:
    st.warning("The file appears to be empty.")
    st.stop()

# ── Run analysis ──
with st.spinner("Analysing your crawl data…"):
    results = analyse(df)

cols_detected = results["cols"]
issues        = results["issues"]
ic            = results["issue_counts"]
total_urls    = results["total_urls"]

# ─────────────────────────────────────────────
# TOP KPI BAR
# ─────────────────────────────────────────────

st.markdown(f"## 📋 Audit: `{site_name}`")
st.markdown(f"*{total_urls:,} URLs analysed — {len(cols_detected)} data columns detected*")

k1, k2, k3, k4 = st.columns(4)
k1.metric("Total URLs", f"{total_urls:,}")
k2.metric("🔴 Critical Issues", ic["critical"])
k3.metric("🟡 Medium Issues",   ic["medium"])
k4.metric("🟢 Low Issues",      ic["low"])

st.markdown("---")

# ─────────────────────────────────────────────
# TABS
# ─────────────────────────────────────────────

tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "🎯 Priority Actions",
    "📊 Charts",
    "🔎 Raw Data",
    "📝 Insights",
    "📤 Export",
])


# ── TAB 1: Priority Actions ──
with tab1:
    st.markdown("### Prioritised Issue List")
    st.markdown(
        "Issues are ranked **Critical → Medium → Low** based on SEO impact. "
        "Address Critical items first."
    )

    if not issues:
        st.success("✅ No known issues detected from the available column data.")
    else:
        # Colour-coded table
        issue_df = pd.DataFrame(issues)

        def style_priority(val):
            if "Critical" in str(val):
                return "color: #EF4444; font-weight: bold;"
            elif "Medium" in str(val):
                return "color: #F59E0B; font-weight: bold;"
            elif "Low" in str(val):
                return "color: #22C55E; font-weight: bold;"
            return ""

        styled = issue_df.style.applymap(style_priority, subset=["Priority"])
        st.dataframe(styled, use_container_width=True, hide_index=True)

        # Individual issue cards
        st.markdown("---")
        st.markdown("### Issue Detail Cards")

        for issue in issues:
            p = issue["Priority"]
            icon = "🔴" if "Critical" in p else ("🟡" if "Medium" in p else "🟢")
            with st.expander(f"{icon} {issue['Issue']} — {issue['Count']:,} affected"):
                c1, c2, c3 = st.columns(3)
                c1.markdown(f"**Priority**  \n{p}")
                c2.markdown(f"**Count**  \n{issue['Count']:,}")
                c3.markdown(f"**Impact**  \n{issue['Impact']}")
                st.markdown(f"**Recommended Action:** {issue['Action']}")


# ── TAB 2: Charts ──
with tab2:
    charts = results["charts"]
    if not charts:
        st.info("No chartable columns were detected. Ensure your file contains standard crawl columns.")
    else:
        st.markdown(f"### {len(charts)} Chart{'s' if len(charts) != 1 else ''} Generated")
        chart_items = list(charts.items())
        for i in range(0, len(chart_items), 2):
            cols_c = st.columns(2)
            for j, (name, fig) in enumerate(chart_items[i:i+2]):
                fig.update_layout(
                    paper_bgcolor="rgba(0,0,0,0)",
                    plot_bgcolor="#0A2540",
                    font_color="#E8F4F8",
                    title_font_color="#00B4D8",
                )
                with cols_c[j]:
                    st.plotly_chart(fig, use_container_width=True)


# ── TAB 3: Raw Data ──
with tab3:
    st.markdown("### Raw Crawl Data")
    st.markdown(f"*{total_urls:,} rows × {len(df.columns)} columns*")

    # Quick column filter
    search_col = st.text_input("🔎 Filter by column name", key="col_filter")
    visible_cols = [c for c in df.columns if search_col.lower() in c.lower()] if search_col else list(df.columns)

    st.dataframe(df[visible_cols], use_container_width=True, height=500)

    # Detected columns
    with st.expander("🔬 Detected column mappings"):
        st.markdown("These are the columns your file contained that were matched to known SEO fields:")
        if cols_detected:
            mapping_df = pd.DataFrame([
                {"SEO Field": k, "Your Column": v}
                for k, v in cols_detected.items()
            ])
            st.dataframe(mapping_df, hide_index=True, use_container_width=True)
        else:
            st.warning("No standard SEO columns detected. Check your column header names.")


# ── TAB 4: Insights ──
with tab4:
    st.markdown("### Auto-Generated Insights")
    st.markdown("*All insights are derived strictly from the data in your file.*")

    summaries = results["summaries"]
    if not summaries:
        st.info("No summary-level data could be derived. Ensure columns like Status Code, Title, or Response Time are present.")
    else:
        for key, summary in summaries.items():
            label = key.replace("_", " ").title()
            st.markdown(f"**{label}:** {summary}")

    st.markdown("---")
    st.markdown("### Data Quality Check")
    null_pct = (df.isnull().sum() / len(df) * 100).round(1)
    null_df  = null_pct[null_pct > 0].reset_index()
    null_df.columns = ["Column", "% Missing"]
    if null_df.empty:
        st.success("✅ No missing values detected across all columns.")
    else:
        st.markdown("Columns with missing values:")
        st.dataframe(null_df, hide_index=True, use_container_width=True)


# ── TAB 5: Export ──
with tab5:
    st.markdown("### Export Your Audit")

    col_e1, col_e2 = st.columns(2)

    with col_e1:
        st.markdown("#### 📄 Priority Action Table (CSV)")
        st.markdown("Download the full prioritised issue list for your records or a client brief.")
        if issues:
            issue_csv = pd.DataFrame(issues).to_csv(index=False).encode("utf-8")
            st.download_button(
                label="⬇️ Download Action Table",
                data=issue_csv,
                file_name=f"{site_name.replace('.', '_')}_seo_audit_actions.csv",
                mime="text/csv",
            )
        else:
            st.info("No issues to export.")

    with col_e2:
        st.markdown("#### 📊 Full Data Export (CSV)")
        st.markdown("Download the complete crawl dataset as-is for further processing.")
        full_csv = df.to_csv(index=False).encode("utf-8")
        st.download_button(
            label="⬇️ Download Full Data",
            data=full_csv,
            file_name=f"{site_name.replace('.', '_')}_crawl_data.csv",
            mime="text/csv",
        )

    st.markdown("---")
    st.markdown("#### 🎞️ PowerPoint Presentation")
    st.markdown(
        "Generate a client-ready slide deck with an executive summary, "
        "priority action plan, and per-issue deep-dives."
    )

    if st.button("🪄 Generate PowerPoint"):
        with st.spinner("Building your presentation…"):
            try:
                pptx_bytes = build_pptx(results, site_name=site_name)
                st.download_button(
                    label="⬇️ Download Presentation (.pptx)",
                    data=pptx_bytes,
                    file_name=f"{site_name.replace('.', '_')}_seo_tech_audit.pptx",
                    mime="application/vnd.openxmlformats-officedocument.presentationml.presentation",
                )
                st.success("✅ Presentation ready. Click above to download.")
            except Exception as e:
                st.error(f"Error generating presentation: {e}")

    st.markdown("---")
    st.markdown("##### What's in the PowerPoint?")
    pptx_contents = [
        "**Slide 1** — Title slide with site name and issue count summary",
        "**Slide 2** — Executive summary with KPIs and top findings",
        "**Slide 3** — Full priority action table (top 10 issues)",
        "**Slides 4+** — Individual deep-dive per Critical and Medium issue",
        "**Final slide** — Recommended next steps timeline",
    ]
    for item in pptx_contents:
        st.markdown(f"• {item}")
