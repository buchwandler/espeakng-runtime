from espeakng_runtime._text import _validate_batch_texts, split_best_effort_clauses


def test_split_best_effort_clauses() -> None:
    assert split_best_effort_clauses("Hello, world!") == [
        ("Hello", ",", False),
        (" world", "!", True),
    ]


def test_punctuation_clusters_are_single_clauses() -> None:
    assert split_best_effort_clauses("Hello?!") == [("Hello", "?!", True)]
    assert split_best_effort_clauses("Hello...") == [("Hello", "...", True)]


def test_batch_texts_allow_embedded_line_breaks() -> None:
    """_validate_batch_texts accepts inputs with embedded line breaks."""
    values = ["One", "\n\nTwo", "Three\r\nFour"]
    assert _validate_batch_texts(values) == values


def test_batch_texts_passthrough_plain_inputs() -> None:
    """_validate_batch_texts returns plain inputs unchanged."""
    values = ["One", "Two", "Three"]
    assert _validate_batch_texts(values) == values
