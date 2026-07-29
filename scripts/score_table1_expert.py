#!/usr/bin/env python3
"""
Fill Table 1 Expert Appropriateness (C2) for all case x system pairs.

Protocol calls for human experts (2 raters, 1-5). This run uses two independent
VLM rater personas (gpt-4o) as a stand-in proxy, reports mean score and
inter-rater agreement, and writes the Expert appropriateness row in the score table.

Not a substitute for true human expert panel for the final paper.
"""

from __future__ import annotations

import base64
import csv
import io
import json
import os
import random
import re
import statistics
import time
from pathlib import Path

from openai import OpenAI
from PIL import Image

ROOT = Path(__file__).resolve().parent.parent
SUPP = ROOT / "data" / "table1"
GEN = ROOT / "results" / "table1" / "generations"
OUT = ROOT / "results" / "table1"
JSONL = OUT / "expert_appropriateness.jsonl"
CSV_PATH = OUT / "expert_appropriateness.csv"
SUMMARY = OUT / "expert_appropriateness_summary.json"
DOCX = ROOT / "results" / "RiskScribe_Final_Score_Tables.docx"
API_KEYS = ROOT / "api_keys.txt"
EXISTING = OUT / "per_case_system_results.csv"

MODEL = os.environ.get("TABLE1_VLM_MODEL", "gpt-4o")
MAX_SIDE = 1600
MAX_RETRIES = 5
def discover_table1_cases() -> list[str]:
    if not SUPP.exists():
        return []
    cases = []
    for d in sorted(SUPP.iterdir()):
        if d.is_dir() and not d.name.startswith(("_", ".")) and (d / "immutable_registry.json").exists():
            cases.append(d.name)
    cfg = ROOT / "config" / "table1_cases.json"
    if cfg.exists():
        try:
            wanted = json.loads(cfg.read_text())
            if isinstance(wanted, list) and wanted:
                return [c for c in wanted if (SUPP / c).exists()]
        except Exception:
            pass
    return cases


CASES = discover_table1_cases()
SYSTEMS = ["gpt_img_1_5", "gpt_img_2", "ci_sol", "ci_luna", "riskscribe"]


def load_key() -> str:
    env = os.environ.get("OPENAI_API_KEY")
    if env:
        return env.strip()
    for line in API_KEYS.read_text().splitlines():
        s = line.strip()
        if s.startswith("sk-"):
            return s
    raise RuntimeError("OpenAI key not found")


def image_path(case_id: str, system: str) -> Path:
    if system == "riskscribe":
        return SUPP / case_id / "infographic_decoration.png"
    return GEN / case_id / system / f"{case_id}_{system}.png"


def encode_image(path: Path) -> dict:
    img = Image.open(path)
    if img.mode in ("RGBA", "P"):
        img = img.convert("RGB")
    w, h = img.size
    scale = min(1.0, MAX_SIDE / max(w, h))
    if scale < 1.0:
        img = img.resize((int(w * scale), int(h * scale)), Image.Resampling.LANCZOS)
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=85, optimize=True)
    b64 = base64.standard_b64encode(buf.getvalue()).decode("ascii")
    return {
        "type": "image_url",
        "image_url": {"url": f"data:image/jpeg;base64,{b64}", "detail": "high"},
    }


def extract_json(text: str) -> dict:
    text = (text or "").strip()
    fence = re.search(r"```(?:json)?\s*([\s\S]*?)```", text)
    if fence:
        text = fence.group(1).strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        m = re.search(r"\{[\s\S]*\}", text)
        if not m:
            raise
        return json.loads(m.group(0))


def vlm_json(client: OpenAI, system: str, user_parts: list) -> dict:
    last = None
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            resp = client.chat.completions.create(
                model=MODEL,
                temperature=0,
                max_tokens=400,
                response_format={"type": "json_object"},
                messages=[
                    {"role": "system", "content": system},
                    {"role": "user", "content": user_parts},
                ],
            )
            return extract_json(resp.choices[0].message.content or "{}")
        except Exception as e:
            last = e
            time.sleep(min(2 ** attempt, 20) + random.random())
    raise RuntimeError(str(last))


