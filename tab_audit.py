"""
tab_audit.py — Renders the Full Audit Framework tab.
Imported by app.py and called inside `with tab8:`.
"""

import io
from collections import Counter

import pandas as pd
import streamlit as st

from audit_framework import AUDIT_FRAMEWORK, SEVERITY_ORDER
from audit_runner import run_all, CHECK_REGISTRY


def render(df, cols_detected, site_name):
   """Render the Full Audit Framework tab. Call this inside `with tab8:`."""

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

   safe_name = site_name.replace(".", "_")

   col_x1, col_x2 = st.columns(2)
   with col_x1:
       st.download_button(
           "⬇️ Download Full Audit (CSV)",
           data=framework_df.to_csv(index=False).encode("utf-8"),
           file_name=f"{safe_name}_full_audit.csv",
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
           file_name=f"{safe_name}_full_audit.xlsx",
           mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
       )
