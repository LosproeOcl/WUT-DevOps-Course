import pandas as pd

from ml.aspects import ASPECTS, map_category, tokenize_zh
from ml.data_pipeline import build_v2, parse_asap_csv

SAMPLE_CSV = (
    "id,review,star,Food#Taste,Service#Hospitality,Price#Level,Ambience#Decoration\n"
    "1,食物很棒,5,1,1,-2,1\n"
    "2,服务一般,3,-2,0,-2,-2\n"
    "3,价格太贵,2,-2,-2,-1,-2\n"
)


def test_map_category_maps_and_drops():
    assert map_category("Food#Taste") == "food"
    assert map_category("Food#Portion") == "food"
    assert map_category("Service#Hospitality") == "service"
    assert map_category("Price#Level") == "price"
    assert map_category("Ambience#Decoration") == "ambience"
    assert map_category("Location#Transportation") is None
    assert map_category("Unknown") is None


def test_tokenize_zh_splits_chars():
    assert tokenize_zh("食物很棒") == "食 物 很 棒"


def test_parse_asap_csv_extracts_aspects(tmp_path):
    csv = tmp_path / "t.csv"
    csv.write_text(SAMPLE_CSV, encoding="utf-8")
    df = parse_asap_csv(str(csv))
    assert len(df) == 5
    assert set(df["aspect"]) == {"food", "service", "price", "ambience"}
    assert (df[df["aspect"] == "food"]["label"] == "positive").all()
    assert set(df[df["aspect"] == "service"]["label"]) == {"positive", "neutral"}
    assert (df[df["aspect"] == "price"]["label"] == "negative").all()
    assert (df[df["aspect"] == "ambience"]["label"] == "positive").all()


def test_parse_asap_csv_drops_unmentioned(tmp_path):
    csv = tmp_path / "t.csv"
    csv.write_text(SAMPLE_CSV, encoding="utf-8")
    df = parse_asap_csv(str(csv))
    assert -2 not in df["polarity"].tolist()


def test_build_v2_tokenizes_and_deduplicates():
    df = pd.DataFrame(
        [
            {"text": "食物很棒", "aspect": "food", "polarity": 1, "label": "positive", "split": "train"},
            {"text": "食物很棒", "aspect": "food", "polarity": 1, "label": "positive", "split": "train"},
        ]
    )
    v2 = build_v2(df)
    assert len(v2) == 1
    assert v2.iloc[0]["text"] == "食 物 很 棒"


def test_aspects_are_four():
    assert ASPECTS == ["food", "service", "price", "ambience"]
