from __future__ import annotations

import json
import os

from agent_core import (
    deterministic_answer,
    high_risk_queue,
    kpi_snapshot,
    load_orders,
    proposed_actions,
    root_causes,
    simulate_scenario,
    supplier_analysis,
)

TOOLS = [
    {"type": "function", "name": "get_kpi_snapshot", "description": "Get the current supply-chain KPI snapshot.", "parameters": {"type": "object", "properties": {}, "additionalProperties": False}, "strict": True},
    {"type": "function", "name": "analyze_suppliers", "description": "Rank suppliers by high-risk orders and late-delivery performance.", "parameters": {"type": "object", "properties": {}, "additionalProperties": False}, "strict": True},
    {"type": "function", "name": "get_root_causes", "description": "Return the leading operational root-cause signals.", "parameters": {"type": "object", "properties": {}, "additionalProperties": False}, "strict": True},
    {"type": "function", "name": "get_high_risk_orders", "description": "Return prioritized high-risk open orders.", "parameters": {"type": "object", "properties": {"limit": {"type": "integer", "minimum": 1, "maximum": 20}}, "required": ["limit"], "additionalProperties": False}, "strict": True},
    {"type": "function", "name": "simulate_supply_chain_scenario", "description": "Estimate KPI impact of improving supply-chain process stages.", "parameters": {"type": "object", "properties": {"confirmation_days_saved": {"type": "integer", "minimum": 0, "maximum": 5}, "quality_days_saved": {"type": "integer", "minimum": 0, "maximum": 5}, "transit_days_saved": {"type": "integer", "minimum": 0, "maximum": 5}, "inventory_cover_uplift": {"type": "number", "minimum": 0, "maximum": 30}}, "required": ["confirmation_days_saved", "quality_days_saved", "transit_days_saved", "inventory_cover_uplift"], "additionalProperties": False}, "strict": True},
    {"type": "function", "name": "get_proposed_actions", "description": "Generate actions that require human approval.", "parameters": {"type": "object", "properties": {}, "additionalProperties": False}, "strict": True},
]

SYSTEM = """You are a supply-chain business analytics decision-support agent.
Use tools for quantitative claims. Never invent data. Separate evidence from recommendation.
Do not claim an action was executed: recommendations require explicit human approval.
When discussing a simulation, label it as a counterfactual estimate, not a forecast.
Be concise and business-oriented."""


def _run_tool(name, args, rows):
    if name == "get_kpi_snapshot":
        return kpi_snapshot(rows)
    if name == "analyze_suppliers":
        return supplier_analysis(rows)
    if name == "get_root_causes":
        return root_causes(rows)
    if name == "get_high_risk_orders":
        return high_risk_queue(rows, args["limit"])
    if name == "simulate_supply_chain_scenario":
        return simulate_scenario(
            rows,
            args["confirmation_days_saved"],
            args["quality_days_saved"],
            args["transit_days_saved"],
            args["inventory_cover_uplift"],
        )
    if name == "get_proposed_actions":
        return proposed_actions(rows)
    raise ValueError(f"Unknown tool: {name}")


def ask_agent(question, api_key=None, model=None):
    rows = load_orders()
    effective_key = api_key or os.getenv("OPENAI_API_KEY")
    effective_model = model or os.getenv("OPENAI_MODEL") or "gpt-4.1-mini"

    if not effective_key:
        fallback = deterministic_answer(question, rows)
        fallback["mode"] = "Deterministic fallback (no API key in session/environment)"
        return fallback

    try:
        from openai import OpenAI

        client = OpenAI(api_key=effective_key)
        response = client.responses.create(
            model=effective_model,
            instructions=SYSTEM,
            input=question,
            tools=TOOLS,
            tool_choice="auto",
        )
        calls_used = []

        for _ in range(5):
            calls = [item for item in response.output if getattr(item, "type", None) == "function_call"]
            if not calls:
                return {
                    "answer": response.output_text,
                    "evidence": calls_used,
                    "tool_used": ", ".join(c["tool"] for c in calls_used) or "LLM direct",
                    "mode": f"Live LLM tool-calling ({effective_model})",
                }

            tool_outputs = []
            for call in calls:
                args = json.loads(call.arguments or "{}")
                result = _run_tool(call.name, args, rows)
                calls_used.append({"tool": call.name, "arguments": args, "result": result})
                tool_outputs.append({"type": "function_call_output", "call_id": call.call_id, "output": json.dumps(result)})

            response = client.responses.create(
                model=effective_model,
                instructions=SYSTEM,
                previous_response_id=response.id,
                input=tool_outputs,
                tools=TOOLS,
                tool_choice="auto",
            )

        return {
            "answer": response.output_text or "Tool loop ended without a final text response.",
            "evidence": calls_used,
            "tool_used": ", ".join(c["tool"] for c in calls_used),
            "mode": f"Live LLM tool-calling ({effective_model})",
        }
    except Exception as exc:
        fallback = deterministic_answer(question, rows)
        fallback["mode"] = f"Fallback after LLM error: {type(exc).__name__}"
        return fallback
