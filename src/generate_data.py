"""
Generate a realistic, fully synthetic cross-border payout dataset.

The data imitates how a real-time payments network moves money from
"members" (gig platforms, remittance companies, fintechs, PSPs, banks)
to recipients' mobile wallets and bank accounts in other countries.

All company and partner names are fictional. The data is synthetic and
contains a few deliberate business patterns and data quality issues so the
analysis has something real to find.

Run:  python src/generate_data.py
Out:  data/raw/transactions.csv.gz, data/raw/members.csv, data/raw/payout_partners.csv
"""

from pathlib import Path

import numpy as np
import pandas as pd

SEED = 42
N_TXNS = 120_000
START = pd.Timestamp("2026-01-01")
END = pd.Timestamp("2026-09-30 23:59:59")

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw"

rng = np.random.default_rng(SEED)

# ---------------------------------------------------------------------------
# 1. Corridors: where money is sent from and to
# ---------------------------------------------------------------------------
# share = share of total volume, wallet = share paid out to mobile wallets
# fx_margin = FX margin earned (as % of send amount)
CORRIDORS = pd.DataFrame(
    [
        # send, receive, send_ccy, payout_ccy, fx_rate, share, wallet, fx_margin
        ("US", "PH", "USD", "PHP", 57.2, 0.17, 0.70, 0.0080),
        ("US", "MX", "USD", "MXN", 18.6, 0.12, 0.25, 0.0060),
        ("US", "IN", "USD", "INR", 85.1, 0.10, 0.10, 0.0050),
        ("AE", "IN", "AED", "INR", 85.1, 0.12, 0.10, 0.0055),
        ("AE", "PK", "AED", "PKR", 281.0, 0.08, 0.50, 0.0090),
        ("GB", "KE", "GBP", "KES", 129.0, 0.07, 0.85, 0.0110),
        ("GB", "NG", "GBP", "NGN", 1540.0, 0.06, 0.10, 0.0120),
        ("SG", "ID", "SGD", "IDR", 16250.0, 0.07, 0.60, 0.0070),
        ("SA", "BD", "SAR", "BDT", 120.0, 0.06, 0.60, 0.0090),
        ("FR", "SN", "EUR", "XOF", 590.0, 0.04, 0.80, 0.0100),
        ("US", "GH", "USD", "GHS", 15.4, 0.04, 0.70, 0.0110),
        ("HK", "CN", "HKD", "CNY", 7.2, 0.07, 0.90, 0.0045),
    ],
    columns=["send_country", "receive_country", "send_currency", "payout_currency",
             "fx_rate", "share", "wallet_share", "fx_margin"],
)
CORRIDORS["corridor"] = CORRIDORS["send_country"] + "-" + CORRIDORS["receive_country"]
CORRIDORS["share"] /= CORRIDORS["share"].sum()

# ---------------------------------------------------------------------------
# 2. Payout partners: the local wallets and banks that deliver the money
# ---------------------------------------------------------------------------
partner_rows = []
pid = 1
for rc in CORRIDORS["receive_country"].unique():
    # Philippines and India get two partners per method, others one
    n = 2 if rc in ("PH", "IN") else 1
    for method in ("Mobile wallet", "Bank account"):
        for k in range(n):
            label = "Wallet" if method == "Mobile wallet" else "Bank"
            partner_rows.append({
                "partner_id": f"P{pid:02d}",
                "partner_name": f"{rc} {label} Partner {'AB'[k]}",
                "country": rc,
                "payout_method": method,
            })
            pid += 1
partners = pd.DataFrame(partner_rows)

# ---------------------------------------------------------------------------
# 3. Members: the businesses sending payouts through the network
# ---------------------------------------------------------------------------
SEGMENTS = {
    # segment: (number of members, median ticket USD, ticket spread, fixed fee USD, % fee)
    "Gig economy": (8, 45, 0.7, 0.30, 0.0040),
    "Remittance (MTO)": (12, 260, 0.6, 0.90, 0.0030),
    "Fintech": (10, 150, 0.8, 0.60, 0.0035),
    "PSP": (6, 120, 0.8, 0.50, 0.0035),
    "Bank": (4, 850, 0.9, 1.50, 0.0020),
}
NAME_PARTS = ["Nova", "Swift", "Atlas", "Orbit", "Kite", "Pulse", "Harbor", "Zen",
              "Bolt", "Lumen", "Arc", "Vela", "Peak", "Fern", "Sol", "Echo", "Rally",
              "Tidal", "Crest", "Ember", "Quill", "Brio", "Nimbus", "Haven", "Juno",
              "Maple", "Onyx", "Prism", "Ridge", "Sage", "Terra", "Umbra", "Vivo",
              "Willow", "Zephyr", "Coral", "Delta", "Flint", "Golden", "Ivory"]
