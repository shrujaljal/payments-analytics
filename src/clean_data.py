"""
Data quality checks and cleaning for the raw payout extract.

Every check is logged with how many rows it affected, so the cleaning is
transparent and repeatable. The script writes:

  data/clean/transactions_clean.csv.gz   clean fact table (used by the SQL)
  data/clean/data_quality_report.csv  one row per check, with row counts
  tableau/payments_tableau.csv        one flat, Tableau-ready file

Run:  python src/clean_data.py
"""

from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
RAW, CLEAN, TABLEAU = ROOT / "data" / "raw", ROOT / "data" / "clean", ROOT / "tableau"

VALID_STATUS = {"Completed", "Failed", "Reversed", "Pending"}

tx = pd.read_csv(RAW / "transactions.csv.gz", parse_dates=["created_at", "completed_at"])
members = pd.read_csv(RAW / "members.csv", parse_dates=["onboarded_date"])
partners = pd.read_csv(RAW / "payout_partners.csv")

log = []


def record(check, rows, action):
    log.append({"check": check, "rows_affected": int(rows), "action": action})
    print(f"{check:<48} {rows:>6,}  -> {action}")


start_rows = len(tx)
record("Rows in raw extract", start_rows, "starting point")

# 1. Exact duplicate rows (export retried twice)
d = tx.duplicated().sum()
tx = tx.drop_duplicates()
record("Exact duplicate rows", d, "dropped")

# 2. Same transaction_id appearing more than once with different values
d = tx["transaction_id"].duplicated().sum()
tx = tx.drop_duplicates("transaction_id", keep="last")
record("Duplicate transaction_id (different values)", d, "kept latest row")

# 3. Inconsistent status labels ("completed ", "failed ")
raw_status = tx["status"].copy()
tx["status"] = tx["status"].str.strip().str.title()
record("Status labels with wrong case or spaces", (raw_status != tx["status"]).sum(), "standardized")
bad = ~tx["status"].isin(VALID_STATUS)
record("Unknown status values", bad.sum(), "dropped")
tx = tx[~bad]

# 4. Zero or negative amounts (internal test payouts)
bad = tx["send_amount_usd"] <= 0
record("Zero or negative send amounts", bad.sum(), "dropped as test records")
tx = tx[~bad]

# 5. Failure reason filled on a non-failed payout
bad = (tx["status"] != "Failed") & tx["failure_reason"].notna()
record("Failure reason on non-failed payout", bad.sum(), "cleared")
tx.loc[bad, "failure_reason"] = np.nan

# 6. Failed payout with no reason
bad = (tx["status"] == "Failed") & tx["failure_reason"].isna()
record("Failed payout missing a reason", bad.sum(), "set to 'Unknown'")
tx.loc[bad, "failure_reason"] = "Unknown"

# 7. Missing fee on a completed payout: rebuild from the member's fee schedule
miss = tx["fee_usd"].isna()
if miss.any():
    seg = tx["member_id"].map(members.set_index("member_id")["segment"])
    ok = tx[~miss & (tx["status"] == "Completed")].assign(segment=seg)
    # fee = fixed + pct * amount, estimated per segment with least squares
    sched = {}
    for s, g in ok.groupby("segment"):
        pct, fixed = np.polyfit(g["send_amount_usd"], g["fee_usd"], 1)
        sched[s] = (fixed, pct)
    est = [round(sched[s][0] + sched[s][1] * a, 2)
           for s, a in zip(seg[miss], tx.loc[miss, "send_amount_usd"])]
    tx.loc[miss, "fee_usd"] = est
record("Missing fee on completed payout", miss.sum(), "rebuilt from segment fee schedule")

# 8. Completed earlier than created (clock issues)
bad = tx["completed_at"] < tx["created_at"]
record("completed_at before created_at", bad.sum(), "dropped")
tx = tx[~bad]

# 9. Orphan keys
bad = ~tx["member_id"].isin(members["member_id"]) | ~tx["partner_id"].isin(partners["partner_id"])
record("Unknown member or partner id", bad.sum(), "dropped")
tx = tx[~bad]

record("Rows in clean table", len(tx), f"{len(tx) / start_rows:.1%} of raw rows kept")

# ---------------------------------------------------------------------------
# Derived fields used everywhere downstream
# ---------------------------------------------------------------------------
tx = tx.sort_values("created_at").reset_index(drop=True)
tx["revenue_usd"] = (tx["fee_usd"] + tx["fx_margin_usd"]).round(2)
tx["is_failed"] = (tx["status"] == "Failed").astype(int)
tx["is_final"] = tx["status"].isin(["Completed", "Failed", "Reversed"]).astype(int)

CLEAN.mkdir(parents=True, exist_ok=True)
tx.to_csv(CLEAN / "transactions_clean.csv.gz", index=False)
pd.DataFrame(log).to_csv(CLEAN / "data_quality_report.csv", index=False)

# ---------------------------------------------------------------------------
# One flat file for Tableau (no joins needed inside Tableau Public)
# ---------------------------------------------------------------------------
flat = (tx.merge(members, on="member_id", how="left")
          .merge(partners[["partner_id", "partner_name"]], on="partner_id", how="left"))
flat["created_date"] = flat["created_at"].dt.date
flat["processing_minutes"] = (flat["processing_seconds"] / 60).round(2)
country_names = {"US": "United States", "AE": "United Arab Emirates", "GB": "United Kingdom",
                 "SG": "Singapore", "SA": "Saudi Arabia", "FR": "France", "HK": "Hong Kong",
                 "PH": "Philippines", "MX": "Mexico", "IN": "India", "PK": "Pakistan",
                 "KE": "Kenya", "NG": "Nigeria", "ID": "Indonesia", "BD": "Bangladesh",
                 "SN": "Senegal", "GH": "Ghana", "CN": "China"}
flat["send_country_name"] = flat["send_country"].map(country_names)
flat["receive_country_name"] = flat["receive_country"].map(country_names)
# Only the fields the dashboard needs, so the file stays under GitHub's 25 MB browser-upload limit
cols = ["transaction_id", "created_at", "member_name", "segment", "send_country_name",
        "receive_country_name", "corridor", "payout_method", "partner_name", "send_amount_usd",
        "revenue_usd", "status", "failure_reason", "is_failed", "is_final", "processing_minutes"]
TABLEAU.mkdir(parents=True, exist_ok=True)
flat[cols].to_csv(TABLEAU / "payments_tableau.csv", index=False)
print(f"\nWrote {len(tx):,} clean rows and a {len(cols)}-column Tableau file.")
