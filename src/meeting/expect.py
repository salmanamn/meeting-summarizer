"""How close a transcript came to the script it was spoken from: word error rate (D7). The summary is scored by
`meeting.evaluate` (D26); this module only measures the words."""

from meeting.words import normalize

MAX_WER = 0.15  # clean synthetic speech: a working transcriber stays well below this

__all__ = ["MAX_WER", "edit_distance", "normalize", "wer"]


def edit_distance(ref: list[str], hyp: list[str]) -> int:
    previous = list(range(len(hyp) + 1))
    for i, r in enumerate(ref, start=1):
        current = [i]
        for j, h in enumerate(hyp, start=1):
            current.append(min(previous[j] + 1, current[j - 1] + 1, previous[j - 1] + (r != h)))
        previous = current
    return previous[-1]


def wer(reference: str, hypothesis: str) -> float:
    ref, hyp = normalize(reference), normalize(hypothesis)
    return edit_distance(ref, hyp) / len(ref) if ref else float(bool(hyp))
