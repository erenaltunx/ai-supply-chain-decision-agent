import os

import pandas as pd
import streamlit as st

from agent_core import (
    APPROVAL_PATH,
    BASE_FIELDS,
    DATA_PATH,
    clear_approval_log,
    get_action_history,
    get_approval_log,
    high_risk_queue,
    kpi_snapshot,
    list_snapshots,
    load_orders,
    proposed_actions,
    replace_dataset_from_bytes,
    reset_to_demo,
    restore_snapshot,
    root_causes,
    save_snapshot,
    simulate_scenario,
    submit_decision,
    supplier_analysis,
    undo_last_change,
)
from llm_agent import ask_agent

st.set_page_config(page_title="Supply Chain Business Analytics AI Agent", layout="wide")
st.title("AI-Powered Supply Chain Business Analytics Decision Agent")
st.caption("Business analytics + supply chain + explainable AI + scenario simulation + human approval + saved state")

with st.sidebar:
    st.header("Secure AI Connection")
    st.caption("The API key is kept only in this browser session. It is not written to disk or to the project files.")
    if "openai_api_key" not in st.session_state:
        st.session_state.openai_api_key = ""
    key = st.text_input(
        "OpenAI API key",
        type="password",
        value=st.session_state.openai_api_key,
        placeholder="sk-...",
        help="Optional. Leave blank to use deterministic fallback mode.",
    )
    st.session_state.openai_api_key = key
    model = st.text_input("Model", value=os.getenv("OPENAI_MODEL", "gpt-4.1-mini"))
    if key or os.getenv("OPENAI_API_KEY"):
        st.success("Live LLM mode available")
    else:
        st.info("Fallback mode: no API key connected")
    if st.button("Clear session key"):
        st.session_state.openai_api_key = ""
        st.rerun()

try:
    rows = load_orders()
except Exception as exc:
    st.error(f"Could not load dataset: {exc}")
    st.stop()

kpis = kpi_snapshot(rows)

c1, c2, c3, c4 = st.columns(4)
c1.metric("On-time delivery", f'{kpis["on_time_delivery_pct"]}%')
c2.metric("Avg lead time", f'{kpis["avg_lead_time_days"]} days')
c3.metric("Open orders", kpis["open_orders"])
c4.metric("High-risk open", kpis["high_risk_open_orders"])

agent_tab, scenario_tab, approval_tab, manager_tab, data_tab = st.tabs([
    "AI Agent", "Scenario Lab", "Human Approval", "Data Manager", "Data & Evidence"
])

with agent_tab:
    st.subheader("Ask the decision-support agent")
    if st.session_state.openai_api_key or os.getenv("OPENAI_API_KEY"):
        st.success("Live LLM tool-calling mode is available.")
    else:
        st.info("No API key detected. The app is using deterministic fallback mode.")

    question = st.text_input("Question", value="Why is delivery performance weak and what should I do?")
    if st.button("Ask agent", type="primary"):
        result = ask_agent(question, api_key=st.session_state.openai_api_key or None, model=model)
        st.markdown("### Agent answer")
        st.write(result["answer"])
        st.caption(f'Mode: {result.get("mode", "unknown")} | Tool(s): {result.get("tool_used", "n/a")}')
        if result.get("evidence"):
            with st.expander("Tool evidence / audit trail"):
                st.json(result["evidence"])

    st.markdown("**Try these:**")
    st.code(
        "Which suppliers need attention?\n"
        "Why is delivery performance weak?\n"
        "Which orders should I prioritize today?\n"
        "What if supplier confirmation improves by 1 day?"
    )

with scenario_tab:
    st.subheader("Counterfactual Scenario Simulator")
    st.caption("This estimates process impact under changed assumptions; it is not a forecast.")
    a, b, c, d = st.columns(4)
    confirm_saved = a.slider("Confirmation days saved", 0, 5, 1)
    quality_saved = b.slider("Quality days saved", 0, 5, 0)
    transit_saved = c.slider("Transit days saved", 0, 5, 0)
    inventory_uplift = d.slider("Inventory cover uplift (days)", 0, 30, 0)

    sim = simulate_scenario(rows, confirm_saved, quality_saved, transit_saved, inventory_uplift)
    s1, s2, s3 = st.columns(3)
    s1.metric("Projected OTD", f'{sim["scenario_projected_otd_pct"]}%', f'{sim["otd_delta_pp"]:+.1f} pp')
    s2.metric("Avg process lead time", f'{sim["scenario_avg_process_lead_days"]} days', f'{sim["lead_time_delta_days"]:+.1f} days')
    s3.metric("High-risk open orders", sim["scenario_high_risk_open"], sim["high_risk_open_delta"])
    st.json(sim)

