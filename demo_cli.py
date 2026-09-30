from agent_core import kpi_snapshot, load_orders, proposed_actions, simulate_scenario
from llm_agent import ask_agent

rows = load_orders()
print("KPI:", kpi_snapshot(rows))
print("SCENARIO:", simulate_scenario(rows, confirmation_days_saved=1))
print("ACTIONS:", proposed_actions(rows)[:2])
print("AGENT:", ask_agent("Why is delivery performance weak?"))
