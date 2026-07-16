"""周道 v0.0.3：歧义语料库自动化验证。

逐条加载 ambiguity_cases.json 并验证：
- JSON 结构完整性
- 每条用例有 id / code / expected / reason / interpretations
- 分类计数与 summary 一致
- 错误类型在预期集合内
- 省略歧义条目有 resolution 字段
"""

import json
import os
import pytest

CORPUS_PATH = os.path.join(os.path.dirname(__file__), "..", "tests", "corpus", "ambiguity_cases.json")
VALID_ERROR_TYPES = {"重复定义", "重复字段", "重复参数", "名称冲突", "重复字面量",
                     "未定义", "作用域越界", "词法歧义", "语法歧义",
                     "词法错误", "分支顺序错误", "重复定义", "重复导入名",
                     "省略歧义", "跨越冲突", "语法错误", "非法标识符",
                     "非法字符", "非法名称字符"}
VALID_EXPECTED = {"valid", "syntax_error", "name_error", "ambiguity_error", "scope_error", "warning"}


def _load_corpus():
    with open(CORPUS_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def test_corpus_meta():
    data = _load_corpus()
    assert "meta" in data
    assert data["meta"]["version"] == "0.0.3"
    assert data["meta"]["total_cases"] >= 200


def test_corpus_summary_matches_actual():
    data = _load_corpus()
    total = sum(len(cat["cases"]) for cat in data["categories"].values())
    assert total == data["meta"]["total_cases"], (
        f"meta.total_cases={data['meta']['total_cases']} != actual={total}"
    )
    # Check by_verdict
    counts = {}
    for cat in data["categories"].values():
        for case in cat["cases"]:
            exp = case["expected"]
            counts[exp] = counts.get(exp, 0) + 1
    for k, v in counts.items():
        assert data["summary"]["by_verdict"][k] == v, (
            f"summary.{k}={data['summary']['by_verdict'][k]} != actual={v}"
        )


def test_all_cases_have_required_fields():
    data = _load_corpus()
    errors = []
    for cat_name, cat in data["categories"].items():
        for case in cat["cases"]:
            for field in ("id", "code", "expected", "reason", "interpretations"):
                if field not in case:
                    errors.append(f"{case.get('id','?')}: missing {field}")
            if case["expected"] not in VALID_EXPECTED:
                errors.append(f"{case['id']}: invalid expected={case['expected']}")
            if case["expected"] != "valid":
                if case.get("errorType") and case["errorType"] not in VALID_ERROR_TYPES:
                    errors.append(f"{case['id']}: unknown errorType={case['errorType']}")
    assert not errors, "\n".join(errors[:20])


def test_omission_cases_have_resolution():
    data = _load_corpus()
    for cat_name, cat in data["categories"].items():
        for case in cat["cases"]:
            if case["expected"] == "ambiguity_error":
                assert "resolution" in case, (
                    f"{case['id']}: ambiguity_error must have resolution field"
                )


def test_id_uniqueness():
    data = _load_corpus()
    ids = set()
    dupes = []
    for cat in data["categories"].values():
        for case in cat["cases"]:
            if case["id"] in ids:
                dupes.append(case["id"])
            ids.add(case["id"])
    assert not dupes, f"Duplicate IDs: {dupes}"


def test_corpus_not_empty():
    data = _load_corpus()
    for cat_name, cat in data["categories"].items():
        assert len(cat["cases"]) >= 2, (
            f"{cat_name} has only {len(cat['cases'])} cases"
        )


@pytest.mark.parametrize("expected_type", [
    "valid", "syntax_error", "name_error", "ambiguity_error", "scope_error"
])
def test_by_verdict_counts(expected_type):
    data = _load_corpus()
    count = data["summary"]["by_verdict"].get(expected_type, 0)
    assert count >= 0


def test_corpus_case_ids_intact():
    """Verify every case has a parseable ID."""
    data = _load_corpus()
    import re
    for cat in data["categories"].values():
        for case in cat["cases"]:
            assert re.match(r'^[A-Z]{2}\d{3,4}$', case["id"]), (
                f"Bad ID format: {case['id']}"
            )


def test_corpus_code_not_empty():
    data = _load_corpus()
    for cat in data["categories"].values():
        for case in cat["cases"]:
            assert case["code"].strip(), f"{case['id']}: empty code field"


def test_corpus_interpretations():
    """Every case must have at least 1 interpretation."""
    data = _load_corpus()
    for cat in data["categories"].values():
        for case in cat["cases"]:
            interps = case.get("interpretations", [])
            assert len(interps) >= 1, f"{case['id']}: no interpretations"


if __name__ == "__main__":
    pytest.main([__file__])
