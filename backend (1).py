"""
backend.py — Logic and data processing for SEO Tech Audit Tool
Strictly uses only data present in the uploaded file. No synthetic data.
"""

import pandas as pd
import io
from pptx import Presentation
from pptx.util import Inches, Pt, Emu
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN
import plotly.express as px
import plotly.graph_objects as go


# ─────────────────────────────────────────────
# COLUMN DETECTION
# ─────────────────────────────────────────────

# Known column aliases mapped to canonical names
COLUMN_ALIASES = {
    "url":            ["url", "address", "page", "page url", "full url", "link"],
    "status_code":    ["status code", "status", "http status", "response code", "code"],
    "title":          ["title", "page title", "meta title", "title tag"],
    "title_length":   ["title length", "title len", "title character count", "title chars"],
    "meta_desc":      ["meta description", "description", "meta desc", "description tag"],
    "meta_desc_length": ["meta description length", "description length", "meta desc length", "description len"],
    "h1":             ["h1", "h1 tag", "h1 text", "h1 1"],
    "h1_count":       ["h1 count", "h1 number", "number of h1", "h1s count"],
    "canonical":      ["canonical", "canonical url", "canonical link", "rel canonical"],
    "indexable":      ["indexable", "is indexable", "index", "indexed"],
    "noindex":        ["noindex", "no index", "robots noindex", "meta robots noindex"],
    "word_count":     ["word count", "words", "content words", "word count (body)"],
    "response_time":  ["response time", "load time", "time (ms)", "response time (ms)", "server response time"],
    "page_size":      ["page size (bytes)", "page size", "size (bytes)", "size bytes", "html size"],
    "depth":          ["crawl depth", "depth", "level", "folder depth"],
    "inlinks":        ["inlinks", "inlinks count", "unique inlinks", "internal links in"],
    "outlinks":       ["outlinks", "outlinks count", "unique outlinks", "internal links out"],
    "images":         ["images", "image count", "total images"],
    "missing_alt":    ["images missing alt text", "missing alt", "alt text missing", "images without alt"],
    "redirect_chain": ["redirect chain", "redirect type", "redirect"],
    "duplicate_title":["duplicate title", "duplicate page title"],
    "duplicate_meta": ["duplicate meta description", "duplicate description"],
    "robots":         ["robots", "x-robots-tag", "meta robots", "robots tag"],
    "sitemap":        ["sitemap", "in sitemap", "xml sitemap"],
    "structured_data":["structured data", "schema", "schema markup", "json-ld"],
    "hreflang":       ["hreflang", "hreflang tag"],
}


def detect_columns(df: pd.DataFrame) -> dict:
    """Map canonical column names to actual DataFrame column names."""
    df_cols_lower = {col.lower().strip(): col for col in df.columns}
    mapping = {}
    for canonical, aliases in COLUMN_ALIASES.items():
        for alias in aliases:
            if alias in df_cols_lower:
                mapping[canonical] = df_cols_lower[alias]
                break
    return mapping


# ─────────────────────────────────────────────
# FILE LOADING
# ─────────────────────────────────────────────

def load_file(uploaded_file) -> tuple[pd.DataFrame | None, str]:
    """Load Excel or CSV file. Returns (df, error_message)."""
    try:
        name = uploaded_file.name.lower()
        if name.endswith(".csv"):
            df = pd.read_csv(uploaded_file, low_memory=False)
        elif name.endswith((".xlsx", ".xls")):
            df = pd.read_excel(uploaded_file, engine="openpyxl" if name.endswith(".xlsx") else "xlrd")
        else:
            return None, "Unsupported file type. Please upload a CSV or Excel file."
        df.columns = df.columns.str.strip()
        return df, ""
    except Exception as e:
        return None, f"Error loading file: {str(e)}"


def get_sheet_names(uploaded_file) -> list[str]:
    """Return sheet names for Excel files."""
    try:
        xl = pd.ExcelFile(uploaded_file, engine="openpyxl")
        return xl.sheet_names
    except Exception:
        return []


def load_sheet(uploaded_file, sheet_name: str) -> tuple[pd.DataFrame | None, str]:
    try:
        df = pd.read_excel(uploaded_file, sheet_name=sheet_name, engine="openpyxl")
        df.columns = df.columns.str.strip()
        return df, ""
    except Exception as e:
        return None, str(e)


