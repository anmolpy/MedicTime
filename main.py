"""Compatibility entry point: use the maintained, bounded backend and frontend.
Install backend/requirements.txt. Both entry points now share the same protections.
"""
import os
from backend.app.main import app

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=int(os.getenv("PORT", "8001")))
