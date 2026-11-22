"""Checks for descriptive BI metrics independent of Streamlit."""
import numpy as np
import pandas as pd
import pytest
from src.commercial_dashboard import metrics, grouped, service_review


def sample():
    rows=[]
    for pdv,units,delivered in [("A",5,100),("B",100,80),("C",100,100),("D",110,100)]:
        rows.append(dict(pdv_id=pdv,sku="SKU",channel="Retail",zone="North",
                         date=pd.Timestamp("2026-07-06"),revenue=10*units,
                         contribution=3*units,units_sold=units,
                         units_ordered=100,units_delivered=delivered))
    return pd.DataFrame(rows)


def test_weighted_service_and_margin():
    frame=sample()
    k=metrics(frame)
    assert k["service"]==pytest.approx(.95)
    assert k["margin"]==pytest.approx(.3)
    assert k["unfilled"]==20
    sites=grouped(frame,["pdv_id"])
    assert sites.revenue.sum()==k["revenue"]


def test_distinct_delivery_and_commercial_review():
    low,commercial=service_review(sample(),threshold=.90,min_orders=50)
    assert set(low.pdv_id)=={"B"}
    assert set(commercial.pdv_id)=={"A"}
    assert commercial.peers.min()==4


def test_peer_minimum_and_zero_denominator():
    low,commercial=service_review(sample().iloc[:3],threshold=.90,min_orders=50)
    assert commercial.empty
    assert np.isnan(metrics(sample().iloc[:0])["service"])
