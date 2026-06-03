# 🔍 SEO Tech Audit Tool

A focused, practical Streamlit app for SEO consultants to upload crawl data, surface prioritised technical issues, visualise patterns, and export client-ready reports — all from real data only.

---

## What It Does

| Feature | Detail |
|---|---|
| **File upload** | Accepts CSV and Excel (.xlsx / .xls) crawl exports |
| **Auto column detection** | Recognises 20+ standard crawl column names automatically |
| **Priority issue table** | Critical → Medium → Low ranked issues with counts and actions |
| **Charts** | Plotly visualisations for status codes, title lengths, response times, word count, depth, and more |
| **Insights** | Plain-text summaries derived from detected data |
| **CSV export** | Download action table or full crawl data |
| **PowerPoint export** | Client-ready slide deck with title, summary, action plan, and per-issue slides |

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
├── backend.py        ← Data loading, column detection, analysis, PPTX generation
├── requirements.txt  ← Python dependencies
└── README.md         ← This file
```

---

## Supported Input Formats

Any CSV or Excel crawl export that contains standard column names. The tool recognises columns by name (case-insensitive), including common variations used by Screaming Frog, Sitebulb, and manual exports.

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

If a column is not detected, that check is simply skipped — no errors.

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

## PowerPoint Deck Structure

When you click **Generate PowerPoint**, the app produces:

1. **Title slide** — Site name, total URLs, issue count summary
2. **Executive Summary** — KPI blocks (Critical / Medium / Low counts) + key findings
3. **Priority Action Plan** — Table of top 10 issues with priority, count, and recommended action
4. **Issue deep-dives** — One slide per Critical and Medium issue with impact and action cards
5. **Next Steps** — Timeline split into Immediate / Short Term / Ongoing

---

## Tips for Best Results

- Use a **Screaming Frog** full export (File → Export → All) for the richest column coverage
- Ensure your Excel file uses the first row as column headers
- For multi-sheet Excel files, select the relevant sheet in the sidebar
- Enter the client's domain in **Site name** before generating the PowerPoint

---

## Deploying to Streamlit Cloud

1. Push the project to a public GitHub repo
2. Go to [share.streamlit.io](https://share.streamlit.io)
3. Connect your repo and set `app.py` as the entry point
4. Deploy — it will install `requirements.txt` automatically

---

## Requirements

```
streamlit==1.35.0
pandas==2.2.2
openpyxl==3.1.2
plotly==5.22.0
python-pptx==0.6.23
xlrd==2.0.1
```

Python 3.9+ recommended.

---

## Limitations (MVP)

- Does not crawl websites — requires a pre-exported crawl file
- Structured data / hreflang checks require those columns to exist in the export
- Charts are not embedded in the PowerPoint (PPTX generation uses text/shape data only)
- No user authentication or saved sessions

---

## License

MIT — free to use, modify, and distribute.
