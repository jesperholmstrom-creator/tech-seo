# audit_runner.py
"""
Maps each framework check to an evaluator function.
Each evaluator returns: {"status": "pass"|"fail"|"warn"|"na", "count": int, "samples": list[str], "detail": str}
"""

import pandas as pd
from urllib.parse import urlparse
from audit_framework import AUDIT_FRAMEWORK

# ─────────────────────────────────────────────
# Result helper
# ─────────────────────────────────────────────

def _result(status, count=0, samples=None, detail=""):
    return {"status": status, "count": count,
            "samples": (samples or [])[:10], "detail": detail}

def _na(reason="Required column not in crawl"):
    return _result("na", detail=reason)

    # ─────────────────────────────────────────────
    # CHECK FUNCTIONS  (one per auto_check key)
    # ─────────────────────────────────────────────

def check_non_https_urls(df, cols, ctx):
    if "url" not in cols:
        return _na()
    url_col = cols["url"]
    bad = df[df[url_col].astype(str).str.startswith("http://")]
    if bad.empty:
        return _result("pass", detail="All URLs use HTTPS.")
    return _result("fail", count=len(bad),
                   samples=bad[url_col].head(10).tolist(),
                   detail=f"{len(bad)} HTTP URLs found.")

def check_errors_4xx(df, cols, ctx):
    if "status_code" not in cols:
        return _na()
    sc = pd.to_numeric(df[cols["status_code"]], errors="coerce")
    bad = df[sc.between(400, 499)]
    if bad.empty:
        return _result("pass", detail="No 4xx errors.")
    return _result("fail", count=len(bad),
                   samples=bad[cols.get("url", df.columns[0])].head(10).tolist(),
                   detail=f"{len(bad)} URLs return 4xx.")

def check_errors_5xx(df, cols, ctx):
    if "status_code" not in cols:
        return _na()
    sc = pd.to_numeric(df[cols["status_code"]], errors="coerce")
    bad = df[sc.between(500, 599)]
    if bad.empty:
        return _result("pass", detail="No 5xx errors.")
    return _result("fail", count=len(bad),
                   samples=bad[cols.get("url", df.columns[0])].head(10).tolist(),
                   detail=f"{len(bad)} URLs return 5xx.")

def check_title_missing(df, cols, ctx):
    if "title" not in cols:
        return _na()
    t = df[cols["title"]].astype(str).str.strip()
    bad = df[(t == "") | (t == "nan")]
    return (_result("pass", detail="All pages have titles.") if bad.empty
            else _result("fail", count=len(bad),
                         samples=bad[cols.get("url", df.columns[0])].head(10).tolist(),
                         detail=f"{len(bad)} pages missing titles."))

def check_title_duplicate(df, cols, ctx):
    if "title" not in cols:
        return _na()
    titles = df[cols["title"]].dropna().astype(str).str.strip()
    titles = titles[titles != ""]
    dup_mask = titles.duplicated(keep=False)
    n = int(dup_mask.sum())
    if n == 0:
        return _result("pass", detail="All titles unique.")
    samples = titles[dup_mask].head(10).tolist()
    return _result("fail", count=n, samples=samples,
                   detail=f"{n} pages share duplicate titles.")

def check_title_too_short(df, cols, ctx):
    if "title" not in cols:
        return _na()
    lens = df[cols["title"]].astype(str).str.len()
    n = int((lens.between(1, 29)).sum())
    return _result("warn" if n else "pass", count=n,
                   detail=f"{n} titles < 30 characters.")

def check_title_too_long(df, cols, ctx):
    if "title" not in cols:
        return _na()
    lens = df[cols["title"]].astype(str).str.len()
    n = int((lens > 60).sum())
    return _result("warn" if n else "pass", count=n,
                   detail=f"{n} titles > 60 characters.")

def check_h1_missing(df, cols, ctx):
    if "h1" not in cols:
        return _na()
    h = df[cols["h1"]].astype(str).str.strip()
    bad = df[(h == "") | (h == "nan")]
    return (_result("pass") if bad.empty
            else _result("fail", count=len(bad),
                         samples=bad[cols.get("url", df.columns[0])].head(10).tolist()))

