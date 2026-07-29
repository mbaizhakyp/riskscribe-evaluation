# RiskScribe Evaluation Blueprint

**Public evaluation framework only** — no raw study data, no real case images, no filled private results.

Use this package to:
1. Understand the RiskScribe evaluation **policy** and metrics
2. Follow **reproduction steps** for scoring
3. Run the same **code** and **prompts** on **your own** generated infographics

If you already have generated images + gold facts, you can score them without using our private corpus.

---

## What's included

| Path | Contents |
|------|----------|
| `docs/EVALUATION_POLICY_AND_RUNBOOK.md` | Policy, metrics, formulas, run steps |
| `docs/PROMPTS.md` | Exported generation + judge prompts |
| `docs/RiskScribe_Evaluation_Protocol.docx` | Protocol document |
| `docs/Aesthetics_referenced_score.png` | Referenced-score formula figure |
| `scripts/` | Input builder, baseline generators, scorers |
| `config/` | Optional case list |
| `data/table1/example_case/` | **Synthetic** Table 1 layout demo |
| `data/table2/example_poster/` | **Synthetic** Table 2 layout demo |
| `results/` | Empty output tree (created by runs) |

**Not included:** real RiskScribe study cases, agency originals, registries with real hazard data, baseline study outputs, or final private score tables.

---

## Quick start (score your own results)

```bash
python3 -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install openai pillow python-docx
export OPENAI_API_KEY=sk-...   # required for VLM judges / generators
```

### Table 1 — complex-data fidelity / quality

1. Add a case under `data/table1/<case_id>/`:
   - `requirement.txt`
   - `immutable_registry.json` (gold numbers — see example)
   - `infographic_decoration.png` (your system output)
2. Optionally put baseline PNGs at  
   `results/table1/generations/<case_id>/<system>/<case_id>_<system>.png`  
   with `system` ∈ `gpt_img_1_5`, `gpt_img_2`, `ci_sol`, `ci_luna`, `riskscribe`  
   (or only score `riskscribe` by providing decoration + registry).
3. Run:

```bash
python scripts/build_table1_inputs.py   # optional fair packs for generation
python scripts/score_table1.py
```

### Table 2 — vs original poster

1. Add `data/table2/<case_id>/original_preview.png`
2. Add `data/table2/<case_id>/infographic_decoration.png`
3. Run:

```bash
python scripts/score_table2.py
```

### Optional: generate baselines yourself

```bash
python scripts/build_table1_inputs.py
python scripts/generate_table1_baselines.py
# ONLY_CASES=example_case ONLY_SYSTEMS=gpt_img_2 python scripts/generate_table1_baselines.py
```

---

## Metrics (summary)

**Table 1:** FFR / HR / numeric accuracy (VLM transcription → gold match), layout validity, story completeness, aesthetic quality; expert appropriateness is human 1–5.

**Table 2:** layout validity, element coverage, aesthetics & readability win/tie/loss → referenced scores  
\((100 N_{win} + 50 N_{tie}) / N\) with **50 = parity**.

Full definitions: `docs/EVALUATION_POLICY_AND_RUNBOOK.md`.

---

## Systems supported by the baseline generator

| ID | Model |
|----|--------|
| `gpt_img_1_5` | gpt-image-1.5 |
| `gpt_img_2` | gpt-image-2 |
| `ci_sol` | gpt-5.6-sol + code_interpreter |
| `ci_luna` | gpt-5.6-luna + code_interpreter |

Your own system only needs images in the paths above; it does not need to be re-implemented here.

---

## License / data notice

Synthetic placeholders in `data/` are **not** scientific results. Do not treat example numbers or placeholder graphics as evaluation evidence.
