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

Supported language codes: `en`, `hi`, `ta`, `te`. Text is limited to 1000 characters. `GET /` is a basic health check.

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

In Render, add `SARVAM_API_KEY` under the service's Environment settings, using the API key from your Sarvam dashboard. Save the change so Render redeploys/restarts the service. Do not put this key in the ESP32 code or commit it to GitHub.

## ESP32

Set the sketch URL to `https://YOUR-SERVICE.onrender.com/speak`. The request must be HTTPS, use `Content-Type: application/json`, and send the `text` and `lang` fields. The response is raw MP3 audio bytes. The sketch must read the HTTP response body as binary and pass those bytes to its audio playback component. Use proper certificate validation where possible; `setInsecure()` disables server certificate verification.

This service assumes incoming text is English. English output is passed directly to Edge TTS. Hindi, Tamil, and Telugu are translated with Sarvam's `mayura:v1` API in modern colloquial mode, then sent to Edge TTS. Set `SARVAM_API_KEY` as a secret environment variable in Render before using those languages. The Sarvam key stays on the server and must not be placed in the ESP32 sketch. Sarvam supports the three target languages; its API limits and pricing are set by Sarvam.
