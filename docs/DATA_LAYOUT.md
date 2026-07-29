# Data layout (bring your own)

This repository does **not** ship evaluation cases or images. Researchers supply their own generated results under a local `data/` tree (gitignored if it contains private assets).

## Table 1 — `data/table1/<case_id>/`

| File | Required | Role |
|------|----------|------|
| `requirement.txt` | for generation | Task brief |
| `immutable_registry.json` | for FFR | Gold numeric facts |
| `infographic_decoration.png` | for scoring | System output image |

**Minimal gold registry schema:**

```json
{
  "data_targets": {
    "my_table": {
      "records": [
        {"label": "A", "value": 10.0, "unit": "%"}
      ]
    }
  },
  "fact_packet": {
    "facts": [
      {
        "fact_id": "kpi.total",
        "display": "Total: 10%",
        "value": 10.0,
        "unit": "%",
        "numeric_tokens": ["10", "10.0"]
      }
    ]
  }
}
```

Baseline PNGs (optional), written by the generator or provided by you:

```text
results/table1/generations/<case_id>/<system>/<case_id>_<system>.png
```

`system` ∈ `gpt_img_1_5` | `gpt_img_2` | `ci_sol` | `ci_luna` | `riskscribe`

## Table 2 — `data/table2/<case_id>/`

| File | Required | Role |
|------|----------|------|
| `original_preview.png` | yes | Reference / original poster |
| `infographic_decoration.png` | yes | Generated remake to score |
| `requirement.txt` | optional | Brief |

## Discovery

- Table 1: all `data/table1/*/` with `immutable_registry.json`, or override via `config/table1_cases.json`
- Table 2: all `data/table2/*/` with both PNGs present
