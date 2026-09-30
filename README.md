# AI-Powered Supply Chain Decision Agent

An explainable supply-chain decision-support prototype that combines **business analytics, rule-based risk scoring, counterfactual scenario analysis, optional LLM tool-calling, and human-in-the-loop approval**.

> **Decision loop:** Data → Detect → Explain → Simulate → Recommend → Human Approval → Audit

## Why this project exists

Supply-chain dashboards are useful for monitoring, but they often stop at showing what happened. This project goes one step further: it turns operational data into a structured decision workflow.

The application can:

- calculate supply-chain KPIs from order-level data;
- identify high-risk open orders;
- rank supplier performance signals;
- surface likely root-cause patterns;
- test deterministic "what-if" scenarios;
- generate evidence-backed action recommendations;
- require explicit human approval before a recommendation is treated as a decision;
- keep an auditable decision log;
- save, restore, undo, reset, upload, and export application state;
- optionally use an OpenAI-powered agent to select analytics tools from natural-language questions.

## Demo workflow

1. Load the current order dataset.
2. Recalculate derived lead-time, lateness, risk, and root-cause fields.
3. Review KPIs and supplier-level signals.
4. Ask the decision-support agent a business question.
5. Run a counterfactual scenario in Scenario Lab.
6. Review proposed actions.
7. Approve or reject recommendations.
8. Audit, save, undo, restore, or export the resulting state.

## Analytics methodology

The analytics engine is intentionally transparent. The mathematical layer is not delegated to the LLM.

### KPI calculations

The application calculates metrics such as:

- on-time delivery (OTD);
- average lead time;
- open orders;
- overdue open orders;
- high-risk open orders.

### Rule-based risk scoring

Each order receives a weighted risk score based on operational signals including supplier-confirmation delay, quality delay, low inventory cover, priority, and overdue status. Risk scores are converted into **Low**, **Medium**, and **High** categories.

### Root-cause analysis

Medium- and high-risk orders are grouped by their dominant operational driver. The application reports each driver's frequency and share of flagged orders.

### Counterfactual scenario analysis

Scenario Lab is a **deterministic what-if simulator**, not a Monte Carlo or discrete-event simulation and not a forecast.

Users can test improvements in:

- supplier confirmation time;
- quality-processing time;
- transit time;
- inventory cover.

The engine recalculates projected OTD, average process lead time, and the number of high-risk open orders under the changed assumptions.

Example from the synthetic demo dataset:

| Metric | Baseline | Scenario | Change |
|---|---:|---:|---:|
| Projected OTD | 35.7% | 45.0% | +9.3 pp |
| Avg. process lead time | 10.9 days | 10.2 days | -0.7 days |
| High-risk open orders | 9 | 6 | -3 |

The scenario assumes supplier confirmation becomes one day faster.

## AI agent architecture

The AI layer is optional. With an API key connected, the LLM can choose among predefined analytics tools such as:

- `get_kpi_snapshot`
- `analyze_suppliers`
- `get_root_causes`
- `get_high_risk_orders`
- `simulate_supply_chain_scenario`
- `get_proposed_actions`

Quantitative results come from deterministic Python functions. The LLM's role is to interpret the user's question, select tools, and communicate the results.

If no API key is provided, the application automatically switches to a deterministic fallback router, so the core analytics demo remains usable.

## Human-in-the-loop governance

Recommendations are not treated as executed actions. The user must explicitly **Approve** or **Reject** them. Decisions are written to an audit log with supporting evidence and an optional note.

The application also supports:

- named snapshots;
- restoring snapshots;
- undoing the latest reversible change;
- resetting to the original demo dataset;
- clearing approval decisions;
- uploading a replacement CSV dataset;
- exporting the current data and decision log.

## Project structure

```text
ai-supply-chain-decision-agent/
├── app.py
├── agent_core.py
├── llm_agent.py
├── demo_cli.py
├── requirements.txt
├── START_WINDOWS.bat
├── .env.example
├── .gitignore
├── data/
│   ├── demo_orders.csv
│   ├── orders.csv
│   ├── approval_log.json
│   └── action_history.json
├── screenshots/
│   ├── ai-agent.png
│   ├── scenario-lab.png
│   └── human-approval.png
└── docs/
    └── project-handbook.pdf
```

## Run locally

### Requirements

- Python 3.10+
- pip

### Standard setup

```bash
python -m venv .venv
```

Activate the environment.

**Windows PowerShell:**

```powershell
.\.venv\Scripts\Activate.ps1
```

**macOS / Linux:**

```bash
source .venv/bin/activate
```

Install dependencies:

```bash
pip install -r requirements.txt
```

Launch the application:

```bash
streamlit run app.py
```

Then open `http://localhost:8501` if the browser does not open automatically.

### Windows quick start

Windows users can also double-click:

```text
START_WINDOWS.bat
```

The launcher creates a virtual environment, installs the required packages, and starts Streamlit.

## Optional OpenAI connection

The application works without an API key.

For live LLM tool-calling, either enter an API key in the Streamlit sidebar or define it as an environment variable:

```text
OPENAI_API_KEY=your_key_here
```

The sidebar password field stores the key only in the current Streamlit session. The key is not written to the project files by the application.

**Never commit a real API key to GitHub.**

## Required CSV columns

```text
Order_ID
Supplier
Region
Category
Priority
Order_Date
Expected_Delivery
Delivery_Date
Supplier_Confirm_Days
Processing_Days
Quality_Days
Transit_Days
Quantity
Order_Value_EUR
Inventory_Cover_Days
Status
```

Uploaded datasets are validated before replacing the current working dataset, and derived analytics fields are recalculated automatically.

## Tech stack

- Python
- Streamlit
- pandas
- OpenAI Python SDK (optional agent layer)
- CSV / JSON state storage

## Current limitations

This is a portfolio prototype rather than a production planning system.

- The demo dataset is synthetic.
- Risk weights and operational thresholds are rule-based and would need business-specific calibration in a real deployment.
- Scenario analysis is deterministic and counterfactual; it does not model probability distributions or uncertainty.
- The root-cause module identifies dominant operational signals rather than proving statistical causality.
- CSV/JSON storage is suitable for a local prototype; a production implementation would normally use a database, authentication, access control, testing, observability, and stronger data governance.

## Future development

Potential next steps include:

- SQL-backed data storage;
- configurable risk weights and thresholds;
- Monte Carlo uncertainty simulation;
- predictive delay-risk modeling;
- optimization of recovery actions;
- cost/service trade-off analysis;
- automated tests and CI;
- role-based access control;
- deployment as a hosted internal analytics application.

## Portfolio context

This project was built to demonstrate the combination of **Industrial Engineering, Supply Chain Analytics, Business Analytics, Python, AI agents, scenario analysis, and decision governance** in one end-to-end workflow.

**Project author:** Eren Altun
