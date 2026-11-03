"""
voice.py — 해설(선생님) 목소리 한 가지로 통일

1) assets/audio/narrator/<md5>.mp3 에 미리 만들어 둔 소리가 있으면 그걸 재생 (tools/pregen_audio.py)
2) 없으면 그 자리에서 TTS로 만들어 재생 (edge-tts, 네트워크 필요)
3) 둘 다 안 되면 None → 앱은 글자만 보여 줘요
Wacky는 목소리 없이 말풍선·표정만 써요.
"""
from __future__ import annotations

import hashlib
from pathlib import Path

import streamlit as st

from . import speech

DIR = Path(__file__).resolve().parent.parent / "assets" / "audio" / "narrator"


def audio_name(text: str) -> str:
    return hashlib.md5(text.strip().encode("utf-8")).hexdigest()[:16] + ".mp3"


def pregenerated(text: str) -> Path | None:
    p = DIR / audio_name(text)
    return p if p.exists() else None


@st.cache_data(show_spinner=False, max_entries=300)
def _live(text: str) -> bytes | None:
    return speech.synthesize(text, "narrator")


def get(text: str) -> bytes | str | None:
    """st.audio에 넣을 수 있는 값(경로 또는 bytes) 또는 None."""
    p = pregenerated(text)
    if p:
        return str(p)
    return _live(text)