def check_h1_duplicate(df, cols, ctx):
    if "h1" not in cols:
        return _na()
    h = df[cols["h1"]].dropna().astype(str).str.strip()
    h = h[h != ""]
    n = int(h.duplicated(keep=False).sum())
    return _result("warn" if n else "pass", count=n,
                   detail=f"{n} pages share duplicate H1.")

def check_h1_multiple(df, cols, ctx):
    if "h1_count" not in cols:
        return _na()
    c = pd.to_numeric(df[cols["h1_count"]], errors="coerce")
    n = int((c > 1).sum())
    return _result("warn" if n else "pass", count=n)

def check_md_missing(df, cols, ctx):
    if "meta_desc" not in cols:
        return _na()
    m = df[cols["meta_desc"]].astype(str).str.strip()
    bad = df[(m == "") | (m == "nan")]
    return (_result("pass") if bad.empty
            else _result("warn", count=len(bad),
                         samples=bad[cols.get("url", df.columns[0])].head(10).tolist()))

def check_md_duplicate(df, cols, ctx):
    if "meta_desc" not in cols:
        return _na()
    m = df[cols["meta_desc"]].dropna().astype(str).str.strip()
    m = m[m != ""]
    n = int(m.duplicated(keep=False).sum())
    return _result("warn" if n else "pass", count=n)

def check_canonical_missing(df, cols, ctx):
    if "canonical" not in cols:
        return _na()
    c = df[cols["canonical"]].astype(str).str.strip()
    bad = df[(c == "") | (c == "nan")]
    return (_result("pass") if bad.empty
            else _result("warn", count=len(bad)))

def check_canonical_self_referencing(df, cols, ctx):
    if "canonical" not in cols or "url" not in cols:
        return _na()
    self_ref = (df[cols["canonical"]].astype(str).str.strip() ==
                df[cols["url"]].astype(str).str.strip())
    n = int(self_ref.sum())
    return _result("pass" if n else "warn", count=n,
                   detail=f"{n} pages have self-referencing canonical.")

def check_non_indexable_pages(df, cols, ctx):
    if "indexable" not in cols:
        return _na()
    val = df[cols["indexable"]].astype(str).str.lower()
    bad = df[val.isin(["false", "no", "0", "non-indexable"])]
    return (_result("pass") if bad.empty
            else _result("warn", count=len(bad),
                         samples=bad[cols.get("url", df.columns[0])].head(10).tolist()))

def check_meta_noindex(df, cols, ctx):
    if "robots" not in cols:
        return _na()
    bad = df[df[cols["robots"]].astype(str).str.contains("noindex", case=False, na=False)]
    return (_result("pass") if bad.empty else _result("warn", count=len(bad)))

def check_orphans(df, cols, ctx):
    if "inlinks" not in cols:
        return _na()
    il = pd.to_numeric(df[cols["inlinks"]], errors="coerce")
    n = int((il == 0).sum())
    return _result("warn" if n else "pass", count=n)

def check_empty_pages(df, cols, ctx):
    if "word_count" not in cols:
        return _na()
    wc = pd.to_numeric(df[cols["word_count"]], errors="coerce")
    n = int((wc < 100).sum())
    return _result("fail" if n else "pass", count=n,
                   detail=f"{n} pages with < 100 words.")

def check_url_underscore(df, cols, ctx):
    if "url" not in cols:
        return _na()
    n = int(df[cols["url"]].astype(str).str.contains("_").sum())
    return _result("warn" if n else "pass", count=n)

def check_url_capitals(df, cols, ctx):
    if "url" not in cols:
        return _na()
    s = df[cols["url"]].astype(str)
    paths = s.apply(lambda u: urlparse(u).path)
    n = int(paths.str.contains(r"[A-Z]").sum())
    return _result("warn" if n else "pass", count=n)

def check_url_double_slash(df, cols, ctx):
    if "url" not in cols:
        return _na()
    s = df[cols["url"]].astype(str)
    paths = s.apply(lambda u: urlparse(u).path)
    n = int(paths.str.contains(r"//").sum())
    return _result("warn" if n else "pass", count=n)

def check_url_too_long(df, cols, ctx):
    if "url" not in cols:
        return _na()
    n = int((df[cols["url"]].astype(str).str.len() > 115).sum())
    return _result("warn" if n else "pass", count=n)

