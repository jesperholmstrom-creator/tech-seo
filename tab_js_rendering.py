# tab_js_rendering.py
import requests
import streamlit as st
import pandas as pd
import io
from bs4 import BeautifulSoup

def fetch_raw_data(url):
"""Fetch the raw, server-side HTML response."""
headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
response = requests.get(url, headers=headers, timeout=10)
response.raise_for_status()
return response.text

def fetch_rendered_data(url):
"""Fetch fully client-rendered data using the free Jina AI Reader API.
Runs Chromium in the cloud, executes JavaScript, and returns JSON."""
jina_url = f"https://r.jina.ai/{url}"
headers = {
    "Accept": "application/json",
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
}
response = requests.get(jina_url, headers=headers, timeout=20)
response.raise_for_status()
json_data = response.json()
if json_data.get("code") == 200 and "data" in json_data:
    return json_data["data"]
else:
    raise ValueError(json_data.get("message", "Failed to fetch rendered data from cloud proxy."))

def detect_js_framework(html):
"""Scan the raw HTML for signatures of client-side frameworks."""
html_low = html.lower()
if 'id="root"' in html_low or 'id="__next"' in html_low or 'react-data' in html_low or '_react' in html_low:
    return "React / Next.js"
elif 'vue' in html_low or 'data-v-' in html_low or 'id="__nuxt"' in html_low:
    return "Vue.js / Nuxt.js"
elif 'ng-version' in html_low or 'ng-app' in html_low or 'angular' in html_low:
    return "Angular"
elif 'svelte' in html_low:
    return "Svelte"
return "Unknown/Standard HTML"

def parse_sitemap_urls(sitemap_url):
"""Fetch sitemap.xml and parse all URL location tags."""
headers = {"User-Agent": "Mozilla/5.0"}
response = requests.get(sitemap_url, headers=headers, timeout=15)
response.raise_for_status()
soup = BeautifulSoup(response.text, "xml")
urls = [loc.text.strip() for loc in soup.find_all("loc") if loc.text]
return urls

def parse_uploaded_file(uploaded_file):
"""Parses URLs from an uploaded .txt or Excel file."""
urls = []
filename = uploaded_file.name.lower()

if filename.endswith(".txt"):
    bytes_data = uploaded_file.read()
    lines = bytes_data.decode("utf-8").split("\n")
    urls = [line.strip() for line in lines if line.strip().startswith("http")]
elif filename.endswith(".xlsx") or filename.endswith(".xls"):
    df_upload = pd.read_excel(uploaded_file)
    # Find column containing URL or default to first column
    url_col = None
    for col in df_upload.columns:
        if "url" in str(col).lower():
            url_col = col
            break
    if url_col is None:
        url_col = df_upload.columns[0]
        
    urls = [str(val).strip() for val in df_upload[url_col].dropna() if str(val).strip().startswith("http")]
    
return urls

def scan_hidden_blocks(raw_html, raw_soup, rendered_text):
"""Scans the page structure for collapsible segments and accordions."""
detected_blocks = []
html_low = raw_html.lower()

details_tags = raw_soup.find_all("details")
if details_tags:
    detected_blocks.append({
        "block_type": "Native Collapsible Block (<details>)",
        "count": len(details_tags),
        "severity": "🟢 Google-Safe",
        "desc": f"Found {len(details_tags)} HTML-native collapsibles. Search engines can index this easily."
    })

js_acc_count = 0
keywords = ["accordion", "collapsible", "faq-question", "faq-answer", "toggle-content", "read-more", "readmore-wrap"]
for kw in keywords:
    elements = raw_soup.find_all(class_=lambda c: c and kw in c.lower()) or raw_soup.find_all(id=lambda i: i and kw in i.lower())
    if elements:
        js_acc_count += len(elements)
        
if js_acc_count > 0:
    detected_blocks.append({
        "block_type": "Custom JS Accordion / FAQ Block",
        "count": js_acc_count,
        "severity": "🟡 Review Recommended",
        "desc": f"Discovered {js_acc_count} custom collapsible elements. If content inside loads dynamically post-click, bots will miss it."
    })

tab_count = len(raw_soup.find_all(class_=lambda c: c and "tab-content" in c.lower() or "tab-pane" in c.lower()))
if tab_count > 0:
    detected_blocks.append({
        "block_type": "Tabbed Navigation Container",
        "count": tab_count,
        "severity": "🟡 Review Recommended",
        "desc": f"Detected {tab_count} tab panels. Standard crawlers only read the active tab on load."
    })

