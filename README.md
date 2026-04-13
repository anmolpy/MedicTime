# MedicTime

MedicTime is structured for split deployment:

- `frontend/` is a static client intended for Vercel or Cloudflare Pages
- `backend/` is a FastAPI API intended for Render

## Deployment plan

### Frontend

- deploy the `frontend/` directory to Vercel
- point `frontend/config.js` at the backend URL after Render is live
- keep the frontend static so there are no oversized server bundles

### Backend

- deploy the `backend/` directory to Render using `render.yaml`
- use environment variables for `HF_TOKEN`, `HF_MODEL`, `WHISPER_MODEL`, `ALLOWED_ORIGINS`, and `MAX_UPLOAD_MB`
- keep large local-only assets out of the deployment

## Large-file constraints

These should not be part of the hosted deployment path:

- `kokoro-v1.0.onnx`
- `voices-v1.0.bin`
- `medical_rag_store_v2/`
- `rag.index`

## Local run

Backend:

```bash
pip install -r backend/requirements.txt
uvicorn app.main:app --app-dir backend --reload
```

Frontend:

```bash
python -m http.server 3000 --directory frontend
```