SUFFIX = {"Gig economy": "Ride", "Remittance (MTO)": "Remit", "Fintech": "Pay",
          "PSP": "Pay Gateway", "Bank": "Bank"}

member_rows = []
mid = 1
names = rng.permutation(NAME_PARTS)
for seg, (n, *_rest) in SEGMENTS.items():
    for _ in range(n):
        onboard = START - pd.Timedelta(days=int(rng.integers(60, 900)))
        member_rows.append({
            "member_id": f"M{mid:03d}",
            "member_name": f"{names[mid - 1]}{SUFFIX[seg]}",
            "segment": seg,
            "onboarded_date": onboard.date(),
        })
        mid += 1
members = pd.DataFrame(member_rows)

# A few members are onboarded during the year (new business)
new_ids = ["M038", "M039", "M040", "M015"]
new_dates = ["2026-03-02", "2026-05-11", "2026-07-06", "2026-02-02"]
for m, d in zip(new_ids, new_dates):
    members.loc[members["member_id"] == m, "onboarded_date"] = pd.Timestamp(d).date()

# Pareto-style volume: a few members send most of the volume
weights = rng.lognormal(0, 1.0, len(members))
members["volume_weight"] = weights / weights.sum()

# Each member sends through a subset of corridors
member_corridors = {}
for _, m in members.iterrows():
    k = int(rng.integers(3, 9))
    member_corridors[m["member_id"]] = rng.choice(
        CORRIDORS["corridor"], size=k, replace=False, p=CORRIDORS["share"])

# ---------------------------------------------------------------------------
# 4. Transaction timestamps with growth, daily and weekly seasonality
# ---------------------------------------------------------------------------
days = pd.date_range(START.normalize(), END.normalize(), freq="D")
t = np.arange(len(days))
growth = 1.045 ** (t / 30.4)                      # ~4.5% monthly growth
dow = np.array([1.00, 0.98, 0.99, 1.02, 1.15, 1.08, 0.80])[days.dayofweek]
payday = np.where(np.isin(days.day, [1, 2, 15, 16, 28, 29, 30, 31]), 1.18, 1.0)
day_w = growth * dow * payday
day_w /= day_w.sum()

day_idx = rng.choice(len(days), size=N_TXNS, p=day_w)
hour_w = np.array([2, 1.5, 1, 1, 1, 1.5, 3, 5, 7, 8, 8, 8, 8, 8, 8, 8, 8, 8, 7, 6, 5, 4, 3, 2.5])
hour_w /= hour_w.sum()
hours = rng.choice(24, size=N_TXNS, p=hour_w)
secs = rng.integers(0, 3600, size=N_TXNS)
created_at = days[day_idx] + pd.to_timedelta(hours, unit="h") + pd.to_timedelta(secs, unit="s")

# ---------------------------------------------------------------------------
# 5. Assign member, corridor, payout method and partner
# ---------------------------------------------------------------------------
member_idx = rng.choice(len(members), size=N_TXNS, p=members["volume_weight"])
member_id = members["member_id"].to_numpy()[member_idx]

# Members onboarded mid-year cannot send before onboarding
onb = pd.to_datetime(members.set_index("member_id")["onboarded_date"])
too_early = created_at < onb.reindex(member_id).to_numpy()
while too_early.any():
    member_idx[too_early] = rng.choice(len(members), size=too_early.sum(), p=members["volume_weight"])
    member_id = members["member_id"].to_numpy()[member_idx]
    too_early = created_at < onb.reindex(member_id).to_numpy()

corr_lookup = CORRIDORS.set_index("corridor")
corridor = np.empty(N_TXNS, dtype=object)
for m in np.unique(member_id):
    mask = member_id == m
    allowed = member_corridors[m]
    p = corr_lookup.loc[allowed, "share"].to_numpy()
    corridor[mask] = rng.choice(allowed, size=mask.sum(), p=p / p.sum())

c = corr_lookup.loc[corridor].reset_index()
is_wallet = rng.random(N_TXNS) < c["wallet_share"].to_numpy()
payout_method = np.where(is_wallet, "Mobile wallet", "Bank account")

