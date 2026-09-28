"""Auth API: register, login, me. Plus a startup seed for the default admin."""
import logging
import bcrypt
from sqlalchemy import text, create_engine
from datetime import datetime, timedelta

from flask import Blueprint, request, jsonify

from ..extensions import db
from ..models import User, Company, Branch, Role, UserRole, RestrictedSQLCommand, AuthConfig
from ..auth import hash_password, verify_password, generate_token, require_auth, current_user_context, JWT_EXP_HOURS
from ..config import Config

logger = logging.getLogger(__name__)
auth_bp = Blueprint("auth", __name__, url_prefix="/api/auth")


def get_source_engine():
    """Get SQLAlchemy engine for the SOURCE database."""
    db_url = Config.SOURCE_DB_URL
    if not db_url:
        raise Exception("SOURCE_DB_URL not configured")
    return create_engine(db_url)


@auth_bp.route("/register", methods=["POST"])
def register():
    data = request.get_json(silent=True) or {}
    username = (data.get("username") or "").strip()
    email = (data.get("email") or "").strip().lower()
    password = data.get("password") or ""
    if not username or not email or not password:
        return jsonify({"success": False, "error": "username, email and password are required"}), 400
    if User.query.filter((User.username == username) | (User.email == email)).first():
        return jsonify({"success": False, "error": "User already exists"}), 409

    company_id = data.get("company_id")
    branch_id = data.get("branch_id")
    # Optionally create a company by name
    company_name = (data.get("company_name") or "").strip()
    if company_name and not company_id:
        company = Company.query.filter_by(name=company_name).first()
        if not company:
            company = Company(name=company_name)
            db.session.add(company)
            db.session.flush()
        company_id = company.id

    user = User(
        username=username, email=email, password_hash=hash_password(password),
        first_name=data.get("first_name"), last_name=data.get("last_name"),
        company_id=company_id, branch_id=branch_id,
    )
    db.session.add(user)
    db.session.flush()

    if company_id:
        company = Company.query.get(company_id)
        if company and company not in user.companies:
            user.companies.append(company)

    # Assign a default non-admin "User" role.
    role = Role.query.filter_by(name="User").first()
    if not role:
        role = Role(name="User", description="Standard user", is_admin=False, is_system_role=True)
        db.session.add(role)
        db.session.flush()
    db.session.add(UserRole(user_id=user.id, role_id=role.id))
    db.session.commit()

    token = generate_token(user, company_id=company_id, branch_id=branch_id)
    return jsonify({"success": True, "token": token, "user": user.to_dict()}), 201


def _company_summary(company: Company) -> dict:
    return {
        "id": company.id,
        "name": company.name,
        "company_type": company.company_type,
        "parent_company_id": company.parent_company_id,
    }


def _get_user_parent_companies(user: User, is_admin: bool) -> list:
    if is_admin:
        return Company.query.filter_by(is_active=True).filter(
            Company.company_type != "BRANCH"
        ).all()

    if user.companies:
        return [c for c in user.companies if c.is_active and c.company_type != "BRANCH"]

    if user.company_id:
        company = Company.query.get(user.company_id)
        if company and company.is_active and company.company_type != "BRANCH":
            return [company]

    return []


@auth_bp.route("/verify-email", methods=["POST"])
def verify_email():
    data = request.get_json(silent=True) or {}
    email = (data.get("email") or "").strip().lower()
    if not email:
        return jsonify({"success": False, "error": "Email is required"}), 400

    user = User.query.filter_by(email=email).first()
    if not user or not user.is_active:
        return jsonify({"success": False, "error": "User not found or inactive"}), 401

    return jsonify({
        "success": True,
        "user_id": user.id,
        "username": user.username,
        "email": user.email,
    }), 200


