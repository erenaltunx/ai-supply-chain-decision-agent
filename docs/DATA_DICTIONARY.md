# Data Dictionary

The application expects a CSV dataset with the following base columns.

| Column | Type | Description |
|---|---|---|
| `Order_ID` | text | Unique order identifier |
| `Supplier` | text | Supplier name or code |
| `Region` | text | Operational region |
| `Category` | text | Material/product category |
| `Priority` | text | Typical values: Low, Medium, High, Critical |
| `Order_Date` | date | Order creation date (`YYYY-MM-DD`) |
| `Expected_Delivery` | date | Required/expected delivery date |
| `Delivery_Date` | date/blank | Actual delivery date; blank for open orders |
| `Supplier_Confirm_Days` | integer | Days required for supplier confirmation |
| `Processing_Days` | integer | Internal/operational processing days |
| `Quality_Days` | integer | Quality/inspection processing days |
| `Transit_Days` | integer | Transportation days |
| `Quantity` | integer | Order quantity |
| `Order_Value_EUR` | numeric | Order value in euros |
| `Inventory_Cover_Days` | numeric | Estimated days of inventory cover |
| `Status` | text | `Open` or `Delivered` |

## Derived fields

The analytics engine recalculates these fields automatically:

| Column | Description |
|---|---|
| `Actual_or_Current_Lead_Time` | Days from order date to delivery date, or to the configured reference date for open orders |
| `Days_Late` | Positive lateness versus expected delivery date |
| `On_Time` | `Yes`, `No`, or `Open` |
| `Risk_Score` | Transparent rule-based score from 0 to 100 |
| `Risk_Level` | Low, Medium, or High |
| `Primary_Driver` | Dominant operational risk signal |

Uploaded files only need the base columns. Existing derived columns may be present, but the application recalculates them.

## Demo data

`data/demo_orders.csv` contains 150 synthetic orders. It is included only for demonstration and portfolio purposes and does not represent a real company or supplier network.
