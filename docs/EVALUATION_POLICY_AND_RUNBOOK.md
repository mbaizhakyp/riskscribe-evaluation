# RiskScribe Evaluation Policy & Runbook

This document is the evaluation **policy**, **metric definitions**, and **reproduction steps** for the public blueprint.  
It does not include study data. Researchers supply their own images and gold registries.

---

## 1. Goals

1. Optionally generate baseline infographics (GPT-Image / Code Interpreter) under fair shared inputs  
2. Score systems on **Table 1** (complex-data fidelity and presentation quality)  
3. Score reverse-engineered posters on **Table 2** (vs an original anchor)  

---

## 2. Evaluation policy

### Table 1 — complex data

| Metric | Scale | Method |
|--------|-------|--------|
| Fact-Fidelity Rate (FFR) ↑ | 0–1 | VLM transcribes visible numbers → match gold in `immutable_registry.json` |
| Hallucination Rate (HR) ↓ | 0–1 | `HR = 1 − FFR` |
| Numeric accuracy ↑ | 0–1 | same match rate as FFR |
| Expert appropriateness ↑ | 1–5 | human chart-fit (recommended for papers) |
| Layout validity ↑ | pass-rate % | VLM checklist |
| Story completeness ↑ | 0–5 mean | location, time, quantity, guidance, source |
| Aesthetic quality ↑ | 1–5 mean | VLM absolute rating; median of 3 passes |

**FFR matching tolerance:** absolute error ≤ 0.05 if \|gold\| < 100; else relative error ≤ 0.5%.  
Gold values: numeric fields in `data_targets.*.records`, plus fact `value` and `numeric_tokens` in `fact_packet`.

**Fair comparison (baselines):** identical requirement + data + knowledge packs per case; attempt budget 3; portrait canvas; first success kept (no aesthetic cherry-picking).

### Table 2 — vs original

| Metric | Scale | Method |
|--------|-------|--------|
| Layout validity | pass-rate % | VLM checklist on generated image |
| Element coverage | 0–1 mean | original elements present in generated? |
| Aesthetics win / tie / loss | % | blinded pairwise (prefer **tie** when close) |
| Readability win / tie / loss | % | blinded pairwise |
| Referenced scores | 0–100 | \((100 N_{\mathrm{win}} + 50 N_{\mathrm{tie}}) / N\) |

**50 = parity** with the original. See `docs/Aesthetics_referenced_score.png`.

### Automation limits

VLM FFR may count chart axis ticks as data; gold lists may omit valid subtype counts.  
Pairwise judges may under-use ties. Document human adjudication when used.

---

## 3. Local data layout (not shipped)

### Table 1 — `data/table1/<case_id>/`

| File | Role |
|------|------|
| `requirement.txt` | Task brief (for generation) |
| `immutable_registry.json` | Gold numbers (for FFR) |
| `infographic_decoration.png` | Output image to score |

**Minimal gold registry:**

```json
{
  "data_targets": {
    "my_table": {
      "records": [{ "field_a": 1.23, "field_b": 4.56 }]
    }
  },
  "fact_packet": {
    "facts": [
      {
        "fact_id": "kpi.total",
        "display": "Total: 5.79",
        "value": 5.79,
        "unit": null,
        "numeric_tokens": ["5.79"]
      }
    ]
  }
}
```

Optional baseline images:

```text
results/table1/generations/<case_id>/<system>/<case_id>_<system>.png
```

`system` ∈ `gpt_img_1_5` | `gpt_img_2` | `ci_sol` | `ci_luna` | `riskscribe`

### Table 2 — `data/table2/<case_id>/`

| File | Role |
|------|------|
| `original_preview.png` | Reference / original |
| `infographic_decoration.png` | Generated remake |
| `requirement.txt` | Optional brief |

### Discovery

- Table 1: every `data/table1/*/` containing `immutable_registry.json`, or restrict with optional `config/table1_cases.json` (JSON list of IDs).  
- Table 2: every `data/table2/*/` containing both PNGs.

---

## 4. Code inventory

| Script | Role |
|--------|------|
| `scripts/build_table1_inputs.py` | Registry → fair data/knowledge packs (no LLM) |
| `scripts/generate_table1_baselines.py` | GPT-Image + Code Interpreter generators |
| `scripts/score_table1.py` | Table 1 automated metrics |
| `scripts/score_table1_expert.py` | Optional dual VLM expert-proxy ratings |
| `scripts/score_table2.py` | Table 2 layout, coverage, pairwise scores |

Prompts used by these scripts: **`docs/PROMPTS.md`**.

Judge models default to `gpt-4o` (`TABLE1_VLM_MODEL` / `TABLE2_VLM_MODEL`).

---

## 5. Reproduction steps

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
export OPENAI_API_KEY=sk-...

# After placing your cases under data/:
python scripts/build_table1_inputs.py          # optional
python scripts/generate_table1_baselines.py    # optional
python scripts/score_table1.py
python scripts/score_table2.py
```

Filters:

```bash
ONLY_CASES=my_case ONLY_SYSTEMS=gpt_img_2,ci_sol python scripts/generate_table1_baselines.py
```

Run outputs go under local `results/` (not part of this public package).

---

## 6. Compliance checklist

- [ ] No private study data committed to a public fork  
- [ ] Gold registries match generator inputs  
- [ ] Baseline attempt budget ≤ 3  
- [ ] Prefer human expert ratings for publication  
- [ ] Use ties in pairwise metrics when appropriate  
- [ ] API keys never committed  