partner_id = np.empty(N_TXNS, dtype=object)
for (rc, meth), grp in partners.groupby(["country", "payout_method"]):
    mask = (c["receive_country"].to_numpy() == rc) & (payout_method == meth)
    ids = grp["partner_id"].to_numpy()
    p = np.array([0.6, 0.4]) if len(ids) == 2 else np.array([1.0])
    partner_id[mask] = rng.choice(ids, size=mask.sum(), p=p)

# ---------------------------------------------------------------------------
# 6. Amounts, fees, FX
# ---------------------------------------------------------------------------
seg = members.set_index("member_id").loc[member_id, "segment"].to_numpy()
seg_tbl = pd.DataFrame(SEGMENTS, index=["n", "median", "spread", "fixed_fee", "pct_fee"]).T
median = seg_tbl.loc[seg, "median"].to_numpy(float)
spread = seg_tbl.loc[seg, "spread"].to_numpy(float)
amount = np.round(np.exp(np.log(median) + rng.normal(0, spread)), 2)
amount = np.clip(amount, 2, 25_000)

fee = np.round(seg_tbl.loc[seg, "fixed_fee"].to_numpy(float)
               + amount * seg_tbl.loc[seg, "pct_fee"].to_numpy(float), 2)
fx_drift = 1 + 0.03 * np.sin(day_idx / 45) + rng.normal(0, 0.002, N_TXNS)
fx_rate = np.round(c["fx_rate"].to_numpy() * fx_drift, 4)
fx_margin_usd = np.round(amount * c["fx_margin"].to_numpy(), 2)
payout_amount = np.round(amount * fx_rate, 2)

# ---------------------------------------------------------------------------
# 7. Status and failure reasons, with deliberate business patterns
# ---------------------------------------------------------------------------
rc = c["receive_country"].to_numpy()
cor = corridor.astype(str)
ts = pd.DatetimeIndex(created_at)
REASONS = ["Invalid account details", "Name mismatch", "Wallet not registered",
           "Recipient limit exceeded", "Partner timeout", "Compliance rejection",
           "Insufficient prefunding", "Other"]

# baseline failure probability per reason
p = {r: np.full(N_TXNS, v) for r, v in zip(
    REASONS, [0.008, 0.005, 0.0, 0.003, 0.003, 0.002, 0.0005, 0.002])}
p["Wallet not registered"] = np.where(payout_method == "Mobile wallet", 0.006, 0.0)
p["Invalid account details"] = np.where(payout_method == "Bank account", 0.012, 0.004)

# Pattern A: UK to Nigeria bank payouts fail a lot on bad account details
p["Invalid account details"] = np.where((cor == "GB-NG") & (payout_method == "Bank account"),
                                        0.065, p["Invalid account details"])
# Pattern B: one Philippine wallet partner has a 6 day outage in June
outage = (partner_id == partners.loc[partners.partner_name == "PH Wallet Partner A", "partner_id"].item()) \
    & (ts >= "2026-06-08") & (ts < "2026-06-14")
p["Partner timeout"] = np.where(outage, 0.32, p["Partner timeout"])
# Pattern C: compliance screening is stricter on UAE to Pakistan
p["Compliance rejection"] = np.where(cor == "AE-PK", 0.018, p["Compliance rejection"])
# Pattern D: Kenya prefunding runs low in the last 3 days of each month
month_end = ts.day >= (ts.days_in_month - 2)
p["Insufficient prefunding"] = np.where((rc == "KE") & month_end, 0.09, p["Insufficient prefunding"])
# Pattern E: one fintech member's recipient data quality drops after July 1
bad_member = "M025"
p["Name mismatch"] = np.where((member_id == bad_member) & (ts >= "2026-07-01"), 0.07, p["Name mismatch"])
p["Invalid account details"] = np.where((member_id == bad_member) & (ts >= "2026-07-01"),
                                        p["Invalid account details"] + 0.05, p["Invalid account details"])
# Large bank-sent payouts to wallets often hit wallet balance limits
p["Recipient limit exceeded"] = np.where((seg == "Bank") & (payout_method == "Mobile wallet"),
                                         0.03, p["Recipient limit exceeded"])

P = np.column_stack([p[r] for r in REASONS])
fail_prob = 1 - np.prod(1 - P, axis=1)
failed = rng.random(N_TXNS) < fail_prob
reason_idx = np.array([rng.choice(len(REASONS), p=row / row.sum()) if f else -1
                       for f, row in zip(failed, P)])
failure_reason = np.where(reason_idx >= 0, np.array(REASONS + [""])[reason_idx], "")

