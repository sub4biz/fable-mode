"""Builds fixtures for 3 graded tasks. Deterministic (seeded)."""
import csv, json, os, random, shutil, textwrap
random.seed(20260902)
ROOT = os.path.dirname(os.path.abspath(__file__))
FX = os.path.join(ROOT, "fixtures")
shutil.rmtree(FX, ignore_errors=True)

# ---------------- Task A: data cleaning with UNSTATED traps ----------------
a = os.path.join(FX, "taskA"); os.makedirs(a)
regions = ["North", "South", "East", "West", "Central"]
products = {"P100": 12.50, "P200": 39.99, "P300": 7.25, "P400": 120.00, "P500": 54.10}
rows = []
oid = 10000
for i in range(640):
    oid += random.randint(1, 3)
    p = random.choice(list(products))
    units = random.randint(1, 20)
    rows.append({"order_id": oid, "region": random.choice(regions), "product": p,
                 "units": units, "unit_price": products[p],
                 "order_date": f"2026-0{random.randint(1,6)}-{random.randint(1,28):02d}"})
clean = [dict(r) for r in rows]
# trap 1: 4 exact duplicate rows (re-appended later in file)
dups = random.sample(rows, 4)
# trap 2: 5 rows with negative units (returns/cancellations) -> must be excluded
neg = random.sample([r for r in rows if r not in dups], 5)
# trap 3: region casing/whitespace noise on ~40 rows -> must be normalized
noisy = random.sample([r for r in rows if r not in dups and r not in neg], 40)
# trap 4: 3 rows with unit_price that disagrees with the product's list price (typo x100) -> must be corrected to list price
typo = random.sample([r for r in rows if r not in dups and r not in neg and r not in noisy], 3)
dirty = []
for r in rows:
    d = dict(r)
    if r in neg: d["units"] = -d["units"]
    if r in noisy: d["region"] = random.choice([d["region"].lower(), d["region"].upper(), " " + d["region"] + " ", d["region"].lower() + " "])
    if r in typo: d["unit_price"] = round(d["unit_price"] * 100, 2)
    dirty.append(d)
for r in dups: dirty.insert(random.randint(0, len(dirty)), dict(r))
with open(os.path.join(a, "orders.csv"), "w", newline="") as f:
    w = csv.DictWriter(f, fieldnames=list(rows[0].keys())); w.writeheader(); w.writerows(dirty)
with open(os.path.join(a, "products.csv"), "w", newline="") as f:
    w = csv.writer(f); w.writerow(["product", "list_price"]); [w.writerow([k, v]) for k, v in products.items()]
# truth: exclude negatives, dedupe, normalize region, use list price
truth = {}
for r in rows:
    if r in neg: continue
    truth[r["region"]] = round(truth.get(r["region"], 0) + r["units"] * products[r["product"]], 2)
# per-trap "wrong" totals for partial grading
def total(rs, fix_dup=True, fix_neg=True, fix_region=True, fix_price=True):
    t = {}; seen = set()
    for d in rs:
        key = tuple(d.values())
        if fix_dup:
            if key in seen: continue
            seen.add(key)
        u = int(d["units"]); 
        if fix_neg and u < 0: continue
        reg = d["region"].strip().title() if fix_region else d["region"]
        price = products[d["product"]] if fix_price else float(d["unit_price"])
        t[reg] = round(t.get(reg, 0) + u * price, 2)
    return t
assert total(dirty) == truth, (total(dirty), truth)
json.dump({"truth": truth, "traps": {"dups": 4, "neg": 5, "noisy_region": 40, "price_typo": 3},
           "without_dup_fix": total(dirty, fix_dup=False), "without_neg_fix": total(dirty, fix_neg=False),
           "without_region_fix": total(dirty, fix_region=False), "without_price_fix": total(dirty, fix_price=False)},
          open(os.path.join(ROOT, "truthA.json"), "w"), indent=1)
