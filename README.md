# RiskScribe Evaluation Blueprint

Public **evaluation framework** only: policy, instructions, reproduction steps, code, and prompts.  
No study data, case images, or filled scores.

---

## Contents

| Path | Role |
|------|------|
| `docs/EVALUATION_POLICY_AND_RUNBOOK.md` | Evaluation policy + full reproduction guide |
| `docs/PROMPTS.md` | Generation and judge prompts (exported) |
| `docs/RiskScribe_Evaluation_Protocol.docx` | Formal evaluation protocol |
| `docs/Aesthetics_referenced_score.png` | Referenced-score formula figure |
| `scripts/` | Build inputs, generate baselines, score Table 1 & 2 |
| `requirements.txt` | Python dependencies |

---

## Setup

```bash
python3 -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt
export OPENAI_API_KEY=sk-...       # required for generation and VLM scoring
```

Optional: create `api_keys.txt` with a line `sk-...` (gitignored; do not commit).

---

## Bring your own data

Create cases **locally** (not shipped in this repo):

**Table 1** — `data/table1/<case_id>/`

- `requirement.txt` — task brief  
- `immutable_registry.json` — gold numbers for FFR  
- `infographic_decoration.png` — system output to score  

**Table 2** — `data/table2/<case_id>/`

- `original_preview.png` — original / reference poster  
- `infographic_decoration.png` — generated remake  

Optional: `config/table1_cases.json` as a JSON list of case IDs to restrict Table 1 discovery.

Gold registry schema, metric definitions, and full policy: **`docs/EVALUATION_POLICY_AND_RUNBOOK.md`**.

---

## Reproduction steps

```bash
# Optional: fair shared packs + baseline generators (GPT-Image / Code Interpreter)
python scripts/build_table1_inputs.py
python scripts/generate_table1_baselines.py
# ONLY_CASES=my_case ONLY_SYSTEMS=gpt_img_2,ci_sol python scripts/generate_table1_baselines.py

# Score
python scripts/score_table1.py
python scripts/score_table2.py
# optional VLM expert proxy:
python scripts/score_table1_expert.py
```

Outputs are written under local `results/` (gitignored).

---

## Systems (baseline generator)

| ID | Model |
|----|--------|
| `gpt_img_1_5` | gpt-image-1.5 |
| `gpt_img_2` | gpt-image-2 |
| `ci_sol` | gpt-5.6-sol + code_interpreter |
| `ci_luna` | gpt-5.6-luna + code_interpreter |

Prompts: `docs/PROMPTS.md` (source of truth also lives in `scripts/`).