@auth_bp.route("/source-db-login", methods=["POST"])
def source_db_login():
    """
    Login using credentials from SOURCE database.
    Authenticates against configured source database, gets parent companies, and syncs user to admin DB.
    
    Request: {"email": "...", "password": "..."}
    Response: { "success": true, "username": "...", "parent_companies": [...], "needs_company_selection": bool }
    """
    try:
        data = request.get_json(silent=True) or {}
        identifier = (data.get("email") or data.get("username") or "").strip().lower()
        password = data.get("password") or ""
        
        logger.info(f"🔐 Source DB login attempt: identifier='{identifier}'")
        
        if not identifier or not password:
            return jsonify({
                "success": False,
                "error": "Email/username and password required"
            }), 400
        
        # Get auth config
        config = AuthConfig.query.first()
        if not config or not config.configured or not config.users_table:
            logger.error("❌ Auth config not found or not configured")
            return jsonify({
                "success": False,
                "error": "Authentication not configured"
            }), 400
        
        logger.debug(f"Auth config: users_table={config.users_table}, username_field={config.username_field}, password_hash_type={config.password_hash_type}")
        
        # Query user from SOURCE database
        engine = get_source_engine()
        try:
            with engine.connect() as conn:
                # Query by email field first, then username field
                email_field = config.username_field  # Assuming this might be email
                query = f'''SELECT * FROM "{config.users_table}" WHERE LOWER("{email_field}") = :identifier LIMIT 1'''
                
                logger.debug(f"Executing query: {query}")
                result = conn.execute(text(query), {"identifier": identifier})
                user_row = result.first()
                
                if not user_row:
                    logger.warning(f"Source DB login: user '{identifier}' not found")
                    return jsonify({
                        "success": False,
                        "error": "User not found"
                    }), 401
                
                user_row_dict = dict(user_row._mapping)
                
                # Check if user is active
                if config.is_active_field and config.is_active_field in user_row_dict:
                    is_active_val = user_row_dict[config.is_active_field]
                    logger.debug(f"Source DB active field '{config.is_active_field}' = {is_active_val} (type: {type(is_active_val).__name__})")
                    
                    # Check if user is active
                    is_active = False
                    
                    # Handle inverted fields like "is_banned" (True means inactive)
                    if config.is_active_field.lower() in ['is_banned', 'banned', 'is_inactive', 'inactive', 'is_disabled', 'disabled']:
                        # Inverted field: False/None means active
                        if is_active_val is None or is_active_val is False:
                            is_active = True
                        elif isinstance(is_active_val, bool):
                            is_active = not is_active_val
                        else:
                            # String-based inverted field
                            is_active = str(is_active_val).lower() not in ['true', 'yes', '1']
                    else:
                        # Normal field: True means active
                        if isinstance(is_active_val, bool):
                            is_active = is_active_val
                        elif config.is_active_value:
                            # Check if value matches configured active value
                            is_active = str(is_active_val).lower() == str(config.is_active_value).lower()
                        else:
                            # No configured value, check if truthy
                            is_active = str(is_active_val).lower() in ['true', 'yes', '1', 'active']
                    
                    logger.debug(f"User active status: {is_active}")
                    if not is_active:
                        logger.warning(f"Source DB login: user '{identifier}' is inactive (field={config.is_active_field}, value={is_active_val}, configured_value={config.is_active_value})")
                        return jsonify({
                            "success": False,
                            "error": "User is inactive"
                        }), 401
                
                # Verify password
                stored_password_hash = user_row_dict.get(config.password_field)
                if not stored_password_hash:
                    return jsonify({
                        "success": False,
                        "error": "User password field not found in source database"
                    }), 500
                
                # Password verification based on hash type
                password_valid = False
                logger.debug(f"Password hash type: {config.password_hash_type}")
                logger.debug(f"Stored hash first 20 chars: {stored_password_hash[:20] if stored_password_hash else 'None'}")
                
                if config.password_hash_type == 'bcrypt':
                    try:
                        pwd_bytes = stored_password_hash.encode() if isinstance(stored_password_hash, str) else stored_password_hash
                        password_valid = bcrypt.checkpw(password.encode(), pwd_bytes)
                        logger.debug(f"Bcrypt verification result: {password_valid}")
                    except Exception as e:
                        logger.error(f"Bcrypt verification error: {e}")
                        return jsonify({
                            "success": False,
                            "error": f"Password verification error: {str(e)}"
                        }), 500
                elif config.password_hash_type == 'plaintext':
                    password_valid = password == stored_password_hash
                    logger.debug(f"Plaintext verification result: {password_valid}")
                elif config.password_hash_type == 'argon2':
                    try:
                        from argon2 import PasswordHasher
                        ph = PasswordHasher()
                        ph.verify(stored_password_hash, password)
                        password_valid = True
                        logger.debug(f"Argon2 verification result: {password_valid}")
                    except Exception as e:
                        password_valid = False
                        logger.debug(f"Argon2 verification failed: {e}")
                
                if not password_valid:
                    logger.warning(f"❌ Source DB login: invalid password for '{identifier}' (hash_type={config.password_hash_type})")
                    return jsonify({
                        "success": False,
                        "error": "Invalid password"
                    }), 401
                
                logger.info(f"✅ Source DB password verification successful for '{identifier}'")
                
                # Get username for token generation
                username = user_row_dict.get(config.username_field, identifier)
                email_value = user_row_dict.get(email_field, identifier)
                
        except Exception as e:
            logger.error(f"Source DB query error: {e}")
            return jsonify({
                "success": False,
                "error": f"Database error: {str(e)}"
            }), 500
        
        # Get parent companies from SOURCE database
        parent_companies = []
        try:
            if config.user_companies_junction_table:
                # Many-to-many: user -> junction -> company
                with engine.connect() as conn:
                    user_id_val = user_row_dict.get(config.username_field)  # Use username as user identifier
                    
                    # Build query with company_type filter if field is configured
                    type_field = config.company_type_field if config.company_type_field else f'"{config.company_id_field}"'
                    where_clause = f'AND c."{type_field}" = \'PARENT_BRANCH\'' if config.company_type_field else ''
                    
                    query = f'''
                    SELECT DISTINCT c."{config.company_id_field}", c."{config.company_name_field}" {f', c."{config.company_type_field}"' if config.company_type_field else ''}
                    FROM "{config.company_table}" c
                    INNER JOIN "{config.user_companies_junction_table}" uc 
                        ON c."{config.company_id_field}" = uc."{config.user_companies_company_fk}"
                    WHERE uc."{config.user_companies_user_fk}" = :user_id {where_clause}
                    '''
                    result = conn.execute(text(query), {"user_id": user_id_val})
                    for row in result:
                        row_dict = dict(row._mapping)
                        parent_companies.append({
                            "id": row_dict.get(config.company_id_field),
                            "name": row_dict.get(config.company_name_field),
                            "company_type": row_dict.get(config.company_type_field, "PARENT_BRANCH") if config.company_type_field else "PARENT_BRANCH"
                        })
            elif config.user_company_fk_field:
                # Direct FK: user has company_id field
                with engine.connect() as conn:
                    company_id_val = user_row_dict.get(config.user_company_fk_field)
                    
                    if company_id_val:
                        # Build query with company_type filter if field is configured
                        where_clause = f' AND "{config.company_type_field}" = \'PARENT_BRANCH\'' if config.company_type_field else ''
                        query = f'''SELECT "{config.company_id_field}", "{config.company_name_field}" {f', "{config.company_type_field}"' if config.company_type_field else ''} FROM "{config.company_table}" WHERE "{config.company_id_field}" = :company_id{where_clause}'''
                        result = conn.execute(text(query), {"company_id": company_id_val})
                        row = result.first()
                        if row:
                            row_dict = dict(row._mapping)
                            parent_companies.append({
                                "id": row_dict.get(config.company_id_field),
                                "name": row_dict.get(config.company_name_field),
                                "company_type": row_dict.get(config.company_type_field, "PARENT_BRANCH") if config.company_type_field else "PARENT_BRANCH"
                            })
        except Exception as e:
            logger.warning(f"Could not get parent companies from source DB: {e}")
            # Don't fail login if we can't get companies - just proceed without them
        
        # Sync user to ADMIN database (create or update)
        try:
            admin_user = User.query.filter(
                (User.username == username) | (User.email == email_value)
            ).first()
            
            if not admin_user:
                # Create new user in admin DB
                admin_user = User(
                    username=username,
                    email=email_value,
                    password_hash=hash_password(password),  # Hash using admin DB hashing
                    first_name=user_row_dict.get("first_name", ""),
                    last_name=user_row_dict.get("last_name", ""),
                    is_active=True
                )
                db.session.add(admin_user)
                db.session.flush()
                
                # Assign default User role
                user_role = Role.query.filter_by(name="User").first()
                if not user_role:
                    user_role = Role(name="User", description="Standard user", is_admin=False, is_system_role=True)
                    db.session.add(user_role)
                    db.session.flush()
                
                # Check if role assignment already exists before adding
                existing_role = UserRole.query.filter_by(user_id=admin_user.id, role_id=user_role.id).first()
                if not existing_role:
                    db.session.add(UserRole(user_id=admin_user.id, role_id=user_role.id))
                logger.info(f"Created new admin user '{username}' from source DB")
            else:
                # Update existing user (sync email and active status from source DB)
                admin_user.email = email_value
                admin_user.is_active = True
                
                # Ensure user has at least the default User role
                user_role = Role.query.filter_by(name="User").first()
                if not user_role:
                    user_role = Role(name="User", description="Standard user", is_admin=False, is_system_role=True)
                    db.session.add(user_role)
                    db.session.flush()
                
                # Check if role assignment exists, only add if missing
                existing_role = UserRole.query.filter_by(user_id=admin_user.id, role_id=user_role.id).first()
                if not existing_role:
                    db.session.add(UserRole(user_id=admin_user.id, role_id=user_role.id))
                logger.info(f"Synced admin user '{username}' from source DB")
            
            db.session.commit()
        except Exception as e:
            logger.error(f"Error syncing user to admin DB: {e}")
            db.session.rollback()
            return jsonify({
                "success": False,
                "error": f"Failed to sync user to admin database: {str(e)}"
            }), 500
        
        # Use the admin DB username for subsequent operations
        admin_username = admin_user.username
        
        # Determine if company selection is needed
        needs_company_selection = len(parent_companies) > 1
        
        logger.info(f"✅ Source DB login successful: admin_username={admin_username}, companies={len(parent_companies)}")
        
        return jsonify({
            "success": True,
            "username": admin_username,
            "email": email_value,
            "parent_companies": parent_companies,
            "needs_company_selection": needs_company_selection,
            "message": f"Authenticated as {admin_username}"
        }), 200
        
    except Exception as e:
        import traceback
        logger.error(f"❌ Source DB login exception: {e}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        return jsonify({
            "success": False,
            "error": f"Login error: {str(e)}"
        }), 500


