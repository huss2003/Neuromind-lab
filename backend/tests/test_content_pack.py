import copy
import json
from pathlib import Path

import pytest

from app.content_pack import PackError, build_rows, check_collection, check_pack, uid

PACKS = sorted((Path(__file__).resolve().parents[2] / "content" / "lectures").glob("*.json"))
COURSE, MODULE = "c-1", "m-1"


def load(path: Path) -> dict:
    return json.loads(path.read_text())


def fake_tests(pack) -> dict:
    return {t.key: {"kind": "stdout_equals", "expected": "x"} for t in pack.lab.tests}


def valid() -> dict:
    return load(PACKS[0])


def errors_for(mutate) -> list[str]:
    data = valid()
    mutate(data)
    pack, errs = check_pack(data)
    assert pack is None
    return errs


def test_committed_packs_are_valid_and_numbered_once():
    assert len(PACKS) >= 3
    packs = []
    for p in PACKS:
        pack, errs = check_pack(load(p))
        assert errs == [], f"{p.name}: {errs}"
        packs.append(pack)
    assert check_collection(packs) == []


def test_packs_never_contain_hidden_test_definitions():
    for p in PACKS:
        text = p.read_text()
        assert '"definition"' not in text and "expected_output_hash" not in text
        assert "correct_option" in text  # answers to questions live in the pack; hidden lab tests do not


def test_rows_are_deterministic_and_link_up():
    pack, _ = check_pack(valid())
    a = build_rows(pack, fake_tests(pack), course_id=COURSE, module_id=MODULE)
    b = build_rows(pack, fake_tests(pack), course_id=COURSE, module_id=MODULE)
    assert a == b
    lecture_id = a["lectures"][0]["id"]
    assert lecture_id == uid(f"lecture{pack.lecture_number}")
    seg_ids = {s["id"] for s in a["lecture_segments"]}
    assert len(seg_ids) == len(pack.segments)
    assert {t["remediation_segment_id"] for t in a["exercise_tests"]} <= seg_ids
    assert {s["checkpoint_id"] for s in a["lecture_segments"] if s["checkpoint_id"]} == {c["id"] for c in a["lecture_checkpoints"]}
    assert all(s["exercise_id"] == a["lecture_exercises"][0]["id"] for s in a["lecture_segments"] if s["segment_type"] == "exercise")
    assert sum(t["is_hidden"] for t in a["exercise_tests"]) >= 1


def test_draft_by_default_and_publish_flag():
    pack, _ = check_pack(valid())
    draft = build_rows(pack, fake_tests(pack), course_id=COURSE, module_id=MODULE)
    live = build_rows(pack, fake_tests(pack), course_id=COURSE, module_id=MODULE, publish=True)
    assert draft["lectures"][0]["status"] == "draft" and draft["lectures"][0]["published_at"] is None
    assert live["lectures"][0]["status"] == "published" and live["lectures"][0]["published_at"]
    for table in ("mcq_questions", "lecture_exercises"):
        assert {r["status"] for r in draft[table]} == {"draft"}
        assert {r["status"] for r in live[table]} == {"published"}


def test_prerequisite_ids_can_be_overridden():
    pack, _ = check_pack(valid())
    rows = build_rows(pack, fake_tests(pack), course_id=COURSE, module_id=MODULE, prerequisite_ids={pack.prerequisites[0]: "fixed-id"})
    assert rows["lectures"][0]["prerequisites"] == ["fixed-id"]


def test_missing_hidden_definitions_are_reported_by_key():
    pack, _ = check_pack(valid())
    tests = fake_tests(pack)
    dropped = next(iter(tests))
    del tests[dropped]
    with pytest.raises(PackError, match=dropped):
        build_rows(pack, tests, course_id=COURSE, module_id=MODULE)


def test_exit_check_defaults_to_full_marks_threshold():
    pack, _ = check_pack(valid())
    rows = build_rows(pack, fake_tests(pack), course_id=COURSE, module_id=MODULE)
    by_type = {c["checkpoint_type"]: c["pass_threshold"] for c in rows["lecture_checkpoints"]}
    assert by_type["exit_check"] == 100 and by_type["mcq"] is None


def test_wrong_correct_option_is_rejected():
    errs = errors_for(lambda d: d["checkpoints"][0]["question"].update(correct_option_id="z"))
    assert any("correct_option_id" in e for e in errs)


def test_duplicate_option_text_is_rejected():
    def mutate(d):
        opts = d["checkpoints"][0]["question"]["options"]
        opts[1]["text"] = opts[0]["text"]

    assert any("same text" in e for e in errors_for(mutate))


def test_unknown_fields_are_rejected():
    assert errors_for(lambda d: d.update(surprise=1))


def test_segment_must_reference_a_known_checkpoint():
    def mutate(d):
        next(s for s in d["segments"] if s["type"] == "checkpoint")["checkpoint"] = "nope"

    assert any("unknown checkpoint" in e for e in errors_for(mutate))


def test_checkpoint_type_must_match_segment_type():
    def mutate(d):
        d["checkpoints"][-1]["type"] = "mcq"

    assert any("is type" in e for e in errors_for(mutate))


def test_every_checkpoint_must_be_used():
    def mutate(d):
        d["segments"] = [s for s in d["segments"] if s["key"] != "check-1"]

    assert any("checkpoint" in e for e in errors_for(mutate))


def test_exit_check_must_be_last():
    def mutate(d):
        d["segments"].reverse()

    assert errors_for(mutate)


def test_lab_needs_a_hidden_test():
    def mutate(d):
        for t in d["lab"]["tests"]:
            t["hidden"] = False

    assert any("hidden" in e for e in errors_for(mutate))


def test_remediation_must_point_before_the_lab():
    def mutate(d):
        d["lab"]["tests"][0]["remediation_segment"] = "exit"

    assert any("before the lab" in e for e in errors_for(mutate))


def test_prerequisites_must_be_earlier_lectures():
    def mutate(d):
        d["prerequisites"] = [d["lecture_number"]]

    assert any("prerequisite" in e for e in errors_for(mutate))


def test_reading_needs_a_body():
    def mutate(d):
        next(s for s in d["segments"] if s["type"] == "reading")["body"] = ""

    assert any("body" in e for e in errors_for(mutate))


def test_duplicate_lecture_numbers_across_packs():
    pack, _ = check_pack(valid())
    other = copy.deepcopy(pack)
    assert check_collection([pack, other]) == [f"lecture number {pack.lecture_number} appears 2 times"]


def test_non_object_input_does_not_crash():
    pack, errs = check_pack([])
    assert pack is None and errs