def load_all_sheets(uploaded_file) -> tuple[pd.DataFrame | None, str, list[str]]:
    """
    Load ALL sheets from an Excel file and concatenate them.
    Adds a '_sheet' column so rows can be traced back to their source sheet.
    Returns (combined_df, error_message, sheet_names_loaded).
    """
    try:
        engine = "openpyxl" if uploaded_file.name.lower().endswith(".xlsx") else "xlrd"
        xl = pd.ExcelFile(uploaded_file, engine=engine)
        sheet_names = xl.sheet_names
        frames = []
        loaded = []
        for sheet in sheet_names:
            try:
                df_sheet = xl.parse(sheet)
                df_sheet.columns = df_sheet.columns.str.strip()
                if df_sheet.empty:
                    continue
                df_sheet["_sheet"] = sheet
                frames.append(df_sheet)
                loaded.append(sheet)
            except Exception:
                continue  # skip unreadable sheets silently
        if not frames:
            return None, "No readable data found in any sheet.", []
        combined = pd.concat(frames, ignore_index=True, sort=False)
        return combined, "", loaded
    except Exception as e:
        return None, f"Error loading workbook: {str(e)}", []


# ─────────────────────────────────────────────
# CORE ANALYSIS
# ─────────────────────────────────────────────

def analyse(df: pd.DataFrame) -> dict:
    """Run all available analyses based on detected columns."""
    cols = detect_columns(df)
    results = {
        "total_urls": len(df),
        "cols": cols,
        "issues": [],       # list of issue dicts for priority table
        "charts": {},       # plotly figures
        "summaries": {},    # plain-text summaries
        "raw": df,
    }

    # ── Status codes ──
    if "status_code" in cols:
        sc_col = cols["status_code"]
        df[sc_col] = pd.to_numeric(df[sc_col], errors="coerce")
        sc_counts = df[sc_col].value_counts().reset_index()
        sc_counts.columns = ["Status Code", "Count"]
        fig_sc = px.bar(
            sc_counts, x="Status Code", y="Count",
            color="Status Code",
            title="HTTP Status Code Distribution",
            color_continuous_scale="RdYlGn",
        )
        fig_sc.update_layout(showlegend=False)
        results["charts"]["status_codes"] = fig_sc

        errors_4xx = int(df[sc_col].between(400, 499).sum())
        errors_5xx = int(df[sc_col].between(500, 599).sum())
        redirects   = int(df[sc_col].between(300, 399).sum())

        if errors_4xx:
            results["issues"].append({
                "Priority": "🔴 Critical",
                "Issue": "4xx Client Errors",
                "Count": errors_4xx,
                "Impact": "Broken pages harm UX and waste crawl budget",
                "Action": "Fix or redirect all 4xx URLs",
            })
        if errors_5xx:
            results["issues"].append({
                "Priority": "🔴 Critical",
                "Issue": "5xx Server Errors",
                "Count": errors_5xx,
                "Impact": "Server errors block crawling and indexing",
                "Action": "Investigate and resolve server-side errors",
            })
        if redirects:
            results["issues"].append({
                "Priority": "🟡 Medium",
                "Issue": "Redirect Responses",
                "Count": redirects,
                "Impact": "Redirect chains dilute PageRank and slow load",
                "Action": "Audit redirects; eliminate unnecessary chains",
            })
        results["summaries"]["status_codes"] = (
            f"{len(df)} URLs crawled. "
            f"{errors_4xx} 4xx errors, {errors_5xx} 5xx errors, {redirects} redirects."
        )

    # ── Missing / duplicate titles ──
    if "title" in cols:
        t_col = cols["title"]
        missing_title = int(df[t_col].isna().sum() + (df[t_col].astype(str).str.strip() == "").sum())
        dup_title     = int(df[t_col].dropna().duplicated().sum())
        if missing_title:
            results["issues"].append({
                "Priority": "🔴 Critical",
                "Issue": "Missing Title Tags",
                "Count": missing_title,
                "Impact": "Title tags are a top on-page ranking factor",
                "Action": "Add unique, descriptive title tags to all pages",
            })
        if dup_title:
            results["issues"].append({
                "Priority": "🔴 Critical",
                "Issue": "Duplicate Title Tags",
                "Count": dup_title,
                "Impact": "Duplicate titles confuse search engines",
                "Action": "Rewrite titles to be unique per page",
            })
        results["summaries"]["titles"] = (
            f"{missing_title} pages missing title tags. {dup_title} duplicate titles found."
        )

    # ── Title length ──
    if "title_length" in cols:
        tl_col = cols["title_length"]
        df["_tl"] = pd.to_numeric(df[tl_col], errors="coerce")
        too_short = int((df["_tl"] < 30).sum())
        too_long  = int((df["_tl"] > 60).sum())
        fig_tl = px.histogram(
            df.dropna(subset=["_tl"]),
            x="_tl", nbins=30,
            title="Title Tag Length Distribution",
            labels={"_tl": "Characters"},
        )
        fig_tl.add_vline(x=30, line_dash="dash", line_color="orange", annotation_text="Min 30")
        fig_tl.add_vline(x=60, line_dash="dash", line_color="red",    annotation_text="Max 60")
        results["charts"]["title_length"] = fig_tl
        if too_short:
            results["issues"].append({
                "Priority": "🟡 Medium",
                "Issue": "Title Tags Too Short (<30 chars)",
                "Count": too_short,
                "Impact": "Short titles miss keyword opportunities",
                "Action": "Expand titles to 30–60 characters",
            })
        if too_long:
            results["issues"].append({
                "Priority": "🟡 Medium",
                "Issue": "Title Tags Too Long (>60 chars)",
                "Count": too_long,
                "Impact": "Long titles get truncated in SERPs",
                "Action": "Trim titles to under 60 characters",
            })

    # ── Meta descriptions ──
    if "meta_desc" in cols:
        md_col = cols["meta_desc"]
        missing_md = int(df[md_col].isna().sum() + (df[md_col].astype(str).str.strip() == "").sum())
        dup_md     = int(df[md_col].dropna().duplicated().sum())
        if missing_md:
            results["issues"].append({
                "Priority": "🟡 Medium",
                "Issue": "Missing Meta Descriptions",
                "Count": missing_md,
                "Impact": "Missing meta descriptions reduce SERP click-through rate",
                "Action": "Write unique meta descriptions (120–155 chars) per page",
            })
        if dup_md:
            results["issues"].append({
                "Priority": "🟢 Low",
                "Issue": "Duplicate Meta Descriptions",
                "Count": dup_md,
                "Impact": "Duplicate descriptions miss targeting opportunities",
                "Action": "Rewrite for uniqueness; include primary keyword",
            })

    # ── Meta description length ──
    if "meta_desc_length" in cols:
        mdl_col = cols["meta_desc_length"]
        df["_mdl"] = pd.to_numeric(df[mdl_col], errors="coerce")
        md_short = int((df["_mdl"] < 70).sum())
        md_long  = int((df["_mdl"] > 155).sum())
        fig_mdl = px.histogram(
            df.dropna(subset=["_mdl"]),
            x="_mdl", nbins=30,
            title="Meta Description Length Distribution",
            labels={"_mdl": "Characters"},
        )
        fig_mdl.add_vline(x=70,  line_dash="dash", line_color="orange", annotation_text="Min 70")
        fig_mdl.add_vline(x=155, line_dash="dash", line_color="red",    annotation_text="Max 155")
        results["charts"]["meta_desc_length"] = fig_mdl
        if md_short:
            results["issues"].append({
                "Priority": "🟢 Low",
                "Issue": "Meta Descriptions Too Short (<70 chars)",
                "Count": md_short,
                "Impact": "Underutilises SERP real-estate",
                "Action": "Expand meta descriptions to 70–155 characters",
            })
        if md_long:
            results["issues"].append({
                "Priority": "🟢 Low",
                "Issue": "Meta Descriptions Too Long (>155 chars)",
                "Count": md_long,
                "Impact": "Long descriptions get truncated in SERPs",
                "Action": "Trim to under 155 characters",
            })

    # ── H1 tags ──
    if "h1" in cols:
        h1_col = cols["h1"]
        missing_h1 = int(df[h1_col].isna().sum() + (df[h1_col].astype(str).str.strip() == "").sum())
        dup_h1     = int(df[h1_col].dropna().duplicated().sum())
        if missing_h1:
            results["issues"].append({
                "Priority": "🔴 Critical",
                "Issue": "Missing H1 Tags",
                "Count": missing_h1,
                "Impact": "H1 is a primary on-page relevancy signal",
                "Action": "Add one unique H1 per page",
            })
        if dup_h1:
            results["issues"].append({
                "Priority": "🟡 Medium",
                "Issue": "Duplicate H1 Tags",
                "Count": dup_h1,
                "Impact": "Reduces topical differentiation across pages",
                "Action": "Ensure each page has a unique H1",
            })

    # ── H1 count (multiple H1s) ──
    if "h1_count" in cols:
        h1c_col = cols["h1_count"]
        df["_h1c"] = pd.to_numeric(df[h1c_col], errors="coerce")
        multi_h1 = int((df["_h1c"] > 1).sum())
        if multi_h1:
            results["issues"].append({
                "Priority": "🟡 Medium",
                "Issue": "Multiple H1 Tags on Page",
                "Count": multi_h1,
                "Impact": "Multiple H1s dilute heading hierarchy",
                "Action": "Reduce to exactly one H1 per page",
            })

    # ── Indexability ──
    if "indexable" in cols:
        idx_col = cols["indexable"]
        non_indexable = int((df[idx_col].astype(str).str.lower().isin(["false", "no", "0"])).sum())
        indexable_ct  = int((df[idx_col].astype(str).str.lower().isin(["true", "yes", "1"])).sum())
        labels = ["Indexable", "Non-Indexable"]
        values = [indexable_ct, non_indexable]
        fig_idx = px.pie(values=values, names=labels, title="Indexability Breakdown",
                         color_discrete_map={"Indexable": "#22c55e", "Non-Indexable": "#ef4444"})
        results["charts"]["indexability"] = fig_idx
        if non_indexable:
            results["issues"].append({
                "Priority": "🔴 Critical",
                "Issue": "Non-Indexable Pages",
                "Count": non_indexable,
                "Impact": "Pages blocked from index cannot rank",
                "Action": "Audit noindex/robots directives; fix unintentional blocks",
            })
        results["summaries"]["indexability"] = (
            f"{indexable_ct} indexable pages, {non_indexable} non-indexable."
        )

    # ── Response time ──
    if "response_time" in cols:
        rt_col = cols["response_time"]
        df["_rt"] = pd.to_numeric(df[rt_col], errors="coerce")
        slow = int((df["_rt"] > 2000).sum())  # > 2s
        fig_rt = px.histogram(
            df.dropna(subset=["_rt"]), x="_rt", nbins=40,
            title="Server Response Time Distribution (ms)",
            labels={"_rt": "Response Time (ms)"},
        )
        fig_rt.add_vline(x=2000, line_dash="dash", line_color="red", annotation_text="2000ms threshold")
        results["charts"]["response_time"] = fig_rt
        if slow:
            results["issues"].append({
                "Priority": "🔴 Critical",
                "Issue": "Slow Server Response (>2s)",
                "Count": slow,
                "Impact": "Slow TTFB hurts Core Web Vitals and rankings",
                "Action": "Optimise server config, caching, and hosting",
            })
        results["summaries"]["response_time"] = (
            f"Avg response time: {df['_rt'].mean():.0f}ms. {slow} pages exceed 2000ms."
        )

    # ── Images missing alt text ──
    if "missing_alt" in cols:
        alt_col = cols["missing_alt"]
        df["_alt"] = pd.to_numeric(df[alt_col], errors="coerce")
        missing_alt = int((df["_alt"] > 0).sum())
        total_missing = int(df["_alt"].sum())
        if missing_alt:
            results["issues"].append({
                "Priority": "🟡 Medium",
                "Issue": "Images Missing Alt Text",
                "Count": total_missing,
                "Impact": "Alt text is required for accessibility and image SEO",
                "Action": f"Add descriptive alt attributes to images ({missing_alt} pages affected)",
            })

    # ── Word count ──
    if "word_count" in cols:
        wc_col = cols["word_count"]
        df["_wc"] = pd.to_numeric(df[wc_col], errors="coerce")
        thin = int((df["_wc"] < 300).sum())
        fig_wc = px.histogram(
            df.dropna(subset=["_wc"]), x="_wc", nbins=40,
            title="Word Count Distribution",
            labels={"_wc": "Words"},
        )
        fig_wc.add_vline(x=300, line_dash="dash", line_color="orange", annotation_text="Thin <300")
        results["charts"]["word_count"] = fig_wc
        if thin:
            results["issues"].append({
                "Priority": "🟡 Medium",
                "Issue": "Thin Content (<300 words)",
                "Count": thin,
                "Impact": "Thin pages rarely rank and may dilute site quality",
                "Action": "Expand, consolidate, or noindex thin content pages",
            })

    # ── Crawl depth ──
    if "depth" in cols:
        d_col = cols["depth"]
        df["_depth"] = pd.to_numeric(df[d_col], errors="coerce")
        deep = int((df["_depth"] > 4).sum())
        fig_depth = px.histogram(
            df.dropna(subset=["_depth"]), x="_depth", nbins=20,
            title="Crawl Depth Distribution",
            labels={"_depth": "Crawl Depth"},
        )
        results["charts"]["crawl_depth"] = fig_depth
        if deep:
            results["issues"].append({
                "Priority": "🟡 Medium",
                "Issue": "Pages Buried Deep (>4 clicks from homepage)",
                "Count": deep,
                "Impact": "Deep pages receive less PageRank and are crawled less often",
                "Action": "Improve internal linking to reduce depth",
            })

    # ── Canonical ──
    if "canonical" in cols:
        can_col = cols["canonical"]
        missing_can = int(df[can_col].isna().sum() + (df[can_col].astype(str).str.strip() == "").sum())
        if missing_can:
            results["issues"].append({
                "Priority": "🟡 Medium",
                "Issue": "Missing Canonical Tags",
                "Count": missing_can,
                "Impact": "Without canonicals, duplicate content signals are unclear",
                "Action": "Implement self-referencing canonicals on all pages",
            })

    # ── Inlinks (orphan pages) ──
    if "inlinks" in cols:
        il_col = cols["inlinks"]
        df["_il"] = pd.to_numeric(df[il_col], errors="coerce")
        orphans = int((df["_il"] == 0).sum())
        if orphans:
            results["issues"].append({
                "Priority": "🟡 Medium",
                "Issue": "Orphan Pages (0 Internal Inlinks)",
                "Count": orphans,
                "Impact": "Orphans receive no PageRank and are hard to discover",
                "Action": "Add internal links to orphaned pages",
            })

    # ── Sort by priority ──
    priority_order = {"🔴 Critical": 0, "🟡 Medium": 1, "🟢 Low": 2}
    results["issues"].sort(key=lambda x: priority_order.get(x["Priority"], 9))

    # ── Overall score ──
    critical = sum(1 for i in results["issues"] if i["Priority"] == "🔴 Critical")
    medium   = sum(1 for i in results["issues"] if i["Priority"] == "🟡 Medium")
    low      = sum(1 for i in results["issues"] if i["Priority"] == "🟢 Low")
    results["issue_counts"] = {"critical": critical, "medium": medium, "low": low}

    return results


