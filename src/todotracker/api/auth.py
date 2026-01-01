"""Authentication for the API."""

import secrets
from typing import Annotated

from fastapi import Depends, HTTPException, Security, status
from fastapi.security import APIKeyHeader, APIKeyQuery

from todotracker.config import get_settings

# Support API key via header or query parameter
api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)
api_key_query = APIKeyQuery(name="api_key", auto_error=False)


async def verify_api_key(
    header_key: Annotated[str | None, Security(api_key_header)] = None,
    query_key: Annotated[str | None, Security(api_key_query)] = None,
) -> None:
    """Verify API key if authentication is enabled.

    API key can be provided via:
    - X-API-Key header (preferred)
    - api_key query parameter (for convenience in browsers)

    If TODOTRACKER_API_KEY is not set, authentication is disabled.
    """
    settings = get_settings()

    # If no API key configured, authentication is disabled
    if settings.api_key is None:
        return

    # In Home Assistant environment, authentication may be handled externally
    if settings.is_homeassistant:
        return

    # Get the provided key (prefer header over query)
    provided_key = header_key or query_key

    if provided_key is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="API key required. Provide via X-API-Key header or api_key query parameter.",
            headers={"WWW-Authenticate": "ApiKey"},
        )

    # Use constant-time comparison to prevent timing attacks
    if not secrets.compare_digest(provided_key, settings.api_key):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API key",
            headers={"WWW-Authenticate": "ApiKey"},
        )


# Dependency for use in routes
RequireAuth = Annotated[None, Depends(verify_api_key)]
