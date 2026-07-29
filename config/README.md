# Config

- `table1_cases.json` — optional ordered list of Table 1 case IDs under `data/table1/`.
  If omitted, scorers discover every case directory that contains `immutable_registry.json`.
- Table 2 cases are auto-discovered: every directory under `data/table2/` that has both
  `original_preview.png` and `infographic_decoration.png`.
