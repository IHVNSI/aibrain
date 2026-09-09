"""Microservice authentication mode - validates tokens from main server."""
import logging
import os
import jwt
import json
import base64
from datetime import datetime
from functools import wraps
from flask import request, g, jsonify

logger = logging.getLogger(__name__)

# Import models for company lookup
try:
    from .models import Company
    HAS_MODELS = True
except ImportError:
    HAS_MODELS = False
    logger.warning("Could not import Company model for company lookup")

# Microservice configuration
MICROSERVICE_MODE = os.getenv("MICROSERVICE_MODE", "false").lower() == "true"
MICROSERVICE_TOKEN_PUBLIC_KEY_RAW = os.getenv("MICROSERVICE_TOKEN_PUBLIC_KEY", None)
MICROSERVICE_TOKEN_SECRET = os.getenv("MICROSERVICE_TOKEN_SECRET", None)
MICROSERVICE_TOKEN_ALGORITHM = os.getenv("MICROSERVICE_TOKEN_ALGORITHM", "HS256")
MICROSERVICE_TOKEN_INTROSPECTION_URL = os.getenv("MICROSERVICE_TOKEN_INTROSPECTION_URL", None)

logger.info(f"🔧 Microservice mode: {MICROSERVICE_MODE}")
logger.info(f"🔐 Token algorithm: {MICROSERVICE_TOKEN_ALGORITHM}")


def _extract_user_id(payload: dict) -> str:
    """
    Extract user_id from token payload.
    Handles both numeric IDs and string identifiers (email, username, etc).
    """
    # Try 'userId' claim first (external auth server format)
    user_id = payload.get("userId")
    if user_id:
        try:
            return int(user_id)
        except (ValueError, TypeError):
            return str(user_id)
    
    # Try 'sub' claim (standard JWT subject claim)
    sub = payload.get("sub")
    if sub:
        # Try to convert to int if it looks numeric
        try:
            return int(sub)
        except (ValueError, TypeError):
            # It's a string (email, username, uuid, etc) - use as-is
            return str(sub)
    
    # Fall back to 'user_id' claim
    user_id = payload.get("user_id")
    if user_id:
        try:
            return int(user_id)
        except (ValueError, TypeError):
            return str(user_id)
    
    # Default
    return 0


def _lookup_company_id(company_code: str = None, company_name: str = None) -> int:
    """
    Look up company ID from database using company code or name.
    
    Lookup hierarchy:
    1. By company_code column (if company_code provided)
    2. By name matching company_code (fallback if code not in DB)
    3. By company_name column
    
    Args:
        company_code: Parent company code (preferred, from token)
        company_name: Company name (fallback)
    
    Returns:
        Company ID if found, None otherwise
    """
    if not HAS_MODELS:
        logger.debug("Models not available for company lookup")
        return None
    
    try:
        # Try lookup by company_code column first (most efficient)
        if company_code:
            company = Company.query.filter_by(company_code=company_code).first()
            if company:
                logger.debug(f"[OK] Found company by code '{company_code}': ID={company.id}")
                return company.id
            
            # Fallback: search by name matching the code
            company = Company.query.filter_by(name=company_code).first()
            if company:
                logger.debug(f"[OK] Found company by name matching code '{company_code}': ID={company.id}")
                return company.id
        
        # Try lookup by company name
        if company_name:
            company = Company.query.filter_by(name=company_name).first()
            if company:
                logger.debug(f"[OK] Found company by name '{company_name}': ID={company.id}")
                return company.id
        
        logger.debug(f"[WARNING] Company not found for code='{company_code}', name='{company_name}'")
        return None
    
    except Exception as e:
        logger.warning(f"Error looking up company: {e}")
        return None


