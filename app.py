"""
app.py — SEO Tech Audit Tool
Frontend & UI built with Streamlit.
"""

import streamlit as st
import pandas as pd
import io
from backend import (
    load_file, load_sheet, load_all_sheets, get_sheet_names,
    analyse, build_pptx,
    crawl_site, fetch_gsc_data, merge_gsc_with_crawl,
)

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
            sheet_options = ["📂 All Sheets (merged)"] + sheets
            selected_sheet_option = st.selectbox(
                "Select sheet",
                sheet_options,
                help="Choose a single sheet or merge all sheets into one analysis.",
            )
            if selected_sheet_option == "📂 All Sheets (merged)":
                selected_sheet = "__ALL__"
            else:
                selected_sheet = selected_sheet_option
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
sheets_loaded = []
if selected_sheet == "__ALL__":
    uploaded_file.seek(0)
    df, err, sheets_loaded = load_all_sheets(uploaded_file)
elif selected_sheet:
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
if sheets_loaded:
    st.markdown(f"*{total_urls:,} URLs analysed across **{len(sheets_loaded)} sheets** ({', '.join(sheets_loaded)}) — {len(cols_detected)} data columns detected*")
else:
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

tab1, tab2, tab3, tab4, tab5, tab6, tab7, tab8 = st.tabs([
  "🎯 Priority Actions",
  "📊 Charts",
  "🔎 Raw Data",
  "📝 Insights",
  "📤 Export",
  "🕷️ Live Crawler",
  "📈 Search Console",
  "📋 Full Audit Framework",   # NEW
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

        styled = issue_df.style.map(style_priority, subset=["Priority"])        
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


# ── TAB 6: Live Crawler ──
with tab6:
    st.markdown("### 🕷️ Live Site Crawler")
    st.markdown(
        "Enter a URL and the tool will crawl the site directly — no need to upload a file. "
        "It discovers pages via **sitemap.xml** first, then follows internal links. "
        "The crawl results are loaded into the analysis above automatically."
    )
    st.info(
        "⚠️ **Requirements:** Add `requests beautifulsoup4 lxml` to `requirements.txt` and restart the app. "
        "Crawling respects a polite delay and a page cap to avoid overloading servers."
    )

    with st.form("crawler_form"):
        crawl_url = st.text_input(
            "Start URL",
            value="https://",
            help="Enter the homepage or sitemap URL, e.g. https://example.com",
        )
        crawl_limit = st.slider("Max pages to crawl", min_value=10, max_value=500, value=100, step=10)
        run_crawl = st.form_submit_button("🚀 Start Crawl")

    if run_crawl:
        if not crawl_url.startswith("http"):
            st.error("Please enter a valid URL starting with http:// or https://")
        else:
            with st.spinner(f"Crawling {crawl_url} — up to {crawl_limit} pages…"):
                crawl_df, crawl_err = crawl_site(crawl_url, max_pages=crawl_limit)

            if crawl_err:
                st.error(f"❌ {crawl_err}")
            elif crawl_df is not None and not crawl_df.empty:
                st.success(f"✅ Crawled {len(crawl_df):,} pages successfully!")
                st.dataframe(crawl_df, use_container_width=True, height=400)

                # Run analysis on crawl results
                with st.spinner("Analysing crawl results…"):
                    crawl_results = analyse(crawl_df)

                crawl_ic = crawl_results["issue_counts"]
                c1, c2, c3 = st.columns(3)
                c1.metric("🔴 Critical", crawl_ic["critical"])
                c2.metric("🟡 Medium",   crawl_ic["medium"])
                c3.metric("🟢 Low",      crawl_ic["low"])

                if crawl_results["issues"]:
                    st.markdown("#### Issues Found")
                    st.dataframe(
                        pd.DataFrame(crawl_results["issues"]),
                        use_container_width=True, hide_index=True,
                    )

                # Export crawl data
                crawl_csv = crawl_df.to_csv(index=False).encode("utf-8")
                st.download_button(
                    "⬇️ Download Crawl Data (CSV)",
                    data=crawl_csv,
                    file_name=f"crawl_{crawl_url.replace('https://','').replace('http://','').replace('/','_')}.csv",
                    mime="text/csv",
                )
            else:
                st.warning("No pages were crawled. Check the URL and your internet connection.")

    st.markdown("---")
    st.markdown("#### 🔌 Recommended Crawl APIs (for production use)")
    st.markdown(
        "For large sites or commercial projects, consider these dedicated crawling APIs — "
        "they handle JavaScript rendering, rate limits, and scale far better than a lightweight crawler:"
    )

    api_cols = st.columns(3)
    with api_cols[0]:
        st.markdown("**[DataForSEO API](https://dataforseo.com/apis/on-page-api)**")
        st.markdown(
            "Full on-page crawler API with JavaScript support. "
            "Provides all standard SEO fields. Pay-per-use pricing. "
            "Best for programmatic auditing at scale."
        )
    with api_cols[1]:
        st.markdown("**[Screaming Frog API](https://www.screamingfrog.co.uk/seo-spider/api/)**")
        st.markdown(
            "If you already have an SF licence, its built-in scheduling and API let you "
            "trigger crawls and export data in the exact format this tool expects."
        )
    with api_cols[2]:
        st.markdown("**[Ahrefs Site Audit API](https://ahrefs.com/api)**")
        st.markdown(
            "Crawl + backlink data combined. Good if you want to enrich "
            "technical findings with authority and link data in one place."
        )


# ── TAB 7: Google Search Console ──
with tab7:
    st.markdown("### 📈 Google Search Console Integration")
    st.markdown(
        "Connect your GSC property to pull **clicks, impressions, CTR, and average position** "
        "per page and overlay them with your crawl audit data."
    )

    with st.expander("📋 Setup instructions — Service Account (recommended)"):
        st.markdown("""
1. Go to [Google Cloud Console](https://console.cloud.google.com/) → **APIs & Services** → **Enable APIs** → enable **Google Search Console API**.
2. Create a **Service Account**: IAM & Admin → Service Accounts → Create → download the JSON key.
3. In Search Console, go to **Settings → Users and permissions** → Add the service account email with *Restricted* access.
4. Paste the full contents of the JSON key file into the text area below.
        """)

    with st.expander("📋 Alternative — OAuth2 (for personal use)"):
        st.markdown("""
1. In Google Cloud Console, create an **OAuth 2.0 Client ID** (Desktop app).
2. Download `client_secret.json`.
3. Run `gsc_auth.py` (provided separately) once locally to generate `token.json`.
4. Paste the token JSON contents below. Token expires after 1 hour — re-run to refresh.

Install extra dependency: `pip install google-auth google-auth-httplib2 google-api-python-client`
        """)

    gsc_creds = st.text_area(
        "Service Account JSON key (paste full file contents)",
        height=150,
        placeholder='{\n  "type": "service_account",\n  "project_id": "...",\n  ...\n}',
        help="Never commit this to version control. Use Streamlit Secrets in production.",
    )

    gsc_site = st.text_input(
        "GSC Property URL",
        value="https://example.com/",
        help="Must match exactly as it appears in Search Console, including trailing slash.",
    )

    col_d1, col_d2 = st.columns(2)
    with col_d1:
        gsc_start = st.date_input("Start date", value=pd.Timestamp.today() - pd.Timedelta(days=90))
    with col_d2:
        gsc_end = st.date_input("End date", value=pd.Timestamp.today() - pd.Timedelta(days=1))

    gsc_limit = st.slider("Row limit", min_value=100, max_value=25000, value=5000, step=500)

    if st.button("🔗 Fetch Search Console Data"):
        if not gsc_creds.strip():
            st.error("Please paste your Service Account JSON key.")
        elif not gsc_site.startswith("http"):
            st.error("Please enter a valid property URL.")
        else:
            with st.spinner("Connecting to Search Console API…"):
                gsc_df, gsc_err = fetch_gsc_data(
                    credentials_json=gsc_creds,
                    site_url=gsc_site,
                    start_date=str(gsc_start),
                    end_date=str(gsc_end),
                    row_limit=gsc_limit,
                )

            if gsc_err:
                st.error(f"❌ {gsc_err}")
            elif gsc_df is not None and not gsc_df.empty:
                st.success(f"✅ Fetched {len(gsc_df):,} pages from Search Console.")

                # Summary KPIs
                g1, g2, g3, g4 = st.columns(4)
                g1.metric("Total Clicks",       f"{int(gsc_df['Clicks'].sum()):,}")
                g2.metric("Total Impressions",  f"{int(gsc_df['Impressions'].sum()):,}")
                g3.metric("Avg CTR",            f"{gsc_df['CTR'].mean():.2f}%")
                g4.metric("Avg Position",       f"{gsc_df['Avg Position'].mean():.1f}")

                st.markdown("#### Top Pages by Clicks")
                top_pages = gsc_df.sort_values("Clicks", ascending=False).head(20)
                st.dataframe(top_pages, use_container_width=True, hide_index=True)

                # Merge with crawl data if available
                url_col = cols_detected.get("url")
                if url_col:
                    st.markdown("#### 🔗 Merged Crawl + GSC Data")
                    st.markdown(
                        "Crawl issues joined with Search Console performance — "
                        "prioritise fixes on pages that actually get impressions."
                    )
                    merged_df = merge_gsc_with_crawl(df, gsc_df, url_col)
                    st.dataframe(merged_df, use_container_width=True, height=400)

                    merged_csv = merged_df.to_csv(index=False).encode("utf-8")
                    st.download_button(
                        "⬇️ Download Merged Data (CSV)",
                        data=merged_csv,
                        file_name=f"{site_name.replace('.','_')}_crawl_gsc_merged.csv",
                        mime="text/csv",
                    )
                else:
                    st.info("Upload a crawl file with URL data to merge with Search Console results.")

                # Export GSC data
                gsc_csv = gsc_df.to_csv(index=False).encode("utf-8")
                st.download_button(
                    "⬇️ Download GSC Data (CSV)",
                    data=gsc_csv,
                    file_name=f"{site_name.replace('.','_')}_gsc_data.csv",
                    mime="text/csv",
                )
# ── TAB 8: Full Audit Framework ──
with tab8:
 from audit_framework import AUDIT_FRAMEWORK, SEVERITY_ORDER
 from audit_runner import run_all, CHECK_REGISTRY
 from collections import Counter

 st.markdown("### 📋 Full SEO Audit Framework")
 st.markdown(
     f"**{len(AUDIT_FRAMEWORK)} structured checks** across 5 audit areas. "
     f"**{len(CHECK_REGISTRY)} run automatically** on your data — the rest are manual review items "
     "(framework modelled on Lumar + Screaming Frog + Moz best practices)."
 )

 if "manual_state" not in st.session_state:
     st.session_state.manual_state = {}

 with st.spinner("Running framework checks…"):
     framework_results = run_all(df, cols_detected, st.session_state.manual_state)

 # ── KPI bar ──
 status_counts = Counter(r["result_status"] for r in framework_results)
 a, b, c, d, e, f = st.columns(6)
 a.metric("✅ Pass",    status_counts.get("pass", 0))
 b.metric("❌ Fail",    status_counts.get("fail", 0))
 c.metric("⚠️ Warn",    status_counts.get("warn", 0))
 d.metric("👤 Manual",  status_counts.get("manual", 0))
 e.metric("➖ N/A",     status_counts.get("na", 0))
 f.metric("📋 Total",   len(framework_results))

 st.markdown("---")

 # ── Filters ──
 col_f1, col_f2, col_f3 = st.columns(3)
 with col_f1:
     show_all = st.checkbox(
         "Show all checks",
         value=False,
         help="By default only fail/warn results are shown. Tick to see passes, manual review items, and N/A.",
     )
 with col_f2:
     sel_areas = st.multiselect(
         "Filter by area",
         sorted({r["area"] for r in framework_results}),
     )
 with col_f3:
     sel_sev = st.multiselect(
         "Filter by severity",
         ["High", "Medium", "Low", "Info"],
     )

 # Apply filters
 visible = framework_results
 if not show_all:
     visible = [r for r in visible if r["result_status"] in ("fail", "warn", "error")]
 if sel_areas:
     visible = [r for r in visible if r["area"] in sel_areas]
 if sel_sev:
     visible = [r for r in visible if r.get("severity") in sel_sev]

 if not visible:
     if not show_all:
         st.success(
             "🎉 No fail or warn results from automated checks on this data. "
             "Tick **'Show all checks'** above to review the full framework manually."
         )
     else:
         st.info("No checks match your filters.")
 else:
     st.markdown(f"#### Showing {len(visible)} of {len(framework_results)} checks")

     status_order = {"fail": 0, "error": 1, "warn": 2, "manual": 3, "pass": 4, "na": 5}
     visible = sorted(
         visible,
         key=lambda r: (status_order.get(r["result_status"], 9),
                        SEVERITY_ORDER.get(r.get("severity"), 9)),
     )

     grouped = {}
     for r in visible:
         grouped.setdefault(r["area"], []).append(r)

     icons = {"pass": "✅", "fail": "❌", "warn": "⚠️", "manual": "👤", "na": "➖", "error": "⛔"}

     for area, checks in grouped.items():
         st.markdown(f"#### {area} · *{len(checks)} checks*")
         for r in checks:
             icon = icons.get(r["result_status"], "•")
             count_str = f" · `{r['result_count']:,} affected`" if r["result_count"] else ""
             label = f"{icon} **{r['issue']}** — {r.get('severity', '—')}{count_str}"

             with st.expander(label):
                 col_a, col_b = st.columns([2, 1])
                 with col_a:
                     st.markdown(f"**Problem:** {r.get('problem', '—')}")
                     st.markdown(f"**Preferred state:** {r.get('preferred', '—')}")
                     st.markdown(f"**Why it matters:** {r.get('explanation', '—')}")
                     st.markdown(f"**Recommended action:** {r.get('action', '—')}")
                     if r.get("samples"):
                         st.markdown("**Sample affected URLs:**")
                         for s in r["samples"][:5]:
                             st.code(s, language="text")
                 with col_b:
                     st.markdown(f"**Tool:** {r.get('tool', '—')}")
                     st.markdown(f"**Category:** {r.get('category', '—')}")
                     st.markdown(f"**Detail:** {r.get('result_detail', '—')}")

                     st.markdown("---")
                     st.markdown("**Consultant override:**")
                     new_status = st.selectbox(
                         "Status",
                         ["(use auto)", "pass", "fail", "warn", "na"],
                         key=f"override_status_{r['id']}",
                     )
                     notes = st.text_area(
                         "Notes",
                         value=st.session_state.manual_state.get(r["id"], {}).get("notes", ""),
                         key=f"override_notes_{r['id']}",
                         height=80,
                     )
                     if st.button("💾 Save", key=f"save_{r['id']}"):
                         if new_status == "(use auto)":
                             st.session_state.manual_state.pop(r["id"], None)
                         else:
                             st.session_state.manual_state[r["id"]] = {
                                 "status": new_status,
                                 "notes": notes,
                             }
                         st.rerun()

 # ── Export ──
 st.markdown("---")
 st.markdown("### 📤 Export full audit (all checks)")

 framework_df = pd.DataFrame([{
     "Area":        r["area"],
     "Category":    r["category"],
     "Issue":       r["issue"],
     "Severity":    r.get("severity", ""),
     "Tool":        r.get("tool", ""),
     "Status":      r["result_status"],
     "Count":       r["result_count"],
     "Problem":     r.get("problem", ""),
     "Preferred":   r.get("preferred", ""),
     "Explanation": r.get("explanation", ""),
     "Action":      r.get("action", ""),
     "Detail":      r.get("result_detail", ""),
     "Sample URLs": " | ".join(r.get("samples", [])[:5]),
 } for r in framework_results])

 col_x1, col_x2 = st.columns(2)
 with col_x1:
     st.download_button(
         "⬇️ Download Full Audit (CSV)",
         data=framework_df.to_csv(index=False).encode("utf-8"),
         file_name=f"{site_name.replace('.','_')}_full_audit.csv",
         mime="text/csv",
     )
 with col_x2:
     excel_buf = io.BytesIO()
     with pd.ExcelWriter(excel_buf, engine="openpyxl") as writer:
         framework_df.to_excel(writer, sheet_name="Full Audit", index=False)
         for area in framework_df["Area"].unique():
             sheet = area.replace(" ", "_").replace(".", "")[:31]
             framework_df[framework_df["Area"] == area].to_excel(
                 writer, sheet_name=sheet, index=False
             )
     st.download_button(
         "⬇️ Download Full Audit (Excel, multi-sheet)",
         data=excel_buf.getvalue(),
         file_name=f"{site_name.replace('.','_')}_full_audit.xlsx",
         mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
     )