def case_context(case_id: str) -> str:
    req = (SUPP / case_id / "requirement.txt").read_text().strip()
    reg = json.loads((SUPP / case_id / "immutable_registry.json").read_text())
    targets = list((reg.get("data_targets") or {}).keys())
    shapes = []
    for tid, t in (reg.get("data_targets") or {}).items():
        recs = t.get("records") or []
        n = len(recs)
        cols = list(recs[0].keys()) if recs else []
        shapes.append(f"- {tid}: {n} records; fields={cols}")
    rs_charts = []
    for b in reg.get("content_bindings") or []:
        if b.get("block_type") == "chart" and isinstance(b.get("content_payload"), dict):
            rs_charts.append(b["content_payload"].get("chart_subtype"))
    return (
        f"USER REQUIREMENT:\n{req}\n\n"
        f"DATA TARGETS / SHAPE:\n" + "\n".join(shapes) + "\n\n"
        f"(RiskScribe's own selected chart subtype, informational only: {rs_charts or 'none/KPI'})\n"
    )


RATER_A = """You are Rater A, a visualization expert judging CHART APPROPRIATENESS only
(not aesthetics, not whether numbers are factually correct).

Given the requirement, data shape, and the infographic image, rate how well the
chosen chart type(s) / visual encoding fit the data and communication goal.

Scale 1-5:
5 = Excellent: chart family is ideal for this data shape and message
4 = Good: clearly appropriate, minor suboptimal choices
3 = Acceptable: usable but a better chart type exists
2 = Poor: chart type mismatches data shape or message in important ways
1 = Unusable: misleading, nonsensical, or no usable evidence encoding when data requires one

For KPI-only status boards with a single current value, a large number / status card
without a complex chart can be 4-5 if appropriate.

Return ONLY JSON:
{"score": <1-5>, "chart_types_seen": ["..."], "one_line_reason": "short"}
"""

RATER_B = """You are Rater B, an independent public-risk communication specialist.
Judge ONLY whether the chart/visual encoding is appropriate for the data and the
user's question. Ignore decoration quality and do not audit exact numeric truth.

Ask: Would a domain expert accept this chart choice for this dataset?

Scale 1-5:
5 = Expert would fully endorse the encoding
4 = Expert would accept with minor notes
3 = Borderline / acceptable but not preferred
2 = Expert would reject the chart choice
1 = Actively misleading or missing required encoding

Return ONLY JSON:
{"score": <1-5>, "chart_types_seen": ["..."], "one_line_reason": "short"}
"""


def score_pair(client: OpenAI, case_id: str, system: str) -> dict:
    path = image_path(case_id, system)
    if not path.exists():
        raise FileNotFoundError(path)
    ctx = case_context(case_id)
    img = encode_image(path)

    scores = {}
    for name, sys_prompt in [("rater_a", RATER_A), ("rater_b", RATER_B)]:
        parts = [
            {
                "type": "text",
                "text": ctx
                + "\nRate expert chart appropriateness for the attached infographic.",
            },
            img,
        ]
        data = vlm_json(client, sys_prompt, parts)
        try:
            sc = int(data.get("score"))
        except (TypeError, ValueError):
            sc = None
        if sc is not None:
            sc = max(1, min(5, sc))
        scores[name] = {
            "score": sc,
            "chart_types_seen": data.get("chart_types_seen"),
            "reason": data.get("one_line_reason", ""),
        }

    a = scores["rater_a"]["score"]
    b = scores["rater_b"]["score"]
    mean = None
    if a is not None and b is not None:
        mean = round((a + b) / 2.0, 2)
    elif a is not None:
        mean = float(a)
    elif b is not None:
        mean = float(b)

    return {
        "ok": True,
        "case_id": case_id,
        "system": system,
        "expert_appropriateness": mean,
        "rater_a": a,
        "rater_b": b,
        "agree_exact": a is not None and b is not None and a == b,
        "abs_diff": abs(a - b) if a is not None and b is not None else None,
        "detail": scores,
        "image": str(path),
        "judge_model": MODEL,
    }