with approval_tab:
    st.subheader("Human-in-the-loop Approval Queue")
    st.caption("The agent may recommend actions, but execution requires an explicit human decision.")
    ca, cb, cc = st.columns(3)

    if ca.button("Undo last change", help="Reverts the latest reversible decision, upload, reset or restore."):
        undone = undo_last_change()
        st.success(f"Undone: {undone.get('description')}" if undone else "Nothing to undo.")
        st.rerun()

    if cb.button("Clear approval log"):
        clear_approval_log()
        st.rerun()

    snap_label = cc.text_input("Snapshot label", value="Before demo")
    if cc.button("Save snapshot"):
        meta = save_snapshot(snap_label)
        st.success(f"Snapshot saved: {meta['snapshot_id']}")

    actions = proposed_actions(rows)
    existing = get_approval_log()
    decided_ids = {record["action_id"] for record in existing}

    for action in actions:
        with st.container(border=True):
            st.markdown(f'**{action["action_id"]} — {action["scope"]}**')
            st.write("Problem:", action["problem"])
            st.write("Recommendation:", action["recommendation"])
            st.write("Evidence:", action["evidence"])

            if action["action_id"] in decided_ids:
                latest = [x for x in existing if x["action_id"] == action["action_id"]][-1]
                st.info(f'Already decided: {latest["decision"]}')
            else:
                note = st.text_input(
                    "Decision note",
                    key=f'note_{action["action_id"]}',
                    placeholder="Optional rationale",
                )
                approve_col, reject_col = st.columns(2)
                if approve_col.button("Approve", key=f'approve_{action["action_id"]}'):
                    submit_decision(action["action_id"], "Approved", action["recommendation"], action["evidence"], note)
                    st.rerun()
                if reject_col.button("Reject", key=f'reject_{action["action_id"]}'):
                    submit_decision(action["action_id"], "Rejected", action["recommendation"], action["evidence"], note)
                    st.rerun()

    st.markdown("### Decision audit log")
    log = get_approval_log()
    if log:
        st.dataframe(pd.DataFrame(log), use_container_width=True, hide_index=True)
    else:
        st.info("No decisions recorded yet.")

with manager_tab:
    st.subheader("Data & State Manager")
    st.caption("Save the current state, undo changes, reset the demo, or replace the CSV dataset.")

    m1, m2, m3 = st.columns(3)
    if m1.button("Save current state"):
        meta = save_snapshot("Manual state save")
        st.success(f"Saved snapshot: {meta['snapshot_id']}")

    if m2.button("Undo last reversible change"):
        undone = undo_last_change()
        st.success(f"Undone: {undone.get('description')}" if undone else "Nothing to undo.")
        st.rerun()

    if m3.button("Reset to demo data"):
        reset_to_demo(clear_approvals=True)
        st.success("Demo dataset and approval log restored.")
        st.rerun()

    st.markdown("### Snapshots")
    snaps = list_snapshots()
    if snaps:
        labels = {
            f'{s["created_at_utc"]} — {s["label"]} ({s["snapshot_id"]})': s["snapshot_id"]
            for s in snaps
        }
        choice = st.selectbox("Saved states", list(labels.keys()))
        if st.button("Restore selected snapshot"):
            restore_snapshot(labels[choice])
            st.success("Snapshot restored.")
            st.rerun()
        st.dataframe(pd.DataFrame(snaps), use_container_width=True, hide_index=True)
    else:
        st.info("No saved snapshots yet.")

    st.markdown("### Replace dataset")
    st.caption("Upload a CSV with the required supply-chain columns. Derived risk fields are recalculated automatically.")
    with st.expander("Required columns"):
        st.code(", ".join(BASE_FIELDS))

    upload = st.file_uploader("Upload CSV", type=["csv"])
    if upload:
        try:
            content = upload.getvalue()
            preview = pd.read_csv(upload)
            st.dataframe(preview.head(10), use_container_width=True, hide_index=True)
            if st.button("Replace current dataset with uploaded CSV", type="primary"):
                new_rows = replace_dataset_from_bytes(content, upload.name)
                st.success(f"Dataset replaced successfully: {len(new_rows)} rows")
                st.rerun()
        except Exception as exc:
            st.error(f"Upload rejected: {exc}")

    st.markdown("### Export current state")
    colx, coly = st.columns(2)
    colx.download_button("Download current orders.csv", DATA_PATH.read_bytes(), file_name="orders_current.csv", mime="text/csv")
    coly.download_button("Download approval_log.json", APPROVAL_PATH.read_bytes(), file_name="approval_log.json", mime="application/json")

    st.markdown("### Action history")
    history = get_action_history()
    if history:
        st.dataframe(pd.DataFrame(history), use_container_width=True, hide_index=True)
    else:
        st.info("No actions recorded yet.")

with data_tab:
    left, right = st.columns(2)
    with left:
        st.subheader("Supplier analysis")
        st.dataframe(pd.DataFrame(supplier_analysis(rows)), use_container_width=True, hide_index=True)
    with right:
        st.subheader("Root-cause signals")
        st.dataframe(pd.DataFrame(root_causes(rows)), use_container_width=True, hide_index=True)

    st.subheader("High-risk open orders")
    st.dataframe(pd.DataFrame(high_risk_queue(rows, 10)), use_container_width=True, hide_index=True)

    st.subheader("Raw data")
    st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
