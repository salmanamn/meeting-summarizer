"""Word-level text helpers shared by grounding (summary.py), the long-meeting merge (summarize.py) and the
evaluation (evaluate.py). English only (D2), deterministic, no models."""

import re
import unicodedata

# Words that say nothing about what an item is: function words, and the words every meeting item is made of.
STOPWORDS = frozenset(
    """a an and are as at be been by can could did do does for from had has have he her his how i if in into is it
    its let let's me my no not of on or our she so that the their them then there these they this those to up us was
    we were what when where which who will with would you your yes ok okay also just about all any some one more
    should shall must may might need needs going get got make made team group meeting decide decided decision
    agree agreed agreement""".split()
)


def normalize(text: str) -> list[str]:
    """Words for scoring English: lower case, no punctuation, apostrophes kept inside words."""
    text = unicodedata.normalize("NFKC", text).casefold().replace("\u2019", "'")  # typographic apostrophe
    return re.findall(r"[a-z0-9]+(?:'[a-z]+)?", text)


def stem(word: str) -> str:
    """A light suffix strip, enough for 'icons'/'icon', 'approved'/'approve', 'testing'/'test'. Not a word, a key:
    'notes' and 'note' both become 'not'."""
    for suffix in ("ing", "ed", "s"):
        if word.endswith(suffix) and len(word) - len(suffix) >= 3:
            word = word[: -len(suffix)]
            break
    return word[:-1] if word.endswith("e") and len(word) > 3 else word


_ONES = "one two three four five six seven eight nine ten eleven twelve thirteen fourteen fifteen sixteen".split()
_ONES += "seventeen eighteen nineteen".split()
_ORDINALS = "first second third fourth fifth sixth seventh eighth ninth tenth eleventh twelfth thirteenth".split()
_ORDINALS += "fourteenth fifteenth sixteenth seventeenth eighteenth nineteenth".split()


def number_word(word: str) -> str:
    """'9th' -> 'ninth', '15' -> 'fifteen', '21st' -> 'twenty first': a model writes digits where Whisper wrote
    words, and the two must count as the same words (D29). Other words unchanged."""
    digits, suffix = word.rstrip("stndrh"), word[len(word.rstrip("stndrh")) :]
    if not digits.isdigit() or suffix not in ("", "st", "nd", "rd", "th") or not 1 <= int(digits) <= 31:
        return word
    n = int(digits)
    names = _ORDINALS if suffix else _ONES
    if n < 20:
        return names[n - 1]
    tens = "twenty" if n < 30 else "thirty"
    if n % 10 == 0:
        return "twentieth" if suffix and n == 20 else "thirtieth" if suffix else tens
    return f"{tens} {names[n % 10 - 1]}"


def content_words(text: str) -> set[str]:
    words = [part for w in normalize(text) for part in number_word(w).split()]
    return {stem(w) for w in words if w not in STOPWORDS}


def similarity(a: str, b: str) -> float:
    """Jaccard overlap of the two texts' content words (0 when either has none)."""
    x, y = content_words(a), content_words(b)
    return len(x & y) / len(x | y) if x and y else 0.0


def covers(reference: str, candidate: str) -> float:
    """Share of the reference's content words that the candidate contains (recall of the reference)."""
    ref = content_words(reference)
    return len(ref & content_words(candidate)) / len(ref) if ref else 0.0


def contains_phrase(text: str, phrase: str) -> bool:
    """The phrase's words occur in the text consecutively, in order (case and punctuation ignored)."""
    words = normalize(phrase)
    return bool(words) and f" {' '.join(words)} " in f" {' '.join(normalize(text))} "


TIME_WORDS = frozenset(
    """monday tuesday wednesday thursday friday saturday sunday today tomorrow tonight morning afternoon evening noon
    week weekend month year quarter january february march april may june july august september october november
    december first second third fourth fifth sixth seventh eighth ninth tenth eleventh twelfth thirteenth
    fourteenth fifteenth sixteenth seventeenth eighteenth nineteenth twentieth thirtieth""".split()
)


def deadline_in(text: str, phrase: str) -> str | None:
    """The first (then longest) run of the phrase's words that occurs in the text, in order, and names a time (a
    weekday, a month, "week", a number ...): what is left of a deadline once a model's comment is taken away.
    "Tuesday (no specific date provided)" -> "Tuesday"; "No specific due date mentioned" -> None."""
    words = normalize(phrase)
    shown = re.findall(r"[A-Za-z0-9]+(?:'[A-Za-z]+)?", unicodedata.normalize("NFKC", phrase).replace("\u2019", "'"))
    if len(shown) != len(words):  # letters outside ASCII: keep the lower-case words
        shown = words
    haystack = f" {' '.join(normalize(text))} "
    for start in range(len(words)):  # leftmost first: the deadline comes first, the comment after it
        for size in range(len(words) - start, 0, -1):
            run = words[start : start + size]
            timed = any(w in TIME_WORDS or w.isdigit() or w[:-2].isdigit() for w in run)
            if timed and f" {' '.join(run)} " in haystack:
                return " ".join(shown[start : start + size])
    return None
