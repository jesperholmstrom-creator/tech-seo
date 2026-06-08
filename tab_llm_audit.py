# tab_llm_audit.py
"""AI Crawler Access Audit — checks robots.txt for LLM bot access."""

import requests
import streamlit as st
from urllib.parse import urlparse

AI_BOTS = [
{"name": "GPTBot",            "owner": "OpenAI (ChatGPT)",         "priority": "High"},
{"name": "ChatGPT-User",      "owner": "OpenAI (ChatGPT browsing)","priority": "High"},
{"name": "Google-Extended",   "owner": "Google (Gemini / SGE)",    "priority": "High"},
{"name": "ClaudeBot",         "owner": "Anthropic (Claude)",       "priority": "High"},
{"name": "anthropic-ai",      "owner": "Anthropic (Claude)",       "priority": "High"},
{"name": "PerplexityBot",     "owner": "Perplexity AI",            "priority": "High"},
{"name": "Meta-ExternalAgent","owner": "Meta AI",                  "priority": "High"},
{"name": "CCBot",             "owner": "Common Crawl (training)",  "priority": "Medium"},
{"name": "Bytespider",        "owner": "ByteDance / TikTok",       "priority": "Medium"},
{"name": "cohere-ai",         "owner": "Cohere AI",                "priority": "Medium"},
{"name": "Applebot",          "owner": "Apple (Siri / Spotlight)", "priority": "Medium"},
{"name": "Diffbot",           "owner": "Diffbot",                  "priority": "Low"},
{"name": "YouBot",            "owner": "You.com",                  "priority": "Low"},
]

def fetch_robots(domain):
    domain = domain.strip().rstrip("/")
    if not domain.startswith("http"):
        domain = "https://" + domain
    parsed = urlparse(domain)
    for scheme in ["https", "http"]:
        url = f"{scheme}://{parsed.netloc}/robots.txt"
        try:
            r = requests.get(url, timeout=8, headers={"User-Agent": "Mozilla/5.0"})
            if r.status_code == 200:
                return r.text, url
        except Exception:
            continue
    return None, None

def parse_robots(content, bot_name):
"""Parse robots.txt and return status for a given bot."""
groups = {}
current_agents = []

for raw in content.splitlines():
    line = raw.split("#")[0].strip()
    if not line:
        current_agents = []
        continue
    low = line.lower()
    if low.startswith("user-agent:"):
        agent = line.split(":", 1)[1].strip().lower()
        current_agents = [agent]
        groups.setdefault(agent, [])
    elif low.startswith("disallow:") or low.startswith("allow:"):
        for a in current_agents:
            groups.setdefault(a, []).append(low)

bot_key = bot_name.lower()

def is_blocked(rules):
    disallows = [r.split(":", 1)[1].strip() for r in rules if r.startswith("disallow:")]
    allows    = [r.split(":", 1)[1].strip() for r in rules if r.startswith("allow:")]
    if "/" in disallows and "/" not in allows:
        return True
    return False

if bot_key in groups:
    rules = groups[bot_key]
    if not rules:
        return "allowed"
    return "blocked" if is_blocked(rules) else "allowed"

wildcard = groups.get("*", [])
if not wildcard:
    return "not_mentioned"
return "blocked_wildcard" if is_blocked(wildcard) else "not_mentioned"

def render(df=None, cols_detected=None, site_name=None):
st.header("🤖 AI Crawler Access Audit")
st.markdown(
    "Check whether major AI crawlers can access your site via `robots.txt`. "
    "Blocking them means your content won't appear in **ChatGPT, Gemini, Claude, Perplexity** responses."
)

domain = st.text_input(
    "Domain to audit",
    placeholder="example.com",
    value=site_name if site_name and site_name.startswith("http") else "",
)

if not domain:
    st.info("Enter a domain above to begin.")
    return

with st.spinner(f"Fetching robots.txt from {domain} …"):
    content, robots_url = fetch_robots(domain)

if not content:
    st.error(f"Could not fetch robots.txt from **{domain}**. Check the domain and try again.")
    return

st.success(f"Fetched: `{robots_url}`")

with st.expander("View raw robots.txt"):
    st.code(content, language="text")

# ── Run checks ──────────────────────────────────────────
results = []
for bot in AI_BOTS:
    status = parse_robots(content, bot["name"])
    results.append({**bot, "status": status})

blocked  = [r for r in results if r["status"] in ("blocked", "blocked_wildcard")]
allowed  = [r for r in results if r["status"] not in ("blocked", "blocked_wildcard")]

# ── Summary metrics ──────────────────────────────────────
c1, c2, c3 = st.columns(3)
c1.metric("Bots Checked", len(results))
c2.metric("🔴 Blocked",   len(blocked))
c3.metric("🟢 Accessible", len(allowed))

st.markdown("---")

# ── Per-bot results ──────────────────────────────────────
st.subheader("Bot-by-bot breakdown")

STATUS_CONFIG = {
    "blocked":          ("🔴", "BLOCKED — explicit rule"),
    "blocked_wildcard": ("🟡", "BLOCKED — via wildcard (Disallow: *)"),
    "allowed":          ("🟢", "ALLOWED"),
    "not_mentioned":    ("🟢", "NOT MENTIONED (allowed by default)"),
}

for r in results:
    icon, label = STATUS_CONFIG.get(r["status"], ("⚪", r["status"]))
    pri_badge = {"High": "🔥 High", "Medium": "⚡ Medium", "Low": "💤 Low"}[r["priority"]]
    with st.expander(f"{icon} **{r['name']}** — {r['owner']}  |  {pri_badge} priority"):
        st.markdown(f"**Access status:** {label}")
        if r["status"] in ("blocked", "blocked_wildcard"):
            if r["priority"] == "High":
                st.warning(
                    f"⚠️ This is a high-priority AI crawler. "
                    f"Add an explicit `Allow: /` rule for `{r['name']}` to appear in {r['owner']} responses."
                )
        else:
            st.success(f"`{r['name']}` can crawl your site freely.")

# ── Recommended fixes ────────────────────────────────────
high_blocked = [r for r in blocked if r["priority"] == "High"]
if high_blocked:
    st.markdown("---")
    st.subheader("🔧 Recommended robots.txt additions")
    snippet = "\n".join(
        f"User-agent: {r['name']}\nAllow: /\n" for r in high_blocked
    )
    st.code(snippet, language="text")
    st.info("Add these rules to your `robots.txt` to restore access for high-priority AI crawlers.")
elif not blocked:
    st.success("🎉 All AI crawlers can access your site — great LLM visibility.")