# ─────────────────────────────────────────────
# LIVE CRAWLER  (requests + BeautifulSoup)
# ─────────────────────────────────────────────

def crawl_site(start_url: str, max_pages: int = 200) -> tuple[pd.DataFrame | None, str]:
    """
    Lightweight crawler.  Discovers URLs via sitemap.xml first, then
    follows <a> links.  Returns a DataFrame matching the standard crawl schema.
    Requires: requests, beautifulsoup4, lxml  (add to requirements.txt).
    """
    try:
        import requests
        from bs4 import BeautifulSoup
        from urllib.parse import urljoin, urlparse
        import time
    except ImportError:
        return None, "Missing packages. Add `requests beautifulsoup4 lxml` to requirements.txt and restart."

    headers = {
        "User-Agent": "SEO-Audit-Bot/1.0 (+https://github.com/seo-audit-tool)"
    }
    base = start_url.rstrip("/")
    parsed_base = urlparse(base)
    domain = f"{parsed_base.scheme}://{parsed_base.netloc}"

    visited: set[str] = set()
    queue: list[str] = []
    rows: list[dict] = []

    # ── 1. Try sitemap.xml ──
    for sitemap_url in [f"{domain}/sitemap.xml", f"{domain}/sitemap_index.xml"]:
        try:
            r = requests.get(sitemap_url, headers=headers, timeout=10)
            if r.status_code == 200 and "xml" in r.headers.get("Content-Type", ""):
                soup = BeautifulSoup(r.text, "lxml-xml")
                locs = [loc.text.strip() for loc in soup.find_all("loc")]
                queue.extend(locs[:max_pages])
                break
        except Exception:
            pass

    if not queue:
        queue.append(base)

    # ── 2. Crawl ──
    while queue and len(visited) < max_pages:
        url = queue.pop(0)
        if url in visited:
            continue
        visited.add(url)
        try:
            t0 = time.time()
            r = requests.get(url, headers=headers, timeout=10, allow_redirects=True)
            rt_ms = int((time.time() - t0) * 1000)
            final_url = r.url
            status = r.status_code
            size = len(r.content)
            soup = BeautifulSoup(r.text, "lxml") if status == 200 else None

            title = ""
            meta_desc = ""
            h1_text = ""
            h1_count = 0
            canonical = ""
            word_count = 0
            robots_tag = ""
            imgs_missing_alt = 0

            if soup:
                t = soup.find("title")
                title = t.get_text(strip=True) if t else ""
                md = soup.find("meta", attrs={"name": "description"})
                meta_desc = md["content"].strip() if md and md.get("content") else ""
                h1s = soup.find_all("h1")
                h1_count = len(h1s)
                h1_text = h1s[0].get_text(strip=True) if h1s else ""
                can = soup.find("link", attrs={"rel": "canonical"})
                canonical = can["href"].strip() if can and can.get("href") else ""
                body = soup.find("body")
                word_count = len(body.get_text().split()) if body else 0
                rob = soup.find("meta", attrs={"name": "robots"})
                robots_tag = rob["content"] if rob and rob.get("content") else ""
                imgs_missing_alt = sum(1 for img in soup.find_all("img") if not img.get("alt", "").strip())

                # Enqueue new same-domain links
                for a in soup.find_all("a", href=True):
                    href = urljoin(final_url, a["href"]).split("#")[0].split("?")[0]
                    if href.startswith(domain) and href not in visited and href not in queue:
                        queue.append(href)

            rows.append({
                "URL": final_url,
                "Status Code": status,
                "Title": title,
                "Title Length": len(title),
                "Meta Description": meta_desc,
                "Meta Description Length": len(meta_desc),
                "H1": h1_text,
                "H1 Count": h1_count,
                "Canonical": canonical,
                "Word Count": word_count,
                "Response Time (ms)": rt_ms,
                "Page Size (Bytes)": size,
                "Robots": robots_tag,
                "Images Missing Alt Text": imgs_missing_alt,
                "Indexable": "False" if "noindex" in robots_tag.lower() else "True",
            })
        except Exception as exc:
            rows.append({
                "URL": url, "Status Code": 0,
                "Title": "", "Meta Description": "", "H1": "",
                "Word Count": 0, "Response Time (ms)": 0, "Page Size (Bytes)": 0,
                "Indexable": "Unknown",
            })

    if not rows:
        return None, "No pages could be crawled. Check the URL and try again."

    df = pd.DataFrame(rows)
    return df, ""