status = np.where(failed, "Failed", "Completed").astype(object)
# A few completed payouts are later reversed (returned by the bank)
reversed_ = (~failed) & (payout_method == "Bank account") & (rng.random(N_TXNS) < 0.0025)
status[reversed_] = "Reversed"
# The most recent payouts may still be pending at extract time
pending = (ts > END - pd.Timedelta(hours=10)) & (rng.random(N_TXNS) < 0.35)
status[pending] = "Pending"
failure_reason[pending] = ""

# ---------------------------------------------------------------------------
# 8. Processing time (seconds from creation to final status)
# ---------------------------------------------------------------------------
proc = np.where(payout_method == "Mobile wallet",
                rng.lognormal(np.log(6), 0.6, N_TXNS),
                rng.lognormal(np.log(90), 0.8, N_TXNS))
# Nigeria and Bangladesh bank payouts are batch-based
batch = (payout_method == "Bank account") & np.isin(rc, ["NG", "BD"])
proc = np.where(batch, rng.lognormal(np.log(1800), 0.7, N_TXNS), proc)
# Bank payouts created on weekends in India, Pakistan, Bangladesh wait for Monday
weekend = ts.dayofweek >= 5
wait = (payout_method == "Bank account") & weekend & np.isin(rc, ["IN", "PK", "BD"])
proc = np.where(wait & (rng.random(N_TXNS) < 0.55), proc + rng.uniform(4, 30, N_TXNS) * 3600, proc)
# Compliance reviews add hours for a share of UAE to Pakistan payouts
review = (cor == "AE-PK") & (rng.random(N_TXNS) < 0.06)
proc = np.where(review, proc + rng.uniform(1, 8, N_TXNS) * 3600, proc)
# Outage timeouts take ~60 seconds before failing
proc = np.where(failure_reason == "Partner timeout", rng.uniform(55, 65, N_TXNS), proc)
proc = np.round(proc, 1)
completed_at = pd.Series(ts + pd.to_timedelta(proc, unit="s"))
completed_at[status == "Pending"] = pd.NaT
proc = np.where(status == "Pending", np.nan, proc)

# Failed payouts earn no fee
fee = np.where(status == "Failed", 0.0, fee)
fx_margin_usd = np.where(np.isin(status, ["Failed", "Reversed"]), 0.0, fx_margin_usd)

tx = pd.DataFrame({
    "transaction_id": [f"T{n:07d}" for n in range(1, N_TXNS + 1)],
    "created_at": ts,
    "completed_at": completed_at.values,
    "member_id": member_id,
    "send_country": c["send_country"].to_numpy(),
    "receive_country": rc,
    "corridor": cor,
    "send_currency": c["send_currency"].to_numpy(),
    "payout_currency": c["payout_currency"].to_numpy(),
    "payout_method": payout_method,
    "partner_id": partner_id,
    "send_amount_usd": amount,
    "fx_rate": fx_rate,
    "payout_amount": payout_amount,
    "fee_usd": fee,
    "fx_margin_usd": fx_margin_usd,
    "status": status,
    "failure_reason": failure_reason,
    "processing_seconds": proc,
}).sort_values("created_at").reset_index(drop=True)

# ---------------------------------------------------------------------------
# 9. Inject realistic data quality issues (the cleaning script must fix these)
# ---------------------------------------------------------------------------
n = len(tx)
# 1. Duplicate rows from a retried export (~0.4%)
dups = tx.sample(frac=0.004, random_state=SEED)
# 2. Inconsistent status labels
idx = rng.choice(n, 300, replace=False)
tx.loc[idx, "status"] = tx.loc[idx, "status"].str.lower() + " "
# 3. Missing fees
idx = rng.choice(np.flatnonzero(tx["status"].str.strip().str.lower() == "completed"), 180, replace=False)
tx.loc[idx, "fee_usd"] = np.nan
# 4. Zero or negative test amounts
idx = rng.choice(n, 45, replace=False)
tx.loc[idx, "send_amount_usd"] = rng.choice([0.0, -1.0, -50.0], 45)
# 5. Failure reason filled on completed payouts (system bug)
idx = rng.choice(np.flatnonzero(tx["status"] == "Completed"), 60, replace=False)
tx.loc[idx, "failure_reason"] = "Other"
tx = pd.concat([tx, dups]).sample(frac=1, random_state=SEED).reset_index(drop=True)

RAW.mkdir(parents=True, exist_ok=True)
tx.to_csv(RAW / "transactions.csv.gz", index=False)
members.drop(columns="volume_weight").to_csv(RAW / "members.csv", index=False)
partners.to_csv(RAW / "payout_partners.csv", index=False)
print(f"transactions: {len(tx):,} rows | members: {len(members)} | partners: {len(partners)}")
