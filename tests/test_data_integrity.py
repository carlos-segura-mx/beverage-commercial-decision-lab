"""Checks against the published, fully synthetic source tables."""
import json
from pathlib import Path
import numpy as np
import pandas as pd

ROOT=Path(__file__).resolve().parents[1]
DATA=ROOT/"data"

def test_fact_grain_and_key_integrity():
    fact=pd.read_csv(DATA/"fact_sales.csv")
    customers=pd.read_csv(DATA/"dim_customer.csv")
    products=pd.read_csv(DATA/"dim_product.csv")
    dates=pd.read_csv(DATA/"dim_date.csv")
    assert len(fact)==37440
    assert fact.date.nunique()==104
    assert fact.pdv_id.nunique()==60
    assert fact.sku.nunique()==6
    assert not fact.duplicated(["date","pdv_id","sku"]).any()
    assert set(fact.pdv_id).issubset(set(customers.pdv_id))
    assert set(fact.sku).issubset(set(products.sku))
    assert set(fact.date).issubset(set(dates.date))
    assert (fact.units_ordered>=fact.units_delivered).all()
    assert (fact[["units_ordered","units_delivered","units_sold"]]>=0).all().all()

def test_published_financial_totals():
    fact=pd.read_csv(DATA/"fact_sales.csv")
    saved=json.loads((DATA/"model_results.json").read_text(encoding="utf-8"))
    assert np.isclose(fact.revenue.sum(),saved["total_revenue"])
    assert np.isclose(fact.contribution.sum(),saved["total_contribution"])
    assert np.isclose(fact.contribution.sum()/fact.revenue.sum(),saved["overall_margin_pct"])
    assert np.isclose(fact.units_delivered.sum()/fact.units_ordered.sum(),saved["overall_service_level"])

def test_holdout_metrics_are_stored_as_proportions():
    metrics=pd.read_csv(DATA/"forecast_metrics.csv")
    total=metrics.loc[metrics.sku.eq("TOTAL")]
    assert len(total)==3
    assert (total.wape>=0).all()
    assert total.loc[total.method.eq("Promedio movil 8s"),"wape"].iloc[0] == pytest_approx(0.05802837798996736)

def pytest_approx(value):
    import pytest
    return pytest.approx(value)
