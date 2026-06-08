# tab_js_rendering.py
import requests
import streamlit as st
import subprocess
import sys
from bs4 import BeautifulSoup

def ensure_playwright_browsers():
"""Programmatically install Playwright Chromium if not present on Streamlit's server."""
if "playwright_installed" not in st.session_state:
    try:
        import playwright
    except ImportError:
        with st.spinner("Installing playwright library..."):
            subprocess.run([sys.executable, "-m", "pip", "install", "playwright"], check=True)
    
    with st.spinner("Installing headless Chromium browser (takes ~15s on first load)..."):
        try:
            subprocess.run(["playwright", "install", "chromium"], check=True)
            st.session_state["playwright_installed"] = True
        except Exception as e:
            st.error(f"Could not install chromium dependencies: {e}")

def fetch_raw_html(url):
headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
response = requests.get(url, headers=headers, timeout=10)
response.raise_for_status()
return response.text

def fetch_rendered_html(url):
from playwright.sync_api import sync_playwright
with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page()
    page.goto(url, wait_until="networkidle", timeout=15000)
    content = page.content()
    browser.close()
return content

def render(df=None, cols_detected=None, site_name=None):
st.header("⚡ JS Rendering Gap Auditor")
st.markdown(
    "Analyze raw server-side content vs. client-rendered content. "
    "This compares what basic scrapers see (Raw HTML) vs. what users and search engines see (Rendered HTML)."
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
    # Make sure Playwright Chromium is ready on first launch
    ensure_playwright_browsers()

    col1, col2 = st.columns(2)

    raw_html = ""
    rendered_html = ""

    # Fetch Raw HTML
    with col1:
        with st.spinner("Fetching Raw HTML (Requests)..."):
            try:
                raw_html = fetch_raw_html(url)
                st.success("Raw HTML Fetched!")
            except Exception as e:
                st.error(f"Raw Fetch Failed: {e}")

    # Fetch Rendered HTML
    with col2:
        with st.spinner("Executing JS (Playwright)..."):
            try:
                rendered_html = fetch_rendered_html(url)
                st.success("Rendered HTML Fetched!")
            except Exception as e:
                st.error(f"JS Rendering Failed: {e}")

    if raw_html and rendered_html:
        st.markdown("---")
        st.subheader("📊 Rendering Comparison Metrics")

        raw_soup = BeautifulSoup(raw_html, "html.parser")
        rendered_soup = BeautifulSoup(rendered_html, "html.parser")

        raw_text = raw_soup.get_text()
        rendered_text = rendered_soup.get_text()

        raw_word_count = len(raw_text.split())
        rendered_word_count = len(rendered_text.split())

        raw_links = [a.get("href") for a in raw_soup.find_all("a") if a.get("href")]
        rendered_links = [a.get("href") for a in rendered_soup.find_all("a") if a.get("href")]

        raw_title = raw_soup.title.string.strip() if raw_soup.title else "No Title Found"
        rendered_title = rendered_soup.title.string.strip() if rendered_soup.title else "No Title Found"

        # Metrics row
        c1, c2, c3 = st.columns(3)
        
        # Word Count Gap
        word_gap = max(0, 100 - int((raw_word_count / max(1, rendered_word_count)) * 100))
        if word_gap > 30:
            c1.metric("JS Content Gap", f"{word_gap}%", delta=f"-{word_gap}% (Gap)", delta_color="inverse")
        else:
            c1.metric("JS Content Gap", f"{word_gap}%", delta="Healthy Match")

        # Links found
        link_diff = len(rendered_links) - len(raw_links)
        if link_diff > 0:
            c2.metric("Links (Raw vs JS)", f"{len(raw_links)} / {len(rendered_links)}", delta=f"+{link_diff} links found with JS", delta_color="normal")
        else:
            c2.metric("Links (Raw vs JS)", f"{len(raw_links)} / {len(rendered_links)}", delta="Perfect Match")

        # Title Tag Check
        if raw_title == rendered_title:
            c3.metric("Title Tag Match", "MATCHED", delta="Healthy")
        else:
            c3.metric("Title Tag Match", "MISMATCH", delta="Check SEO", delta_color="inverse")

        # Side by side comparison overview
        st.markdown("---")
        st.subheader("🔍 Metadata & Raw Comparison")
        
        col_meta1, col_meta2 = st.columns(2)
        with col_meta1:
            st.markdown("**Raw Server HTML Meta:**")
            st.write(f"- **Title Tag:** `{raw_title}`")
            st.write(f"- **Word Count:** {raw_word_count}")
            st.write(f"- **Discovered Links:** {len(raw_links)}")

        with col_meta2:
            st.markdown("**Rendered DOM Meta:**")
            st.write(f"- **Title Tag:** `{rendered_title}`")
            st.write(f"- **Word Count:** {rendered_word_count}")
            st.write(f"- **Discovered Links:** {len(rendered_links)}")

        with st.expander("View Page Source Comparison"):
            tab_code1, tab_code2 = st.tabs(["Raw Page Source", "Rendered DOM (JS Executed)"])
            with tab_code1:
                st.code(raw_html[:15000] + "\n... [Truncated for readability]", language="html")
            with tab_code2:
                st.code(rendered_html[:15000] + "\n... [Truncated for readability]", language="html")