def _resolve_source_company_fk(company_code: str = None, company_name: str = None):
    """Resolve the company id (and child branch ids) from the SOURCE database.

    The business data tables (e.g. ``complaint.company_fk``) reference the SOURCE
    ``company`` table's primary key — NOT the local admin ``companies`` table id.
    This resolves the real foreign key by matching the token's ``parentCompanyCode``
    against the SOURCE ``company.company_code`` column, then includes child branch
    companies (``parent_company_fk = id``) so a parent tenant sees all its branches.

    Args:
        company_code: parentCompanyCode claim from the token (matched to company_code).
        company_name: Company/parent name (fallback when code lookup fails).

    Returns:
        (company_fk, related_company_ids):
        - company_fk: the SOURCE company id (parent), or None if not found.
        - related_company_ids: [parent_id, *child_branch_ids] (always includes parent).
    """
    if not company_code and not company_name:
        return None, []

    try:
        from .config import Config
        from sqlalchemy import create_engine, text

        db_url = Config.SOURCE_DB_URL
        if not db_url:
            logger.debug("[company_fk] SOURCE_DB_URL not configured")
            return None, []

        # Source schema standard names; overridable via AuthConfig mappings.
        company_table, id_field, name_field = "company", "id", "name"
        code_field, parent_field = "company_code", "parent_company_fk"
        try:
            from .models import AuthConfig
            cfg = AuthConfig.query.first()
            if cfg:
                company_table = cfg.company_table or company_table
                id_field = cfg.company_id_field or id_field
                name_field = cfg.company_name_field or name_field
        except Exception:
            pass

        engine = create_engine(db_url)
        with engine.connect() as conn:
            row = None
            if company_code:
                row = conn.execute(
                    text(f'SELECT "{id_field}" FROM "{company_table}" WHERE "{code_field}" = :v LIMIT 1'),
                    {"v": company_code},
                ).fetchone()
            if row is None and company_name:
                row = conn.execute(
                    text(f'SELECT "{id_field}" FROM "{company_table}" WHERE "{name_field}" = :v LIMIT 1'),
                    {"v": company_name},
                ).fetchone()

            if row is None:
                logger.warning(
                    f"[company_fk] No SOURCE company matched code='{company_code}', name='{company_name}'"
                )
                return None, []

            company_fk = int(row[0])
            related = [company_fk]

            # Include child branch companies so a parent sees all its branches.
            try:
                kids = conn.execute(
                    text(f'SELECT "{id_field}" FROM "{company_table}" WHERE "{parent_field}" = :p'),
                    {"p": company_fk},
                ).fetchall()
                related.extend(int(k[0]) for k in kids if k[0] is not None)
            except Exception as kid_err:
                logger.debug(f"[company_fk] Could not load child branches: {kid_err}")

            related = sorted(set(related))
            logger.info(f"[company_fk] Resolved SOURCE company_fk={company_fk}, related={related}")
            return company_fk, related

    except Exception as e:
        logger.warning(f"[company_fk] Error resolving from source DB: {e}")
        return None, []



def _format_rsa_public_key(key_data: str) -> str:
    """
    Convert raw base64 RSA public key to PEM format.
    Handles both PEM-formatted and raw base64 keys.
    """
    if not key_data:
        return None
    
    key_data = key_data.strip()
    
    # If already in PEM format, return as-is
    if key_data.startswith("-----BEGIN"):
        return key_data
    
    # Check if it looks like a raw base64 RSA key (DER format in base64)
    try:
        # Decode base64 to get DER bytes
        der_bytes = base64.b64decode(key_data)
        
        # Encode back to base64 with line wrapping for PEM format
        b64_wrapped = base64.b64encode(der_bytes).decode('utf-8')
        
        # Insert line breaks every 64 characters for PEM formatting
        pem_lines = [b64_wrapped[i:i+64] for i in range(0, len(b64_wrapped), 64)]
        pem_key = "-----BEGIN PUBLIC KEY-----\n"
        pem_key += "\n".join(pem_lines)
        pem_key += "\n-----END PUBLIC KEY-----"
        
        logger.debug(f"✅ Converted raw RSA key to PEM format")
        return pem_key
    except Exception as e:
        logger.warning(f"Could not convert RSA key to PEM: {e}")
        # Return raw key - PyJWT might still handle it
        return key_data


# Format the public key if provided
MICROSERVICE_TOKEN_PUBLIC_KEY = _format_rsa_public_key(MICROSERVICE_TOKEN_PUBLIC_KEY_RAW)


# ============================================================================
# ROLE-BASED ACCESS CONTROL (RBAC) MAPPING
# ============================================================================

