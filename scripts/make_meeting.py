"""Make a synthetic test meeting (D7): every line of eval/meetings/<ID>.json spoken by Piper, one LibriTTS-R voice
per participant, with a pause between turns, into one WAV file.

uv run python scripts/make_meeting.py M01 [M02 ...] [--seed N]     -> out/meetings/<ID>.wav

The voice model is CC BY 4.0 (LibriTTS-R); Piper itself is GPL and only used here, never in the app (D10).
Piper adds random variation to every line. ONNX Runtime's seed only takes effect for a session created after it is
set, so every meeting loads the voice afresh after setting the seed: same meeting + same seed = same file on this
machine, whatever else runs in the same call. Another seed gives the same script spoken slightly differently
(scripts/stt_modes.py uses that). The audio is regenerated, never committed.
"""

import argparse
import io
import json
import sys
import wave
from pathlib import Path

import onnxruntime
from piper import PiperVoice, SynthesisConfig

from meeting.settings import load

ROOT = Path(__file__).resolve().parents[1]
MEETINGS = ROOT / "eval" / "meetings"
OUT = ROOT / "out" / "meetings"
VOICE = "tts-en-libritts"
PAUSE_SECONDS = 0.7  # between turns: a gap the voice-activity filter sees as silence


def read_meeting(meeting_id: str) -> dict:
    return json.loads((MEETINGS / f"{meeting_id}.json").read_text(encoding="utf-8"))


def load_voice(models_dir: Path, seed: int) -> PiperVoice:
    directory = models_dir / VOICE
    models = sorted(directory.glob("*.onnx"))
    if len(models) != 1:
        raise SystemExit(f"{directory}: expected one .onnx file (run: uv run python scripts/fetch_models.py {VOICE})")
    onnxruntime.set_seed(seed)  # before the session exists, or it has no effect
    return PiperVoice.load(models[0])


def speak(voice: PiperVoice, text: str, speaker_id: int) -> bytes:
    """16-bit mono PCM frames of one line."""
    buffer = io.BytesIO()
    with wave.open(buffer, "wb") as wav_file:
        voice.synthesize_wav(text, wav_file, syn_config=SynthesisConfig(speaker_id=speaker_id))
    buffer.seek(0)
    with wave.open(buffer, "rb") as wav_file:
        return wav_file.readframes(wav_file.getnframes())


def render(meeting: dict, models_dir: Path, seed: int = 0) -> tuple[bytes, int]:
    """The whole meeting as PCM frames, and the sample rate."""
    voice = load_voice(models_dir, seed)
    rate = voice.config.sample_rate
    pause = b"\x00\x00" * int(PAUSE_SECONDS * rate)
    frames = bytearray(pause)
    for speaker, text in meeting["lines"]:
        frames += speak(voice, text, meeting["speakers"][speaker]) + pause
    return bytes(frames), rate


def write_wav(path: Path, frames: bytes, rate: int) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(path), "wb") as wav_file:
        wav_file.setnchannels(1)
        wav_file.setsampwidth(2)
        wav_file.setframerate(rate)
        wav_file.writeframes(frames)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("meetings", nargs="+", metavar="ID", help="meeting ids in eval/meetings/, e.g. M01")
    parser.add_argument("--seed", type=int, default=0, help="Piper's random variation (default 0)")
    args = parser.parse_args()
    missing = [m for m in args.meetings if not (MEETINGS / f"{m}.json").is_file()]
    if missing:
        parser.error(f"no eval/meetings/{missing[0]}.json")
    models_dir = load().models_dir
    for meeting_id in args.meetings:
        meeting = read_meeting(meeting_id)
        frames, rate = render(meeting, models_dir, args.seed)
        target = OUT / f"{meeting_id}.wav"
        write_wav(target, frames, rate)
        names = ", ".join(meeting["speakers"])
        seconds = len(frames) / 2 / rate
        print(f"{target.relative_to(ROOT)}: {len(meeting['lines'])} lines, {names}, {seconds:.1f} s at {rate} Hz")
    return 0


if __name__ == "__main__":
    sys.exit(main())
