# Deploying MedicTime

## Backend on Render

Use `render.yaml` or create a Python web service with:

- Build command: `pip install -r backend/requirements.txt`
- Start command: `uvicorn app.main:app --app-dir backend --host 0.0.0.0 --port $PORT`

Recommended environment variables:

```env
HF_TOKEN=your_huggingface_token
HF_MODEL=meta-llama/Llama-3.2-1B-Instruct
WHISPER_MODEL=tiny
ALLOWED_ORIGINS=https://your-pages-site.pages.dev
```

## Frontend on Cloudflare Pages

Deploy the `frontend/` directory with no build command.

Set `frontend/config.js` to your Render backend URL.

## Free-tier advice

Do not deploy these local-only assets on free hosting:

- `kokoro-v1.0.onnx`
- `voices-v1.0.bin`
- `medical_rag_store_v2/`

Use browser speech synthesis for voice replies and keep server inference lightweight.
