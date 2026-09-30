from __future__ import annotations

import csv
import json
import os
import shutil
import uuid
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from statistics import mean

ROOT = Path(__file__).parent
DATA_DIR = ROOT / "data"
DATA_PATH = DATA_DIR / "orders.csv"
DEMO_DATA_PATH = DATA_DIR / "demo_orders.csv"
APPROVAL_PATH = DATA_DIR / "approval_log.json"
HISTORY_PATH = DATA_DIR / "action_history.json"
SNAPSHOT_DIR = DATA_DIR / "snapshots"

BASE_FIELDS = [
    "Order_ID", "Supplier", "Region", "Category", "Priority", "Order_Date",
    "Expected_Delivery", "Delivery_Date", "Supplier_Confirm_Days", "Processing_Days",
    "Quality_Days", "Transit_Days", "Quantity", "Order_Value_EUR",
    "Inventory_Cover_Days", "Status",
]
DERIVED_FIELDS = [
    "Actual_or_Current_Lead_Time", "Days_Late", "On_Time",
    "Risk_Score", "Risk_Level", "Primary_Driver",
]
ALL_FIELDS = BASE_FIELDS + DERIVED_FIELDS

# Reproducible synthetic demo date. Override for another dataset/date.
REFERENCE_DATE = datetime.fromisoformat(os.getenv("SC_REFERENCE_DATE", "2026-09-25"))
# Demo-only calibration for the synthetic suppliers. Replace/remove for real deployments.
SUPPLIER_RISK_ADJUSTMENTS = {"Supplier B": 10, "Supplier D": 8}


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _read_json(path: Path, default):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError):
        return default


def _write_json(path: Path, value) -> None:
    path.write_text(json.dumps(value, indent=2), encoding="utf-8")


def _initialize_runtime() -> None:
    DATA_DIR.mkdir(exist_ok=True)
    SNAPSHOT_DIR.mkdir(exist_ok=True)
    if not DATA_PATH.exists() and DEMO_DATA_PATH.exists():
        shutil.copy2(DEMO_DATA_PATH, DATA_PATH)
    if not APPROVAL_PATH.exists():
        _write_json(APPROVAL_PATH, [])
    if not HISTORY_PATH.exists():
        _write_json(HISTORY_PATH, [])


_initialize_runtime()


def _to_int(value, default=0) -> int:
    return default if value in (None, "") else int(float(value))


def _to_float(value, default=0.0) -> float:
    return default if value in (None, "") else float(value)


def _parse_date(value):
    return None if value in (None, "") else datetime.fromisoformat(str(value).strip())


def _primary_driver(row) -> str:
    if row["Supplier_Confirm_Days"] > 3:
        return "Supplier confirmation delay"
    if row["Quality_Days"] > 2:
        return "Quality delay"
    if row["Inventory_Cover_Days"] < 7:
        return "Low inventory cover"
    if row["Transit_Days"] > 4:
        return "Transit delay"
    if row["Status"] == "Open" and row["Days_Late"] > 0:
        return "Overdue open order"
    return "No dominant issue"


def _risk_score(row) -> int:
    score = 0
    score += 25 if row["Supplier_Confirm_Days"] > 3 else 0
    score += 20 if row["Quality_Days"] > 2 else 0
    score += 20 if row["Inventory_Cover_Days"] < 7 else 0
    score += 20 if row["Priority"] == "Critical" else 10 if row["Priority"] == "High" else 0
    score += 25 if row["Status"] == "Open" and row["Days_Late"] > 0 else 0
    score += SUPPLIER_RISK_ADJUSTMENTS.get(row["Supplier"], 0)
    return min(100, score)