def check_url_with_params(df, cols, ctx):
    if "url" not in cols:
        return _na()
    n = int(df[cols["url"]].astype(str).str.contains(r"\?").sum())
    return _result("warn" if n else "pass", count=n)

def check_img_missing_alt(df, cols, ctx):
    if "missing_alt" not in cols:
        return _na()
    a = pd.to_numeric(df[cols["missing_alt"]], errors="coerce")
    n_pages = int((a > 0).sum())
    n_imgs = int(a.sum())
    return _result("warn" if n_pages else "pass", count=n_imgs,
                   detail=f"{n_imgs} images missing alt across {n_pages} pages.")

def check_render_word_mismatch(df, cols, ctx):
    if "word_count" not in cols or "rendered_word_count" not in df.columns:
        return _na("Requires rendered word-count column.")
    raw = pd.to_numeric(df[cols["word_count"]], errors="coerce")
    rend = pd.to_numeric(df["rendered_word_count"], errors="coerce")
    diff = (rend - raw).abs()
    n = int((diff > 100).sum())
    return _result("fail" if n else "pass", count=n,
                   detail=f"{n} pages with >100-word rendering gap.")

    # ────────────────────────────────────────
    # REGISTRY  (auto_check key → function)
    # ────────────────────────────────────────

CHECK_REGISTRY = {
    "non_https_urls":             check_non_https_urls,
    "errors_4xx":                 check_errors_4xx,
    "errors_5xx":                 check_errors_5xx,
    "title_missing":              check_title_missing,
    "title_duplicate":            check_title_duplicate,
    "title_too_short":            check_title_too_short,
    "title_too_long":             check_title_too_long,
    "h1_missing":                 check_h1_missing,
    "h1_duplicate":               check_h1_duplicate,
    "h1_multiple":                check_h1_multiple,
    "md_missing":                 check_md_missing,
    "md_duplicate":               check_md_duplicate,
    "canonical_missing":          check_canonical_missing,
    "canonical_self_referencing": check_canonical_self_referencing,
    "non_indexable_pages":        check_non_indexable_pages,
    "meta_noindex":               check_meta_noindex,
    "orphans":                    check_orphans,
    "empty_pages":                check_empty_pages,
    "url_underscore":             check_url_underscore,
    "url_capitals":               check_url_capitals,
    "url_double_slash":           check_url_double_slash,
    "url_too_long":               check_url_too_long,
    "url_with_params":            check_url_with_params,
    "img_missing_alt":            check_img_missing_alt,
    "render_word_mismatch":       check_render_word_mismatch,
}

def run_all(df, cols_detected, manual_state=None, gsc_df=None):
    """
    Run all framework checks and return a list of enriched check results.
    `manual_state`: dict {check_id: {"status": "pass"|"fail"|"na", "notes": str}}
    """
    manual_state = manual_state or {}
    ctx = {"gsc_df": gsc_df}
    results = []
    for check in AUDIT_FRAMEWORK:
        cid = check["id"]
        # 1) Manual override always wins
        if cid in manual_state and manual_state[cid].get("status"):
            res = {**check, **{
                "result_status": manual_state[cid]["status"],
                "result_count":  manual_state[cid].get("count", 0),
                "result_detail": manual_state[cid].get("notes", ""),
                "samples":       [],
                "auto_run":      False,
            }}
            results.append(res)
            continue

        # 2) Automated check if registered
        fn_key = check.get("auto_check")
        fn = CHECK_REGISTRY.get(fn_key)
        if fn:
            try:
                r = fn(df, cols_detected, ctx)
                results.append({**check, **{
                    "result_status": r["status"],
                    "result_count":  r["count"],
                    "result_detail": r["detail"],
                    "samples":       r["samples"],
                    "auto_run":      True,
                }})
            except Exception as e:
                results.append({**check, **{
                    "result_status": "error",
                    "result_count":  0,
                    "result_detail": f"Check error: {e}",
                    "samples": [], "auto_run": True,
                }})
        else:
            # 3) No auto-check → manual
            results.append({**check, **{
                "result_status": "manual",
                "result_count":  0,
                "result_detail": "Manual review required.",
                "samples": [], "auto_run": False,
            }})

    return results