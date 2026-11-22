"""Auditable, linear price what-if model for the synthetic beverage portfolio.

Own-price elasticities are fitted to synthetic observations. Cross-price
elasticities are explicit assumptions, not causal estimates. Prices, volumes,
and costs are synthetic and all calculations are illustrative.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Mapping

import numpy as np
import pandas as pd

MAX_DISCOUNT = 0.20


def load_model(path: str | Path) -> dict:
    """Load and validate the six-product model exported by build_analysis.py."""
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    products = data.get("products", [])
    keys = [p["sku"] for p in products]
    matrix = np.asarray(data.get("elasticity_matrix", []), dtype=float)
    if len(keys) == 0 or len(keys) != len(set(keys)):
        raise ValueError("Model products must have distinct nonempty SKU identifiers")
    if matrix.shape != (len(keys), len(keys)) or not np.isfinite(matrix).all():
        raise ValueError("Elasticity matrix must be square and contain finite values")
    for p in products:
        if (float(p["base_price"]) <= 0 or float(p["unit_cost"]) < 0
                or float(p["base_volume"]) < 0):
            raise ValueError("Price, cost and volume inputs must be economically valid")
        if not np.isfinite([p["base_price"],p["unit_cost"],p["base_volume"],p["own_elasticity"]]).all():
            raise ValueError("Model contains invalid values")
    diagonal = np.array([float(p["own_elasticity"]) for p in products])
    if not np.allclose(np.diag(matrix), diagonal, atol=1e-9):
        raise ValueError("Diagonal elasticities differ from the named product inputs")
    return data


def simulate(model: dict, discount_by_sku: Mapping[str, float], use_cross: bool = True) -> tuple[pd.DataFrame, dict]:
    """Compare portfolio baselines and one simultaneous price-change scenario.

    Positive discounts lower prices. Change in volume is linearized as
    q_new_i = max(0, q_i * (1 + sum_j elasticity_ij * price_change_j)).
    This is a local scenario approximation, not an estimated causal response.
    """
    products = pd.DataFrame(model["products"])
    sku = products["sku"].tolist()
    unknown = set(discount_by_sku) - set(sku)
    if unknown:
        raise ValueError(f"Discounts refer to unknown SKUs: {sorted(unknown)}")
    d = np.array([float(discount_by_sku.get(x, 0.0)) for x in sku])
    if not np.isfinite(d).all() or np.any(d < 0) or np.any(d > MAX_DISCOUNT):
        raise ValueError("Discount fractions must be within 0 and 0.20")
    E = np.asarray(model["elasticity_matrix"], dtype=float)
    if not use_cross:
        E = np.diag(np.diag(E))
    base_q = products["base_volume"].to_numpy(dtype=float)
    base_p = products["base_price"].to_numpy(dtype=float)
    costs = products["unit_cost"].to_numpy(dtype=float)
    pdelta = -d
    own_effect = base_q * np.diag(E) * pdelta
    cross_effect = base_q * ((E - np.diag(np.diag(E))) @ pdelta)
    scenario_q = np.maximum(0, base_q + own_effect + cross_effect)
    scenario_p = base_p * (1 + pdelta)
    base_sales = base_q * base_p
    new_sales = scenario_q * scenario_p
    base_contribution = (base_p - costs) * base_q
    new_contribution = (scenario_p - costs) * scenario_q

    output = products[["sku","product"]].copy()
    output["discount_pct"] = d * 100
    output["own_elasticity"] = np.diag(E)
    output["base_price"] = base_p
    output["scenario_price"] = scenario_p
    output["base_volume"] = base_q
    output["scenario_volume"] = scenario_q
    output["own_effect_units"] = own_effect
    output["cross_effect_units"] = cross_effect
    output["volume_change"] = scenario_q-base_q
    output["base_revenue"] = base_sales
    output["scenario_revenue"] = new_sales
    output["revenue_change"] = new_sales-base_sales
    output["base_contribution"] = base_contribution
    output["scenario_contribution"] = new_contribution
    output["contribution_change"] = new_contribution-base_contribution

    for metric in ("volume", "revenue"):
        b = output[f"base_{metric}"].to_numpy()
        c = output[f"scenario_{metric}"].to_numpy()
        denominator_b = b.sum()
        denominator_c = c.sum()
        output[f"base_{metric}_share_pct"] = 100*b/denominator_b if denominator_b>0 else 0.0
        output[f"scenario_{metric}_share_pct"] = 100*c/denominator_c if denominator_c>0 else 0.0
    summary = {}
    for metric in ("volume","revenue","contribution"):
        b = float(output[f"base_{metric}"].sum())
        c = float(output[f"scenario_{metric}"].sum())
        summary.update({f"base_{metric}":b,f"scenario_{metric}":c,
                        f"delta_{metric}":c-b,
                        f"delta_{metric}_pct":(c/b-1) if abs(b)>1e-12 else float("nan")})
    summary["base_margin_pct"] = (summary["base_contribution"]/summary["base_revenue"]*100
                                  if summary["base_revenue"] else float("nan"))
    summary["scenario_margin_pct"] = (summary["scenario_contribution"]/summary["scenario_revenue"]*100
                                      if summary["scenario_revenue"] else float("nan"))
    summary["discounted_skus"] = int(np.count_nonzero(d))
    summary["cross_effects_enabled"] = bool(use_cross)
    return output,summary


def discount_curve(model: dict, selected_sku: str, other_discounts: Mapping[str,float] | None = None,
                   use_cross: bool = True) -> pd.DataFrame:
    """Sensitivity from 0 to 20% in 1 percentage point steps, keeping other inputs fixed."""
    other_discounts = dict(other_discounts or {})
    if selected_sku not in {p["sku"] for p in model["products"]}:
        raise ValueError("Unknown selected SKU")
    rows=[]
    for pct in range(21):
        inputs=dict(other_discounts)
        inputs[selected_sku]=pct/100
        _, summary=simulate(model,inputs,use_cross=use_cross)
        rows.append({"discount_pct":pct,**summary})
    return pd.DataFrame(rows)