def normalize_row(raw) -> dict:
    row = {key: (raw.get(key, "") if raw.get(key, "") is not None else "") for key in ALL_FIELDS}
    for key in ["Supplier_Confirm_Days", "Processing_Days", "Quality_Days", "Transit_Days", "Quantity"]:
        row[key] = _to_int(row[key])
    row["Order_Value_EUR"] = _to_float(row["Order_Value_EUR"])
    row["Inventory_Cover_Days"] = _to_float(row["Inventory_Cover_Days"])

    row["Status"] = str(row.get("Status") or "").strip().title()
    if row["Status"] not in ("Open", "Delivered"):
        row["Status"] = "Delivered" if row.get("Delivery_Date") else "Open"

    order_date = _parse_date(row["Order_Date"])
    expected = _parse_date(row["Expected_Delivery"])
    delivered = _parse_date(row["Delivery_Date"])
    if not order_date or not expected:
        raise ValueError(f"Order {row.get('Order_ID', '<unknown>')} has invalid required dates")

    evaluation_date = delivered if row["Status"] == "Delivered" and delivered else REFERENCE_DATE
    row["Actual_or_Current_Lead_Time"] = (evaluation_date - order_date).days
    row["Days_Late"] = max(0, (evaluation_date - expected).days)
    row["On_Time"] = "Yes" if delivered and delivered <= expected else "No" if delivered else "Open"
    row["Risk_Score"] = _risk_score(row)
    row["Risk_Level"] = "High" if row["Risk_Score"] >= 60 else "Medium" if row["Risk_Score"] >= 35 else "Low"
    row["Primary_Driver"] = _primary_driver(row)
    return row


def validate_csv_file(path: Path) -> list[dict]:
    with path.open(encoding="utf-8-sig", newline="") as handle:
        rows = list(csv.DictReader(handle))
    if not rows:
        raise ValueError("CSV file is empty")
    missing = [field for field in BASE_FIELDS if field not in rows[0]]
    if missing:
        raise ValueError("Missing required columns: " + ", ".join(missing))
    return [normalize_row(row) for row in rows]


def write_orders(rows, path: Path = DATA_PATH) -> list[dict]:
    normalized = [normalize_row(row) for row in rows]
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=ALL_FIELDS)
        writer.writeheader()
        writer.writerows(normalized)
    return normalized


def load_orders() -> list[dict]:
    rows = validate_csv_file(DATA_PATH)
    return write_orders(rows)


def kpi_snapshot(rows) -> dict:
    delivered = [r for r in rows if r["Status"] == "Delivered"]
    open_orders = [r for r in rows if r["Status"] == "Open"]
    on_time = [r for r in delivered if r["On_Time"] == "Yes"]
    return {
        "total_orders": len(rows),
        "delivered_orders": len(delivered),
        "open_orders": len(open_orders),
        "on_time_delivery_pct": round(100 * len(on_time) / len(delivered), 1) if delivered else 0,
        "avg_lead_time_days": round(mean(r["Actual_or_Current_Lead_Time"] for r in rows), 1) if rows else 0,
        "high_risk_open_orders": sum(r["Risk_Level"] == "High" for r in open_orders),
        "overdue_open_orders": sum(r["Days_Late"] > 0 for r in open_orders),
    }


def supplier_analysis(rows) -> list[dict]:
    groups = defaultdict(list)
    for row in rows:
        groups[row["Supplier"]].append(row)
    result = []
    for supplier, group in groups.items():
        delivered = [r for r in group if r["Status"] == "Delivered"]
        late = [r for r in delivered if r["On_Time"] == "No"]
        result.append({
            "supplier": supplier,
            "orders": len(group),
            "avg_confirmation_days": round(mean(r["Supplier_Confirm_Days"] for r in group), 1),
            "late_delivery_rate_pct": round(100 * len(late) / len(delivered), 1) if delivered else 0,
            "high_risk_orders": sum(r["Risk_Level"] == "High" for r in group),
        })
    return sorted(result, key=lambda x: (x["high_risk_orders"], x["late_delivery_rate_pct"]), reverse=True)


def root_causes(rows) -> list[dict]:
    flagged = [r for r in rows if r["Risk_Level"] in ("High", "Medium")]
    counts = Counter(r["Primary_Driver"] for r in flagged if r["Primary_Driver"] != "No dominant issue")
    total = sum(counts.values()) or 1
    return [{"driver": d, "orders": n, "share_pct": round(100 * n / total, 1)} for d, n in counts.most_common()]


