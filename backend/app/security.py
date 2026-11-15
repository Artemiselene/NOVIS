"""
ASTRA MIND — Security, Authentication & Access Control (Hardened)
================================================================
Provides environment-configured API key / Bearer authentication,
role-based authorization, and per-astronaut data isolation.

Roles:
  - flight_surgeon: Full access to all astronauts' physiological & behavioral health.
  - mission_director: Access to mission summaries, crew operational status.
  - astronaut: Restricted access strictly scoped to their own astronaut_id.
  - ground_crew: Read-only access to operational non-medical telemetry.

SECURITY HARDENING (SEC-01, SEC-04):
  - No administrative default user fallback.
  - Missing credentials return HTTP 401 Unauthorized.
  - Invalid credentials return HTTP 401 Unauthorized.
  - All API keys loaded from environment variables (.env / os.environ).
  - Production fails safely with empty credentials if unconfigured.
"""

import os
import logging
from typing import Optional, Dict, Any, List
from fastapi import Header, HTTPException, status, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

logger = logging.getLogger("astra_mind.security")
security_scheme = HTTPBearer(auto_error=False)


def load_dotenv_if_present() -> None:
    """Load configuration from .env file if present in working directory or parents."""
    candidates = [
        os.path.join(os.getcwd(), ".env"),
        os.path.join(os.path.dirname(__file__), ".env"),
        os.path.join(os.path.dirname(os.path.dirname(__file__)), ".env"),
        os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), ".env"),
    ]
    for path in candidates:
        if os.path.isfile(path):
            try:
                with open(path, "r", encoding="utf-8") as f:
                    for line in f:
                        line = line.strip()
                        if line and not line.startswith("#") and "=" in line:
                            k, v = line.split("=", 1)
                            k = k.strip()
                            v = v.strip().strip("'\"")
                            if k not in os.environ:
                                os.environ[k] = v
                break
            except Exception as e:
                logger.warning(f"Failed to read .env file at {path}: {e}")


# Initialize environment on module load
load_dotenv_if_present()


def get_valid_credentials() -> Dict[str, Dict[str, Any]]:
    """
    Dynamically build the authorized credential registry from environment configuration.
    Fails safely in production if credentials are not configured.
    """
    env = os.getenv("ASTRA_ENV", "development").lower()
    credentials: Dict[str, Dict[str, Any]] = {}

    # Flight Surgeon Key
    surgeon_key = os.getenv("ASTRA_SURGEON_API_KEY")
    if surgeon_key:
        credentials[surgeon_key.strip()] = {
            "user_id": "surgeon_1",
            "role": "flight_surgeon",
            "name": "Flight Surgeon",
        }

    # Mission Director Key
    director_key = os.getenv("ASTRA_MISSION_DIRECTOR_API_KEY")
    if director_key:
        credentials[director_key.strip()] = {
            "user_id": "flight_dir_1",
            "role": "mission_director",
            "name": "Mission Director",
        }

    # Crew 1 Key
    crew_1_key = os.getenv("ASTRA_CREW_1_API_KEY")
    if crew_1_key:
        credentials[crew_1_key.strip()] = {
            "user_id": "crew_1",
            "role": "astronaut",
            "astronaut_id": 1,
            "name": "Dr. Sarah Walker",
        }

    # Crew 2 Key
    crew_2_key = os.getenv("ASTRA_CREW_2_API_KEY")
    if crew_2_key:
        credentials[crew_2_key.strip()] = {
            "user_id": "crew_2",
            "role": "astronaut",
            "astronaut_id": 2,
            "name": "Mark Kelly",
        }

    # Optional Extra Crew Keys (format: "TOKEN_A:3,TOKEN_B:4")
    extra_crew = os.getenv("ASTRA_EXTRA_CREW_KEYS")
    if extra_crew:
        for pair in extra_crew.split(","):
            if ":" in pair:
                token, a_id = pair.split(":", 1)
                token = token.strip()
                try:
                    a_id_int = int(a_id.strip())
                    credentials[token] = {
                        "user_id": f"crew_{a_id_int}",
                        "role": "astronaut",
                        "astronaut_id": a_id_int,
                        "name": f"Astronaut {a_id_int}",
                    }
                except ValueError:
                    pass

    # In production, missing credentials fail safely (empty registry -> all requests 401)
    if env == "production" and not credentials:
        logger.critical("PRODUCTION SECURITY WARNING: No authorized credentials configured in environment.")

    return credentials


def verify_token(token: Optional[str]) -> Optional[Dict[str, Any]]:
    """Validate a raw token string and return the user identity dict, or None."""
    if not token:
        return None
    valid_creds = get_valid_credentials()
    return valid_creds.get(token.strip())


def authenticate_user(
    x_api_key: Optional[str] = Header(None, alias="X-API-Key"),
    auth_header: Optional[HTTPAuthorizationCredentials] = Depends(security_scheme),
) -> Dict[str, Any]:
    """
    Authenticate request via X-API-Key header or Bearer Token.
    Returns user dictionary containing role and astronaut_id.
    Missing or invalid credentials return HTTP 401 Unauthorized.
    """
    token = None
    if x_api_key:
        token = x_api_key.strip()
    elif auth_header and auth_header.credentials:
        token = auth_header.credentials.strip()

    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing authentication credentials. Provide an X-API-Key or Bearer token.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user = verify_token(token)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials or expired API key.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return user


def require_role(allowed_roles: List[str]):
    """Enforce role-based authorization."""
    def role_checker(user: Dict[str, Any] = Depends(authenticate_user)) -> Dict[str, Any]:
        user_role = user.get("role", "")
        if user_role not in allowed_roles and user_role != "flight_surgeon":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access forbidden: role '{user_role}' lacks required permissions ({allowed_roles}).",
            )
        return user
    return role_checker


def enforce_astronaut_isolation(
    target_astronaut_id: int,
    user: Dict[str, Any] = Depends(authenticate_user),
) -> None:
    """Enforce astronaut-level data isolation."""
    user_role = user.get("role", "")
    if user_role in ["flight_surgeon", "mission_director"]:
        return

    scoped_id = user.get("astronaut_id")
    if scoped_id is not None and int(scoped_id) == int(target_astronaut_id):
        return

    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail=f"Access denied: astronaut {scoped_id} cannot access records for astronaut {target_astronaut_id}.",
    )
