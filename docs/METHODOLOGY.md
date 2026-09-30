# Analytics Methodology

This document describes what the prototype calculates and, equally importantly, what it does **not** claim to calculate.

## 1. KPI layer

The application derives operational KPIs from order-level data:

- **On-Time Delivery (OTD):** delivered orders completed on or before the expected delivery date divided by delivered orders.
- **Average lead time:** average elapsed calendar days from order date to delivery date for delivered orders, or to the configured demo reference date for open orders.
- **Open orders:** orders whose status is `Open`.
- **Overdue open orders:** open orders whose expected delivery date is before the evaluation date.
- **High-risk open orders:** open orders whose rule-based risk score is at least 60.

The synthetic demo uses `2026-09-25` as a fixed reference date so the published example remains reproducible. This can be overridden with `SC_REFERENCE_DATE=YYYY-MM-DD`.

## 2. Rule-based risk score

The current prototype uses a transparent weighted rule set:

| Signal | Risk points |
|---|---:|
| Supplier confirmation > 3 days | +25 |
| Quality stage > 2 days | +20 |
| Inventory cover < 7 days | +20 |
| Critical priority | +20 |
| High priority | +10 |
| Open and overdue | +25 |

The synthetic demo also contains small supplier-specific calibration adjustments for `Supplier B` and `Supplier D`. These values are explicitly demo-only and should be replaced by business-calibrated logic in a real implementation.

Risk categories:

- **High:** score >= 60
- **Medium:** score >= 35 and < 60
- **Low:** score < 35

The score is capped at 100.

## 3. Root-cause signal analysis

Each order is assigned one dominant operational signal using a deterministic priority sequence:

1. supplier confirmation delay;
2. quality delay;
3. low inventory cover;
4. transit delay;
5. overdue open order;
6. no dominant issue.

The root-cause view counts these dominant signals across medium- and high-risk orders and reports each signal's share of flagged orders.

This is an **operational signal analysis**, not statistical proof of causality.

## 4. Supplier analysis

Orders are grouped by supplier. For each supplier the application calculates:

- number of orders;
- average supplier-confirmation days;
- late-delivery rate among delivered orders;
- number of high-risk orders.

Suppliers are sorted primarily by number of high-risk orders and secondarily by late-delivery rate.

## 5. Counterfactual scenario simulator

Scenario Lab is a **deterministic counterfactual / what-if analysis**.

It is not:

- a Monte Carlo simulation;
- a discrete-event simulation;
- a machine-learning forecast;
- a probabilistic prediction.

Users can change four assumptions:

- confirmation days saved;
- quality days saved;
- transit days saved;
- inventory-cover uplift.

For delivered orders, the prototype defines process lead time as:

`Supplier Confirmation + Processing + Quality + Transit`

The baseline and scenario process times are compared with each order's allowed time window (`Expected_Delivery - Order_Date`). This produces baseline and scenario projected OTD values.

The engine also recalculates average process lead time and the number of high-risk open orders under the changed assumptions.

## 6. AI agent layer

The LLM does not perform the core mathematics. The application exposes deterministic analytics functions as tools. When an API key is connected, the LLM can select the appropriate tool(s), interpret the structured outputs, and communicate them in natural language.

When no API key is connected, a deterministic fallback router maps common question types to the same analytics functions.

## 7. Human-in-the-loop governance

Recommendations are proposals, not executions. A recommendation only becomes a recorded decision when the user explicitly selects **Approve** or **Reject**.

The application stores:

- action ID;
- decision;
- recommendation;
- supporting evidence;
- optional user note;
- timestamp.

Snapshot, restore, reset, dataset replacement, and approval decisions can be tracked through the state-management layer.

## 8. Production extensions

A production version could replace or extend the current deterministic prototype with:

- configurable business rules stored outside the codebase;
- historical supplier-performance calibration;
- probabilistic delay models;
- Monte Carlo uncertainty analysis;
- optimization models for recovery actions;
- SQL/database persistence;
- automated tests and CI/CD;
- authentication and role-based access control;
- observability and model/tool audit monitoring.