if "faqpage" in html_low:
    detected_blocks.append({
        "block_type": "Structured FAQ Schema (JSON-LD)",
        "count": 1,
        "severity": "🟢 Good Metadata",
        "desc": "FAQ Page structured data found. Google can index this directly."
    })

return detected_blocks

def export_to_excel_buffer(df):
"""Compiles a Pandas DataFrame into a styled Excel file stream."""
output = io.BytesIO()
with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
    df.to_excel(writer, sheet_name='JS SEO Audit Report', index=False)
    workbook  = writer.book
    worksheet = writer.sheets['JS SEO Audit Report']
    
    header_format = workbook.add_format({
        'bold': True,
        'text_wrap': True,
        'valign': 'vcenter',
        'align': 'center',
        'fg_color': '#1E293B',
        'font_color': '#FFFFFF',
        'border': 1
    })
    
    for col_num, value in enumerate(df.columns.values):
        worksheet.write(0, col_num, value, header_format)
        max_len = max(df[value].astype(str).map(len).max(), len(value)) + 3
        worksheet.set_column(col_num, col_num, min(max_len, 60))
        
output.seek(0)
return output

def audit_single_page(url):
"""Executes comparison audit on a single URL."""
try:
    raw_html = fetch_raw_data(url)
    rendered_data = fetch_rendered_data(url)
except Exception as e:
    return {"URL": url, "Status": "Error", "Error Details": str(e)}

raw_soup = BeautifulSoup(raw_html, "html.parser")
raw_text = raw_soup.get_text()
raw_word_count = len(raw_text.split())
raw_links = list(set([a.get("href") for a in raw_soup.find_all("a") if a.get("href")]))
raw_title = raw_soup.title.string.strip() if raw_soup.title else "No Title Found"

raw_desc = "No Description Found"
meta_desc_tag = raw_soup.find("meta", attrs={"name": "description"}) or raw_soup.find("meta", attrs={"property": "og:description"})
if meta_desc_tag:
    raw_desc = meta_desc_tag.get("content", "").strip()

rendered_title = rendered_data.get("title", "No Title Found").strip()
rendered_text = rendered_data.get("content", "")
rendered_word_count = len(rendered_text.split())
rendered_desc = rendered_data.get("description", "No Description Found").strip()

rendered_links_dict = rendered_data.get("links", {})
rendered_links = list(set(rendered_links_dict.values())) if isinstance(rendered_links_dict, dict) else []

word_gap = max(0, 100 - int((raw_word_count / max(1, rendered_word_count)) * 100))
js_only_links = [link for link in rendered_links if link not in raw_links]
title_match = "MATCHED" if raw_title == rendered_title else "MISMATCH"
framework = detect_js_framework(raw_html)

scanned_blocks = scan_hidden_blocks(raw_html, raw_soup, rendered_text)

severity = "🟢 Healthy"
if word_gap > 35 or len(js_only_links) > 15:
    severity = "🔴 Critical"
elif word_gap > 10 or len(js_only_links) > 0:
    severity = "🟡 Medium"

return {
    "URL": url,
    "Status": "Success",
    "Raw Word Count": raw_word_count,
    "Rendered Word Count": rendered_word_count,
    "JS Content Gap (%)": word_gap,
    "Raw Links": len(raw_links),
    "Rendered Links": len(rendered_links),
    "JS-Only Links Count": len(js_only_links),
    "Title Match": title_match,
    "Raw Title": raw_title,
    "Rendered Title": rendered_title,
    "Raw Description": raw_desc,
    "Rendered Description": rendered_desc,
    "Detected Framework": framework,
    "Severity Level": severity,
    "js_only_links_list": js_only_links,
    "raw_html": raw_html,
    "rendered_text": rendered_text,
    "scanned_blocks": scanned_blocks
}

def run_batch_audit(urls, max_urls):
"""Runs progress-tracked batch audits on a list of URLs."""
results = []
progress_bar = st.progress(0.0)
status_text = st.empty()

for i, url in enumerate(urls[:max_urls]):
    status_text.text(f"Auditing URL ({i+1}/{max_urls}): {url}")
    res = audit_single_page(url)
    results.append(res)
    progress_bar.progress((i + 1) / max_urls)

status_text.success("🎉 Batch Audit Complete!")
report_df = pd.DataFrame(results)
return report_df

def render_batch_report_ui(report_df):
"""Aggregates batch data and renders the final styled Excel report."""
display_df = report_df.drop(columns=["js_only_links_list", "raw_html", "rendered_text", "Status", "scanned_blocks"], errors="ignore")

