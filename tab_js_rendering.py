# tab_js_rendering.py
import requests
import streamlit as st
from bs4 import BeautifulSoup

def fetch_raw_data(url):
"""Fetch the raw, server-side HTML response."""
headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
response = requests.get(url, headers=headers, timeout=10)
response.raise_for_status()
return response.text

def fetch_rendered_data(url):
"""
Fetch fully client-rendered data using the free Jina AI Reader API.
This runs Chromium in the cloud, executes JavaScript, and returns JSON.
Requires no keys or compilation dependencies on your Streamlit server!
"""
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

def render(df=None, cols_detected=None, site_name=None):
st.header("⚡ JS Rendering Gap Auditor")
st.markdown(
    "Analyze raw server-side content vs. client-rendered content. "
    "This compares what basic scrapers see (Raw HTML) vs. what search engines and users see (Rendered DOM)."
)

url = st.text_input(
    "URL to audit",
    placeholder="https://example.com",
    value=site_name if site_name and site_name.startswith("http") else "",
)

if not url:
    st.info("Enter a complete URL (including https://) to begin.")
    return

if st.button("Start JS Audit", type="primary"):
    col1, col2 = st.columns(2)

    raw_html = ""
    rendered_data = None

    # Fetch Raw HTML (Server-Side)
    with col1:
        with st.spinner("Fetching Raw Server HTML..."):
            try:
                raw_html = fetch_raw_data(url)
                st.success("✅ Raw Server HTML Fetched!")
            except Exception as e:
                st.error(f"❌ Raw Fetch Failed: {e}")

    # Fetch Rendered Data (Client-Side via Cloud Browser Proxy)
    with col2:
        with st.spinner("Executing JS in Cloud Browser..."):
            try:
                rendered_data = fetch_rendered_data(url)
                st.success("✅ JS-Rendered DOM Fetched!")
            except Exception as e:
                st.error(f"❌ Cloud Rendering Failed: {e}")

    if raw_html and rendered_data:
        st.markdown("---")
        st.subheader("📊 Rendering Comparison Metrics")

        # Parse Raw HTML
        raw_soup = BeautifulSoup(raw_html, "html.parser")
        raw_text = raw_soup.get_text()
        raw_word_count = len(raw_text.split())
        raw_links = list(set([a.get("href") for a in raw_soup.find_all("a") if a.get("href")]))
        raw_title = raw_soup.title.string.strip() if raw_soup.title else "No Title Found"

        # Parse Rendered Data from Cloud
        rendered_title = rendered_data.get("title", "No Title Found").strip()
        rendered_text = rendered_data.get("content", "")
        rendered_word_count = len(rendered_text.split())
        
        # Extract links from Jina link dictionary
        rendered_links_dict = rendered_data.get("links", {})
        rendered_links = list(set(rendered_links_dict.values())) if isinstance(rendered_links_dict, dict) else []

        # Metrics Row
        c1, c2, c3 = st.columns(3)
        
        # 1. Content Gap
        word_gap = max(0, 100 - int((raw_word_count / max(1, rendered_word_count)) * 100))
        if word_gap > 30:
            c1.metric("JS Content Gap", f"{word_gap}%", delta=f"-{word_gap}% (Gap)", delta_color="inverse")
        else:
            c1.metric("JS Content Gap", f"{word_gap}%", delta="Healthy Match")

        # 2. Link Discrepancies
        link_diff = len(rendered_links) - len(raw_links)
        if link_diff > 0:
            c2.metric("Links (Raw vs JS)", f"{len(raw_links)} / {len(rendered_links)}", delta=f"+{link_diff} links hidden in JS", delta_color="normal")
        else:
            c2.metric("Links (Raw vs JS)", f"{len(raw_links)} / {len(rendered_links)}", delta="Perfect Match")

        # 3. Title Tag Check
        if raw_title == rendered_title:
            c3.metric("Title Tag Match", "MATCHED", delta="Healthy")
        else:
            c3.metric("Title Tag Match", "MISMATCH", delta="Check SEO", delta_color="inverse")

        # Side-by-side details
        st.markdown("---")
        st.subheader("🔍 Metadata & Raw Comparison")
        
        col_meta1, col_meta2 = st.columns(2)
        with col_meta1:
            st.markdown("**Raw Server HTML Meta (Scrapers see this):**")
            st.write(f"- **Title Tag:** `{raw_title}`")
            st.write(f"- **Word Count:** {raw_word_count}")
            st.write(f"- **Discovered Links:** {len(raw_links)}")

        with col_meta2:
            st.markdown("**Rendered DOM Meta (Users & Google see this):**")
            st.write(f"- **Title Tag:** `{rendered_title}`")
            st.write(f"- **Word Count:** {rendered_word_count}")
            st.write(f"- **Discovered Links:** {len(rendered_links)}")

        with st.expander("View Page Source Comparison"):
            tab_code1, tab_code2 = st.tabs(["Raw Page Source", "Rendered Content (Markdown)"])
            with tab_code1:
                st.code(raw_html[:15000] + "\n... [Truncated for readability]", language="html")
            with tab_code2:
                st.code(rendered_text[:15000] + "\n... [Truncated for readability]", language="markdown")
