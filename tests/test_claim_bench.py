"""The claim-support benchmark's construction: labels known from how each item was built. Offline."""

from __future__ import annotations

import random

from vera.bench.claims import MAX_OVERLAP, alter_number, build_items, flip_direction, items_hash, overlap

P1 = {"source_key": "R1", "id": "R1-P1", "kind": "fulltext", "locator": "sec. Results, para 4",
      "text": "In our experiments the interaction estimate becomes unstable across bootstrap refits when the "
              "correlation exceeds 0.9, while the residual stays near 1% of the output variance."}
P2 = {"source_key": "R1", "id": "R1-P2", "kind": "fulltext", "locator": "sec. Method, para 2",
      "text": "We fit the ensemble with a hundred trees and record the wall clock time of every run."}
P3 = {"source_key": "R2", "id": "R2-P1", "kind": "fulltext", "locator": "sec. Intro, para 1",
      "text": "Shapley values attribute a prediction to features by averaging marginal contributions over coalitions."}
CLAIM = "Interaction estimates become unstable under correlation above 0.9."
TITLES = {"R1": "TreeHFD", "R2": "Shapley attributions"}


def base(topic: str = "t-a") -> dict:
    return {"topic": topic, "run": f"scope-{topic}", "claim": CLAIM, "source_key": "R1", "title": "TreeHFD",
            "passage": P1, "passages": [P1, P2, P3], "titles": TITLES}  # fmt: skip


def test_a_direction_word_is_reversed_and_a_claim_without_one_is_left_alone() -> None:
    assert flip_direction("Effects are more stable than others.") == "Effects are less stable than others."
    assert flip_direction("Results were Higher at depth.") == "Results were Lower at depth."
    assert flip_direction("The paper describes an algorithm.") is None


def test_a_number_in_the_claim_is_changed_only_when_the_passage_holds_it() -> None:
    rng = random.Random(1)
    changed = alter_number(CLAIM, P1["text"], rng)
    assert changed is not None and "0.9" not in changed and changed.startswith("Interaction estimates")
    assert alter_number(CLAIM, "a passage without that figure", rng) is None
    assert alter_number("It appeared in 2019 and 2021.", "in 2019 and 2021", rng) is None  # years are left alone


def test_every_item_label_follows_from_its_construction() -> None:
    items = build_items([base("t-a")], dev_topic="t-b")
    kinds = {i.construction["kind"]: i for i in items}
    assert set(kinds) == {"supported", "other_paper", "other_passage", "reversed", "altered_number"}
    assert kinds["supported"].label is True and all(i.label is False for k, i in kinds.items() if k != "supported")
    supported = kinds["supported"].state
    assert "Interaction estimates become unstable" in supported and P1["text"] in supported
    assert P3["text"] in kinds["other_paper"].state and P2["text"] in kinds["other_passage"].state
    assert "stable under correlation" in kinds["reversed"].state.replace("unstable", "stable")  # the flipped claim
    assert P1["text"] in kinds["reversed"].state and P1["text"] in kinds["altered_number"].state
    assert {i.split for i in items} == {"test"} and all(i.task == "claim_support" for i in items)
    assert all(i.question.id == "lit.claim_supported" for i in items)


def test_a_negative_that_shares_many_words_with_the_claim_is_dropped() -> None:
    close = {**P3, "id": "R2-P9", "text": "Interaction estimates become unstable under correlation above 0.9 in the "
                                           "estimates we computed."}
    assert overlap(CLAIM, close["text"]) >= MAX_OVERLAP
    b = {**base(), "passages": [P1, P2, close]}
    kinds = {i.construction["kind"] for i in build_items([b], dev_topic="t-b")}
    assert "other_paper" not in kinds  # it might be supported after all


def test_the_split_is_by_topic_and_the_hash_covers_the_test_items_only() -> None:
    items = build_items([base("t-a"), base("t-b")], dev_topic="t-b")
    assert {i.construction["topic"] for i in items if i.split == "dev"} == {"t-b"}
    assert {i.construction["topic"] for i in items if i.split == "test"} == {"t-a"}
    test = [i for i in items if i.split == "test"]
    assert items_hash(test) == items_hash(list(reversed(test)))  # order does not matter
    again = [i for i in build_items([base("t-a"), base("t-b")], "t-b") if i.split == "test"]
    assert items_hash(test) == items_hash(again)
    assert items_hash(test) != items_hash(test[:-1])