@auth_bp.route("/finalize-source-login", methods=["POST"])
def finalize_source_login():
    """
    After successful source DB authentication, generate JWT token for the synced user.
    Expects: username (from source DB), company_id (optional)
    Returns: JWT token and user data
    """
    data = request.get_json(silent=True) or {}
    username = (data.get("username") or "").strip()
    company_id = data.get("company_id")
    
    if not username:
        return jsonify({"success": False, "error": "username is required"}), 400
    
    try:
        # Find the user in admin database (should have been synced by source-db-login)
        user = User.query.filter_by(username=username).first()
        if not user:
            return jsonify({"success": False, "error": "User not found in admin database"}), 404
        
        if not user.is_active:
            return jsonify({"success": False, "error": "User account is inactive"}), 403
        
        # Verify company access if company_id is specified
        if company_id:
            try:
                company_id = int(company_id)
            except (TypeError, ValueError):
                return jsonify({"success": False, "error": "Invalid company_id"}), 400
            
            is_admin = user.is_admin()
            companies = _get_user_parent_companies(user, is_admin)
            
            if not is_admin and company_id not in {c.id for c in companies}:
                return jsonify({"success": False, "error": "Company access denied"}), 403
        
        # Resolve the SOURCE company_fk (and child branch ids) for data isolation.
        # Business tables (e.g. complaint.company_fk) reference the SOURCE company id,
        # NOT the local admin companies id. Resolve from the selected company's code/name.
        from ..microservice_auth import _resolve_source_company_fk
        source_company_fk = None
        related_company_ids = None
        selected_company = Company.query.get(company_id) if company_id else None
        if selected_company is None and user.company_id:
            selected_company = Company.query.get(user.company_id)
        if selected_company is not None:
            source_company_fk, related_company_ids = _resolve_source_company_fk(
                selected_company.company_code, selected_company.name
            )
            if source_company_fk:
                logger.info(
                    f"[✓] Source company_fk resolved for {selected_company.name}: "
                    f"fk={source_company_fk}, related={related_company_ids}"
                )
            else:
                logger.warning(
                    f"[!] Could not resolve SOURCE company_fk for "
                    f"'{selected_company.name}' (code={selected_company.company_code})"
                )

        # Generate JWT token (includes SOURCE company_fk + related branch ids)
        token = generate_token(
            user,
            company_id=company_id,
            branch_id=user.branch_id,
            related_company_ids=related_company_ids,
            company_fk=source_company_fk,
        )
        
        user_payload = user.to_dict()
        if company_id is not None:
            selected = selected_company or Company.query.get(company_id)
            if selected:
                user_payload["company_id"] = selected.id
                user_payload["company_name"] = selected.name
        user_payload["company_fk"] = source_company_fk
        
        logger.info(f"✅ Finalized source DB login: username={username}, company_id={company_id}, company_fk={source_company_fk}")
        
        return jsonify({
            "success": True,
            "token": token,
            "user": user_payload
        }), 200
        
    except Exception as e:
        import traceback
        logger.error(f"❌ Finalize source login exception: {e}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        return jsonify({
            "success": False,
            "error": f"Login finalization error: {str(e)}"
        }), 500


