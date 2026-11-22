# Methodology and interpretation

[English](methodology.md) | [Español](methodology.es.md)

## Business question

The central question is whether a price promotion improves portfolio contribution once changes in volume, product substitution and price are considered together. The dashboard also provides descriptive sell-out views and a historical forecasting comparison.

## Synthetic setting

The case has 104 indexed weekly periods (with simulated dates), 60 points of sale, six beverage products and 37,440 point-of-sale, SKU and week records. Synthetic sell-out revenue is units sold to the consumer times a synthetic net price. Contribution is this revenue minus synthetic cost of sales, not operating profit or distributor margin.

## Price what-if model

For product i, with price P_i, volume Q_i and unit cost C_i, enter discount d_i in 0 to 0.20. Its proportional price change is -d_i. The tool applies a linear response:

`Q_i_new = max(0, Q_i * (1 + sum_j(E_ij * (-d_j))))`

`P_i_new = P_i * (1 - d_i)`

`Revenue_i_new = Q_i_new * P_i_new`

`Contribution_i_new = Q_i_new * (P_i_new - C_i)`

The diagonal of E contains own-price elasticity estimates fitted to synthetic data. All off-diagonal entries in E are substitution assumptions. With cross effects switched off, the off-diagonal coefficients are set to zero for that scenario. Positive discount inputs must not be confused with positive price changes.

The reference baseline uses mean weekly sell-out volume, mean net price and mean unit cost over the last eight synthetic weeks. In the reference scenario, only Classic Coffee receives a 10% discount. This gives volume +1.94%, revenue -0.48% and contribution -2.59% compared with unchanged prices. The sensitivity view varies the selected SKU's discount in 1 percentage point steps, holding the other current inputs constant.

These are small-scenario approximations, not proven causal elasticities or optimal prices. They do not account for competitor response, stock constraints, nonlinear price response, supplier terms or cost changes.

## Forecast evaluation

The eight-week holdout compares a seasonal baseline, an eight-week moving average and additive Holt-Winters across six product series. The reported WAPE is total absolute error divided by total observed units. Bias is the signed sum of forecast minus observed units divided by observed units. The eight-week moving average has 5.80% aggregated WAPE; Holt-Winters is within approximately 0.001 percentage points on WAPE but with a lower absolute bias in the displayed test. One holdout is not continuous rolling validation.

## Inventory and delivery

The synthetic service-level ratio uses delivered units divided by ordered units. The existing generator creates opening inventories independently by observation and does not guarantee continuity across weeks. End-of-period inventories therefore must not be used for replenishment advice or financial exposure. Power BI inventory DAX and report navigation need separate validation in Power BI Desktop.

## Reproducibility

The Streamlit application reads versioned synthetic CSV files plus `data/pricing_model_inputs.json`. The scenario formulas are in `src/scenario_engine.py` and have unit tests that reconcile the original reference scenario stored in `data/model_results.json`. The historical `src/build_analysis.py` recreates synthetic data and analytical outputs. It may regenerate the notebook and other files, so review changes before committing results.

See [data provenance](data_provenance.md) and [validation](validation.md).