# ─────────────────────────────────────────────
# GOOGLE SEARCH CONSOLE  (via google-auth + requests)
# ─────────────────────────────────────────────

def fetch_gsc_data(
    credentials_json: str,
    site_url: str,
    start_date: str,
    end_date: str,
    row_limit: int = 5000,
) -> tuple[pd.DataFrame | None, str]:
    """
    Fetch page-level performance data from Search Console API.

    credentials_json : contents of a Service Account JSON key file
                       (or OAuth client_secret.json — see README).
    site_url         : exact property URL, e.g. "https://example.com/"
    Returns a DataFrame with columns:
        page, clicks, impressions, ctr, position
    """
    try:
        import json, requests as req
        from google.oauth2 import service_account
        from google.auth.transport.requests import Request as GRequest
    except ImportError:
        return None, (
            "Missing packages. Add `google-auth google-auth-httplib2 google-api-python-client` "
            "to requirements.txt and restart."
        )

    try:
        info = json.loads(credentials_json)
        creds = service_account.Credentials.from_service_account_info(
            info,
            scopes=["https://www.googleapis.com/auth/webmasters.readonly"],
        )
        creds.refresh(GRequest())
        token = creds.token
    except Exception as e:
        return None, f"Authentication failed: {e}"

    endpoint = f"https://searchconsole.googleapis.com/webmasters/v3/sites/{site_url}/searchAnalytics/query"
    payload = {
        "startDate": start_date,
        "endDate": end_date,
        "dimensions": ["page"],
        "rowLimit": row_limit,
        "dataState": "all",
    }
    try:
        resp = req.post(
            endpoint,
            json=payload,
            headers={"Authorization": f"Bearer {token}"},
            timeout=30,
        )
        resp.raise_for_status()
        data = resp.json()
    except Exception as e:
        return None, f"API request failed: {e}"

    rows = data.get("rows", [])
    if not rows:
        return None, "No data returned for this date range. Check your property URL and date range."

    records = []
    for row in rows:
        keys = row.get("keys", [])
        records.append({
            "URL": keys[0] if keys else "",
            "Clicks": row.get("clicks", 0),
            "Impressions": row.get("impressions", 0),
            "CTR": round(row.get("ctr", 0) * 100, 2),
            "Avg Position": round(row.get("position", 0), 1),
        })

    df = pd.DataFrame(records)
    return df, ""


