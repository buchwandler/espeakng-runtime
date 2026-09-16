from espeakng_runtime._text import split_best_effort_clauses


def test_split_best_effort_clauses() -> None:
    assert split_best_effort_clauses("Hello, world!") == [
        ("Hello", ",", False),
        (" world", "!", True),
    ]


def test_punctuation_clusters_are_single_clauses() -> None:
    assert split_best_effort_clauses("Hello?!") == [("Hello", "?!", True)]
    assert split_best_effort_clauses("Hello...") == [("Hello", "...", True)]
