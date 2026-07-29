# Results

Score and generation outputs are **created at run time** under `results/table1/` and `results/table2/` (gitignored). This folder only documents what the scripts write:

- `table1/inputs/` — fair packs from `build_table1_inputs.py`
- `table1/generations/` — baseline PNGs from `generate_table1_baselines.py`
- `table1/per_case_system_results.*` / `aggregate_summary.json`
- `table2/per_case_results.*` / `aggregate_summary.json`
- `RiskScribe_Final_Score_Tables.docx` — updated by scorers when present

No study scores are shipped in this repository.
