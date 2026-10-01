# Deploying the security fixes

Both `main:app` and `app.main:app --app-dir backend` now use the maintained backend. The compatibility entry point serves the current frontend and uses browser speech synthesis; the old Kokoro/base64 voice response is retired. Install `backend/requirements.txt` for either entry point.

## Required deployment configuration

- Set `UPSTASH_REDIS_REST_URL` (HTTPS) and `UPSTASH_REDIS_REST_TOKEN` on the API server. All replicas must use the same Redis database. These are server secrets and must never be shipped in frontend code. If storage is absent or unavailable, expensive API routes return 503; health and static files remain available.
- Use `APP_ENV=production` on hosted instances. `APP_ENV=development` explicitly enables in-memory quotas for local use only.
- Set `DEPLOYED_API_ORIGIN` in `frontend/config.js` to the HTTPS backend origin when hosting the frontend separately. For the bundled frontend it defaults to the same origin. Query parameters and localStorage cannot override this. Configure `ALLOWED_ORIGINS` to the actual frontend origins.
- Keep `HF_TOKEN` in server environment variables. If the old root-static-file server was exposed, revoke its old Hugging Face token and check provider usage before deploying a replacement.

## Demo limits

The server permits 6 requests/minute and 30/day per peer IP, and 100/day globally using atomic Redis counters. The daily period starts with the first request. At most two workloads run per server process. All replicas share the global daily limit, but their concurrency limits are local. Failed processing consumes quota too. No client forwarding header is used by this middleware; configure Uvicorn trusted proxies narrowly, or disable proxy headers. Behind an unconfigured proxy, users may share one IP quota, which is intentionally conservative.

Request bodies are limited to 16 MiB including multipart overhead; audio payloads also honor MAX_UPLOAD_MB. Uploads time out after 30 seconds. Audio decoding uses only the first 90 seconds and a 30-second decoder timeout; HF calls time out after 60 seconds. Chat text is capped at 4,000 characters; generated transcripts sent to the LLM at 12,000. Configure provider-side spend limits as an additional account safeguard. These anonymous demo limits do not supply clinical user authentication; use an authenticated deployment before accepting real patient data.

Only four reviewed frontend assets are served. No project-root static mount remains. Backend errors expose a reference ID, not exception details or input text. Temporary upload files are removed on failed reads, oversize rejection, and after processing.

## Verification

`pytest -q tests/test_security.py` uses FastAPI/httpx/pytest/python-multipart/python-dotenv and stubs the model integrations. `node --test tests/config.test.cjs` verifies link-based redirects are ignored. Tests use synthetic input and never contact the model provider.
