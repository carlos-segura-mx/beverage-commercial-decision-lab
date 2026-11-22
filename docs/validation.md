# Validation and publication status

[English README](../README.md) | [README en español](README.es.md)

The primary deliverable is a bilingual Streamlit application. The repository includes automated tests for the data grain, reference totals, scenario calculations, discount bounds, cross-product effects, public copy and the Streamlit app in both languages.

## Quantitative reference scenario

| Check | Reference output |
| --- | ---: |
| Discount on Classic Coffee | 10% |
| Portfolio volume change | +1.94% |
| Portfolio revenue change | -0.48% |
| Portfolio contribution change | -2.59% |
| Model inputs | `data/pricing_model_inputs.json` |
| Source of expected results | `data/model_results.json` |

The test suite compares the entire-portfolio scenario with the stored reference, using the full numerical precision rather than only the rounded figures above.

## Verification boundaries

- Unit and data tests verify model calculations and CSV integrity, not market truth.
- A GitHub Actions pass verifies the Python test suite. It does not independently validate Power BI formulas, cross-filter behavior, screenshots or live cloud rendering.
- The PBIX remains a historical complementary artifact, not a validated source of truth for this Streamlit release.
- No deployment URL or screenshot should be published before the deployed app has been opened and checked.
- If the historic generator is rerun, review its output changes before updating a release.

To run the checks locally:

```bash
python -m pip install -r requirements.txt
python -m pytest -q
python -m compileall -q app.py src tests
```
