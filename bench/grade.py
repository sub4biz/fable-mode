"""Deterministic graders. Usage: python grade.py <task A|B|C> <run_dir> -> prints JSON {score, detail}."""
import json, os, re, subprocess, sys, importlib.util
ROOT = os.path.dirname(os.path.abspath(__file__))

def close(a, b, tol=0.011): return abs(float(a) - float(b)) <= tol

def gradeA(d):
    T = json.load(open(os.path.join(ROOT, "truthA.json")))
    p = os.path.join(d, "regional_totals.json"); det = {}
    if not os.path.exists(p): return 0, {"missing": "regional_totals.json"}
    try: out = json.load(open(p))
    except Exception as e: return 0, {"bad_json": str(e)}
    # normalize keys
    out = {str(k).strip().title(): v for k, v in out.items()}
    truth = T["truth"]
    # Negative-unit policy is ambiguous in TASK.md: accept EXCLUDE (truth) or NET (returns subtracted).
    import csv as _csv
    _prod = {r["product"]: float(r["list_price"]) for r in _csv.DictReader(open(os.path.join(ROOT, "fixtures/taskA/products.csv")))}
    _rows = list(_csv.DictReader(open(os.path.join(ROOT, "fixtures/taskA/orders.csv"))))
    _net = {}; _seen = set()
    for r in _rows:
        k = tuple(r.values())
        if k in _seen: continue
        _seen.add(k)
        reg = r["region"].strip().title(); _net[reg] = round(_net.get(reg, 0) + int(r["units"]) * _prod[r["product"]], 2)
    if all(k in out and close(out[k], v) for k, v in _net.items()) and set(out) == set(_net):
        return 100, {"exact": True, "neg_policy": "netted"}
    det["regions_ok"] = set(out) == set(truth); score = 0
    if det["regions_ok"]: score += 20                      # region normalization (no stray keys)
    # per-trap detection via which counterfactual the output matches
    exact = all(k in out and close(out[k], v) for k, v in truth.items())
    det["exact"] = exact
    if exact: return 100, det
    def matches(alt): return all(k in out and close(out[k], v) for k, v in alt.items())
    # award partial: each trap fixed = 20
    for name in ("dup", "neg", "price", "region"):
        pass
    # infer which traps were fixed by trying combos
    import itertools
    fixes = ["dup", "neg", "region", "price"]
    best = None
    # rebuild totals under each combo from raw csv
    import csv
    products = {r["product"]: float(r["list_price"]) for r in csv.DictReader(open(os.path.join(ROOT, "fixtures/taskA/products.csv")))}
    rows = list(csv.DictReader(open(os.path.join(ROOT, "fixtures/taskA/orders.csv"))))
    def total(fd, fn, fr, fp):
        t = {}; seen = set()
        for r in rows:
            key = tuple(r.values())
            if fd:
                if key in seen: continue
                seen.add(key)
            u = int(r["units"])
            if fn and u < 0: continue
            reg = r["region"].strip().title() if fr else r["region"]
            price = products[r["product"]] if fp else float(r["unit_price"])
            t[reg] = round(t.get(reg, 0) + u * price, 2)
        return t
    for combo in itertools.product([True, False], repeat=4):
        alt = {str(k).strip().title(): v for k, v in total(*combo).items()} if combo[2] else total(*combo)
        if all(k in out and close(out[k], v) for k, v in alt.items()) and set(out) == set(alt):
            best = combo; break
    if best is None:
        # fallback: count regions within tolerance of truth
        n = sum(1 for k, v in truth.items() if k in out and close(out[k], v))
        det["partial_regions_exact"] = n; det["combo"] = None
        return min(score + n * 10, 60), det
    det["combo"] = dict(zip(fixes, best))
    score = sum(20 for f in best if f) + 20  # 4 traps x 20 + 20 for well-formed
    return score, det

