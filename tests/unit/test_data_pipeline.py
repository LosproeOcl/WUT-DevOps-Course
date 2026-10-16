import pandas as pd

from ml.aspects import ASPECTS, map_category
from ml.data_pipeline import build_v2, parse_xml_file

SAMPLE_XML = """<?xml version="1.0" encoding="utf-8"?>
<sentences>
  <sentence>
    <text>The food was great but the service was slow.</text>
    <aspectCategories>
      <aspectCategory category="food" polarity="positive"/>
      <aspectCategory category="service" polarity="negative"/>
    </aspectCategories>
  </sentence>
  <sentence>
    <text>Reasonable price and nice ambience.</text>
    <aspectCategories>
      <aspectCategory category="price" polarity="neutral"/>
      <aspectCategory category="miscellaneous" polarity="neutral"/>
    </aspectCategories>
  </sentence>
</sentences>
"""


def test_map_category_maps_and_drops():
    assert map_category("food") == "food"
    assert map_category("menu") == "food"
    assert map_category("staff") == "service"
    assert map_category("ambience") == "ambience"
    assert map_category("place") == "ambience"
    assert map_category("miscellaneous") is None
    assert map_category("UNKNOWN") is None


def test_parse_xml_file_extracts_aspects(tmp_path):
    xml = tmp_path / "sample.xml"
    xml.write_text(SAMPLE_XML, encoding="utf-8")
    records = parse_xml_file(str(xml))
    # 3 aspectCategory rows survive (miscellaneous is dropped)
    assert len(records) == 3
    food = next(r for r in records if r["aspect"] == "food")
    assert food["label"] == "positive"
    assert food["polarity"] == 1
    assert any(r["aspect"] == "service" and r["label"] == "negative" for r in records)
    assert any(r["aspect"] == "price" and r["label"] == "neutral" for r in records)
    assert not any(r["aspect"] == "miscellaneous" for r in records)


def test_parse_xml_file_handles_empty_text(tmp_path):
    xml = tmp_path / "empty.xml"
    xml.write_text(
        '<?xml version="1.0"?><sentences><sentence><text> </text>'
        '<aspectCategories><aspectCategory category="food" polarity="positive"/>'
        "</aspectCategories></sentence></sentences>",
        encoding="utf-8",
    )
    records = parse_xml_file(str(xml))
    assert len(records) == 1
    assert records[0]["text"] == ""


def test_build_v2_deduplicates():
    df = pd.DataFrame(
        [
            {"text": "great food", "aspect": "food", "polarity": 1, "label": "positive", "split": "train"},
            {"text": "great food", "aspect": "food", "polarity": 1, "label": "positive", "split": "train"},
        ]
    )
    v2 = build_v2(df)
    assert len(v2) == 1
    assert v2.iloc[0]["text"] == "great food"


def test_aspects_are_four():
    assert ASPECTS == ["food", "service", "price", "ambience"]
