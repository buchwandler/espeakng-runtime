from espeakng_runtime._text import split_best_effort_clauses


def test_split_best_effort_clauses() -> None:
    assert split_best_effort_clauses("Hello, world!") == [
        ("Hello", ",", False),
        (" world", "!", True),
    ]
