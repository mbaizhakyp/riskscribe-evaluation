#!/usr/bin/env python3
"""
Extract fair-comparison generation inputs for Table 1 baselines.

For each data/table1/req_* case, builds:
  - requirement   (from requirement.txt)
  - data_block    (authoritative tables from immutable_registry data_targets)
  - knowledge_block (contextual text ONLY from registry facts/bindings/plan)

No LLM. No invented facts. Reformat only.

Writes:
  - results/table1/inputs/cases.json
  - results/table1/inputs/<case_id>/{requirement,data_block,knowledge_block}.txt
  - results/table1/inputs/<case_id>/meta.json
"""

from __future__ import annotations

import csv
import io
import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
SUPPLEMENTAL = ROOT / "data" / "table1"
OUT_DIR = ROOT / "results" / "table1" / "inputs"


def _fmt_value(v: Any) -> str:
    if v is None:
        return ""
    if isinstance(v, float):
        # keep reasonable precision; avoid long binary floats in tables
        if abs(v - round(v)) < 1e-9:
            return str(int(round(v)))
        return f"{v:.6g}"
    if isinstance(v, (dict, list)):
        return json.dumps(v, ensure_ascii=False, sort_keys=True)
    return str(v)


def records_to_markdown_table(records: list[dict]) -> str:
    if not records:
        return "_(no records)_"
    # stable column order: union of keys in first-seen order
    cols: list[str] = []
    seen = set()
    for row in records:
        for k in row.keys():
            if k not in seen:
                seen.add(k)
                cols.append(k)
    # markdown header
    lines = [
        "| " + " | ".join(cols) + " |",
        "| " + " | ".join("---" for _ in cols) + " |",
    ]
    for row in records:
        lines.append("| " + " | ".join(_fmt_value(row.get(c, "")) for c in cols) + " |")
    return "\n".join(lines)


def records_to_csv(records: list[dict]) -> str:
    if not records:
        return ""
    cols: list[str] = []
    seen = set()
    for row in records:
        for k in row.keys():
            if k not in seen:
                seen.add(k)
                cols.append(k)
    buf = io.StringIO()
    w = csv.DictWriter(buf, fieldnames=cols, extrasaction="ignore")
    w.writeheader()
    for row in records:
        w.writerow({c: _fmt_value(row.get(c, "")) for c in cols})
    return buf.getvalue().strip()


def build_data_block(reg: dict) -> str:
    """Authoritative retrieved data tables only."""
    parts: list[str] = []
    data_targets: dict = reg.get("data_targets") or {}
    for target_id, target in data_targets.items():
        status = target.get("status", "unknown")
        source = target.get("source") or {}
        src_table = source.get("table") or source.get("type") or "unknown"
        query_role = source.get("query_role") or ""
        records = target.get("records") or []
        summary = target.get("summary") or {}

        parts.append(f"### DATA TARGET: {target_id}")
        parts.append(f"- status: {status}")
        parts.append(f"- source_table: {src_table}")
        if query_role:
            parts.append(f"- query_role: {query_role}")
        if summary:
            parts.append(f"- summary: {json.dumps(summary, ensure_ascii=False)}")
        parts.append(f"- record_count: {len(records)}")
        parts.append("")
        parts.append("#### Table (markdown)")
        parts.append(records_to_markdown_table(records))
        parts.append("")
        parts.append("#### Table (CSV)")
        parts.append("```csv")
        parts.append(records_to_csv(records))
        parts.append("```")
        parts.append("")
    return "\n".join(parts).strip() + "\n"


def _fact_lines(reg: dict) -> list[str]:
    lines: list[str] = []
    facts = (reg.get("fact_packet") or {}).get("facts") or []
    for f in facts:
        # Include all facts for audit; mark non-narratable clearly.
        fid = f.get("fact_id", "")
        display = f.get("display")
        label = f.get("label")
        unit = f.get("unit")
        narratable = bool(f.get("narratable"))
        value = f.get("value")
        tokens = f.get("numeric_tokens") or []

        if display:
            core = str(display)
        else:
            core = f"{label}: {_fmt_value(value)}"
            if unit:
                core = f"{core} {unit}"

        flag = "narratable" if narratable else "internal"
        extra = f" | numeric_tokens={tokens}" if tokens else ""
        lines.append(f"- [{flag}] {fid}: {core}{extra}")
    return lines


