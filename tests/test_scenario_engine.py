import json
import math
from pathlib import Path
import numpy as np
import pytest
from src.scenario_engine import load_model,simulate,discount_curve

ROOT=Path(__file__).resolve().parents[1]
MODEL={
    "products":[
       {"sku":"A","product":"A","base_price":37.35925,"unit_cost":17.515,"base_volume":877.0,"own_elasticity":-1.096727141864895},
       {"sku":"B","product":"B","base_price":40.620583333333336,"unit_cost":19.3225,"base_volume":644.25,"own_elasticity":-1.1347540662705797},
       {"sku":"C","product":"C","base_price":42.70016666666667,"unit_cost":20.7025,"base_volume":529.25,"own_elasticity":-1.7414602822617617},
       {"sku":"D","product":"D","base_price":29.867395833333333,"unit_cost":13.27125,"base_volume":820.625,"own_elasticity":-.7380203197985437},
       {"sku":"E","product":"E","base_price":32.068895833333336,"unit_cost":14.65125,"base_volume":732.625,"own_elasticity":-.9368512160694873},
       {"sku":"F","product":"F","base_price":48.072937499999995,"unit_cost":24.41875,"base_volume":490.375,"own_elasticity":-.7034201764922716},
    ],
    "elasticity_matrix":[
      [-1.096727141864895,.18,.1,0,0,0],
      [.18,-1.1347540662705797,.18,0,0,0],
      [.1,.18,-1.7414602822617617,0,0,0],
      [0,0,0,-.7380203197985437,.14,0],
      [0,0,0,.14,-.9368512160694873,.05],
      [0,0,0,0,.05,-.7034201764922716]
    ]}

def test_zero_discounts_reproduce_baseline():
    d,s=simulate(MODEL,{})
    for metric in ("volume","revenue","contribution"):
        assert math.isclose(s[f"base_{metric}"],s[f"scenario_{metric}"],rel_tol=1e-12)
    assert np.isclose(d["volume_change"],0).all()
    assert np.isclose(d["contribution_change"],0).all()
    assert np.isclose(d["base_volume_share_pct"].sum(),100)
    assert np.isclose(d["scenario_revenue_share_pct"].sum(),100)

def test_existing_published_10_percent_promotion():
    d,s=simulate(MODEL,{"A":.10})
    assert s["delta_volume_pct"] == pytest.approx(0.019367745328135122)
    assert s["delta_revenue_pct"] == pytest.approx(-0.004829578877724283)
    assert s["delta_contribution_pct"] == pytest.approx(-0.025889336737129676)
    a=d.set_index("sku")
    assert a.loc["A","scenario_volume"] == pytest.approx(973.1829703415513)
    assert a.loc["B","scenario_volume"] == pytest.approx(632.6535)
    assert a.loc["C","scenario_volume"] == pytest.approx(523.9575)

def test_cross_effects_are_explicit_and_optional():
    full,_=simulate(MODEL,{"A":.10},use_cross=True)
    solo,_=simulate(MODEL,{"A":.10},use_cross=False)
    a=full.set_index("sku");b=solo.set_index("sku")
    assert a.loc["B","cross_effect_units"]<0
    assert a.loc["B","scenario_volume"]<b.loc["B","scenario_volume"]
    assert np.allclose(solo["cross_effect_units"],0)

def test_input_bounds_and_unknown_skus():
    for changes in ({"A":-.01},{"A":.21},{"unknown":.05}):
        with pytest.raises(ValueError):simulate(MODEL,changes)

def test_discount_curve_is_not_reoptimizing_other_skus():
    curve=discount_curve(MODEL,"A",{"B":.03})
    assert curve.discount_pct.tolist()==list(range(21))
    _,s=simulate(MODEL,{"A":.10,"B":.03})
    assert curve.loc[curve.discount_pct.eq(10),"scenario_contribution"].iloc[0] == pytest.approx(s["scenario_contribution"])

def test_published_reference_data_if_present():
    root=ROOT/"data"
    if not (root/"pricing_model_inputs.json").exists():
        pytest.skip("Test requires published repository data")
    model=load_model(root/"pricing_model_inputs.json")
    reference=json.loads((root/"model_results.json").read_text(encoding="utf-8"))
    discounts={p["sku"]:float(p.get("default_discount",0)) for p in model["products"]}
    _,summary=simulate(model,discounts)
    for key in ("base_volume","simulated_volume","base_revenue","simulated_revenue",
                "base_contribution","simulated_contribution","delta_volume_pct",
                "delta_revenue_pct","delta_contribution_pct"):
        assert summary["scenario_"+key[len("simulated_"):] if key.startswith("simulated_") else key] == pytest.approx(reference["scenario"][key],rel=1e-9,abs=1e-7)