def high_risk_queue(rows, limit=10) -> list[dict]:
    queue = [r for r in rows if r["Status"] == "Open" and r["Risk_Level"] == "High"]
    return sorted(queue, key=lambda r: (r["Risk_Score"], r["Order_Value_EUR"]), reverse=True)[:limit]


def recommend_action(driver: str) -> str:
    return {
        "Supplier confirmation delay": "Escalate supplier response and review the confirmation SLA.",
        "Quality delay": "Review inspection capacity, queue size and quality-release ownership.",
        "Low inventory cover": "Review safety stock and expedite replenishment for exposed items.",
        "Transit delay": "Review carrier performance and consider shipment expediting.",
        "Overdue open order": "Create an immediate recovery plan with a named owner and checkpoint.",
    }.get(driver, "Monitor the signal and investigate before taking action.")


def proposed_actions(rows) -> list[dict]:
    actions = []
    causes = root_causes(rows)
    if causes:
        top = causes[0]
        actions.append({"action_id": "ACT-RCA-001", "scope": "Process", "problem": top["driver"],
                        "recommendation": recommend_action(top["driver"]),
                        "evidence": f'{top["orders"]} flagged orders; {top["share_pct"]}% of flagged primary drivers',
                        "status": "Pending"})
    for index, row in enumerate(high_risk_queue(rows, 5), 1):
        actions.append({"action_id": f"ACT-ORD-{index:03d}", "scope": row["Order_ID"],
                        "problem": row["Primary_Driver"], "recommendation": recommend_action(row["Primary_Driver"]),
                        "evidence": f'risk={row["Risk_Score"]}/100; supplier={row["Supplier"]}; late={row["Days_Late"]}d; value=€{row["Order_Value_EUR"]:,.0f}',
                        "status": "Pending"})
    return actions


def _projected_risk(row, confirm_saved=0, quality_saved=0, inventory_uplift=0) -> int:
    projected = dict(row)
    projected["Supplier_Confirm_Days"] = max(1, row["Supplier_Confirm_Days"] - confirm_saved)
    projected["Quality_Days"] = max(1, row["Quality_Days"] - quality_saved)
    projected["Inventory_Cover_Days"] = row["Inventory_Cover_Days"] + inventory_uplift
    return _risk_score(projected)


def simulate_scenario(rows, confirmation_days_saved=0, quality_days_saved=0, transit_days_saved=0, inventory_cover_uplift=0) -> dict:
    delivered = [r for r in rows if r["Status"] == "Delivered"]
    base_lead, new_lead = [], []
    base_on_time = new_on_time = 0
    for row in delivered:
        allowed = (_parse_date(row["Expected_Delivery"]) - _parse_date(row["Order_Date"])).days
        base = row["Supplier_Confirm_Days"] + row["Processing_Days"] + row["Quality_Days"] + row["Transit_Days"]
        new = max(1, row["Supplier_Confirm_Days"] - confirmation_days_saved) + row["Processing_Days"] + max(1, row["Quality_Days"] - quality_days_saved) + max(1, row["Transit_Days"] - transit_days_saved)
        base_lead.append(base); new_lead.append(new)
        base_on_time += int(base <= allowed); new_on_time += int(new <= allowed)
    base_otd = round(100 * base_on_time / len(delivered), 1) if delivered else 0
    new_otd = round(100 * new_on_time / len(delivered), 1) if delivered else 0
    base_high = sum(r["Status"] == "Open" and r["Risk_Score"] >= 60 for r in rows)
    new_high = sum(r["Status"] == "Open" and _projected_risk(r, confirmation_days_saved, quality_days_saved, inventory_cover_uplift) >= 60 for r in rows)
    return {
        "baseline_projected_otd_pct": base_otd, "scenario_projected_otd_pct": new_otd,
        "otd_delta_pp": round(new_otd - base_otd, 1),
        "baseline_avg_process_lead_days": round(mean(base_lead), 1) if base_lead else 0,
        "scenario_avg_process_lead_days": round(mean(new_lead), 1) if new_lead else 0,
        "lead_time_delta_days": round(mean(new_lead) - mean(base_lead), 1) if base_lead else 0,
        "baseline_high_risk_open": base_high, "scenario_high_risk_open": new_high,
        "high_risk_open_delta": new_high - base_high,
        "assumptions": {"confirmation_days_saved": confirmation_days_saved, "quality_days_saved": quality_days_saved,
                        "transit_days_saved": transit_days_saved, "inventory_cover_uplift_days": inventory_cover_uplift},
    }