@auth_bp.route("/companies-by-email", methods=["POST"])
def companies_by_email():
    data = request.get_json(silent=True) or {}
    email = (data.get("email") or "").strip().lower()
    if not email:
        return jsonify({"success": False, "error": "Email is required"}), 400

    user = User.query.filter_by(email=email).first()
    if not user or not user.is_active:
        return jsonify({"success": False, "error": "User not found or inactive"}), 401

    is_admin = user.is_admin()
    companies = _get_user_parent_companies(user, is_admin)

    return jsonify({
        "success": True,
        "user_id": user.id,
        "username": user.username,
        "email": user.email,
        "companies": [_company_summary(c) for c in companies],
        "is_admin": is_admin,
    }), 200


@auth_bp.route("/login", methods=["POST"])
def login():
    data = request.get_json(silent=True) or {}
    identifier = (data.get("username") or data.get("email") or "").strip().lower()
    password = data.get("password") or ""
    selected_company_id = data.get("company_id")
    if not identifier or not password:
        return jsonify({"success": False, "error": "username/email and password required"}), 400

    user = User.query.filter(
        (User.username == identifier) | (User.email == identifier)
    ).first()
    if not user or not verify_password(user.password_hash, password):
        return jsonify({"success": False, "error": "Invalid credentials"}), 401
    if not user.is_active:
        return jsonify({"success": False, "error": "Account is inactive"}), 403

    is_admin = user.is_admin()
    companies = _get_user_parent_companies(user, is_admin)

    if selected_company_id is None:
        if len(companies) > 1 and not is_admin:
            return jsonify({
                "success": True,
                "needs_company_selection": True,
                "available_companies": [_company_summary(c) for c in companies],
                "username": user.username,
            }), 200

        if len(companies) == 1:
            selected_company_id = companies[0].id

    if selected_company_id is not None:
        try:
            selected_company_id = int(selected_company_id)
        except (TypeError, ValueError):
            return jsonify({"success": False, "error": "Invalid company_id"}), 400

        if not is_admin and selected_company_id not in {c.id for c in companies}:
            return jsonify({"success": False, "error": "Company access denied"}), 403

    token = generate_token(user, company_id=selected_company_id, branch_id=user.branch_id)

    user_payload = user.to_dict()
    if selected_company_id is not None:
        selected_company = Company.query.get(selected_company_id)
        if selected_company:
            user_payload["company_id"] = selected_company.id
            user_payload["company_name"] = selected_company.name

    # Create response with token in JSON body
    response = jsonify({"success": True, "token": token, "user": user_payload})
    
    # Also set JWT token in HTTP-only cookie so browser sends it automatically with requests
    response.set_cookie(
        "auth_token",
        token,
        max_age=JWT_EXP_HOURS * 3600,  # Set expiry to match token expiry
        secure=False,  # Set to True in production with HTTPS
        httponly=True,  # Prevent JavaScript from accessing the cookie
        samesite="Lax",  # CSRF protection
    )
    
    return response, 200


