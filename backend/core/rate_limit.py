from fastapi import Request, HTTPException, status
from .config import settings
import time

# Very simple in-memory rate limiter for MVP demonstration.
# In a production environment with multiple instances, this MUST be backed by Redis.
# See Part 18 Requirements.

_rate_limit_store = {}

def rate_limit_dependency(requests_per_minute: int = 60):
    def _rate_limit(request: Request):
        if not settings.RATE_LIMIT_ENABLED:
            return
            
        client_ip = request.client.host
        current_time = time.time()
        
        if client_ip not in _rate_limit_store:
            _rate_limit_store[client_ip] = []
            
        # Clear out old requests
        _rate_limit_store[client_ip] = [t for t in _rate_limit_store[client_ip] if current_time - t < 60]
        
        if len(_rate_limit_store[client_ip]) >= requests_per_minute:
            raise HTTPException(status_code=429, detail="Too Many Requests")
            
        _rate_limit_store[client_ip].append(current_time)
        
    return _rate_limit
