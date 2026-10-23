"""HTTP speech endpoint for the Braille translator project."""

import io
import logging
import os

from flask import Flask, jsonify, request, send_file
import requests

app = Flask(__name__)
app.logger.setLevel(logging.INFO)
app.config["MAX_CONTENT_LENGTH"] = 16 * 1024

SARVAM_TARGETS = {
    "hi": "hi-IN",
    "ta": "ta-IN",
    "te": "te-IN",
}

SARVAM_TTS_LANGUAGES = {
    "en": "en-IN",
    "hi": "hi-IN",
    "ta": "ta-IN",
    "te": "te-IN",
}


def synthesize(text: str, language: str) -> bytes:
    """Generate MP3 audio through Sarvam's streaming text-to-speech API."""
    api_key = os.environ.get("SARVAM_API_KEY")
    if not api_key:
        raise RuntimeError("SARVAM_API_KEY is not configured")

    with requests.post(
        "https://api.sarvam.ai/text-to-speech/stream",
        headers={"api-subscription-key": api_key},
        json={
            "text": text,
            "model": "bulbul:v3",
            "language_code": SARVAM_TTS_LANGUAGES[language],
            "output_audio_codec": "mp3",
            "speech_sample_rate": 22050,
        },
        stream=True,
        timeout=(10, 60),
    ) as response:
        if not response.ok:
            app.logger.error(
                "Sarvam speech returned HTTP %s: %s",
                response.status_code,
                response.text[:500],
            )
            response.raise_for_status()
        return b"".join(response.iter_content(chunk_size=8192))


def translate_text(text: str, language: str) -> str:
    """Translate English text with Sarvam; English output needs no translation."""
    if language == "en":
        return text

    api_key = os.environ.get("SARVAM_API_KEY")
    if not api_key:
        raise RuntimeError("SARVAM_API_KEY is not configured")

    response = requests.post(
        "https://api.sarvam.ai/translate",
        headers={
            "api-subscription-key": api_key,
            "Content-Type": "application/json",
        },
        json={
            "input": text,
            "source_language_code": "en-IN",
            "target_language_code": SARVAM_TARGETS[language],
            "model": "mayura:v1",
            "mode": "modern-colloquial",
        },
        timeout=20,
    )
    if not response.ok:
        app.logger.error("Sarvam translation returned HTTP %s: %s", response.status_code, response.text[:500])
        response.raise_for_status()
    translated = response.json().get("translated_text")
    if not isinstance(translated, str) or not translated.strip():
        raise RuntimeError("Sarvam returned an empty translation")
    return translated.strip()


@app.get("/")
def health():
    return jsonify({"status": "ok", "service": "braille-translator-speech"})


@app.post("/speak")
def speak():
    body = request.get_json(silent=True)
    if not isinstance(body, dict):
        return jsonify({"error": "Send a JSON object with text and lang fields."}), 400

    text = body.get("text")
    language = body.get("lang", "en")
    if not isinstance(text, str) or not text.strip():
        return jsonify({"error": "text must be a non-empty string."}), 400
    if len(text) > 1000:
        return jsonify({"error": "text must be 1000 characters or fewer."}), 413
    if not isinstance(language, str):
        return jsonify({"error": "lang must be a language code such as ta or en."}), 400

    language = language.strip().lower().split("-")[0]
    if language not in SARVAM_TTS_LANGUAGES:
        return jsonify({"error": f"Unsupported language: {language}"}), 400
    if not os.environ.get("SARVAM_API_KEY"):
        return jsonify({"error": "Speech is not configured. Add SARVAM_API_KEY in the Render service environment."}), 503

    try:
        translated = translate_text(text.strip(), language)
        if not translated:
            return jsonify({"error": "Translation returned no text."}), 502
        audio_bytes = synthesize(translated, language)
        if not audio_bytes:
            return jsonify({"error": "Speech service returned no audio."}), 502
        return send_file(
            io.BytesIO(audio_bytes),
            mimetype="audio/mpeg",
            as_attachment=True,
            download_name="speech.mp3",
        )
    except Exception:
        app.logger.exception("Speech request failed")
        return jsonify({"error": "Translation or speech generation failed. Check the service logs for details."}), 502


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", "5000")))