def _binding_text_blocks(reg: dict) -> dict[str, list[str]]:
    """Extract human-readable bound content by role."""
    out: dict[str, list[str]] = {
        "headlines": [],
        "kpis": [],
        "context": [],
        "guidance": [],
        "sources": [],
        "charts": [],
        "maps": [],
    }
    for b in reg.get("content_bindings") or []:
        btype = b.get("block_type")
        payload = b.get("content_payload")
        if btype == "headline" and isinstance(payload, str):
            out["headlines"].append(payload)
        elif btype == "kpi" and isinstance(payload, dict):
            label = payload.get("label", "KPI")
            value = payload.get("value")
            unit = payload.get("unit") or ""
            sec = payload.get("secondary_value")
            sec_u = payload.get("secondary_unit") or ""
            line = f"{label}: {_fmt_value(value)} {unit}".strip()
            if sec is not None:
                line += f" | secondary: {_fmt_value(sec)} {sec_u}".strip()
            out["kpis"].append(line)
        elif btype == "annotation" and isinstance(payload, str):
            out["context"].append(payload)
        elif btype == "checklist":
            if isinstance(payload, list):
                out["guidance"].extend(str(x) for x in payload)
            elif isinstance(payload, str):
                out["guidance"].append(payload)
        elif btype == "footer" and isinstance(payload, str):
            out["sources"].append(payload)
        elif btype == "chart" and isinstance(payload, dict):
            subtype = payload.get("chart_subtype", "unknown")
            targets = payload.get("source_targets") or []
            reason = payload.get("reason") or ""
            out["charts"].append(
                f"chart_subtype={subtype}; source_targets={targets}; reason={reason}"
            )
        elif btype == "map" and isinstance(payload, dict):
            targets = payload.get("source_targets") or []
            reason = payload.get("reason") or ""
            out["maps"].append(f"map; source_targets={targets}; reason={reason}")
    return out


def build_knowledge_block(reg: dict) -> str:
    """
    Contextual text permitted for baselines.
    ONLY material already present in the registry (facts, bindings, plan, geo).
    """
    parts: list[str] = []
    parts.append(
        "RETRIEVED KNOWLEDGE (extracted from RiskScribe immutable registry; "
        "do not add facts beyond this block)."
    )
    parts.append("")

    # Location resolution
    rc = reg.get("resolved_county") or {}
    counties = reg.get("resolved_counties") or []
    parts.append("## Location")
    if counties:
        for c in counties:
            parts.append(
                f"- {c.get('county')}, {c.get('state_abbr')} "
                f"(FIPS {c.get('fips_county_code')}; area_sqmi={_fmt_value(c.get('area_sqmi'))})"
            )
    elif rc:
        parts.append(
            f"- {rc.get('county')}, {rc.get('state_abbr')} "
            f"(FIPS {rc.get('fips_county_code')})"
        )
    else:
        parts.append("- (none recorded)")
    parts.append("")

    # Narrative plan (bound text only)
    plan = (reg.get("narrative_contract") or {}).get("plan") or {}
    parts.append("## Narrative plan (registry)")
    if plan.get("angle"):
        parts.append(f"- angle: {plan['angle']}")
    headline = plan.get("headline") or {}
    if isinstance(headline, dict) and headline.get("text"):
        parts.append(f"- headline_text: {headline['text']}")
    kpi_label = plan.get("kpi_label") or {}
    if isinstance(kpi_label, dict) and kpi_label.get("text"):
        parts.append(f"- kpi_label_text: {kpi_label['text']}")
    for cb in plan.get("context_blocks") or []:
        if isinstance(cb, dict) and cb.get("text"):
            parts.append(f"- context: {cb['text']}")
    parts.append("")

    # Bound content
    blocks = _binding_text_blocks(reg)
    parts.append("## Bound content")
    if blocks["headlines"]:
        parts.append("### Headlines")
        parts.extend(f"- {x}" for x in blocks["headlines"])
    if blocks["kpis"]:
        parts.append("### KPIs")
        parts.extend(f"- {x}" for x in blocks["kpis"])
    if blocks["context"]:
        parts.append("### Context captions")
        parts.extend(f"- {x}" for x in blocks["context"])
    if blocks["guidance"]:
        parts.append("### Protective / recommended actions")
        parts.extend(f"- {x}" for x in blocks["guidance"])
    if blocks["sources"]:
        parts.append("### Sources")
        parts.extend(f"- {x}" for x in blocks["sources"])
    if blocks["charts"]:
        parts.append("### Chart selection (RiskScribe; informational for baselines)")
        parts.extend(f"- {x}" for x in blocks["charts"])
        parts.append(
            "  (Baselines may choose their own chart type; C2 scores appropriateness.)"
        )
    if blocks["maps"]:
        parts.append("### Map elements (RiskScribe; informational)")
        parts.extend(f"- {x}" for x in blocks["maps"])
    parts.append("")

    # Fact packet (display forms)
    parts.append("## Fact packet (display forms)")
    flines = _fact_lines(reg)
    if flines:
        parts.extend(flines)
    else:
        parts.append("- (none)")
    parts.append("")

    # Freshness
    fg = (reg.get("fact_packet") or {}).get("freshness_gate") or {}
    if fg:
        parts.append("## Freshness gate")
        parts.append(f"- requested_current: {fg.get('requested_current')}")
        parts.append(f"- status: {fg.get('status')}")
        parts.append(f"- current_claim_allowed: {fg.get('current_claim_allowed')}")
        parts.append(f"- observation_period: {fg.get('observation_period')}")
        parts.append(f"- downgraded: {fg.get('downgraded')}")
        if fg.get("reason"):
            parts.append(f"- reason: {fg['reason']}")
        parts.append("")

    parts.append(
        "## Usage rules for generators\n"
        "- Use ONLY values present in the RETRIEVED DATA tables for numbers.\n"
        "- Use ONLY text present in this knowledge block for contextual claims.\n"
        "- Do not invent statistics, locations, dates, or guidance.\n"
        "- If a value is missing, omit it rather than guessing."
    )
    return "\n".join(parts).strip() + "\n"