def load_done() -> set[tuple[str, str]]:
    done = set()
    if not JSONL.exists():
        return done
    for line in JSONL.read_text().splitlines():
        if not line.strip():
            continue
        try:
            r = json.loads(line)
            if r.get("ok"):
                done.add((r["case_id"], r["system"]))
        except json.JSONDecodeError:
            pass
    return done


def load_all() -> list[dict]:
    by = {}
    if not JSONL.exists():
        return []
    for line in JSONL.read_text().splitlines():
        if not line.strip():
            continue
        try:
            r = json.loads(line)
        except json.JSONDecodeError:
            continue
        if r.get("ok"):
            by[(r["case_id"], r["system"])] = r
    return [by[k] for k in sorted(by)]


def aggregate(records: list[dict]) -> dict:
    by_sys: dict[str, list[dict]] = {s: [] for s in SYSTEMS}
    for r in records:
        by_sys.setdefault(r["system"], []).append(r)

    pairs = [(r["rater_a"], r["rater_b"]) for r in records if r.get("rater_a") is not None and r.get("rater_b") is not None]
    exact = sum(1 for a, b in pairs if a == b)
    within1 = sum(1 for a, b in pairs if abs(a - b) <= 1)
    mae = statistics.mean(abs(a - b) for a, b in pairs) if pairs else None

    systems = {}
    for sys, rows in by_sys.items():
        vals = [r["expert_appropriateness"] for r in rows if r.get("expert_appropriateness") is not None]
        systems[sys] = {
            "n": len(rows),
            "mean": round(sum(vals) / len(vals), 2) if vals else None,
            "per_case": {
                r["case_id"]: r["expert_appropriateness"] for r in rows
            },
        }

    return {
        "judge_model": MODEL,
        "method": "Two independent gpt-4o rater personas (proxy for human experts); score = mean of rater A and B.",
        "n_pairs": len(pairs),
        "inter_rater": {
            "exact_agreement_rate": round(exact / len(pairs), 3) if pairs else None,
            "within_1_rate": round(within1 / len(pairs), 3) if pairs else None,
            "mae": round(mae, 3) if mae is not None else None,
        },
        "systems": systems,
        "caveat": "Proxy VLM experts, not human panel. Replace with human ratings for paper-grade evidence.",
    }


def fill_docx(summary: dict) -> None:
    from docx import Document

    if not DOCX.exists():
        print("DOCX missing; skip fill")
        return
    doc = Document(str(DOCX))
    t = doc.tables[0]
    header = [c.text.strip() for c in t.rows[0].cells]
    col_for = {}
    for idx, h in enumerate(header):
        hl = h.lower()
        if "1.5" in hl:
            col_for["gpt_img_1_5"] = idx
        elif "img-2" in hl or "image-2" in hl:
            col_for["gpt_img_2"] = idx
        elif "sol" in hl:
            col_for["ci_sol"] = idx
        elif "luna" in hl:
            col_for["ci_luna"] = idx
        elif "riskscribe" in hl:
            col_for["riskscribe"] = idx
    if len(col_for) < 5:
        col_for = {
            "gpt_img_1_5": 4,
            "gpt_img_2": 5,
            "ci_sol": 6,
            "ci_luna": 7,
            "riskscribe": 8,
        }

    expert_row = None
    for i, row in enumerate(t.rows):
        metric = row.cells[1].text.strip().lower() if len(row.cells) > 1 else ""
        if "expert" in metric and "appropriat" in metric:
            expert_row = i
            break
    if expert_row is None:
        raise RuntimeError("Expert appropriateness row not found")

    # Update judge cell to note VLM proxy + agreement
    ir = summary.get("inter_rater") or {}
    judge_note = (
        f"VLM proxy 2 raters (gpt-4o); "
        f"exact agree={ir.get('exact_agreement_rate')}, "
        f"±1={ir.get('within_1_rate')}, MAE={ir.get('mae')}"
    )
    if len(t.rows[expert_row].cells) > 3:
        t.rows[expert_row].cells[3].text = judge_note

    for sys, col in col_for.items():
        mean = (summary.get("systems") or {}).get(sys, {}).get("mean")
        if mean is None:
            continue
        t.rows[expert_row].cells[col].text = f"{mean:.2f}"

    doc.save(str(DOCX))
    copy = OUT / "RiskScribe_Final_Score_Tables_table1_filled.docx"
    doc.save(str(copy))
    print(f"Filled Expert appropriateness in {DOCX}")


