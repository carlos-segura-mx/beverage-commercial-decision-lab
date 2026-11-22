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
    langs=[x for x in app.sidebar.radio if x.label=="Idioma / Language"]
    assert len(langs)==1
    langs[0].set_value("English").run()
    assert not app.exception,[str(e.message) for e in app.exception]
    assert any(x.label=="Classic Coffee" for x in app.number_input)
    assert any(x.label=="Include cross-product substitution" for x in app.checkbox)
    assert any("Contribution" in x.label for x in app.metric)