def build_case(case_dir: Path) -> dict:
    case_id = case_dir.name
    req_path = case_dir / "requirement.txt"
    reg_path = case_dir / "immutable_registry.json"
    if not req_path.exists() or not reg_path.exists():
        raise FileNotFoundError(f"Missing requirement or registry in {case_dir}")

    requirement = req_path.read_text(encoding="utf-8").strip()
    reg = json.loads(reg_path.read_text(encoding="utf-8"))
    data_block = build_data_block(reg)
    knowledge_block = build_knowledge_block(reg)

    # gold values helpful for later FFR scoring
    gold_numeric = []
    for f in (reg.get("fact_packet") or {}).get("facts") or []:
        if f.get("numeric_tokens") or isinstance(f.get("value"), (int, float)):
            gold_numeric.append(
                {
                    "fact_id": f.get("fact_id"),
                    "display": f.get("display"),
                    "value": f.get("value"),
                    "unit": f.get("unit"),
                    "numeric_tokens": f.get("numeric_tokens") or [],
                }
            )

    chart_subtypes = []
    for b in reg.get("content_bindings") or []:
        if b.get("block_type") == "chart" and isinstance(b.get("content_payload"), dict):
            chart_subtypes.append(b["content_payload"].get("chart_subtype"))

    meta = {
        "case_id": case_id,
        "data_target_ids": list((reg.get("data_targets") or {}).keys()),
        "riskscribe_chart_subtypes": chart_subtypes,
        "n_facts": len((reg.get("fact_packet") or {}).get("facts") or []),
        "gold_numeric_facts": gold_numeric,
        "resolved_counties": [
            {
                "county": c.get("county"),
                "state_abbr": c.get("state_abbr"),
                "fips_county_code": c.get("fips_county_code"),
            }
            for c in (reg.get("resolved_counties") or [])
        ],
        "source": "extracted_from_immutable_registry_v1",
        "note": "knowledge_block is reformat-only; no LLM generation.",
    }

    return {
        "case_id": case_id,
        "requirement": requirement,
        "data_block": data_block,
        "knowledge_block": knowledge_block,
        "meta": meta,
    }


def main() -> None:
    case_dirs = sorted(p for p in SUPPLEMENTAL.iterdir() if p.is_dir() and p.name.startswith("req_"))
    if not case_dirs:
        raise SystemExit(f"No req_* cases under {SUPPLEMENTAL}")

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    cases = []
    for case_dir in case_dirs:
        case = build_case(case_dir)
        cases.append(case)

        case_out = OUT_DIR / case["case_id"]
        case_out.mkdir(parents=True, exist_ok=True)
        (case_out / "requirement.txt").write_text(case["requirement"] + "\n", encoding="utf-8")
        (case_out / "data_block.md").write_text(case["data_block"], encoding="utf-8")
        (case_out / "knowledge_block.md").write_text(case["knowledge_block"], encoding="utf-8")
        (case_out / "meta.json").write_text(
            json.dumps(case["meta"], indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
        print(
            f"OK {case['case_id']}: "
            f"data_targets={case['meta']['data_target_ids']} "
            f"facts={case['meta']['n_facts']} "
            f"charts={case['meta']['riskscribe_chart_subtypes']}"
        )

    # cases.json for code_interpreter.rtf / generators
    payload = [
        {
            "case_id": c["case_id"],
            "requirement": c["requirement"],
            "data_block": c["data_block"],
            "knowledge_block": c["knowledge_block"],
        }
        for c in cases
    ]
    cases_path = OUT_DIR / "cases.json"
    cases_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    index = {
        "n_cases": len(cases),
        "cases": [c["meta"] for c in cases],
        "outputs": {
            "cases_json": str(cases_path.relative_to(ROOT)),
            "per_case_dir": "results/table1/inputs/<case_id>/",
        },
    }
    (OUT_DIR / "index.json").write_text(json.dumps(index, indent=2) + "\n", encoding="utf-8")
    print(f"\nWrote {cases_path} ({len(cases)} cases)")
    print(f"Per-case files under {OUT_DIR}/<case_id>/")


if __name__ == "__main__":
    main()