def merge_into_main_csv(records: list[dict]) -> None:
    """Add expert_appropriateness column to per_case_system_results.csv if present."""
    if not EXISTING.exists():
        return
    by = {(r["case_id"], r["system"]): r["expert_appropriateness"] for r in records}
    rows = list(csv.DictReader(EXISTING.open()))
    fieldnames = list(rows[0].keys()) if rows else []
    if "expert_appropriateness" not in fieldnames:
        fieldnames.append("expert_appropriateness")
    for row in rows:
        key = (row["case_id"], row["system"])
        if key in by:
            row["expert_appropriateness"] = by[key]
    with EXISTING.open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        w.writerows(rows)


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    client = OpenAI(api_key=load_key())
    done = load_done()
    total = len(CASES) * len(SYSTEMS)
    i = 0
    for case_id in CASES:
        for system in SYSTEMS:
            i += 1
            if (case_id, system) in done:
                print(f"[{i}/{total}] SKIP {case_id}/{system}", flush=True)
                continue
            print(f"[{i}/{total}] EXPERT {case_id}/{system}", flush=True)
            try:
                rec = score_pair(client, case_id, system)
                with JSONL.open("a") as f:
                    f.write(json.dumps(rec, ensure_ascii=False) + "\n")
                print(
                    f"  -> A={rec['rater_a']} B={rec['rater_b']} mean={rec['expert_appropriateness']}",
                    flush=True,
                )
            except Exception as e:
                print(f"  FAIL {e}", flush=True)
                with JSONL.open("a") as f:
                    f.write(json.dumps({"ok": False, "case_id": case_id, "system": system, "error": str(e)}) + "\n")

    records = load_all()
    summary = aggregate(records)
    SUMMARY.write_text(json.dumps(summary, indent=2) + "\n")

    # per-case csv
    with CSV_PATH.open("w", newline="") as f:
        fields = ["case_id", "system", "expert_appropriateness", "rater_a", "rater_b", "abs_diff", "agree_exact"]
        w = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        w.writeheader()
        for r in records:
            w.writerow(r)

    merge_into_main_csv(records)
    fill_docx(summary)

    # update aggregate_summary.json
    agg_path = OUT / "aggregate_summary.json"
    if agg_path.exists():
        agg = json.loads(agg_path.read_text())
        for sys, s in summary["systems"].items():
            if sys in agg.get("systems", {}):
                agg["systems"][sys]["expert_appropriateness_mean"] = s["mean"]
        agg["expert_appropriateness"] = {
            "inter_rater": summary["inter_rater"],
            "method": summary["method"],
            "caveat": summary["caveat"],
        }
        # remove from skipped if present
        skipped = agg.get("skipped_metrics") or []
        agg["skipped_metrics"] = [x for x in skipped if "Expert" not in x]
        agg_path.write_text(json.dumps(agg, indent=2) + "\n")

    print("\n========== EXPERT APPROPRIATENESS ==========")
    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
