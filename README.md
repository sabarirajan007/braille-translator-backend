# Braille translator speech backend

Flask service that translates English text to the requested language and returns an MP3 from Microsoft Edge text-to-speech.

## Run locally

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python speak_server.py
```

The service listens on `http://127.0.0.1:5000`.

## API

`POST /speak` accepts JSON and responds with `audio/mpeg`:

```json
{"text":"hello","lang":"ta"}
```

Supported language codes: `en`, `hi`, `ta`, `te`, `kn`, `ml`, `bn`, `mr`, `gu`, `ur`. Text is limited to 1000 characters. `GET /` is a basic health check.

Example request from PowerShell:

```powershell
Invoke-WebRequest -Method Post -Uri http://127.0.0.1:5000/speak `
  -ContentType 'application/json' `
  -Body '{"text":"hello","lang":"ta"}' `
  -OutFile test.mp3
```

## Deploy on Render

Push these files to a GitHub repository, then create a Render Web Service from that repository with:

- Runtime: Python
- Build command: `pip install -r requirements.txt`
- Start command: `gunicorn speak_server:app`

Render supplies the `PORT` environment variable; Gunicorn binds to it automatically. After deployment, test `https://YOUR-SERVICE.onrender.com/speak` using the JSON request above. Free instances may take time to wake after inactivity.

## ESP32

Set the sketch URL to `https://YOUR-SERVICE.onrender.com/speak`. The request must be HTTPS, use `Content-Type: application/json`, and send the `text` and `lang` fields. The response is raw MP3 audio bytes. The sketch must read the HTTP response body as binary and pass those bytes to its audio playback component. Use proper certificate validation where possible; `setInsecure()` disables server certificate verification.

This service assumes incoming text is English. It tries MyMemory first for translation and falls back to Google Translate through `deep-translator`; it then calls Edge TTS. Both translation providers and Edge TTS must be reachable from the deployed instance. These library integrations are unofficial and can be rate-limited or changed by their providers.
