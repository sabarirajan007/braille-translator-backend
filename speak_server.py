"""HTTP speech endpoint for the Braille translator project."""

import asyncio
import io
import logging
import os

import edge_tts
from deep_translator import GoogleTranslator, MyMemoryTranslator
from flask import Flask, jsonify, request, send_file

app = Flask(__name__)
app.logger.setLevel(logging.INFO)
app.config["MAX_CONTENT_LENGTH"] = 16 * 1024

LANGUAGE_VOICES = {
    "en": "en-US-AriaNeural",
    "hi": "hi-IN-SwaraNeural",
    "ta": "ta-IN-PallaviNeural",
    "te": "te-IN-ShrutiNeural",
    "kn": "kn-IN-SapnaNeural",
    "ml": "ml-IN-SobhanaNeural",
    "bn": "bn-IN-TanishaaNeural",
    "mr": "mr-IN-AarohiNeural",
    "gu": "gu-IN-DhwaniNeural",
    "ur": "ur-IN-GulNeural",
}

MYMEMORY_TARGETS = {
    "en": "english us",
    "hi": "hindi",
    "ta": "tamil india",
    "te": "telugu",
    "kn": "kannada",
    "ml": "malayalam",
    "bn": "bengali",
    "mr": "marathi",
    "gu": "gujarati",
    "ur": "urdu",
}


async def synthesize(text: str, voice: str) -> bytes:
    audio = io.BytesIO()
    communicate = edge_tts.Communicate(text, voice)
    async for chunk in communicate.stream():
        if chunk["type"] == "audio":
            audio.write(chunk["data"])
    return audio.getvalue()


def translate_text(text: str, language: str) -> str:
    """Try MyMemory first, then Google's unofficial endpoint as a fallback."""
    errors = []
    translator_factories = (
        lambda: MyMemoryTranslator(source="auto", target=MYMEMORY_TARGETS[language]),
        lambda: GoogleTranslator(source="auto", target=language),
    )
    for make_translator in translator_factories:
        try:
            translated = make_translator().translate(text)
            if translated:
                return translated
        except Exception as error:
            errors.append(error)
    cause = errors[-1] if errors else None
    raise RuntimeError("All translation providers failed") from cause


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
    voice = LANGUAGE_VOICES.get(language)
    if voice is None:
        return jsonify({"error": f"Unsupported language: {language}"}), 400

    try:
        translated = translate_text(text.strip(), language)
        if not translated:
            return jsonify({"error": "Translation returned no text."}), 502
        audio_bytes = asyncio.run(synthesize(translated, voice))
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
        return jsonify({"error": "Translation or speech generation failed."}), 502


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", "5000")))
