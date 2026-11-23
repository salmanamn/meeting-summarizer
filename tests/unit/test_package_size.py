"""The package gate (scripts/package_size.py, D37): what must never ship, and the size budget."""

from package_size import canonical, gate, installed


def test_distribution_names_come_from_dist_info_folders(tmp_path):
    for folder in ("onnxruntime_gpu-1.23.0.dist-info", "Faster_Whisper-1.2.1.dist-info", "faster_whisper", "x.txt"):
        (tmp_path / folder).mkdir()
    assert installed(tmp_path) == {"onnxruntime-gpu", "faster-whisper"}
    assert canonical("Piper_TTS") == canonical("piper.tts") == "piper-tts"


def test_a_forbidden_distribution_fails_whatever_its_spelling():
    assert gate(10, {"torch", "faster-whisper"}, 200, ["Torch", "piper_tts"]) == ["torch is in the package"]
    assert gate(10, {"faster-whisper"}, 200, ["torch"]) == []


def test_the_zip_budget():
    assert gate(200_000_000, set(), 200, []) == []
    assert gate(200_000_001, set(), 200, []) == ["the zip is 200 MB, over the 200 MB budget"]
    assert gate(10**10, set(), None, []) == []  # no budget given: only reported