def _map_token_claims_to_app_roles(claims: dict) -> dict:
    """
    Map token claims from external auth server to app-level roles.
    
    Handles multiple token formats:
    - Legacy format: tokenRole, role, is_admin claims
    - External format: scopes, userId, companyName, companyType, parentCompanyName, parentCompanyCode
    
    Business logic:
    - If token has "CENTRAL_ADMIN" scope/role → Full app admin (global access)
    - If token has "ADMIN" scope/role + company → Company tenant admin (company-scoped)
    - Otherwise → Regular user (company-scoped if company_name present)
    
    Returns dict with:
    - app_role: "Admin", "Company Admin", or "User"
    - is_admin: Boolean (True for CENTRAL_ADMIN only)
    - is_company_admin: Boolean (True for ADMIN + company)
    - access_scope: "global" or company_code/name
    - company_id: Resolved company ID from database (if possible)
    - company_scoped: Boolean (whether access is scoped to a company)
    """
    
    # Extract role from multiple possible formats
    token_role = claims.get("tokenRole") or claims.get("role") or ""
    
    # Extract roles from scopes claim (external auth format)
    scopes = claims.get("scopes", [])
    if isinstance(scopes, str):
        scopes = scopes.split()
    scopes = [str(s).upper() for s in scopes]
    
    # Extract company info
    company_name = claims.get("companyName", "") or claims.get("company_name", "")
    company_code = claims.get("parentCompanyCode") or claims.get("companyCode") or claims.get("company_code", "")
    company_type = claims.get("companyType", "") or claims.get("company_type", "")
    parent_company_name = claims.get("parentCompanyName", "") or claims.get("parent_company_name", "")
    
    # Try to lookup company_id from database
    company_id = _lookup_company_id(company_code, company_name or parent_company_name)
    
    # Resolve the REAL data foreign key from the SOURCE database. Business tables
    # (e.g. complaint.company_fk) reference the SOURCE company id, not the local
    # admin companies id. Match parentCompanyCode -> SOURCE company.company_code.
    source_company_fk, related_company_ids = _resolve_source_company_fk(
        company_code, company_name or parent_company_name
    )
    
    # Determine if user is CENTRAL_ADMIN (full app admin)
    is_central_admin = (
        token_role.upper() == "CENTRAL_ADMIN" or
        "CENTRAL_ADMIN" in scopes or
        "CENTRAL_ROLE" in scopes
    )
    
    # Determine if user is COMPANY_ADMIN (company tenant admin)
    is_company_admin = (
        (token_role.upper() == "ADMIN" or "ADMIN" in scopes) and 
        (company_name or parent_company_name)
    )
    
    # Determine primary company for scoping
    primary_company = company_name or parent_company_name or company_code or ""
    
    if is_central_admin:
        # CENTRAL_ADMIN in token → Full app admin
        return {
            "app_role": "Admin",
            "is_admin": True,
            "is_company_admin": False,
            "access_scope": "global",
            "company_scoped": False,
            "company_id": None,
            "company_name": None,
            "description": "Application Administrator (CENTRAL_ADMIN)"
        }
    elif is_company_admin:
        # ADMIN + company → Company tenant admin (scoped to this company)
        return {
            "app_role": "Company Admin",
            "is_admin": False,
            "is_company_admin": True,
            "access_scope": company_code or company_name,
            "company_scoped": True,
            "company_id": company_id,
            "company_fk": source_company_fk,
            "related_company_ids": related_company_ids,
            "company_name": primary_company,
            "description": f"Company Administrator for {primary_company}"
        }
    else:
        # Regular user (company-scoped if company info present)
        return {
            "app_role": "User",
            "is_admin": False,
            "is_company_admin": False,
            "access_scope": company_code or primary_company or "public",
            "company_scoped": bool(primary_company),
            "company_id": company_id,
            "company_fk": source_company_fk,
            "related_company_ids": related_company_ids,
            "company_name": primary_company,
            "description": f"Regular User" + (f" ({primary_company})" if primary_company else "")
        }