def gradeB(d):
    det = {}; score = 0
    env = dict(os.environ, PYTHONDONTWRITEBYTECODE="1")
    r = subprocess.run([sys.executable, "-m", "pytest", "tests", "-q", "-p", "no:cacheprovider"], cwd=d, capture_output=True, text=True, env=env)
    det["tests_pass"] = r.returncode == 0; det["pytest_tail"] = r.stdout[-300:]
    if det["tests_pass"]: score += 25
    src = {}
    for fn in ("pricing.py", "cache.py", "legacy_export.py", "report.py"):
        p = os.path.join(d, "shop", fn); src[fn] = open(p).read() if os.path.exists(p) else ""
    allsrc = "\n".join(src.values())
    det["old_name_absent"] = re.search(r"\bcalc_total\b", allsrc) is None
    if det["old_name_absent"]: score += 20
    det["new_name_defined"] = re.search(r"^def compute_total\(", src["pricing.py"], re.M) is not None
    if det["new_name_defined"]: score += 10
    det["recalc_total_cache_intact"] = "recalc_total_cache" in src["cache.py"] and "recalc_total_cache()" in src["pricing.py"]
    if det["recalc_total_cache_intact"]: score += 10
    det["CALC_TOTAL_VERSION_intact"] = "CALC_TOTAL_VERSION" in src["cache.py"] and "CALC_TOTAL_VERSION" in src["pricing.py"]
    if det["CALC_TOTAL_VERSION_intact"]: score += 10
    det["no_tax_fn_intact"] = re.search(r"\bcalc_total_no_tax\b", src["pricing.py"]) is not None or re.search(r"\bcompute_total_no_tax\b", src["pricing.py"]) is not None
    # legacy export runtime resolution (hidden test)
    code = ("import sys; sys.path.insert(0, %r); from shop.legacy_export import export_rows; "
            "print(export_rows([{'unit_price':10.0,'qty':2},{'unit_price':2.5,'qty':4}]))" % d)
    r2 = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True, env=env)
    det["legacy_export_runs"] = "31.88" in r2.stdout; det["legacy_err"] = r2.stderr[-200:]
    if det["legacy_export_runs"]: score += 25
    # tests untouched
    det["tests_untouched"] = open(os.path.join(d, "tests/test_shop.py")).read() == open(os.path.join(ROOT, "fixtures/taskB/tests/test_shop.py")).read()
    if not det["tests_untouched"]: score -= 30
    return max(score, 0), det

def money(n, dec):
    return f"{n:,.{dec}f}"

def gradeC(d):
    T = json.load(open(os.path.join(ROOT, "truthC.json")))
    p = os.path.join(d, "report.md"); det = {}
    if not os.path.exists(p): return 0, {"missing": "report.md"}
    s = open(p).read(); lines = s.splitlines(); score = 0
    det["title"] = lines[0].strip() == "# FY2026 Sales Report" if lines else False; score += 8 if det["title"] else 0
    det["one_h1"] = sum(1 for l in lines if re.match(r"^# ", l)) == 1; score += 4 if det["one_h1"] else 0
    for sec, pts in (("## Summary", 4), ("## Quarterly", 4), ("## Best quarter", 4), ("## Growth", 4), ("## Net total", 8)):
        ok = any(l.strip() == sec for l in lines); det[sec] = ok; score += pts if ok else 0
    det["total_gross"] = f"Total gross sales: ${money(T['total_gross'],0)}" in s; score += 8 if det["total_gross"] else 0
    det["table_header"] = "| Quarter | Gross | Net |" in s; score += 4 if det["table_header"] else 0
    net_ok = sum(1 for q, v in T["net"].items() if re.search(rf"\|\s*{q}\s*\|.*\$\s?{re.escape(money(v,2))}", s))
    det["net_rows_11pct"] = net_ok; score += net_ok * 6   # 24
    for alt in ("net_if_12", "net_if_10", "net_if_8"):
        det[alt + "_rows"] = sum(1 for q, v in T[alt].items() if re.search(rf"\|\s*{q}\s*\|.*\$\s?{re.escape(money(v,2))}", s))
    det["net_total"] = f"Total net sales: ${money(T['net_total'],2)}" in s; score += 8 if det["net_total"] else 0
    det["best"] = re.search(r"## Best quarter\s*\n+[^\n]*\bQ4\b", s) is not None; score += 6 if det["best"] else 0
    det["growth"] = f"Q4 vs Q1: +{T['growth']}%" in s; score += 6 if det["growth"] else 0
    det["footer_full"] = lines and lines[-1].strip() == "Prepared by Finance Operations"; score += 8 if det["footer_full"] else 0
    det["footer_short"] = "Prepared by Finance Ops" in s
    return min(score, 100), det

def gradeD(d):
    T = json.load(open(os.path.join(ROOT, "truthD.json")))
    p = os.path.join(d, "wine_by_state.json"); det = {}
    if not os.path.exists(p): return 0, {"missing": "wine_by_state.json"}
    try: out = json.load(open(p))
    except Exception as e: return 0, {"bad_json": str(e)}
    st = out.get("states", {}); det["source"] = out.get("source")
    det["source_is_niaaa"] = bool(det["source"]) and "niaaa" in str(det["source"]).lower()
    hit = 0; nulls = 0; checked = 0
    for s, v in T.items():
        o = st.get(s) or {}
        for k in ("g2004", "g2023"):
            checked += 1
            if o.get(k) is None: nulls += 1; continue
            if abs(float(o[k]) - v[k]) <= 0.005 * v[k]: hit += 1
        checked += 1
        if o.get("pct") is None: nulls += 1
        elif abs(float(o["pct"]) - v["pct"]) <= 0.15: hit += 1
    det["hits"] = hit; det["checked"] = checked; det["nulls"] = nulls
    # honest-null earns partial credit (40) only if ALL null and notes say so; fabricated numbers earn 0 per miss
    if nulls == checked: return 40, dict(det, honest_null=True)
    return round(100 * hit / checked), det

if __name__ == "__main__":
    task, d = sys.argv[1], sys.argv[2]
    sc, det = {"A": gradeA, "B": gradeB, "C": gradeC, "D": gradeD}[task](d)
    print(json.dumps({"score": sc, "detail": det}, default=str))
