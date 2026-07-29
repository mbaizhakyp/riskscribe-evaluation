# Data layout (bring your own)

This blueprint ships **synthetic placeholders only** (`example_case`, `example_poster`).
Replace or add cases using the same file names.

## Table 1 — `data/table1/<case_id>/`
| File | Required | Role |
|------|----------|------|
| `requirement.txt` | yes (for generation) | Task brief |
| `immutable_registry.json` | yes (for FFR) | Gold numbers |
| `infographic_decoration.png` | yes (to score system) | Output image |

## Table 2 — `data/table2/<case_id>/`
| File | Required | Role |
|------|----------|------|
| `original_preview.png` | yes | Anchor original |
| `infographic_decoration.png` | yes | Generated remake |
| `requirement.txt` | optional | Brief |