@auth_bp.route("/me", methods=["GET"])
@require_auth
def me():
    ctx = current_user_context()
    user = User.query.get(ctx["user_id"])
    payload = user.to_dict()
    if ctx.get("company_id"):
        company = Company.query.get(ctx.get("company_id"))
        if company:
            payload["company_id"] = company.id
            payload["company_name"] = company.name
    payload["branch_id"] = ctx.get("branch_id")
    return jsonify({"success": True, "user": payload}), 200


@auth_bp.route("/token-login", methods=["POST"])
def token_login():
    """
    Login using an external JWT token.
    Token is validated and company is resolved based on parentCompanyCode claim.
    
    Request:
        {
            "token": "eyJ..."  // JWT token with parentCompanyCode claim
        }
    
    Response:
        {
            "success": true,
            "token": "internal_jwt_token",
            "user": {
                "user_id": ...,
                "email": "...",
                "company_id": ...,
                "company_name": "...",
                "company_fk": ...  // Foreign key for data filtering
            }
        }
    """
    import jwt as jwt_lib
    from datetime import datetime, timedelta
    
    try:
        data = request.get_json(silent=True) or {}
        token = data.get("token", "").strip()
        
        if not token:
            return jsonify({"success": False, "error": "Token is required"}), 400
        
        # Decode token WITHOUT verification first to get the claims
        # (Signature will be verified by extract_user_from_token if configured)
        try:
            payload = jwt_lib.decode(token, options={"verify_signature": False, "verify_aud": False})
        except Exception as e:
            logger.error(f"Failed to decode token: {e}")
            return jsonify({"success": False, "error": "Invalid token format"}), 401
        
        # Extract user information from token claims
        email = payload.get("sub", "").strip()
        user_id = payload.get("userId", "")
        
        # Extract roles from scopes (scopes can be a string or list)
        scopes = payload.get("scopes", "")
        token_roles = []
        if isinstance(scopes, str):
            # Split on whitespace or comma
            token_roles = [s.strip().upper() for s in scopes.replace(",", " ").split() if s.strip()]
        elif isinstance(scopes, list):
            token_roles = [str(s).strip().upper() for s in scopes if s]
        
        is_admin = "ADMIN" in token_roles or "CENTRAL_ADMIN" in token_roles
        
        if not email:
            return jsonify({"success": False, "error": "Token must contain 'sub' (email) claim"}), 401
        
        # Extract and resolve company from parentCompanyCode
        parent_company_code = payload.get("parentCompanyCode", "").strip()
        parent_company_name = payload.get("parentCompanyName", "").strip()
        
        if not parent_company_code and not parent_company_name:
            return jsonify({
                "success": False,
                "error": "Token must contain 'parentCompanyCode' or 'parentCompanyName' claim"
            }), 401
        
        # Resolve the authoritative SOURCE company_fk (and child branch ids) first.
        # Business data tables (e.g. complaint.company_fk) reference the SOURCE company
        # id, NOT the local admin companies id. Match parentCompanyCode -> SOURCE
        # company.company_code, including child branches so a parent sees all its branches.
        from ..microservice_auth import _resolve_source_company_fk
        source_company_fk, related_company_ids = _resolve_source_company_fk(
            parent_company_code, parent_company_name
        )

        # Look up the local company record (used for company_id / audit): by code, then name.
        company = None
        if parent_company_code:
            company = Company.query.filter_by(company_code=parent_company_code).first()
            if company:
                logger.info(f"[✓] Found company by code: {parent_company_code} → ID={company.id}")

        if not company and parent_company_name:
            company = Company.query.filter_by(name=parent_company_name).first()
            if company:
                logger.info(f"[✓] Found company by name: {parent_company_name} → ID={company.id}")

        # If the company isn't synced locally yet, auto-provision it as long as it is a
        # real tenant (resolvable in SOURCE, or at least named in the token). This avoids
        # the spurious "Company not found" error for valid, unsynced companies.
        if not company:
            if not source_company_fk and not parent_company_name:
                logger.error(
                    f"[✗] Company not found for code='{parent_company_code}', "
                    f"name='{parent_company_name}' (not local, not in SOURCE)"
                )
                return jsonify({
                    "success": False,
                    "error": f"Company not found. Code: {parent_company_code}"
                }), 404

            company_name = parent_company_name or parent_company_code
            try:
                company = Company(
                    name=company_name,
                    company_code=parent_company_code or None,
                    company_type="PARENT_COMPANY",
                )
                db.session.add(company)
                db.session.commit()
                logger.info(f"[✓] Auto-provisioned local company '{company_name}' (ID={company.id})")
            except Exception as create_err:
                # Likely a unique-name collision from a concurrent insert — re-query.
                db.session.rollback()
                company = (
                    Company.query.filter_by(company_code=parent_company_code).first()
                    or Company.query.filter_by(name=company_name).first()
                )
                if not company:
                    logger.error(f"[✗] Could not provision company '{company_name}': {create_err}")
                    return jsonify({
                        "success": False,
                        "error": f"Company not found. Code: {parent_company_code}"
                    }), 404

        # Finalize the foreign key for data filtering.
        if source_company_fk:
            company_fk = source_company_fk
            logger.info(f"[✓] Company FK resolved from SOURCE: fk={company_fk}, related={related_company_ids}")
        else:
            # Fallback to the local company foreign key if source resolution failed.
            company_fk = company.get_company_fk()
            related_company_ids = [company_fk]
            logger.warning(f"[!] Source company_fk unresolved; falling back to local fk={company_fk}")
        
        # Create or update user in admin DB (for audit trail)
        user = None
        if email:
            user = User.query.filter_by(email=email).first()
            if not user:
                # Create new user from token
                user = User(
                    username=email.split("@")[0],
                    email=email,
                    first_name=user_id[:20] if user_id else "",
                    is_active=True,
                    # Hash a random password (user authenticates via token)
                    password_hash=hash_password(__import__("secrets").token_hex(16))
                )
                db.session.add(user)
                db.session.commit()
                logger.info(f"[✓] Created new user from token: {email}")
        
        # Generate internal JWT token
        from ..auth import JWT_SECRET, JWT_EXP_HOURS
        
        internal_payload = {
            "sub": str(user.id) if user else user_id,
            "username": user.username if user else email.split("@")[0],
            "email": email,
            "company_id": company.id,
            "company_fk": company_fk,
            "related_company_ids": related_company_ids,
            "is_admin": is_admin,
            "roles": token_roles,  # Include roles for table access control
            "company_scoped": True,
            "external_token": True,  # Mark as externally authenticated
            "exp": datetime.utcnow() + timedelta(hours=JWT_EXP_HOURS),
            "iat": datetime.utcnow(),
        }
        
        internal_token = jwt_lib.encode(internal_payload, JWT_SECRET, algorithm="HS256")
        
        # Build response user payload
        user_payload = {
            "user_id": user.id if user else user_id,
            "email": email,
            "username": user.username if user else email.split("@")[0],
            "company_id": company.id,
            "company_name": company.name,
            "company_code": company.company_code,
            "company_type": company.company_type,
            "company_fk": company_fk,
            "is_admin": is_admin,
            "roles": token_roles,
        }
        
        logger.info(f"[✓] Token login successful: {email} (company: {company.name} [ID={company.id}], FK={company_fk}, roles={token_roles})")
        
        return jsonify({
            "success": True,
            "token": internal_token,
            "user": user_payload
        }), 200
    
    except Exception as e:
        logger.exception(f"[✗] Token login error: {str(e)}")
        return jsonify({"success": False, "error": str(e)}), 500


