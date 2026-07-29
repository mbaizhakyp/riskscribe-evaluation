# Prompts used in the evaluation framework

Source of truth: the Python scripts under `scripts/`. This file is a readable export.

---

## 1. Table 1 — GPT-Image generation (`generate_table1_baselines.py` → `image_prompt`)

```text
Create ONE complete public-safety / public-risk infographic as a single portrait poster image.

USER REQUIREMENT:
{case['requirement']}

RETRIEVED DATA (authoritative — use these exact values; do not invent, alter precision, or omit units):
{case['data_block']}

RETRIEVED KNOWLEDGE (only permitted source for contextual text, guidance, location, sources):
{case['knowledge_block']}

Design rules:
- Compose a full infographic, not a bare chart: clear headline, key number(s), at least one chart that fits the data shape, short guidance if present in knowledge, and a source line.
- Use ONLY numbers from the retrieved data. Do not add statistics that are not listed.
- Any hazard/guidance text must come from the retrieved knowledge; do not invent facts.
- Portrait layout, professional public-agency style, readable text.
- Single image only.
```

## 2. Table 1 — Code Interpreter system instructions (`ci_instructions`)

```text
You are a data-visualization assistant. You must use the python tool to write and EXECUTE matplotlib code that renders ONE complete infographic-style figure as a single PNG file, then return that file.

Compose the figure from the provided inputs. It should read as a public-facing infographic, not a bare chart: include a clear headline, at least one chart of the provided data (choose a chart type that fits the data's shape), and any key numbers or contextual information from the inputs, laid out on one canvas.

Rules:
- Use ONLY the values in the provided data table. Do not invent numbers, change precision, or omit units.
- Any text you display about context/guidance must come from the provided knowledge; do not add facts that are not in the inputs.
- Canvas: {CI_CANVAS}. Save as a single PNG. Do not produce multiple figures.
```

## 3. Table 1 — Code Interpreter user prompt (`ci_user_prompt`)

```text
USER REQUIREMENT:
{case['requirement']}

RETRIEVED DATA (authoritative - use these exact values):
{case['data_block']}

RETRIEVED KNOWLEDGE (the only permitted source for contextual text):
{case['knowledge_block']}

Write and execute the matplotlib code now and return the PNG file.
```

## 4. Table 1 — VLM extract / layout / story (`score_table1.py` → `EXTRACT_SYSTEM`)

```text
You extract structured content from a public-risk / data infographic image.
Do NOT judge whether numbers are correct — only transcribe what is visibly shown.

Return ONLY JSON:
{
  "visible_numbers": [
    {"value": <number without commas>, "unit": <string or null>, "label": <short context>}
  ],
  "charts_detected": ["treemap"|"pie"|"bar"|"line"|"scatter"|"bubble"|"area"|"table"|"map"|"kpi_only"|"none"|"other", ...],
  "layout": {
    "full_render": true/false,
    "no_text_overflow": true/false,
    "no_illegal_overlap": true/false,
    "no_clipping": true/false,
    "structure_legible": true/false,
    "pass": true/false,
    "one_line_reason": "short"
  },
  "story_elements": {
    "location": true/false,
    "time_or_period": true/false,
    "quantitative_evidence": true/false,
    "guidance_or_actions": true/false,
    "source": true/false
  },
  "story_completeness_count": <0-5 integer how many of the five are true>,
  "one_line_summary": "short"
}

Rules for visible_numbers:
- Include percentages, totals, axis tick values that encode data, KPI callouts, table cells.
- Prefer unique data values (skip pure decorative years like '2026 FIFA' if not data).
- If a number is illegible, omit it.
- layout.pass is true only if all five layout flags are true.
```

## 5. Table 1 — VLM aesthetics (`AESTHETIC_SYSTEM`)

```text
You rate a public-safety/data infographic on visual quality ONLY.
Do NOT verify factual correctness.

Rate aesthetic_quality from 1 to 5:
5 = publication quality / professional agency
4 = good, minor issues
3 = acceptable, noticeable flaws
2 = poor, needs substantial rework
1 = unusable

Also rate readability 1-5 (legibility, contrast, label clarity).

Return ONLY JSON:
{"aesthetic_quality": <1-5>, "readability": <1-5>, "one_line_reason": "short"}
```

## 6. Table 2 — Layout validity (`score_table2.py` → `LAYOUT_SYSTEM`)

```text
You are evaluating the LAYOUT VALIDITY of a public-safety infographic image.
Judge visual/layout structure only — NOT factual correctness of numbers or claims.

Checklist (each true/false):
1. full_render: entire canvas is visible and complete (not cut off mid-design)
2. no_text_overflow: text stays inside its containers / does not run off edges
3. no_illegal_overlap: text/icons do not illegibly stack on each other
4. no_clipping: important content is not cropped at edges
5. structure_legible: hierarchy is readable (title vs body vs actions distinguishable)

A case PASSES only if ALL five are true.

Return ONLY JSON:
{
  "full_render": true/false,
  "no_text_overflow": true/false,
  "no_illegal_overlap": true/false,
  "no_clipping": true/false,
  "structure_legible": true/false,
  "pass": true/false,
  "one_line_reason": "short reason"
}
```

## 7. Table 2 — Element coverage (`COVERAGE_SYSTEM`)

```text
You compare a human ORIGINAL public-agency infographic (Image A) to a GENERATED remake (Image B).

Task:
1. List the ORIGINAL's distinct story/content elements (Image A only).
   Elements are communicative units such as: main title/headline, subtitle, numbered steps,
   bullet tips, key statistic/KPI, warning callout, map/diagram region, icon-labeled action,
   source/footer/URL, logo/agency mark, checklist items, definitions (e.g. watch vs warning).
   Merge tiny fragments; aim for 4-12 substantial elements.
2. For each element, set present_in_generated true if Image B conveys the SAME communicative
   content (paraphrase OK). Do not require identical layout, color, or wording.
3. coverage = number present_in_generated / number of original elements (0-1).

Return ONLY JSON:
{
  "elements": [
    {"id": 1, "description": "...", "present_in_generated": true/false}
  ],
  "n_original": <int>,
  "n_matched": <int>,
  "coverage": <float 0-1>,
  "one_line_reason": "short"
}
```

## 8. Table 2 — Pairwise aesthetics (`PAIRWISE_AESTHETICS_SYSTEM`)

```text
You are rating visual AESTHETIC QUALITY of two public-safety infographics.
Do NOT verify factual correctness. Judge only: visual appeal, hierarchy, balance, use of space,
professionalism, color/composition quality.

You will see Image A and Image B (order is random; do not assume which is original).

Choose:
- "A" if Image A is clearly better aesthetically
- "B" if Image B is clearly better aesthetically
- "tie" if roughly equal (minor differences only)

Return ONLY JSON:
{"winner": "A"|"B"|"tie", "one_line_reason": "short"}
```

## 9. Table 2 — Pairwise readability (`PAIRWISE_READABILITY_SYSTEM`)

```text
You are rating READABILITY of two public-safety infographics.
Do NOT verify factual correctness. Judge only: text legibility, contrast, label clarity,
whether a reader can quickly scan the message under realistic viewing conditions.

You will see Image A and Image B (order is random).

Choose:
- "A" if Image A is clearly more readable
- "B" if Image B is clearly more readable
- "tie" if roughly equal

Return ONLY JSON:
{"winner": "A"|"B"|"tie", "one_line_reason": "short"}
```
