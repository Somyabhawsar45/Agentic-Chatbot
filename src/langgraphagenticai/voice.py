"""
Voice input: the mic in the chat box records a voice note, and Groq's hosted Whisper model turns it
into the message text. The audio is sent to Groq for transcription only and is not stored by Netra.
"""
WHISPER_MODEL = "whisper-large-v3-turbo"
MAX_AUDIO_BYTES = 20 * 1024 * 1024          # well under Groq's upload limit


class VoiceError(ValueError):
    """A problem the user can fix (empty or too-long recording). Safe to show as-is."""


def transcribe(audio_bytes: bytes, api_keys: list, filename: str = "voice.wav", client_factory=None) -> str:
    """
    Text of a recording. Tries each key in turn if one is rate-limited or rejected.
    `client_factory(api_key)` can be injected for tests (default: groq.Groq).
    """
    if not audio_bytes:
        raise VoiceError("No audio was recorded. Hold the mic button and speak, then send.")
    if len(audio_bytes) > MAX_AUDIO_BYTES:
        raise VoiceError("That recording is too long. Please keep voice notes under a few minutes.")
    keys = [k for k in dict.fromkeys(api_keys or []) if k]
    if not keys:
        raise VoiceError("Voice input needs a Groq API key (add one in ⚙ Settings).")

    import groq
    if client_factory is None:
        client_factory = lambda key: groq.Groq(api_key=key, max_retries=2)   # noqa: E731

    last_error = None
    for key in keys:
        try:
            result = client_factory(key).audio.transcriptions.create(
                file=(filename or "voice.wav", audio_bytes), model=WHISPER_MODEL, temperature=0,
            )
        except (groq.RateLimitError, groq.AuthenticationError) as e:
            last_error = e          # try the next key
            continue
        text = (getattr(result, "text", None) or "").strip()
        if not text:
            raise VoiceError("I couldn't hear anything in that recording. Try again a little closer to the mic.")
        return text
    raise last_error


def combine(typed: str, spoken: str) -> str:
    """Typed text and a voice note sent together become one message."""
    typed = (typed or "").strip()
    return f"{typed}\n\n{spoken}" if typed else spoken
