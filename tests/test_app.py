"""Streamlit smoke checks for both languages and simulator controls."""
from pathlib import Path
from streamlit.testing.v1 import AppTest

ROOT=Path(__file__).resolve().parents[1]

def test_bilingual_dashboard_and_scenario_widgets():
    app=AppTest.from_file(str(ROOT/"app.py"),default_timeout=90).run()
    assert not app.exception,[str(e.message) for e in app.exception]
    assert "Beverage Commercial Decision Lab" in [x.value for x in app.title]
    assert any(x.label=="Café Clásico" for x in app.number_input)
    assert any(x.label=="Incluir sustitución entre productos" for x in app.checkbox)
    assert any("Contribución" in x.label for x in app.metric)
    assert any(x.label=="Periodo" for x in app.sidebar.date_input)
    assert any(x.label=="Canales" for x in app.sidebar.multiselect)
    assert any(x.label=="Indicador en el tiempo" for x in app.selectbox)
    assert any(x.label=="Umbral de servicio (%)" for x in app.slider)
    langs=[x for x in app.sidebar.radio if x.label=="Idioma / Language"]
    assert len(langs)==1
    langs[0].set_value("English").run()
    assert not app.exception,[str(e.message) for e in app.exception]
    assert any(x.label=="Classic Coffee" for x in app.number_input)
    assert any(x.label=="Include cross-product substitution" for x in app.checkbox)
    assert any("Contribution" in x.label for x in app.metric)
    assert any(x.label=="Date range" for x in app.sidebar.date_input)
    assert any(x.label=="Time-series measure" for x in app.selectbox)
    assert any(x.label=="Service threshold (%)" for x in app.slider)
