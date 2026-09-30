# AI-Powered Supply Chain Decision Agent

An explainable supply-chain decision-support prototype combining **business analytics, rule-based risk scoring, deterministic scenario analysis, optional LLM tool-calling, and human-in-the-loop approval**.

> **Decision loop:** Data → Detect → Explain → Simulate → Recommend → Human Approval → Audit

## What the application does

The project turns order-level supply-chain data into a structured decision workflow. It can:

- calculate operational KPIs;
- identify and prioritize high-risk open orders;
- compare supplier performance signals;
- surface dominant operational root-cause patterns;
- run deterministic counterfactual / what-if scenarios;
- generate evidence-backed action recommendations;
- require explicit human approval or rejection;
- keep an auditable decision history;
- save, restore, undo, reset, upload, and export application state;
- optionally use an OpenAI-powered agent to select analytics tools from natural-language questions.

The mathematical layer remains deterministic. The optional LLM layer is used for **tool selection and explanation**, not for inventing quantitative results.

## Example demo result

Using the included 150-order synthetic dataset, a scenario where supplier confirmation becomes one day faster produces:

| Metric | Baseline | Scenario | Change |
|---|---:|---:|---:|
| Projected OTD | 35.7% | 45.0% | +9.3 pp |
| Avg. process lead time | 10.9 days | 10.2 days | -0.7 days |
| High-risk open orders | 9 | 6 | -3 |

This is a **counterfactual estimate**, not a forecast.

## Analytics methodology

### KPI layer

The application calculates on-time delivery, average lead time, open orders, overdue open orders, and high-risk open orders.

### Rule-based risk scoring

Risk is scored with transparent operational rules such as supplier-confirmation delay, quality delay, low inventory cover, order priority, and overdue status. Scores are classified as Low, Medium, or High.

The demo also contains small supplier-specific calibration adjustments for the synthetic data. They are explicitly demo-only and should be replaced by business-calibrated logic in a real implementation.

### Root-cause signal analysis

Medium- and high-risk orders are grouped by their dominant operational driver. The application reports frequency and share of flagged orders. This is an operational signal analysis, not proof of statistical causality.

### Scenario Lab

Scenario Lab is a deterministic what-if simulator. It is **not** Monte Carlo, discrete-event simulation, or an ML forecast.

Users can test changes in:

- supplier confirmation time;
- quality-processing time;
- transit time;
- inventory cover.

The engine recalculates projected OTD, average process lead time, and high-risk open orders.

For full details, see [docs/METHODOLOGY.md](docs/METHODOLOGY.md).

## AI agent architecture

With an API key connected, the agent can select predefined tools including:

- `get_kpi_snapshot`
- `analyze_suppliers`
- `get_root_causes`
- `get_high_risk_orders`
- `simulate_supply_chain_scenario`
- `get_proposed_actions`

Without an API key, the application automatically uses a deterministic fallback router, so the analytics demo remains fully usable.

## Human-in-the-loop governance

Recommendations are proposals, not executions. The user must explicitly **Approve** or **Reject** them. The audit record stores the action, recommendation, evidence, optional note, decision, and timestamp.

The state-management layer also supports snapshots, restore, undo, reset, dataset replacement, and export.

## Project structure

```text
ai-supply-chain-decision-agent/
├── .github/workflows/tests.yml
├── app.py
├── agent_core.py
├── llm_agent.py
├── demo_cli.py
├── requirements.txt
├── START_WINDOWS.bat
├── .env.example
├── .gitignore
├── LICENSE
├── data/
│   └── demo_orders.csv
├── docs/
│   ├── METHODOLOGY.md
│   └── DATA_DICTIONARY.md
└── tests/
    └── test_core.py
```

`orders.csv`, approval logs, action history, snapshots, virtual environments, and secrets are runtime files and are intentionally excluded from Git.

## Run locally

### Requirements

- Python 3.10+
- pip

Create and activate a virtual environment:

```bash
python -m venv .venv
```

Windows PowerShell:

```powershell
.\.venv\Scripts\Activate.ps1
```

macOS / Linux:

```bash
source .venv/bin/activate
```

Install dependencies and launch:

```bash
pip install -r requirements.txt
streamlit run app.py
```

Then open `http://localhost:8501` if the browser does not open automatically.

### Windows quick start

Windows users can also double-click:

```text
START_WINDOWS.bat
```

## Optional OpenAI connection

The application works without an API key.

For live LLM tool-calling, enter a key in the Streamlit sidebar or define `OPENAI_API_KEY` as an environment variable. The sidebar password field keeps the key only in the current Streamlit session and does not write it to project files.

**Never commit a real API key to GitHub.**

The synthetic demo uses a fixed evaluation date for reproducibility. It can be overridden with:

```text
SC_REFERENCE_DATE=YYYY-MM-DD
```

See `.env.example` for the supported environment variables.

## Data schema

The application expects order, supplier, date, process-time, value, inventory-cover, priority, and status fields. Uploaded CSV files are validated before they replace the current working dataset, and derived fields are recalculated automatically.

See [docs/DATA_DICTIONARY.md](docs/DATA_DICTIONARY.md) for the full schema.

## Tests

The repository includes reproducibility tests for the published demo KPIs, scenario result, and leading root-cause signal.

Run locally with:

```bash
python -m unittest discover -s tests -v
```

The same tests run automatically through GitHub Actions on pushes and pull requests.

## Tech stack

- Python
- Streamlit
- pandas
- OpenAI Python SDK (optional agent layer)
- CSV / JSON local state storage
- GitHub Actions

## Current limitations

This is a portfolio prototype, not a production planning system.

- The dataset is synthetic.
- Risk weights and thresholds require real business calibration before deployment.
- Scenario analysis is deterministic and does not model uncertainty distributions.
- The root-cause module identifies dominant operational signals rather than statistical causality.
- Local CSV/JSON persistence would normally be replaced by a governed database architecture in production.

## Future development

Potential next steps include SQL-backed storage, configurable risk logic, historical supplier calibration, Monte Carlo uncertainty analysis, predictive delay-risk modeling, optimization of recovery actions, cost/service trade-off analysis, authentication, and role-based access control.

## Portfolio context

Built to demonstrate the combination of **Industrial Engineering, Supply Chain Analytics, Business Analytics, Python, AI agents, scenario analysis, and decision governance** in one end-to-end workflow.

**Author:** Eren Altun