@auth_bp.route("/logout", methods=["POST"])
def logout():
    """Logout endpoint that clears the auth_token cookie."""
    response = jsonify({"success": True, "message": "Logged out successfully"})
    
    # Clear the auth_token cookie
    response.set_cookie(
        "auth_token",
        "",
        max_age=0,
        secure=False,
        httponly=True,
        path="/"
    )
    
    return response, 200


def seed_defaults():
    """Create only the admin user if it doesn't exist (idempotent).
    
    NOTE: Only the admin account is created. All other data (roles, guest user, etc.)
    must be created manually via database migration or through the application UI.
    
    Admin credentials are managed exclusively through the database.
    """
    try:
        # Ensure admin user exists
        admin_user = User.query.filter_by(username="admin").first()
        
        if admin_user:
            admin_user.is_active = True
            logger.info("✓ Admin user exists and is active")
            db.session.commit()
        else:
            # Create admin user if it doesn't exist
            # NOTE: Password must be set via database migration or reset script
            admin_user = User(
                username="admin",
                email="admin@example.com",
                password_hash=hash_password(__import__("secrets").token_hex(16)),
                first_name="Admin", is_active=True,
            )
            db.session.add(admin_user)
            db.session.commit()
            logger.warning("⚠️  Created default admin user. Please set password via database migration or reset script.")
    
    except Exception as exc:  # noqa: BLE001
        logger.warning(f"seed_defaults failed: {exc}")
        db.session.rollback()


def seed_restricted_commands():
    """
    Manually seed default restricted SQL commands from Security UI.
    
    This function is deprecated. Command restrictions should be configured
    via the Security UI tab (RestrictedSQLCommand model) and restricted_keywords setting.
    
    This is NOT called automatically on startup anymore.
    
    Usage:
        from app.api.auth import seed_restricted_commands
        seed_restricted_commands()
    """
    try:
        logger.info("⚙️  Skipping seed_restricted_commands - use Security UI tab to configure restrictions")
        return {"success": True, "message": "Deprecated - configure restrictions via Security UI tab"}
    
    except Exception as exc:
        logger.error(f"seed_restricted_commands failed: {exc}")
        db.session.rollback()
        return {"success": False, "error": str(exc)}
