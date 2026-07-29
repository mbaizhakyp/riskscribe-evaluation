# RiskScribe Evaluation Blueprint

**Public evaluation framework only** — no study data, no case images, no filled private results.

Use this package to:
1. Understand the RiskScribe evaluation **policy** and metrics  
2. Follow **reproduction steps** for scoring  
3. Run the same **code** and **prompts** on **your own** generated infographics  

---

## What's included

| Path | Contents |
|------|----------|
| `docs/EVALUATION_POLICY_AND_RUNBOOK.md` | Policy, metrics, formulas, run steps |
| `docs/DATA_LAYOUT.md` | How to place your own cases (local `data/`) |
| `docs/PROMPTS.md` | Exported generation + judge prompts |
| `docs/RiskScribe_Evaluation_Protocol.docx` | Protocol document |
| `docs/Aesthetics_referenced_score.png` | Referenced-score formula figure |
| `scripts/` | Input builder, baseline generators, scorers |
| `config/` | Optional Table 1 case-list override |
| `results/` | Notes only; score outputs are created at run time |

**Not included:** evaluation cases, registries, images, or study scores. Create a local `data/` tree when you are ready to run (see `docs/DATA_LAYOUT.md`).

---

## Quick start (score your own results)

```bash
python3 -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
export OPENAI_API_KEY=sk-...   # required for VLM judges / generators
```

### Table 1 — complex-data fidelity / quality

1. Add cases under `data/table1/<case_id>/` (see `docs/DATA_LAYOUT.md`):
   - `requirement.txt`
   - `immutable_registry.json` (gold numbers)
   - `infographic_decoration.png` (your system output)
2. Optionally add baseline PNGs under  
   `results/table1/generations/<case_id>/<system>/`
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
# ONLY_CASES=my_case ONLY_SYSTEMS=gpt_img_2,ci_sol python scripts/generate_table1_baselines.py
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

Your own system only needs images on the paths above; it does not need to be re-implemented here.
