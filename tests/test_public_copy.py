"""Publication standards adopted in the independent portfolio editorial guidelines."""
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
PUBLIC=[
    ROOT/"README.md",ROOT/"docs"/"README.es.md",
    ROOT/"docs"/"methodology.md",ROOT/"docs"/"methodology.es.md",
    ROOT/"docs"/"data_provenance.md",ROOT/"docs"/"validation.md",ROOT/"app.py",
    ROOT/"src"/"commercial_dashboard.py",
]

def test_public_copy_has_no_long_dashes():
    for path in PUBLIC:
        text=path.read_text(encoding="utf-8")
        assert "\u2014" not in text, f"Em dash in {path}"
        assert "\u2013" not in text, f"En dash in {path}"

def test_bilingual_readmes_are_aligned():
    en=(ROOT/"README.md").read_text(encoding="utf-8")
    es=(ROOT/"docs"/"README.es.md").read_text(encoding="utf-8")
    for number in ("37,440","104","60","5.80","1.94","2.59"):
        assert number in en and number in es,number
    assert "docs/README.es.md" in en
    assert "../README.md" in es
    assert "Power BI" in en and "Power BI" in es
