"""Bound anonymous demo workloads before parsing multipart bodies.

Production shares quotas through Redis REST; unavailable quota storage fails closed.
Client identity uses the server's peer IP, never a client-supplied forwarding header.
"""
import asyncio
import hashlib
import os
import time

import httpx
from starlette.responses import JSONResponse

LUA = '''
for i,key in ipairs(KEYS) do
  if tonumber(redis.call('GET', key) or '0') >= tonumber(ARGV[i*2-1]) then return 0 end
end
for i,key in ipairs(KEYS) do
  local n = redis.call('INCR', key)
  if n == 1 then redis.call('EXPIRE', key, ARGV[i*2]) end
end
return 1
'''


class DemoGuard:
    def __init__(self, app):
        self.app = app
        self.counts = {}
        self.active = 0

    async def allowed(self, peer):
        digest = hashlib.sha256(peer.encode()).hexdigest()
        limits = [(f'medictime:minute:{digest}', 6, 60),
                  (f'medictime:day:{digest}', 30, 86400),
                  ('medictime:global:day', 100, 86400)]
        url = os.getenv('UPSTASH_REDIS_REST_URL', '')
        token = os.getenv('UPSTASH_REDIS_REST_TOKEN', '')
        if url and token:
            if not url.startswith('https://'):
                raise RuntimeError('Quota storage must use HTTPS')
            async with httpx.AsyncClient(timeout=5) as client:
                response = await client.post(url, headers={'Authorization': f'Bearer {token}'},
                    json=['EVAL', LUA, len(limits), *[x[0] for x in limits],
                          *[str(v) for x in limits for v in x[1:]]])
                response.raise_for_status()
                payload = response.json()
                if payload.get('result') not in (0, 1) or 'error' in payload:
                    raise RuntimeError('Quota storage failed')
                return payload['result'] == 1
        # Local fallback must be opted into; deployment cannot accidentally fail open.
        if os.getenv('APP_ENV') != 'development':
            raise RuntimeError('Shared quota storage is required')
        now = time.monotonic()
        self.counts = {k: v for k, v in self.counts.items() if v[1] > now}
        if any(self.counts.get(k, (0, 0))[0] >= cap for k, cap, _ in limits):
            return False
        for key, _, seconds in limits:
            count, expiry = self.counts.get(key, (0, now + seconds))
            self.counts[key] = count + 1, expiry
        return True

    async def __call__(self, scope, receive, send):
        if scope['type'] != 'http' or not scope['path'].startswith('/api/') or scope['method'] == 'OPTIONS':
            return await self.app(scope, receive, send)
        if self.active >= 2:
            return await JSONResponse({'error': 'Service busy. Try later.'}, 429)(scope, receive, send)
        # Reserve synchronously before any await so requests cannot race the cap.
        self.active += 1
        try:
            try:
                allowed = await self.allowed((scope.get('client') or ('unknown',))[0])
            except Exception:
                return await JSONResponse({'error': 'Service temporarily unavailable.'}, 503)(scope, receive, send)
            if not allowed:
                return await JSONResponse({'error': 'Demo usage limit reached. Try later.'}, 429)(scope, receive, send)
            # Bound chunked bodies too, before FastAPI parses/spools multipart uploads.
            size = 0
            limit = 16 * 1024 * 1024
            messages = []
            try:
                async with asyncio.timeout(30):
                    while True:
                        message = await receive()
                        if message['type'] == 'http.disconnect':
                            return
                        size += len(message.get('body', b''))
                        if size > limit:
                            return await JSONResponse({'error': 'Request too large.'}, 413)(scope, receive, send)
                        messages.append(message)
                        if not message.get('more_body', False):
                            break
            except TimeoutError:
                return await JSONResponse({'error': 'Upload timed out.'}, 408)(scope, receive, send)
            async def bounded_receive():
                if messages:
                    return messages.pop(0)
                return await receive()
            await self.app(scope, bounded_receive, send)
        finally:
            self.active -= 1
