"""Probes, lab data files, the new check kinds and the in-process practice API (labmock) through the real harness (local subprocess)."""
import asyncio
import base64
import json

import pytest

import sandbox.labmock as labmock
from grader_service.evaluate import check, evaluate, probe_exprs, required_vars, RunResult
from grader_service.runner import SubprocessRunner


def run(code, tests=(), files=None, timeout=10, lab_api=False):
    tests = list(tests)
    r = SubprocessRunner()
    return asyncio.run(r.run(code, required_vars(tests), timeout, files=files, probes=probe_exprs(tests), lab_api=lab_api))


def test_files_are_written_into_the_working_directory_and_readable():
    files = {"marks.csv": "name,mark\nAsha,91\nBilal,78\n", "logo.bin": {"encoding": "base64", "content": base64.b64encode(b"\x00\x01\x02").decode()}}
    r = run("print(open('marks.csv').read().count('\\n')); print(len(open('logo.bin','rb').read()))", files=files)
    assert r.status == "ok" and r.stdout.split() == ["3", "3"]


def test_unsafe_file_names_are_ignored():
    r = run("import os; print(sorted(os.listdir('.')))", files={"../evil": "x", "/etc/x": "y", ".hidden": "z", "ok.txt": "fine"})
    assert r.stdout.strip() == "['ok.txt']"


def test_probes_are_evaluated_after_the_program_and_bounded():
    tests = [
        {"test_order": 1, "points": 1, "is_hidden": False, "definition": {"description": "total is 60", "expr": "total", "expected": 60}},
        {"test_order": 2, "points": 1, "is_hidden": False, "definition": {"description": "squares", "expr": "[x*x for x in nums]", "expected": [1, 4, 9]}},
        {"test_order": 3, "points": 1, "is_hidden": True, "definition": {"description": "has key", "expr": "'a' in d and d['a'] == 1.0", "truthy": True}},
        {"test_order": 4, "points": 1, "is_hidden": True, "definition": {"description": "undefined", "expr": "missing_name", "truthy": True}},
        {"test_order": 5, "points": 1, "is_hidden": True, "definition": {"description": "big list is cut", "expr": "list(range(1000))", "expected": list(range(50))}},
    ]
    r = run("nums = [1, 2, 3]\ntotal = 60\nd = {'a': 1}\nprint('x')\n", tests)
    assert r.probes["total"] == {"ok": True, "value": 60}
    assert r.probes["missing_name"]["ok"] is False and "NameError" in r.probes["missing_name"]["error"]
    res = evaluate(tests, r, 100)
    assert [c["passed"] for c in res["criteria"]] == [True, True, True, False, True]


def test_probes_are_skipped_when_the_program_raised():
    tests = [{"test_order": 1, "points": 1, "is_hidden": False, "definition": {"description": "x", "expr": "x", "expected": 1}}]
    r = run("x = 1\nraise ValueError('boom')\n", tests)
    assert r.error["type"] == "ValueError" and r.probes["x"]["ok"] is False
    assert evaluate(tests, r, 100)["status"] == "failed"


def test_numpy_and_pandas_values_are_reported_as_plain_numbers():
    pytest.importorskip("numpy")
    tests = [{"test_order": 1, "points": 1, "is_hidden": False, "definition": {"description": "mean", "expr": "float(scores.mean())", "expected": 80.0}},
             {"test_order": 2, "points": 1, "is_hidden": False, "definition": {"description": "shape", "expr": "list(df.shape)", "expected": [2, 2]}},
             {"test_order": 3, "points": 1, "is_hidden": False, "definition": {"description": "raw numpy", "expr": "scores.max()", "expected": 90}}]
    r = run("import numpy as np, pandas as pd\nscores = np.array([70, 90])\ndf = pd.DataFrame({'a': [1, 2], 'b': [3, 4]})\nprint(scores.mean())\n", tests, timeout=30)
    assert r.status == "ok", r
    assert all(c["passed"] for c in evaluate(tests, r, 100)["criteria"]), r.probes