def extract_user_from_token(token: str) -> dict:
    """
    Extract user context from a token issued by the main server.
    
    Supports:
    - HS256/RS256 JWT validation (if public key/secret provided)
    - Token introspection via HTTP endpoint (if URL provided)
    - Raw token trust (if MICROSERVICE_MODE=true with no validation config)
    
    Returns dict with keys:
    - user_id, username, email, company_id, branch_id, roles, is_admin
    - Or None if token is invalid
    
    ALSO includes RBAC information:
    - app_role: Mapped role in this application
    - is_admin: Boolean if user is app admin
    - is_company_admin: Boolean if user is company tenant admin
    - access_scope: Global access or company-scoped
    """
    if not token:
        return None
    
    # Debug logging - show token structure and configuration
    token_parts = token.split('.')
    logger.debug(f"🔐 Token validation: parts={len(token_parts)}, algo={MICROSERVICE_TOKEN_ALGORITHM}, has_key={bool(MICROSERVICE_TOKEN_PUBLIC_KEY or MICROSERVICE_TOKEN_SECRET)}")
    
    # Try to decode without verification to see what claims are in the token
    try:
        unverified = jwt.decode(token, options={"verify_signature": False, "verify_aud": False})
        logger.debug(f"📋 Token claims: sub={unverified.get('sub')}, aud={unverified.get('aud')}, roles={unverified.get('roles')}")
    except Exception as e:
        logger.debug(f"Could not inspect token: {e}")
    
    try:
        # Strategy 1: Validate JWT signature
        if MICROSERVICE_TOKEN_PUBLIC_KEY or MICROSERVICE_TOKEN_SECRET:
            key = MICROSERVICE_TOKEN_PUBLIC_KEY or MICROSERVICE_TOKEN_SECRET
            
            # Support multiple algorithms for flexibility
            # Try configured algorithm first, then common ones
            allowed_algos = [MICROSERVICE_TOKEN_ALGORITHM] if MICROSERVICE_TOKEN_ALGORITHM else []
            if "HS256" not in allowed_algos:
                allowed_algos.append("HS256")
            if "RS256" not in allowed_algos:
                allowed_algos.append("RS256")
            
            try:
                payload = jwt.decode(
                    token,
                    key,
                    algorithms=allowed_algos,
                    options={"verify_exp": True, "verify_aud": False}
                )
            except jwt.InvalidAlgorithmError as alg_error:
                # If still failing, try without signature verification as fallback
                logger.warning(f"❌ Algorithm error (trying unverified decode): {alg_error}")
                payload = jwt.decode(
                    token,
                    options={"verify_signature": False, "verify_aud": False}
                )
            
            # Map common JWT claim names to our user context
            user_ctx = {
                "user_id": _extract_user_id(payload),
                "username": payload.get("username", ""),
                "email": payload.get("email", payload.get("sub", "")),  # Use email or sub
                "company_id": payload.get("company_id"),
                "branch_id": payload.get("branch_id"),
                "is_admin": payload.get("is_admin", False),
                "token_issued_at": payload.get("iat"),
                "token_expires_at": payload.get("exp"),
                "raw_payload": payload,
            }
            
            # Extract roles from multiple possible sources
            roles = list(payload.get("roles", []) or [])
            
            # Also include scopes as roles (external auth format)
            scopes = payload.get("scopes", [])
            if isinstance(scopes, str):
                scopes = scopes.split()
            if scopes:
                roles.extend([str(s).upper() for s in scopes])
            
            # Deduplicate and store
            user_ctx["roles"] = list(set(roles))
            
            # Add RBAC mapping based on token claims
            rbac_info = _map_token_claims_to_app_roles(payload)
            user_ctx.update(rbac_info)
            
            # Ensure company_fk is set (use company_id from RBAC mapping or direct field)
            if not user_ctx.get("company_fk") and user_ctx.get("company_id"):
                user_ctx["company_fk"] = user_ctx["company_id"]
            
            return user_ctx
        
        # Strategy 2: Introspect token via HTTP endpoint
        if MICROSERVICE_TOKEN_INTROSPECTION_URL:
            try:
                import requests
                response = requests.post(
                    MICROSERVICE_TOKEN_INTROSPECTION_URL,
                    json={"token": token},
                    timeout=5
                )
                if response.status_code == 200:
                    data = response.json()
                    if data.get("active"):
                        roles = list(data.get("roles", []) or [])
                        # Also include scopes as roles (external auth format)
                        scopes = data.get("scopes", [])
                        if isinstance(scopes, str):
                            scopes = scopes.split()
                        if scopes:
                            roles.extend([str(s).upper() for s in scopes])
                        
                        user_ctx = {
                            "user_id": _extract_user_id(data),
                            "username": data.get("username", ""),
                            "email": data.get("email", data.get("sub", "")),
                            "company_id": data.get("company_id"),
                            "branch_id": data.get("branch_id"),
                            "roles": list(set(roles)),  # Deduplicate
                            "is_admin": data.get("is_admin", False),
                            "raw_payload": data,
                        }
                        rbac_info = _map_token_claims_to_app_roles(data)
                        user_ctx.update(rbac_info)
                        
                        # Ensure company_fk is set (use company_id from RBAC mapping or direct field)
                        if not user_ctx.get("company_fk") and user_ctx.get("company_id"):
                            user_ctx["company_fk"] = user_ctx["company_id"]
                        
                        return user_ctx
            except Exception as e:
                logger.warning(f"Token introspection failed: {e}")
        
        # Strategy 3: Trust token in microservice mode (no validation)
        if MICROSERVICE_MODE and not MICROSERVICE_TOKEN_PUBLIC_KEY and not MICROSERVICE_TOKEN_SECRET:
            # Attempt to decode without verification (development only)
            try:
                payload = jwt.decode(token, options={"verify_signature": False, "verify_aud": False})
                roles = list(payload.get("roles", []) or [])
                # Also include scopes as roles (external auth format)
                scopes = payload.get("scopes", [])
                if isinstance(scopes, str):
                    scopes = scopes.split()
                if scopes:
                    roles.extend([str(s).upper() for s in scopes])
                
                user_ctx = {
                    "user_id": _extract_user_id(payload),
                    "username": payload.get("username", ""),
                    "email": payload.get("email", payload.get("sub", "")),
                    "company_id": payload.get("company_id"),
                    "branch_id": payload.get("branch_id"),
                    "roles": list(set(roles)),  # Deduplicate
                    "is_admin": payload.get("is_admin", False),
                    "raw_payload": payload,
                }
                rbac_info = _map_token_claims_to_app_roles(payload)
                user_ctx.update(rbac_info)
                
                # Ensure company_fk is set (use company_id from RBAC mapping or direct field)
                if not user_ctx.get("company_fk") and user_ctx.get("company_id"):
                    user_ctx["company_fk"] = user_ctx["company_id"]
                
                return user_ctx
            except Exception:
                pass
        
        return None
    
    except jwt.ExpiredSignatureError:
        logger.warning("⏰ Token has expired")
        return None
    except jwt.InvalidTokenError as e:
        logger.warning(f"❌ Invalid token: {type(e).__name__}: {e}")
        return None
    except Exception as e:
        logger.warning(f"❌ Error extracting user from token: {type(e).__name__}: {e}")
        return None


