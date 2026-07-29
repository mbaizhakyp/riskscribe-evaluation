# Score table template (conceptual)

## Table 1 columns
Systems: GPT-Img-1.5 | GPT-Img-2 | CI sol | CI luna | RiskScribe (or your systems)

Rows (means / rates over cases):
- Fact-Fidelity Rate (FFR) ↑
- Hallucination Rate (HR) ↓
- Numeric Accuracy ↑
- Expert appropriateness ↑ (1–5 human)
- Layout Validity ↑ (pass-rate %)
- Story Completeness ↑ (0–5 mean)
- Aesthetic Quality ↑ (1–5 mean)
- Fidelity × Aesthetics (summary)

## Table 2 columns
RiskScribe (or your system) | Original (anchor)

Rows:
- Layout Validity ↑
- Element coverage vs original ↑
- Aesthetics win / tie / loss %
- Aesthetics referenced score (50 = parity)
- Readability referenced score (50 = parity)

Referenced score = (100×N_win + 50×N_tie) / N