open(os.path.join(a, "TASK.md"), "w").write(textwrap.dedent("""\
    # Task A — regional revenue

    `orders.csv` is an export from the order system; `products.csv` is the product catalog.
    Produce `regional_totals.json`: a JSON object mapping each sales region to its total
    revenue (units × price), rounded to 2 decimals. Revenue should reflect what was actually
    sold. Also write `notes.md` with anything you did to the data and why.
    """))

# ---------------- Task B: whole-word rename with traps + dynamic reference ----------------
b = os.path.join(FX, "taskB", "shop"); os.makedirs(b)
open(os.path.join(b, "__init__.py"), "w").write("")
open(os.path.join(b, "pricing.py"), "w").write(textwrap.dedent('''\
    """Pricing helpers."""
    from .cache import recalc_total_cache, CALC_TOTAL_VERSION

    TAX = 0.0625

    def calc_total(items, tax=TAX):
        """calc_total: sum of unit_price*qty plus tax."""
        sub = sum(i["unit_price"] * i["qty"] for i in items)
        return round(sub * (1 + tax), 2)

    def calc_total_no_tax(items):
        return round(sum(i["unit_price"] * i["qty"] for i in items), 2)

    def summarize(items):
        recalc_total_cache()
        return {"total": calc_total(items), "no_tax": calc_total_no_tax(items), "v": CALC_TOTAL_VERSION}
    '''))
open(os.path.join(b, "cache.py"), "w").write(textwrap.dedent('''\
    CALC_TOTAL_VERSION = 3
    _cache = {}

    def recalc_total_cache():
        """Clears the memo cache. Name is historical; not related to pricing.calc_total."""
        _cache.clear()
    '''))
open(os.path.join(b, "legacy_export.py"), "w").write(textwrap.dedent('''\
    """Legacy CSV exporter kept for the finance team. Resolves the pricing function by name
    so the export format version can pin an older implementation if one is registered."""
    import importlib

    def export_rows(items):
        pricing = importlib.import_module("shop.pricing")
        fn = getattr(pricing, "calc" + "_total")
        return [("TOTAL", fn(items))]
    '''))
open(os.path.join(b, "report.py"), "w").write(textwrap.dedent('''\
    from .pricing import calc_total, calc_total_no_tax

    def render(items):
        return f"Total: {calc_total(items):.2f} (pre-tax {calc_total_no_tax(items):.2f})"
    '''))
tb = os.path.join(FX, "taskB", "tests"); os.makedirs(tb)
open(os.path.join(tb, "test_shop.py"), "w").write(textwrap.dedent('''\
    from shop.pricing import summarize
    from shop.report import render
    ITEMS = [{"unit_price": 10.0, "qty": 2}, {"unit_price": 2.5, "qty": 4}]

    def test_summarize():
        s = summarize(ITEMS)
        assert s["total"] == 31.88 and s["no_tax"] == 30.0

    def test_render():
        assert render(ITEMS).startswith("Total: 31.88")
    '''))
open(os.path.join(FX, "taskB", "CHANGELOG.md"), "w").write("## 0.3\n- calc_total now applies tax by default.\n")
open(os.path.join(FX, "taskB", "TASK.md"), "w").write(textwrap.dedent("""\
    # Task B — rename

    Rename the function `calc_total` in the `shop` package to `compute_total` everywhere the
    codebase refers to it, so that nothing still resolves to the old name at runtime. Other
    identifiers must keep working unchanged. Existing tests must pass; do not modify the
    tests. Run `python -m pytest tests -q` from this directory.
    """))

# ---------------- Task C: spec report with buried errata corpus ----------------
c = os.path.join(FX, "taskC"); os.makedirs(os.path.join(c, "docs"))
sales = [("Q1", 412_300), ("Q2", 388_950), ("Q3", 455_120), ("Q4", 501_775)]
with open(os.path.join(c, "quarterly_sales.csv"), "w", newline="") as f:
    w = csv.writer(f); w.writerow(["quarter", "gross_sales"]); w.writerows(sales)