def merge_gsc_with_crawl(crawl_df: pd.DataFrame, gsc_df: pd.DataFrame, url_col: str) -> pd.DataFrame:
    """Left-join GSC performance data onto the crawl DataFrame on the URL column."""
    merged = crawl_df.merge(
        gsc_df.rename(columns={"URL": url_col}),
        on=url_col,
        how="left",
    )
    return merged


# ─────────────────────────────────────────────
# POWERPOINT EXPORT
# ─────────────────────────────────────────────

def _hex(h):
    return RGBColor(int(h[0:2],16), int(h[2:4],16), int(h[4:6],16))

NAVY   = _hex("0D1B2A")
TEAL   = _hex("00B4D8")
WHITE  = _hex("FFFFFF")
LIGHT  = _hex("E8F4F8")
RED    = _hex("EF4444")
YELLOW = _hex("F59E0B")
GREEN  = _hex("22C55E")
GRAY   = _hex("64748B")


def _set_bg(slide, prs, color):
    from pptx.util import Emu
    bg = slide.background
    fill = bg.fill
    fill.solid()
    fill.fore_color.rgb = color


def _txt(txBox, text, size, bold=False, color=WHITE, align=PP_ALIGN.LEFT):
    tf = txBox.text_frame
    tf.word_wrap = True
    p = tf.paragraphs[0]
    p.alignment = align
    run = p.add_run()
    run.text = text
    run.font.size = Pt(size)
    run.font.bold = bold
    run.font.color.rgb = color


