import pandas as pd

from ml.data_pipeline import (
    POLARITY_TO_LABEL,
    build_v1,
    build_v2,
    clean_text,
    inject_term,
    parse_seg_file,
)


def test_polarity_mapping():
    assert POLARITY_TO_LABEL == {-1: "negative", 0: "neutral", 1: "positive"}


def test_inject_term_replaces_placeholder():
    assert inject_term("the $T$ was great", "food") == "the food was great"


def test_inject_term_replaces_all_occurrences():
    assert inject_term("$T$ and $T$", "x") == "x and x"


def test_clean_text_lowercases_and_fixes_parens():
    assert clean_text("Not only was the -LRB- food -RRB- great") == "not only was the ( food ) great"


def test_clean_text_collapses_whitespace():
    assert clean_text("  a   b  ") == "a b"


def test_parse_seg_file_builds_records(tmp_path):
    seg = tmp_path / "sample.seg"
    seg.write_text(
        "the $T$ was good\nfood\n1\n"
        "the $T$ was awful\nservice\n-1\n"
        "the $T$ was ok\nprice\n0\n",
        encoding="utf-8",
    )
    records = parse_seg_file(str(seg))
    assert len(records) == 3
    assert records[0] == {"text": "the $T$ was good", "term": "food", "polarity": 1, "label": "positive"}
    assert records[1]["label"] == "negative"
    assert records[2]["label"] == "neutral"


def test_parse_seg_file_skips_malformed_lines(tmp_path):
    seg = tmp_path / "bad.seg"
    seg.write_text("no term here\n\nnot-a-polarity\n", encoding="utf-8")
    assert parse_seg_file(str(seg)) == []


def test_build_v1_injects_term():
    df = pd.DataFrame(
        [{"text": "the $T$", "term": "food", "polarity": 1, "label": "positive", "split": "train"}]
    )
    v1 = build_v1(df)
    assert v1.iloc[0]["text"] == "the food"


def test_build_v2_cleans_and_deduplicates():
    df = pd.DataFrame(
        [
            {"text": "the $T$ was good", "term": "Food", "polarity": 1, "label": "positive", "split": "train"},
            {"text": "the $T$ was good", "term": "food", "polarity": 1, "label": "positive", "split": "train"},
        ]
    )
    v2 = build_v2(df)
    assert len(v2) == 1
    assert v2.iloc[0]["text"] == "the food was good"
    assert v2.iloc[0]["term"] == "food"