def get_approval_log(): return _read_json(APPROVAL_PATH, [])
def get_action_history(): return _read_json(HISTORY_PATH, [])


def _append_history(event) -> dict:
    history = get_action_history()
    record = {"event_id": str(uuid.uuid4()), "timestamp_utc": _utc_now(), **event}
    history.append(record); _write_json(HISTORY_PATH, history)
    return record


def _backup(label: str) -> str:
    backup_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S") + "_" + uuid.uuid4().hex[:8]
    folder = SNAPSHOT_DIR / "_backups" / backup_id
    folder.mkdir(parents=True, exist_ok=True)
    shutil.copy2(DATA_PATH, folder / "orders.csv"); shutil.copy2(APPROVAL_PATH, folder / "approval_log.json")
    _write_json(folder / "metadata.json", {"snapshot_id": backup_id, "label": label, "internal": True})
    return backup_id


def submit_decision(action_id, decision, recommendation, evidence, notes="") -> dict:
    if decision not in ("Approved", "Rejected"):
        raise ValueError("decision must be Approved or Rejected")
    backup_id = _backup("Before decision")
    record = {"action_id": action_id, "decision": decision, "recommendation": recommendation,
              "evidence": evidence, "notes": notes, "timestamp_utc": _utc_now()}
    log = get_approval_log(); log.append(record); _write_json(APPROVAL_PATH, log)
    _append_history({"type": "decision", "description": f"{decision}: {action_id}", "backup_id": backup_id,
                     "reversible": True, "undone": False, "details": record})
    return record


def save_snapshot(label="Manual snapshot") -> dict:
    snapshot_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S") + "_" + uuid.uuid4().hex[:8]
    folder = SNAPSHOT_DIR / snapshot_id; folder.mkdir(parents=True)
    shutil.copy2(DATA_PATH, folder / "orders.csv"); shutil.copy2(APPROVAL_PATH, folder / "approval_log.json")
    meta = {"snapshot_id": snapshot_id, "label": label or "Manual snapshot", "created_at_utc": _utc_now(), "internal": False}
    _write_json(folder / "metadata.json", meta)
    _append_history({"type": "snapshot", "description": f"Saved snapshot: {meta['label']}", "reversible": False, "undone": False, "details": meta})
    return meta


def list_snapshots() -> list[dict]:
    result = []
    for folder in SNAPSHOT_DIR.iterdir():
        meta = _read_json(folder / "metadata.json", {}) if folder.is_dir() else {}
        if meta and not meta.get("internal"):
            result.append(meta)
    return sorted(result, key=lambda x: x.get("created_at_utc", ""), reverse=True)


def restore_snapshot(snapshot_id: str) -> None:
    folder = SNAPSHOT_DIR / snapshot_id
    if not folder.exists(): raise FileNotFoundError(f"Snapshot not found: {snapshot_id}")
    backup_id = _backup("Before restore")
    shutil.copy2(folder / "orders.csv", DATA_PATH); shutil.copy2(folder / "approval_log.json", APPROVAL_PATH)
    _append_history({"type": "restore_snapshot", "description": f"Restored snapshot: {snapshot_id}", "backup_id": backup_id,
                     "reversible": True, "undone": False, "details": {"snapshot_id": snapshot_id}})