@pytest.mark.parametrize("defn,stdout,ok", [
    ({"stdout_contains": "Hello, Aarav"}, "Hello, Aarav! Welcome\n", True),
    ({"stdout_contains": "hello", "ignore_case": True}, "HELLO there\n", True),
    ({"stdout_contains": "bye"}, "hello\n", False),
    ({"stdout_regex": r"^Total: \d+$"}, "x\nTotal: 60\n", True),
    ({"stdout_regex": r"^Total: \d+$"}, "Total: sixty\n", False),
    ({"stdout_min_lines": 3}, "a\n\nb\nc\n", True),
    ({"stdout_min_lines": 3}, "a\nb\n", False),
    ({"expected_stdout_lines": ["a", "b"]}, " a \nb\n\n", True),
    ({"expected_stdout_lines": ["a", "b"]}, "a\n", False),
])
def test_stdout_check_kinds(defn, stdout, ok):
    assert check(defn, RunResult("ok", stdout=stdout)) is ok


def test_variable_type_check():
    r = RunResult("ok", vars={"age": {"type": "int", "value": 17}, "height": {"type": "float", "value": 1.6}})
    assert check({"check": "variable_type", "name": "age", "type": "int"}, r)
    assert not check({"check": "variable_type", "name": "height", "type": "int"}, r)
    assert check({"check": "variable_equals", "name": "height", "value": 1.6000001}, r)


# ---------------- labmock
def test_weather_books_and_errors_are_deterministic():
    s1, w1 = labmock.call("GET", "/v1/weather", params={"city": "Pune"})
    s2, w2 = labmock.call("GET", "/v1/weather", params={"city": "pune"})
    assert s1 == 200 and w1 == w2 and set(w1) >= {"city", "temperature_c", "condition", "humidity"}
    assert labmock.call("GET", "/v1/weather", params={"city": "Atlantis"})[0] == 404
    assert labmock.call("GET", "/v1/weather")[0] == 400
    assert labmock.call("GET", "/v1/books", params={"author": "Asha Rao"})[1]["count"] == 2
    assert labmock.call("GET", "/v1/books/3")[1]["title"] == "The Thinking Machine"
    assert labmock.call("GET", "/v1/nothing")[0] == 404


def test_secure_endpoint_teaches_header_over_url():
    assert labmock.call("GET", "/v1/secure/profile")[0] == 401
    assert labmock.call("GET", "/v1/secure/profile", params={"api_key": labmock.TEST_KEY})[0] == 401
    assert "URL" in labmock.call("GET", "/v1/secure/profile", params={"api_key": labmock.TEST_KEY})[1]["error"]
    assert labmock.call("GET", "/v1/secure/profile", headers={"Authorization": f"Bearer {labmock.TEST_KEY}"})[0] == 200


def test_flaky_endpoint_fails_twice_then_succeeds():
    codes = [labmock.call("GET", "/v1/flaky", params={"id": "t1"})[0] for _ in range(4)]
    assert codes == [503, 503, 200, 503]


def test_chat_sentiment_entities_embeddings():
    s, c = labmock.call("POST", "/v1/chat", json={"messages": [{"role": "user", "content": "Summarise this: The cat sat on the mat. It was warm."}]})
    assert s == 200 and c["choices"][0]["message"]["content"].startswith("Summary: The cat sat on the mat")
    assert labmock.call("POST", "/v1/chat", json={"messages": "nope"})[0] == 400
    tool = labmock.call("POST", "/v1/chat", json={"messages": [{"role": "user", "content": "What is 12 * 7?"}], "tools": [{"name": "calculator", "description": "does math"}]})[1]
    assert tool["choices"][0]["message"]["tool_calls"][0]["name"] == "calculator"
    assert labmock.call("POST", "/v1/sentiment", json={"text": "The food was great and the staff were friendly"})[1]["label"] == "positive"
    assert labmock.call("POST", "/v1/sentiment", json={"text": "Terrible, slow and rude"})[1]["label"] == "negative"
    ents = labmock.call("POST", "/v1/entities", json={"text": "Asha Rao moved from Pune to London to work at NeuroMind."})[1]["entities"]
    assert {(e["text"], e["type"]) for e in ents} >= {("Asha Rao", "PERSON"), ("Pune", "PLACE"), ("London", "PLACE")}
    e = labmock.call("POST", "/v1/embeddings", json={"input": ["How many vacation days do I get?", "What is the annual leave policy?", "The dog chased the cat"]})[1]["data"]
    v = [x["embedding"] for x in e]
    assert labmock.cosine(v[0], v[1]) > labmock.cosine(v[0], v[2]) and len(v[0]) == 64


