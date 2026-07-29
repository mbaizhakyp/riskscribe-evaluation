# RiskScribe Evaluation Policy & Runbook (Blueprint)

This is the **public** evaluation blueprint: policy, metrics, code, prompts, and reproduction steps.
It does **not** ship raw study data. Bring your own generated images and gold registries.

---

## 1. Goals

Provide a reproducible framework so researchers can:

1. Generate baseline infographics (optional) with GPT-Image / Code Interpreter under fair inputs
2. Score systems on **Table 1** (complex data fidelity + presentation)
3. Score reverse-engineered posters on **Table 2** (vs an original anchor)

---

## 2. Evaluation policy

### Table 1 — complex data

| Metric | Scale | Method |
|--------|-------|--------|
| FFR ↑ | 0–1 | VLM transcribes visible numbers → match gold in `immutable_registry.json` |
| HR ↓ | 0–1 | `1 − FFR` |
| Numeric accuracy ↑ | 0–1 | same match rate as FFR |
| Expert appropriateness ↑ | 1–5 | human chart-fit (recommended for papers) |
| Layout validity ↑ | pass-rate % | VLM checklist |
| Story completeness ↑ | 0–5 mean | location, time, quantity, guidance, source |
| Aesthetic quality ↑ | 1–5 mean | VLM; median of 3 passes |

**FFR tolerance:** abs ≤ 0.05 if |gold| < 100 else relative ≤ 0.5%.

**Fair comparison for baselines:** shared `results/table1/inputs/` packs; attempt budget 3; portrait canvas; no cherry-picking.

### Table 2 — vs original

| Metric | Scale | Method |
|--------|-------|--------|
| Layout validity | pass-rate % | VLM on generated |
| Element coverage | 0–1 mean | original elements present in generated? |
| Aesthetics W/T/L | % | pairwise (prefer ties when close) |
| Readability W/T/L | % | pairwise |
| Referenced scores | 0–100 | `(100×wins + 50×ties) / N` (50 = parity) |

---

## 3. Repository map

```text
riskscribe_evaluation_blueprint/
├── README.md
├── config/table1_cases.json
├── docs/          # policy, prompts, protocol, formula figure
├── scripts/       # build / generate / score
├── data/
│   ├── table1/<case>/   # requirement, registry, decoration.png
│   └── table2/<case>/   # original_preview.png, decoration.png
└── results/       # written by scripts
```

---

## 4. Code inventory

| Script | Role |
|--------|------|
| `scripts/build_table1_inputs.py` | Registry → data/knowledge packs (no LLM) |
| `scripts/generate_table1_baselines.py` | GPT-Image + Code Interpreter generators |
| `scripts/score_table1.py` | Table 1 metrics |
| `scripts/score_table1_expert.py` | Optional VLM expert proxy |
| `scripts/score_table2.py` | Table 2 metrics |

Prompts: `docs/PROMPTS.md` (exported from scripts).

---

## 5. Step-by-step

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install openai pillow python-docx
export OPENAI_API_KEY=sk-...

# Optional: build fair packs + generate baselines for your cases
python scripts/build_table1_inputs.py
python scripts/generate_table1_baselines.py

# Score
python scripts/score_table1.py
python scripts/score_table2.py
```

Filters:

```bash
ONLY_CASES=example_case ONLY_SYSTEMS=gpt_img_2,ci_sol python scripts/generate_table1_baselines.py
TABLE1_VLM_MODEL=gpt-4o TABLE2_VLM_MODEL=gpt-4o python scripts/score_table1.py
```

---

## 6. Gold registry schema (minimal)

```json
{
  "data_targets": {
    "my_table": {
      "records": [
        {"field_a": 1.23, "field_b": 4.56}
      ]
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

All numeric fields in `records` and fact `value` / `numeric_tokens` become FFR gold.

---

## 7. Compliance checklist

- [ ] No private/real sensitive data committed to a public fork of this blueprint
- [ ] Gold registries match the data shown to generators
- [ ] Attempt budget ≤ 3 when generating baselines
- [ ] Human expert ratings used for publication when required
- [ ] Table 2 ties used when neither image is clearly better
- [ ] API keys never committed

---

## 8. Limitations of automation

VLM FFR can over-count chart axis ticks; gold lists can omit valid subtype counts.
Pairwise judges may under-use ties. Document any human adjudication.