# ── EXECUTIVE SUMMARY / SUMMETRIC CARD ──
st.markdown("---")
st.subheader("📊 Executive Batch Summary")

total_audited = len(report_df)
avg_gap = int(report_df["JS Content Gap (%)"].mean()) if "JS Content Gap (%)" in report_df.columns else 0
total_hidden_links = report_df["JS-Only Links Count"].sum() if "JS-Only Links Count" in report_df.columns else 0
title_mismatches = len(report_df[report_df["Title Match"] == "MISMATCH"]) if "Title Match" in report_df.columns else 0

col_sum1, col_meta2, col_sum3, col_sum4 = st.columns(4)
col_sum1.metric("URLs Audited", total_audited)
col_meta2.metric("Avg Content Gap", f"{avg_gap}%", delta="High Risk" if avg_gap > 30 else None, delta_color="inverse")
col_sum3.metric("Hidden Links Discovered", total_hidden_links, delta=f"+{total_hidden_links} links" if total_hidden_links > 0 else None)
col_sum4.metric("Title Gaps Found", title_mismatches)

st.markdown("---")
st.subheader("📋 Detailed Audit Report")
st.dataframe(display_df, use_container_width=True)

# Excel Download
excel_buffer = export_to_excel_buffer(display_df)
st.download_button(
    label="📥 Download Excel Report",
    data=excel_buffer,
    file_name="js_seo_batch_audit_report.xlsx",
    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    type="secondary"
)

def render(df=None, cols_detected=None, site_name=None):
st.header("⚡ JS Rendering Gap Auditor")

audit_mode = st.radio("Choose Audit Mode", ["Single URL", "Sitemap XML", "Upload File (.txt, .xlsx)"], horizontal=True)

if audit_mode == "Single URL":
    url = st.text_input("URL to audit", placeholder="https://example.com")
    if not url:
        st.info("Enter a complete URL to begin.")
        return

    if st.button("Start JS Audit", type="primary"):
        with st.spinner("Analyzing DOM..."):
            res = audit_single_page(url)
            if res["Status"] == "Error":
                st.error(f"Audit failed: {res['Error Details']}")
                return
            
            # Render Metrics
            c1, c2, c3 = st.columns(3)
            c1.metric("JS Content Gap", f"{res['JS Content Gap (%)']}%", delta_color="inverse")
            c2.metric("Links (Raw vs JS)", f"{res['Raw Links']} / {res['Rendered Links']}")
            c3.metric("Title Tag Match", res["Title Match"])

            # FAQ Block scanner display
            st.markdown("---")
            st.subheader("🧩 Hidden Blocks & FAQ Self-Audit")
            if res["scanned_blocks"]:
                for block in res["scanned_blocks"]:
                    if "🟢" in block["severity"]:
                        st.success(f"**{block['block_type']}** (Found: {block['count']})")
                    else:
                        st.warning(f"⚠️ **{block['block_type']}** (Found: {block['count']})")
                    st.markdown(block["desc"])
            else:
                st.info("No interactive widgets discovered.")

elif audit_mode == "Sitemap XML":
    sitemap_url = st.text_input("Sitemap XML URL", placeholder="https://example.com/sitemap.xml")
    max_urls = st.slider("Max URLs to audit", 3, 20, 5)

    if sitemap_url:
        if st.button("Start Sitemap XML Audit", type="primary"):
            try:
                with st.spinner("Fetching sitemap..."):
                    urls = parse_sitemap_urls(sitemap_url)
            except Exception as e:
                st.error(f"Failed to parse sitemap: {e}")
                return

            st.info(f"Discovered {len(urls)} URLs. Commencing audit...")
            report_df = run_batch_audit(urls, max_urls)
            render_batch_report_ui(report_df)

else:
    # File Upload Mode
    uploaded_file = st.file_uploader("Upload list of URLs", type=["txt", "xlsx", "xls"])
    max_urls = st.slider("Max URLs to audit (Avoids API limits)", 3, 20, 5)

    if uploaded_file:
        try:
            urls = parse_uploaded_file(uploaded_file)
            st.success(f"Successfully parsed {len(urls)} URLs from your file!")
        except Exception as e:
            st.error(f"Failed to read file: {e}")
            return

        if st.button("Start File Batch Audit", type="primary"):
            report_df = run_batch_audit(urls, max_urls)
            render_batch_report_ui(report_df)
