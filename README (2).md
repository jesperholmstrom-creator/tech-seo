# 🔍 SEO Tech Audit Tool

A focused, practical Streamlit app for SEO consultants to upload crawl data, surface prioritised technical issues, visualise patterns, and export client-ready reports — all from real data only.

---

## What's New

| Feature | Detail |
|---|---|
| **Multi-sheet Excel** | Choose a single sheet *or* merge all sheets into one combined analysis |
| **Live Crawler** | Crawl any site directly — no file needed. Discovers pages via sitemap.xml then follows links |
| **GSC Integration** | Connect Google Search Console via Service Account to pull clicks, impressions, CTR, and position per page, then merge with crawl data |

---

## What It Does

| Feature | Detail |
|---|---|
| **File upload** | Accepts CSV and Excel (.xlsx / .xls) crawl exports |
| **Multi-sheet merge** | Analyses all sheets in an Excel workbook as one dataset (adds `_sheet` column for traceability) |
| **Auto column detection** | Recognises 20+ standard crawl column names automatically |
| **Priority issue table** | Critical → Medium → Low ranked issues with counts and actions |
| **Charts** | Plotly visualisations for status codes, title lengths, response times, word count, depth, and more |
| **Insights** | Plain-text summaries derived from detected data |
| **CSV export** | Download action table, full crawl data, or merged GSC+crawl data |
| **PowerPoint export** | Client-ready slide deck with title, summary, action plan, and per-issue slides |
| **Live crawl** | Built-in `requests`+`BeautifulSoup` crawler with sitemap discovery |
| **Search Console** | OAuth2 Service Account integration for GSC performance data |

> **Data integrity rule:** The app only analyses and surfaces findings from the data present in your file. It never invents, assumes, or supplements with external data.

---

## Quickstart

### 1. Clone / download the project

```bash
git clone https://github.com/YOUR_USERNAME/seo-audit-tool.git
cd seo-audit-tool
```

### 2. (Optional) Create a virtual environment

```bash
python -m venv venv
source venv/bin/activate        # macOS/Linux
venv\Scripts\activate           # Windows
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Run the app

```bash
streamlit run app.py
```

The app opens at `http://localhost:8501`.

---

## File Structure

```
seo-audit-tool/
├── app.py            ← Streamlit UI and page layout
├── backend.py        ← Data loading, column detection, analysis, crawler, GSC, PPTX generation
├── requirements.txt  ← Python dependencies
└── README.md         ← This file
```

---

## Multi-Sheet Excel Support

When you upload an Excel file, the sidebar now offers:

- **📂 All Sheets (merged)** — concatenates every sheet into one DataFrame. A `_sheet` column is added so you can filter by source sheet in the Raw Data tab.
- **Individual sheet** — analyse a single sheet as before.

Sheets that are empty or unreadable are silently skipped.

---

## Live Crawler (Tab 6)

The built-in crawler is designed for quick audits without needing Screaming Frog:

1. Enter a start URL (e.g. `https://example.com`)
2. Set the page cap (10–500 pages)
3. Click **Start Crawl**

**How it works:**
- Checks `sitemap.xml` and `sitemap_index.xml` first to seed the URL queue
- Falls back to link-following if no sitemap is found
- Extracts: URL, status code, title, meta description, H1, canonical, word count, response time, page size, robots tag, images missing alt text, indexability
- Runs the same issue-detection analysis on crawl results

### Recommended APIs for production crawling

| API | Best for |
|---|---|
| [DataForSEO On-Page API](https://dataforseo.com/apis/on-page-api) | Large-scale programmatic audits, JavaScript rendering |
| [Screaming Frog API](https://www.screamingfrog.co.uk/seo-spider/api/) | Existing SF licence holders; exact column compatibility |
| [Ahrefs Site Audit API](https://ahrefs.com/api) | Combined technical + backlink data |

---

## Google Search Console Integration (Tab 7)

### Setup (Service Account — recommended)

1. Go to [Google Cloud Console](https://console.cloud.google.com/) → **APIs & Services** → Enable **Google Search Console API**
2. Create a **Service Account** → download the JSON key file
3. In Search Console: **Settings → Users and permissions** → add the service account email (*Restricted* access)
4. Paste the full JSON key contents into the text area in the app

### What you get

- Clicks, impressions, CTR, and average position per page for your chosen date range
- Top pages ranked by clicks
- **Merged view**: crawl issues joined to GSC performance data — so you can prioritise fixes on pages that actually receive traffic

### Security note

Never commit your Service Account JSON to version control. When deploying to Streamlit Cloud, use [Streamlit Secrets](https://docs.streamlit.io/deploy/streamlit-community-cloud/deploy-your-app/secrets-management):

```toml
# .streamlit/secrets.toml
[gsc]
credentials = '''
{ "type": "service_account", ... }
'''
```

Then read it in code with `st.secrets["gsc"]["credentials"]`.

---

## Supported Input Formats

Any CSV or Excel crawl export that contains standard column names.

### Detected column types

| SEO Field | Example column names recognised |
|---|---|
| URL | `URL`, `Address`, `Page URL` |
| HTTP Status | `Status Code`, `Response Code`, `HTTP Status` |
| Title Tag | `Title`, `Page Title`, `Meta Title` |
| Title Length | `Title Length`, `Title Chars` |
| Meta Description | `Meta Description`, `Description Tag` |
| Meta Desc Length | `Meta Description Length`, `Description Len` |
| H1 Tag | `H1`, `H1 Tag`, `H1 Text` |
| H1 Count | `H1 Count`, `Number of H1` |
| Canonical | `Canonical`, `Canonical URL` |
| Indexable | `Indexable`, `Is Indexable` |
| Word Count | `Word Count`, `Content Words` |
| Response Time | `Response Time (ms)`, `Load Time` |
| Page Size | `Page Size (Bytes)`, `Size Bytes` |
| Crawl Depth | `Crawl Depth`, `Depth`, `Level` |
| Inlinks | `Inlinks`, `Unique Inlinks` |
| Images Missing Alt | `Images Missing Alt Text`, `Missing Alt` |

---

## Issues Detected

### 🔴 Critical
- 4xx Client Errors
- 5xx Server Errors
- Missing Title Tags
- Duplicate Title Tags
- Missing H1 Tags
- Non-Indexable Pages
- Slow Server Response (>2 seconds)

### 🟡 Medium
- Redirect Responses
- Duplicate H1 Tags
- Multiple H1 Tags on a Page
- Title Tags Too Short or Too Long
- Thin Content (<300 words)
- Pages Buried Deep (>4 crawl depth)
- Missing Canonical Tags
- Orphan Pages (0 inlinks)
- Images Missing Alt Text

### 🟢 Low
- Missing Meta Descriptions
- Duplicate Meta Descriptions
- Meta Descriptions Too Short or Too Long

---

## Requirements

```
streamlit==1.35.0
pandas==2.2.2
openpyxl==3.1.2
plotly==5.22.0
python-pptx==0.6.23
xlrd==2.0.1
requests>=2.31.0
beautifulsoup4>=4.12.0
lxml>=5.2.0
google-auth>=2.29.0
google-auth-httplib2>=0.2.0
google-api-python-client>=2.127.0
```

Python 3.9+ recommended.

---

## Deploying to Streamlit Cloud

1. Push the project to a public GitHub repo
2. Go to [share.streamlit.io](https://share.streamlit.io)
3. Connect your repo and set `app.py` as the entry point
4. Deploy — it will install `requirements.txt` automatically
5. Add your GSC Service Account JSON to Streamlit Secrets

---

## License

MIT — free to use, modify, and distribute.
