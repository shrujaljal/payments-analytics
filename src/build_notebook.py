"""Builds and executes notebooks/payments_analysis.ipynb (so the outputs show on GitHub)."""
from pathlib import Path

import nbformat as nbf
from nbconvert.preprocessors import ExecutePreprocessor

ROOT = Path(__file__).resolve().parents[1]
nb = nbf.v4.new_notebook()
md, code = nbf.v4.new_markdown_cell, nbf.v4.new_code_cell

nb.cells = [
md("""# Cross-Border Payments Analytics

**Question:** Where is the payout network losing reliability, speed and revenue, and what should each team do about it?

Data: ~120K synthetic real-time payouts (Jan to Sep 2026) from 40 member businesses across 12 corridors, paid out to mobile wallets and bank accounts. See `docs/data_dictionary.md` for every field and metric definition.

Steps: **1.** load clean data → **2.** headline KPIs → **3.** growth → **4.** reliability by corridor → **5.** incident detection → **6.** member health → **7.** treasury → **8.** speed → **9.** cost of failures → **10.** recommendations"""),
code("""import duckdb
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.ticker as mtick
from pathlib import Path

ROOT = Path.cwd().parent if Path.cwd().name == "notebooks" else Path.cwd()
IMG = ROOT / "images"; IMG.mkdir(exist_ok=True)

con = duckdb.connect()
con.execute(f\"\"\"
CREATE VIEW transactions AS SELECT * FROM read_csv_auto('{ROOT/'data/clean/transactions_clean.csv.gz'}', timestampformat='%Y-%m-%d %H:%M:%S');
CREATE VIEW members  AS SELECT * FROM read_csv_auto('{ROOT/'data/raw/members.csv'}');
CREATE VIEW partners AS SELECT * FROM read_csv_auto('{ROOT/'data/raw/payout_partners.csv'}');
\"\"\")
sql = lambda name: con.execute((ROOT / 'sql' / f'{name}.sql').read_text()).df()
q = lambda text: con.execute(text).df()

# Chart style: thin marks, recessive grid, one highlight color against gray
BLUE, ORANGE, RED, GRAY, INK, INK2 = '#2a78d6', '#eb6834', '#e34948', '#c9c8c3', '#0b0b0b', '#52514e'
plt.rcParams.update({'figure.facecolor': '#fcfcfb', 'axes.facecolor': '#fcfcfb', 'axes.edgecolor': '#d6d5d0',
    'axes.grid': True, 'grid.color': '#ebeae6', 'grid.linewidth': 0.8, 'axes.axisbelow': True,
    'axes.spines.top': False, 'axes.spines.right': False, 'axes.labelcolor': INK2,
    'xtick.color': INK2, 'ytick.color': INK2, 'font.size': 10, 'axes.titlesize': 12,
    'axes.titleweight': 'bold', 'axes.titlelocation': 'left', 'figure.dpi': 110})
def save(fig, name):
    fig.tight_layout(); fig.savefig(IMG / f'{name}.png', dpi=150, bbox_inches='tight'); plt.show()"""),

md("## 1. Data quality first\nThe raw extract had duplicates, messy status labels, test payouts and missing fees. `src/clean_data.py` fixes each one and logs it:"),
code("pd.read_csv(ROOT / 'data/clean/data_quality_report.csv')"),

md("## 2. Headline KPIs"),
code("sql('01_kpi_summary').T.rename(columns={0: 'value'})"),

md("## 3. Growth\nDaily payouts grew every month. Revenue grew faster than payout count because larger bank and remittance tickets grew."),
code("""m = sql('02_monthly_trend'); display(m)
fig, ax = plt.subplots(figsize=(8, 3.6))
ax.bar(m['month'], m['payouts_per_day'], color=BLUE, width=0.6)
for x, y in zip(m['month'], m['payouts_per_day']):
    ax.text(x, y + 6, f'{y:.0f}', ha='center', fontsize=8, color=INK2)
ax.set_title('Average payouts per day grew 41% from January to September')
ax.set_ylabel('Payouts per day'); ax.grid(axis='x', visible=False)
save(fig, '01_daily_payouts_trend')"""),

md("## 4. Reliability by corridor\nOne corridor stands out: **UK → Nigeria bank payouts fail more than twice as often as the network**, and most of those failures are bad account details entered by the sender."),
code("""c = sql('03_corridor_performance'); display(c.head(8))
c['label'] = c['corridor'] + ' · ' + c['payout_method'].str.replace('Mobile wallet','wallet').str.replace('Bank account','bank')
c = c.sort_values('failure_rate_pct')
net = q("SELECT 100.0*SUM(is_failed)/SUM(is_final) AS r FROM transactions")['r'][0]
fig, ax = plt.subplots(figsize=(8, 6))
colors = [RED if r == c['failure_rate_pct'].max() else GRAY for r in c['failure_rate_pct']]
ax.barh(c['label'], c['failure_rate_pct'], color=colors, height=0.6)
ax.axvline(net, color=INK, lw=1, ls='--'); ax.text(net + 0.1, -0.9, f'Network {net:.1f}%', fontsize=8, color=INK)
ax.xaxis.set_major_formatter(mtick.PercentFormatter(decimals=0))
ax.set_title('UK → Nigeria bank payouts fail at more than twice the network rate')
ax.set_xlabel('Failure rate (corridors with 500+ payouts)'); ax.grid(axis='y', visible=False)
save(fig, '02_failure_rate_by_corridor')"""),
code("sql('04_failure_reasons')"),

md("## 5. Incident detection\nThis query compares each partner's daily failure rate with its own trailing 28-day average and flags days above 3×. It catches a **6-day outage at PH Wallet Partner A (June 8–13)** automatically, with no manual monitoring."),
code("""inc = sql('05_partner_incident_detection'); display(inc)
d = q(\"\"\"
SELECT CAST(created_at AS DATE) AS day, 100.0*SUM(is_failed)/COUNT(*) AS fail_pct
FROM transactions JOIN partners USING (partner_id)
WHERE partner_name = 'PH Wallet Partner A' AND created_at BETWEEN '2026-05-10' AND '2026-07-10'
GROUP BY 1 ORDER BY 1\"\"\")
fig, ax = plt.subplots(figsize=(8, 3.4))
ax.plot(d['day'], d['fail_pct'], color=BLUE, lw=2)
ax.axvspan(pd.Timestamp('2026-06-08'), pd.Timestamp('2026-06-13 23:59'), color=RED, alpha=0.12)
ax.text(pd.Timestamp('2026-06-14'), d['fail_pct'].max() * 0.9, 'Partner outage\\n(timeouts)', fontsize=8, color=INK)
ax.yaxis.set_major_formatter(mtick.PercentFormatter(decimals=0))
import matplotlib.dates as mdates
ax.xaxis.set_major_locator(mdates.WeekdayLocator(byweekday=0, interval=2)); ax.xaxis.set_major_formatter(mdates.DateFormatter('%b %d'))
ax.set_title('PH Wallet Partner A: daily failure rate jumped ~8x for six days')
ax.set_ylabel('Daily failure rate')
save(fig, '03_partner_outage')"""),

md("## 6. Member health\nOne fintech member's failure rate jumped from under 3% to over 14% starting in July, driven by name mismatches and invalid account details. This looks like a change on **their** side (recipient data capture), not ours."),
code("""mh = sql('06_member_health'); display(mh)
worst = mh.iloc[0]['member_name']
w = q(f\"\"\"
SELECT DATE_TRUNC('week', created_at) AS wk,
       100.0*SUM(is_failed) FILTER (WHERE member_name = '{worst}') / SUM(is_final) FILTER (WHERE member_name = '{worst}') member_pct,
       100.0*SUM(is_failed) FILTER (WHERE member_name <> '{worst}') / SUM(is_final) FILTER (WHERE member_name <> '{worst}') network_pct
FROM transactions JOIN members USING (member_id)
GROUP BY 1 HAVING COUNT(*) FILTER (WHERE member_name = '{worst}') >= 20 ORDER BY 1\"\"\")
fig, ax = plt.subplots(figsize=(8, 3.4))
ax.plot(w['wk'], w['network_pct'], color=GRAY, lw=2)
ax.plot(w['wk'], w['member_pct'], color=ORANGE, lw=2)
ax.text(w['wk'].iloc[-1] + pd.Timedelta(days=4), w['member_pct'].iloc[-1], worst, color=INK, fontsize=8, va='center')
ax.text(w['wk'].iloc[-1] + pd.Timedelta(days=4), w['network_pct'].iloc[-1], 'Rest of network', color=INK2, fontsize=8, va='center')
ax.xaxis.set_major_formatter(mdates.DateFormatter('%b'))
ax.yaxis.set_major_formatter(mtick.PercentFormatter(decimals=0))
ax.set_title(f'{worst}: weekly failure rate rose sharply from July')
ax.set_ylabel('Weekly failure rate')
save(fig, '04_member_failure_spike')"""),

md("## 7. Treasury: month-end prefunding\nPrefunding failures are rare everywhere except **Kenya in the last 3 days of each month**, when the prefunded balance runs out before it is topped up."),
code("""display(sql('07_month_end_prefunding').head(5))
k = q(\"\"\"
SELECT DAY(created_at) AS dom,
       100.0*SUM(CASE WHEN failure_reason='Insufficient prefunding' THEN 1 ELSE 0 END)/COUNT(*) AS pct
FROM transactions WHERE receive_country = 'KE' GROUP BY 1 ORDER BY 1\"\"\")
fig, ax = plt.subplots(figsize=(8, 3.2))
ax.bar(k['dom'], k['pct'], color=[RED if d >= 28 else GRAY for d in k['dom']], width=0.7)
ax.yaxis.set_major_formatter(mtick.PercentFormatter(decimals=0))
ax.set_title('Kenya: prefunding failures cluster at month end'); ax.set_xlabel('Day of month')
ax.set_ylabel('Payouts failed for prefunding'); ax.grid(axis='x', visible=False)
save(fig, '05_kenya_month_end_prefunding')"""),

md("## 8. Speed: weekend bank payouts\nWallet payouts settle in seconds every day. Bank payouts to **India, Pakistan and Bangladesh** created on weekends wait hours for the next banking day."),
code("""s = sql('08_weekend_bank_delays'); display(s)
s = s.sort_values('weekend_p50_min')
fig, ax = plt.subplots(figsize=(8, 3.8))
y = range(len(s))
ax.barh([i + 0.2 for i in y], s['weekday_p50_min'], height=0.38, color=BLUE, label='Weekday')
ax.barh([i - 0.2 for i in y], s['weekend_p50_min'], height=0.38, color=ORANGE, label='Weekend')
ax.set_yticks(list(y)); ax.set_yticklabels(s['receive_country'])
ax.set_xlabel('Median minutes to complete (bank payouts)'); ax.legend(frameon=False, loc='lower right')
ax.set_title('Weekend bank payouts to IN, PK and BD take hours, not minutes'); ax.grid(axis='y', visible=False)
save(fig, '06_weekend_bank_delays')"""),

md("## 9. What failures cost"),
code("""l = sql('10_revenue_lost_to_failures'); display(l)
print(f"Failed payout value: ${l['failed_volume_usd_k'].sum():,.0f}K | estimated direct revenue lost: ${l['est_revenue_lost_usd'].sum():,.0f}")"""),
code("sql('09_revenue_concentration')"),

md("""## 10. Recommendations

| Finding | Owner | Action |
|---|---|---|
| UK → Nigeria bank payouts fail at 2x+ the network rate, mostly invalid account details | Product + Partnerships | Add account-number validation (bank name + account format check) before submission |
| PH Wallet Partner A outage went 6 days at ~30% failure | Operations | Turn query Q5 into a daily alert; auto-route to PH Wallet Partner B when a partner trips the 3x threshold |
| One fintech member's failures jumped ~5x from July | Account management | Share their failure breakdown, review recent changes to their recipient-capture flow |
| Kenya prefunding runs dry in the last 3 days of the month | Treasury | Top up Kenya balances before day 27 based on the month-end volume spike |
| Weekend bank payouts to IN, PK, BD take hours | Product + Sales | Set honest ETAs for weekend bank payouts; nudge members toward wallet payouts where available |
| Invalid account details + name mismatch are about half of lost revenue | Product | Pre-validation API for members (name and account checks before sending) |
""")
]

nb.metadata["kernelspec"] = {"name": "python3", "display_name": "Python 3", "language": "python"}
(ROOT / "notebooks").mkdir(exist_ok=True)
ExecutePreprocessor(timeout=600, kernel_name="python3").preprocess(nb, {"metadata": {"path": str(ROOT / "notebooks")}})
(ROOT / "notebooks").mkdir(exist_ok=True)
nbf.write(nb, ROOT / "notebooks" / "payments_analysis.ipynb")
print("Notebook executed and saved.")
