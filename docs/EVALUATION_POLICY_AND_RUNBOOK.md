# RiskScribe Evaluation Policy & Runbook (Blueprint)

Public evaluation blueprint: **policy**, **metrics**, **code**, **prompts**, and **reproduction steps**.  
It does **not** ship study data or images. Bring your own generated results and gold registries (local `data/` — see `docs/DATA_LAYOUT.md`).

---

## 1. Goals

1. Optionally generate baseline infographics with GPT-Image / Code Interpreter under fair shared inputs  
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
riskscribe_evaluation/
├── README.md
├── config/                 # optional case-list override
├── docs/                   # policy, data layout, prompts, protocol
├── scripts/                # build / generate / score
└── results/                # notes; outputs created when you run scripts

# Created locally by you (not shipped):
data/table1/<case>/         # requirement, registry, decoration.png
data/table2/<case>/         # original_preview.png, decoration.png
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

Prompts: `docs/PROMPTS.md`. Case file layout: `docs/DATA_LAYOUT.md`.

---

## 5. Step-by-step

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
export OPENAI_API_KEY=sk-...

# After placing your cases under data/ (see DATA_LAYOUT.md):
python scripts/build_table1_inputs.py          # optional
python scripts/generate_table1_baselines.py    # optional
python scripts/score_table1.py
python scripts/score_table2.py
```

Filters:

```bash
ONLY_CASES=my_case ONLY_SYSTEMS=gpt_img_2,ci_sol python scripts/generate_table1_baselines.py
TABLE1_VLM_MODEL=gpt-4o TABLE2_VLM_MODEL=gpt-4o python scripts/score_table1.py
```

---

## 6. Compliance checklist

- [ ] No private/real sensitive data committed to a public fork  
- [ ] Gold registries match the data shown to generators  
- [ ] Attempt budget ≤ 3 when generating baselines  
- [ ] Human expert ratings used for publication when required  
- [ ] Table 2 ties used when neither image is clearly better  
- [ ] API keys never committed  

---

## 7. Limitations of automation

VLM FFR can over-count chart axis ticks; gold lists can omit valid subtype counts.  
Pairwise judges may under-use ties. Document any human adjudication.