def test_vision_ocr_and_helpers():
    assert labmock.call("POST", "/v1/ocr", json={"image": "receipt.png"})[1]["text"].startswith("NEUROMART")
    assert labmock.call("POST", "/v1/vision/classify", json={"image": "cat.jpg"})[1]["labels"][0]["label"] == "cat"
    assert labmock.call("POST", "/v1/vision/ask", json={"image": "cat.jpg", "question": "What do you see?"})[1]["related_to_image"] is True
    assert labmock.call("POST", "/v1/vision/ask", json={"image": "cat.jpg", "question": "Who won the 1998 world cup?"})[1]["related_to_image"] is False
    assert labmock.call("POST", "/v1/ocr", json={"image": "unknown.png"})[0] == 404
    toks = labmock.tokenize("Photosynthesis is amazing")
    assert [t["token"] for t in toks][:3] == ["Phot", "##osyn", "##thes"] and all(isinstance(t["id"], int) for t in toks)
    idx = labmock.VectorIndex()
    for i, s in enumerate(["annual leave policy", "python coding course", "dog and cat"]):
        idx.add(str(i), labmock.embed(s))
    assert idx.query(labmock.embed("vacation days"), k=1)[0]["id"] == "0"
    assert len(labmock.chunk_text("word " * 200, size=100, overlap=20)) > 5


def test_requests_integration_through_the_harness_blocks_the_internet_and_serves_the_lab_host():
    pytest.importorskip("requests")
    code = ("import requests\n"
            "r = requests.get('https://api.neuromind.lab/v1/weather', params={'city': 'Pune'})\n"
            "print(r.status_code, r.json()['city'])\n"
            "try:\n    requests.get('https://example.com', timeout=2)\n    print('internet reachable')\nexcept requests.ConnectionError as e:\n    print('blocked')\n"
            "r2 = requests.post('https://api.neuromind.lab/v1/chat', json={'messages': [{'role': 'user', 'content': 'hi'}]})\n"
            "print(r2.json()['choices'][0]['message']['content'][:11])\n")
    r = run(code, timeout=30, lab_api=True)
    assert r.status == "ok", r
    assert r.stdout.splitlines() == ["200 Pune", "blocked", "Mock answer"]


def test_without_the_flag_requests_never_reaches_the_simulator():
    pytest.importorskip("requests")
    r = run("import requests\ntry:\n    requests.get('https://api.neuromind.lab/v1/weather?city=Pune', timeout=2)\n    print('served')\nexcept Exception as e:\n    print(type(e).__name__)\n", timeout=30, lab_api=False)
    assert r.stdout.strip() != "served"


def test_browser_runtime_ships_the_same_evaluator_and_simulator():
    """The page's quick check must agree with the server: the copied modules are byte-identical."""
    from pathlib import Path
    root = Path(__file__).resolve().parents[2]
    assert (root / "frontend/public/py/nm_evaluate.py").read_text() == (root / "grader/grader_service/evaluate.py").read_text()
    assert (root / "frontend/public/py/labmock.py").read_text() == (root / "grader/sandbox/labmock.py").read_text()


def test_quickcheck_shim_matches_the_server_evaluation():
    """nm_quickcheck runs in CPython too: same verdicts as the harness path for a visible check set."""
    import importlib.util
    import sys
    from pathlib import Path
    root = Path(__file__).resolve().parents[2] / "frontend" / "public" / "py"
    sys.path.insert(0, str(root))
    try:
        spec = importlib.util.spec_from_file_location("nm_quickcheck", root / "nm_quickcheck.py")
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        cwd = __import__("os").getcwd()
        try:
            tests = [{"test_order": 1, "label": "Prints", "definition": {"match": "non_empty"}}, {"test_order": 2, "label": "total", "definition": {"expr": "total", "expected": 60}},
                     {"test_order": 3, "label": "file", "definition": {"expr": "open('m.csv').read().count(',')", "expected": 1}}]
            res = json.loads(mod.quick_check("total = 12 * 5\nprint(total)\n", json.dumps(tests), json.dumps({"m.csv": "a,b\n"})))
            assert res["status"] == "passed" and [c["passed"] for c in res["criteria"]] == [True, True, True] and res["stdout"].strip() == "60"
            res = json.loads(mod.quick_check("total = 1\nprint(1/0)\n", json.dumps(tests), "{}"))
            assert res["status"] == "failed" and res["error"]["type"] == "ZeroDivisionError" and res["error"]["line"] == 2
        finally:
            __import__("os").chdir(cwd)
    finally:
        sys.path.remove(str(root))