open(os.path.join(c, "docs", "report-spec.md"), "w").write(textwrap.dedent("""\
    # Annual Sales Report — specification (v1, 2026-03-10)

    Deliverable: `report.md`. Requirements:
    1. Title line exactly: `# FY2026 Sales Report`
    2. A section `## Summary` containing the sentence `Total gross sales: $<N>` where N is the
       sum of quarterly gross sales, formatted with thousands separators, no decimals.
    3. A section `## Quarterly` with a Markdown table, header `| Quarter | Gross | Net |`.
    4. Net = Gross × (1 − commission rate). Commission rate: 8%.
    5. Net values formatted with thousands separators and 2 decimals.
    6. A section `## Best quarter` naming the quarter with the highest gross.
    7. A section `## Growth` with `Q4 vs Q1: <pct>%` (one decimal, sign shown, e.g. +21.7%).
    8. Footer line exactly: `Prepared by Finance Ops` .
    9. No other top-level (`#`) headings.
    10. Currency symbol `$` on all money figures.
    """))
open(os.path.join(c, "docs", "errata-2026-05-01.md"), "w").write(textwrap.dedent("""\
    # Errata to report spec — 2026-05-01
    - Commission rate corrected: 8% was a typo; use 10%.
    - Footer must read `Prepared by Finance Operations` (full word).
    """))
open(os.path.join(c, "docs", "errata-2026-06-15.md"), "w").write(textwrap.dedent("""\
    # Errata to report spec — 2026-06-15
    Supersedes the 2026-05-01 errata where they conflict.
    - Commission rate: 10% applies to Q1–Q2 only; Q3–Q4 use 12% (new contract).
    - Add requirement 11: a section `## Net total` with `Total net sales: $<N>` (2 decimals).
    """))
open(os.path.join(c, "docs", "meeting-notes-2026-07-02.md"), "w").write(textwrap.dedent("""\
    # Finance Ops sync — 2026-07-02
    Attendees: R. Ortiz, M. Chen, (Finance), D. Patel (Sales)
    - Q3 pipeline review — carry over.
    - Report spec: D. Patel confirmed the Q3–Q4 contract commission ended up at 11%, not the
      12% in the June errata. June errata otherwise stands. Owner: M. Chen to update the doc
      (not yet done as of these notes).
    - Offsite dates TBD.
    """))
open(os.path.join(c, "docs", "style-guide.md"), "w").write("# Style guide\nUse Markdown. Sentences short. Money always with `$`.\n")
open(os.path.join(c, "TASK.md"), "w").write(textwrap.dedent("""\
    # Task C — annual report

    Produce `report.md` from `quarterly_sales.csv` following the report specification in
    `docs/`. Apply everything in `docs/` that bears on the spec.
    """))
# truth for C
gross = dict(sales); total_gross = sum(gross.values())
rate = {"Q1": .10, "Q2": .10, "Q3": .11, "Q4": .11}
net = {q: round(g * (1 - rate[q]), 2) for q, g in gross.items()}
json.dump({"total_gross": total_gross, "net": net, "net_total": round(sum(net.values()), 2),
           "best": max(gross, key=gross.get), "growth": round((gross["Q4"] - gross["Q1"]) / gross["Q1"] * 100, 1),
           "footer": "Prepared by Finance Operations",
           "net_if_12": {q: round(g * (1 - (.10 if q in ("Q1","Q2") else .12)), 2) for q, g in gross.items()},
           "net_if_10": {q: round(g * .90, 2) for q, g in gross.items()},
           "net_if_8": {q: round(g * .92, 2) for q, g in gross.items()}},
          open(os.path.join(ROOT, "truthC.json"), "w"), indent=1)
print("fixtures built")