def replace_dataset_from_bytes(content: bytes, filename="uploaded.csv") -> list[dict]:
    backup_id = _backup("Before dataset upload")
    candidate = DATA_DIR / "_uploaded_candidate.csv"; candidate.write_bytes(content)
    try:
        rows = validate_csv_file(candidate); write_orders(rows)
    finally:
        candidate.unlink(missing_ok=True)
    _append_history({"type": "dataset_upload", "description": f"Replaced dataset with {filename}", "backup_id": backup_id,
                     "reversible": True, "undone": False, "details": {"filename": filename, "rows": len(rows)}})
    return rows


def reset_to_demo(clear_approvals=True) -> None:
    if not DEMO_DATA_PATH.exists(): raise FileNotFoundError("demo_orders.csv not found")
    backup_id = _backup("Before reset")
    shutil.copy2(DEMO_DATA_PATH, DATA_PATH)
    if clear_approvals: _write_json(APPROVAL_PATH, [])
    _append_history({"type": "reset_demo", "description": "Reset to demo dataset", "backup_id": backup_id,
                     "reversible": True, "undone": False, "details": {"clear_approvals": clear_approvals}})


def clear_approval_log() -> None:
    backup_id = _backup("Before clear approvals"); _write_json(APPROVAL_PATH, [])
    _append_history({"type": "clear_approvals", "description": "Cleared approval log", "backup_id": backup_id,
                     "reversible": True, "undone": False, "details": {}})


def undo_last_change():
    history = get_action_history()
    for index in range(len(history) - 1, -1, -1):
        event = history[index]
        if event.get("reversible") and not event.get("undone") and event.get("backup_id"):
            folder = SNAPSHOT_DIR / "_backups" / event["backup_id"]
            shutil.copy2(folder / "orders.csv", DATA_PATH); shutil.copy2(folder / "approval_log.json", APPROVAL_PATH)
            history[index]["undone"] = True
            history.append({"event_id": str(uuid.uuid4()), "timestamp_utc": _utc_now(), "type": "undo",
                            "description": f"Undid: {event.get('description')}", "reversible": False, "undone": False,
                            "details": {"undone_event_id": event.get("event_id")}})
            _write_json(HISTORY_PATH, history); return event
    return None


def deterministic_answer(question: str, rows=None) -> dict:
    rows = rows or load_orders(); q = question.lower()
    if any(term in q for term in ("scenario", "what if", "simulate")):
        result = simulate_scenario(rows, confirmation_days_saved=1)
        answer = f'If supplier confirmation improves by 1 day, projected OTD changes from {result["baseline_projected_otd_pct"]}% to {result["scenario_projected_otd_pct"]}% ({result["otd_delta_pp"]:+.1f} pp).'
        return {"answer": answer, "evidence": [json.dumps(result)], "tool_used": "simulate_scenario"}
    if any(term in q for term in ("supplier", "vendor")):
        top = supplier_analysis(rows)[:3]
        return {"answer": "Suppliers requiring the most attention: " + "; ".join(f'{s["supplier"]} ({s["high_risk_orders"]} high-risk orders)' for s in top) + ".",
                "evidence": [json.dumps(s) for s in top], "tool_used": "supplier_analysis"}
    if any(term in q for term in ("why", "root cause", "cause", "bottleneck", "problem")):
        top = root_causes(rows)[:3]
        return {"answer": "Leading operational signals: " + ", ".join(f'{c["driver"]} ({c["share_pct"]}%)' for c in top) + ".",
                "evidence": [json.dumps(c) for c in top], "tool_used": "root_causes"}
    if any(term in q for term in ("risk", "priority", "prioritize", "urgent", "action")):
        queue = high_risk_queue(rows, 5)
        return {"answer": f'{len(queue)} high-priority open orders are shown; start with {queue[0]["Order_ID"] if queue else "none"}.',
                "evidence": [json.dumps(r) for r in queue], "tool_used": "high_risk_queue"}
    snapshot = kpi_snapshot(rows)
    return {"answer": f'On-time delivery is {snapshot["on_time_delivery_pct"]}%, average lead time is {snapshot["avg_lead_time_days"]} days, {snapshot["open_orders"]} orders are open and {snapshot["high_risk_open_orders"]} are high risk.',
            "evidence": [json.dumps(snapshot)], "tool_used": "kpi_snapshot"}