def extract_token_from_request() -> str:
    """Extract JWT token from Authorization header."""
    auth = request.headers.get("Authorization", "").strip()
    # Handle case-insensitive Bearer scheme
    if auth.lower().startswith("bearer "):
        token = auth[7:].strip()
        # Remove all embedded whitespace/newlines that break JWT parsing
        token = ''.join(token.split())
        return token
    return ""


def microservice_user_context():
    """Get user context from microservice token (or empty dict)."""
    return getattr(g, "microservice_user_ctx", {}) or {}


def optional_microservice_auth(fn):
    """
    Decorator for microservice mode: extract user context if token present, 
    but don't fail if missing. Endpoint can check user availability.
    """
    @wraps(fn)
    def wrapper(*args, **kwargs):
        if not MICROSERVICE_MODE:
            # Not in microservice mode, skip microservice auth
            return fn(*args, **kwargs)
        
        token = extract_token_from_request()
        user_ctx = {}
        
        if token:
            user_ctx = extract_user_from_token(token) or {}
            if user_ctx:
                logger.debug(f"✅ Microservice user context: {user_ctx.get('email')}")
            else:
                logger.warning("Token provided but could not extract user context")
        
        g.microservice_user_ctx = user_ctx
        return fn(*args, **kwargs)
    
    return wrapper


def require_microservice_auth(fn):
    """
    Decorator for microservice mode: require valid token with user context.
    Use for endpoints that need to know who the user is.
    """
    @wraps(fn)
    def wrapper(*args, **kwargs):
        if not MICROSERVICE_MODE:
            # Not in microservice mode, skip microservice auth
            return fn(*args, **kwargs)
        
        token = extract_token_from_request()
        if not token:
            return jsonify({"success": False, "error": "Authorization required"}), 401
        
        user_ctx = extract_user_from_token(token)
        if not user_ctx:
            return jsonify({"success": False, "error": "Invalid or expired token"}), 401
        
        g.microservice_user_ctx = user_ctx
        logger.debug(f"✅ Authenticated as: {user_ctx.get('email')}")
        return fn(*args, **kwargs)
    
    return wrapper
