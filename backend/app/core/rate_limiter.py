"""
Rate limiting utilities for API protection.
"""

import time
from collections import defaultdict
from typing import Dict, Optional

from fastapi import HTTPException, Request, status

from app.core.config import settings


class TokenBucket:
    """Simple token bucket rate limiter."""
    
    def __init__(self, capacity: int, refill_rate: float):
        """
        Initialize token bucket.
        
        Args:
            capacity: Maximum number of tokens
            refill_rate: Tokens per second refill rate
        """
        self.capacity = capacity
        self.tokens = capacity
        self.refill_rate = refill_rate
        self.last_refill = time.time()
    
    def consume(self, tokens: int = 1) -> bool:
        """
        Try to consume tokens from bucket.
        
        Args:
            tokens: Number of tokens to consume
            
        Returns:
            True if tokens were consumed, False otherwise
        """
        now = time.time()
        
        # Refill tokens based on elapsed time
        elapsed = now - self.last_refill
        self.tokens = min(self.capacity, self.tokens + elapsed * self.refill_rate)
        self.last_refill = now
        
        if self.tokens >= tokens:
            self.tokens -= tokens
            return True
        return False


class RateLimiter:
    """In-memory rate limiter using token bucket algorithm."""
    
    def __init__(self):
        """Initialize rate limiter."""
        self.buckets: Dict[str, TokenBucket] = defaultdict(
            lambda: TokenBucket(
                capacity=settings.RATE_LIMIT_REQUESTS_PER_MINUTE,
                refill_rate=settings.RATE_LIMIT_REQUESTS_PER_MINUTE / 60.0
            )
        )
    
    def is_allowed(self, key: str, tokens: int = 1) -> bool:
        """
        Check if request is allowed for the given key.
        
        Args:
            key: Rate limiting key (e.g., IP address, user ID)
            tokens: Number of tokens to consume
            
        Returns:
            True if request is allowed, False otherwise
        """
        if not settings.RATE_LIMIT_ENABLED:
            return True
        
        bucket = self.buckets[key]
        return bucket.consume(tokens)
    
    def cleanup_old_buckets(self, max_age: int = 3600) -> None:
        """
        Clean up old unused buckets.
        
        Args:
            max_age: Maximum age in seconds before bucket is removed
        """
        now = time.time()
        to_remove = []
        
        for key, bucket in self.buckets.items():
            if now - bucket.last_refill > max_age:
                to_remove.append(key)
        
        for key in to_remove:
            del self.buckets[key]


# Global rate limiter instance
rate_limiter = RateLimiter()


def get_client_ip(request: Request) -> str:
    """
    Get client IP address from request.
    
    Args:
        request: FastAPI request object
        
    Returns:
        Client IP address
    """
    # Check for forwarded IP in headers (for proxy/load balancer)
    forwarded_ip = request.headers.get("X-Forwarded-For")
    if forwarded_ip:
        return forwarded_ip.split(",")[0].strip()
    
    real_ip = request.headers.get("X-Real-IP")
    if real_ip:
        return real_ip
    
    # Fallback to direct connection IP
    return request.client.host if request.client else "unknown"


def rate_limit_dependency(request: Request) -> None:
    """
    FastAPI dependency for rate limiting.
    
    Args:
        request: FastAPI request object
        
    Raises:
        HTTPException: If rate limit is exceeded
    """
    client_ip = get_client_ip(request)
    
    if not rate_limiter.is_allowed(client_ip):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Rate limit exceeded. Please try again later.",
            headers={"Retry-After": "60"}
        )
