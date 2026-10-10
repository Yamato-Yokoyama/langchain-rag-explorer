"""eval_retrieval の部品の仕様(埋め込みモデルは読み込まない)。"""

import json

import pytest

from src.eval_retrieval import evaluate_query, gains_for, item_id, load_golden


def test_item_id_only_for_receipts():
    assert item_id({"receipt_id": "LIDL_1", "source": "r.json"}) == "LIDL_1"
    assert item_id({"company": "SAP"}) is None


def test_gains_for():
    assert gains_for(["a", None, "b", "x"], {"a", "b"}) == [1.0, 0.0, 1.0, 0.0]


def test_perfect_retrieval():
    r = evaluate_query(["a", "b", "x"], ["a", "b"], k=3)
    assert r["ndcg"] == pytest.approx(1.0)
    assert r["recall"] == 1.0
    assert (r["hits"], r["n_relevant"]) == (2, 2)


def test_nothing_found():
    r = evaluate_query(["x", "y"], ["a"], k=2)
    assert r["ndcg"] == 0.0 and r["recall"] == 0.0


def test_golden_file_is_well_formed():
    cases = load_golden()
    assert len(cases) >= 10
    for c in cases:
        assert c["query"] and c["relevant"], c
        assert len(set(c["relevant"])) == len(c["relevant"])