def _add_textbox(slide, text, l, t, w, h, size=14, bold=False, color=WHITE, align=PP_ALIGN.LEFT):
    txBox = slide.shapes.add_textbox(Inches(l), Inches(t), Inches(w), Inches(h))
    _txt(txBox, text, size, bold, color, align)
    return txBox


def _add_rect(slide, l, t, w, h, color):
    shape = slide.shapes.add_shape(1, Inches(l), Inches(t), Inches(w), Inches(h))
    shape.fill.solid()
    shape.fill.fore_color.rgb = color
    shape.line.fill.background()
    return shape


def build_pptx(results: dict, site_name: str = "Website") -> bytes:
    prs = Presentation()
    prs.slide_width  = Inches(13.33)
    prs.slide_height = Inches(7.5)
    blank = prs.slide_layouts[6]  # blank layout

    issues     = results["issues"]
    total_urls = results["total_urls"]
    ic         = results["issue_counts"]

    # ── Slide 1: Title ──
    s1 = prs.slides.add_slide(blank)
    _set_bg(s1, prs, NAVY)
    _add_rect(s1, 0, 2.8, 13.33, 0.06, TEAL)
    _add_textbox(s1, "TECHNICAL SEO AUDIT", 1.0, 1.2, 11, 1.0, size=40, bold=True, color=TEAL)
    _add_textbox(s1, site_name, 1.0, 2.2, 11, 0.6, size=26, bold=False, color=WHITE)
    _add_textbox(s1, f"Total URLs Analysed: {total_urls:,}", 1.0, 3.2, 5, 0.5, size=16, color=LIGHT)
    _add_textbox(s1,
        f"🔴  {ic['critical']} Critical    🟡  {ic['medium']} Medium    🟢  {ic['low']} Low",
        1.0, 3.9, 10, 0.5, size=18, bold=True, color=WHITE)
    _add_textbox(s1, "Prepared by SEO Audit Tool", 1.0, 6.6, 6, 0.4, size=11, color=GRAY)

    # ── Slide 2: Executive Summary ──
    s2 = prs.slides.add_slide(blank)
    _set_bg(s2, prs, NAVY)
    _add_rect(s2, 0, 0, 13.33, 1.1, _hex("0A2540"))
    _add_textbox(s2, "EXECUTIVE SUMMARY", 0.4, 0.2, 12, 0.7, size=28, bold=True, color=TEAL)

    boxes = [
        (ic["critical"], "Critical Issues", RED,    0.4),
        (ic["medium"],   "Medium Issues",   YELLOW, 4.6),
        (ic["low"],      "Low Issues",      GREEN,  8.8),
    ]
    for val, label, col, left in boxes:
        _add_rect(s2, left, 1.3, 3.8, 2.2, _hex("0A2540"))
        _add_textbox(s2, str(val), left+0.15, 1.4, 3.5, 1.1, size=52, bold=True, color=col)
        _add_textbox(s2, label,   left+0.15, 2.5, 3.5, 0.5, size=14, color=WHITE)

    summaries = list(results["summaries"].values())[:6]
    y = 3.9
    for s in summaries:
        _add_textbox(s2, f"• {s}", 0.4, y, 12.5, 0.45, size=12, color=LIGHT)
        y += 0.43

    # ── Slide 3: Priority Action Plan ──
    s3 = prs.slides.add_slide(blank)
    _set_bg(s3, prs, NAVY)
    _add_rect(s3, 0, 0, 13.33, 1.1, _hex("0A2540"))
    _add_textbox(s3, "PRIORITY ACTION PLAN", 0.4, 0.2, 12, 0.7, size=28, bold=True, color=TEAL)

    headers = ["Priority", "Issue", "Count", "Action"]
    col_x   = [0.3, 1.9, 7.1, 8.6]
    col_w   = [1.4, 5.0, 1.4, 4.4]
    _add_rect(s3, 0.3, 1.15, 12.7, 0.4, _hex("0A2540"))
    for i, (h, x, w) in enumerate(zip(headers, col_x, col_w)):
        _add_textbox(s3, h, x, 1.2, w, 0.35, size=11, bold=True, color=TEAL)

    top_issues = issues[:10]
    row_colors = [_hex("091B30"), _hex("0A2540")]
    y = 1.6
    for idx, issue in enumerate(top_issues):
        row_h = 0.48
        _add_rect(s3, 0.3, y, 12.7, row_h, row_colors[idx % 2])
        p_color = RED if "Critical" in issue["Priority"] else (YELLOW if "Medium" in issue["Priority"] else GREEN)
        _add_textbox(s3, issue["Priority"].split()[0], col_x[0], y+0.06, col_w[0], row_h-0.05, size=11, color=p_color)
        _add_textbox(s3, issue["Issue"],               col_x[1], y+0.06, col_w[1], row_h-0.05, size=10, color=WHITE)
        _add_textbox(s3, str(issue["Count"]),           col_x[2], y+0.06, col_w[2], row_h-0.05, size=10, color=LIGHT)
        _add_textbox(s3, issue["Action"],               col_x[3], y+0.06, col_w[3], row_h-0.05, size=9,  color=LIGHT)
        y += row_h

    # ── Slides 4+: Individual Issue Deep-Dives (Critical first) ──
    critical_issues = [i for i in issues if "Critical" in i["Priority"]][:5]
    medium_issues   = [i for i in issues if "Medium"   in i["Priority"]][:3]

    for issue in critical_issues + medium_issues:
        s = prs.slides.add_slide(blank)
        _set_bg(s, prs, NAVY)
        p_color = RED if "Critical" in issue["Priority"] else YELLOW
        _add_rect(s, 0, 0, 13.33, 1.1, _hex("0A2540"))
        _add_textbox(s, issue["Priority"], 0.4, 0.15, 4, 0.5, size=14, bold=True, color=p_color)
        _add_textbox(s, issue["Issue"], 0.4, 0.55, 12, 0.5, size=22, bold=True, color=WHITE)

        cards = [
            ("AFFECTED PAGES", str(issue["Count"]), 0.4, 1.4),
            ("IMPACT",         issue["Impact"],     3.8, 1.4),
            ("RECOMMENDED ACTION", issue["Action"], 8.2, 1.4),
        ]
        for label, val, lx, ly in cards:
            _add_rect(s, lx, ly, 3.7, 2.4, _hex("0A2540"))
            _add_textbox(s, label, lx+0.2, ly+0.15, 3.3, 0.4, size=10, bold=True, color=TEAL)
            _add_textbox(s, val,   lx+0.2, ly+0.6,  3.3, 1.7, size=13, color=WHITE)

        # Percentage bar
        pct = min(issue["Count"] / max(total_urls, 1), 1.0)
        bar_w = 9.0
        _add_rect(s, 0.4, 4.2, bar_w, 0.3, _hex("1E3A4A"))
        _add_rect(s, 0.4, 4.2, bar_w * pct, 0.3, p_color)
        _add_textbox(s, f"{pct*100:.1f}% of crawled URLs affected",
                     0.4, 4.6, 8, 0.4, size=12, color=LIGHT)

    # ── Final Slide: Next Steps ──
    sf = prs.slides.add_slide(blank)
    _set_bg(sf, prs, NAVY)
    _add_rect(sf, 0, 0, 13.33, 1.1, _hex("0A2540"))
    _add_textbox(sf, "RECOMMENDED NEXT STEPS", 0.4, 0.2, 12, 0.7, size=28, bold=True, color=TEAL)

    steps = [
        ("IMMEDIATE (Week 1–2)",   "🔴 Critical", "Fix 4xx errors, server errors, and any pages blocked from indexing unintentionally. These directly block rankings."),
        ("SHORT TERM (Month 1)",   "🟡 Medium",   "Resolve duplicate titles, missing H1s, thin content, and redirect chains. Use a fix tracker to log progress."),
        ("ONGOING (Month 2–3)",    "🟢 Ongoing",  "Address missing alt text, meta descriptions, canonicals, and crawl depth issues. Build a content expansion plan."),
    ]
    y = 1.4
    cols_s = [0.4, 3.4, 7.2]
    for (title, label, desc), lx in zip(steps, cols_s):
        p_c = RED if "Critical" in label else (YELLOW if "Medium" in label else GREEN)
        _add_rect(sf, lx, y, 3.5, 4.6, _hex("0A2540"))
        _add_rect(sf, lx, y, 3.5, 0.5, p_c)
        _add_textbox(sf, title, lx+0.15, y+0.08, 3.2, 0.4, size=10, bold=True, color=NAVY)
        _add_textbox(sf, desc,  lx+0.15, y+0.65, 3.2, 3.8, size=12, color=LIGHT)

    # ── Serialise ──
    buf = io.BytesIO()
    prs.save(buf)
    buf.seek(0)
    return buf.read()
