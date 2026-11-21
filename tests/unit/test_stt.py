import json
from types import SimpleNamespace

import pytest

from meeting.stt import WhisperTranscriber, sentences
from meeting.transcript import Segment


def word(start, end, text):
    return SimpleNamespace(start=start, end=end, word=text)


def test_words_are_regrouped_into_sentences_with_their_times():
    words = [
        word(0.4, 0.8, " Good"),
        word(0.8, 1.3, " morning."),
        word(1.6, 1.9, " Omar,"),
        word(1.9, 2.4, " can"),
        word(2.4, 2.6, " you?"),
        word(3.0, 3.5, " Sure!"),
        word(4.0, 4.4, " And"),  # no end mark: still a segment
        word(4.4, 4.9, " then"),
    ]
    assert sentences(words) == [
        Segment(0.4, 1.3, "Good morning."),
        Segment(1.6, 2.6, "Omar, can you?"),
        Segment(3.0, 3.5, "Sure!"),
        Segment(4.0, 4.9, "And then"),
    ]


def test_no_words_and_blank_words():
    assert sentences([]) == []
    assert sentences([word(0, 1, " ")]) == []


def test_missing_model_files_are_reported_before_anything_is_downloaded(tmp_path):
    (tmp_path / "model.bin").write_bytes(b"x")
    with pytest.raises(
        FileNotFoundError, match=r"missing config\.json, tokenizer\.json \(run scripts/fetch_models\.py\)"
    ):
        WhisperTranscriber(tmp_path)


def test_batched_mode_needs_alignment_heads(tmp_path):
    for name in ("model.bin", "tokenizer.json"):
        (tmp_path / name).write_bytes(b"x")
    (tmp_path / "config.json").write_text(json.dumps({"lang_ids": []}))
    with pytest.raises(ValueError, match="no alignment_heads"):
        WhisperTranscriber(tmp_path)
    with pytest.raises(ValueError, match="batched or sequential"):
        WhisperTranscriber(tmp_path, mode="fast")
