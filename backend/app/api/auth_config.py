"""Authentication configuration endpoints - configure SOURCE database table/field mappings."""
import logging
import os
from flask import Blueprint, request, jsonify, g
import bcrypt
from sqlalchemy import text, create_engine, inspect, MetaData
from sqlalchemy.orm import Session

from ..extensions import db
from ..models import AuthConfig, SecuritySetting, User, Role, UserRole
from ..config import Config
from ..auth import require_auth, current_user_context

logger = logging.getLogger(__name__)

auth_config_bp = Blueprint('auth_config', __name__, url_prefix='/api/auth-config')


def get_source_engine():
    """Get SQLAlchemy engine for the SOURCE database."""
    db_url = Config.SOURCE_DB_URL
    if not db_url:
        raise Exception("SOURCE_DB_URL not configured")
    return create_engine(db_url)


def _check_source_db_configured():
    """Check if SOURCE database is configured. Returns error response if not, None if OK."""
    if not Config.SOURCE_DB_URL:
        return jsonify({
            'success': False,
            'error': 'SOURCE database not configured. Set SOURCE_DB_URL environment variable.',
            'guidance': 'Export: SOURCE_DB_URL="postgresql://user:password@host:port/dbname" or similar'
        }), 503


def _check_docs_folder_configured():
    """Check if docs folder is configured. Returns error response if not, None if OK."""
    docs_path = os.getenv("DOCS_FOLDER", "")
    if not docs_path or not os.path.exists(docs_path):
        return jsonify({
            'success': False,
            'error': 'Docs folder not configured or not found.',
            'guidance': f'Set DOCS_FOLDER environment variable. Current: {docs_path}'
        }), 503


@auth_config_bp.route('/config', methods=['GET'])
@require_auth
def get_auth_config():
    """Get current authentication configuration (admin only)."""
    ctx = current_user_context() or {}
    if not ctx.get("is_admin"):
        return jsonify({
            'success': False,
            'error': 'Admin access required'
        }), 403
    
    try:
        config = AuthConfig.query.first()
        if not config:
            return jsonify({
                'success': True,
                'config': None,
                'configured': False
            })
        
        return jsonify({
            'success': True,
            'config': config.to_dict(),
            'configured': config.configured
        })
    except Exception as e:
        logger.error(f"Error getting auth config: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@auth_config_bp.route('/config', methods=['POST'])
@require_auth
def save_auth_config():
    """Save authentication configuration."""
    try:
        data = request.get_json()
        
        # Get or create config
        config = AuthConfig.query.first()
        if not config:
            config = AuthConfig()
            db.session.add(config)
        
        # Update fields
        config.users_table = data.get('users_table') or None
        config.username_field = data.get('username_field') or None
        config.password_field = data.get('password_field') or None
        config.is_active_field = data.get('is_active_field') or None
        is_active_value = data.get('is_active_value', '').strip()
        config.is_active_value = is_active_value if is_active_value else None
        config.password_hash_type = data.get('password_hash_type', 'bcrypt')
        
        config.company_table = data.get('company_table')
        config.company_id_field = data.get('company_id_field')
        config.company_name_field = data.get('company_name_field')
        config.user_company_fk_field = data.get('user_company_fk_field')
        config.user_companies_junction_table = data.get('user_companies_junction_table')
        config.user_companies_user_fk = data.get('user_companies_user_fk')
        config.user_companies_company_fk = data.get('user_companies_company_fk')
        
        config.roles_table = data.get('roles_table')
        config.role_id_field = data.get('role_id_field')
        config.role_name_field = data.get('role_name_field')
        config.user_roles_junction_table = data.get('user_roles_junction_table')
        config.user_roles_user_fk = data.get('user_roles_user_fk')
        config.user_roles_role_fk = data.get('user_roles_role_fk')
        
        config.banned_keywords = data.get('banned_keywords')
        config.configured = True
        
        db.session.commit()
        
        logger.info(f"✅ Auth config saved")
        logger.info(f"   Users table: {config.users_table}")
        logger.info(f"   Company table: {config.company_table}")
        
        return jsonify({
            'success': True,
            'message': 'Authentication configuration saved',
            'config': config.to_dict()
        })
    
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error saving auth config: {str(e)}", exc_info=True)
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@auth_config_bp.route('/security', methods=['GET'])
def get_security_config():
    """Get security configuration (banned keywords, etc)."""
    try:
        config = SecuritySetting.query.first()
        if not config:
            return jsonify({
                'success': True,
                'config': None
            })
        
        return jsonify({
            'success': True,
            'config': config.to_dict()
        })
    except Exception as e:
        logger.error(f"Error getting security config: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@auth_config_bp.route('/security', methods=['POST'])
@require_auth
def save_security_config():
    """Save security configuration."""
    try:
        data = request.get_json()
        
        config = SecuritySetting.query.first()
        if not config:
            config = SecuritySetting()
            db.session.add(config)
        
        config.sql_banned_keywords = data.get('sql_banned_keywords')
        config.require_password_in_results = data.get('require_password_in_results', False)
        
        db.session.commit()
        
        logger.info(f"✅ Security config saved")
        
        return jsonify({
            'success': True,
            'message': 'Security configuration saved',
            'config': config.to_dict()
        })
    
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error saving security config: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@auth_config_bp.route('/source-tables', methods=['GET'])
def get_source_tables():
    """Get list of tables from SOURCE database."""
    # Check if SOURCE database is configured
    check_result = _check_source_db_configured()
    if check_result:
        return check_result
    
    try:
        engine = get_source_engine()
        inspector = inspect(engine)
        
        tables = []
        for table_name in sorted(inspector.get_table_names()):
            if not table_name.startswith('sqlite_') and table_name not in ['alembic_version']:
                columns = [col['name'] for col in inspector.get_columns(table_name)]
                
                # Get row count
                try:
                    with engine.connect() as conn:
                        result = conn.execute(text(f'SELECT COUNT(*) as count FROM "{table_name}"'))
                        row_count = result.scalar() or 0
                except Exception as count_error:
                    logger.warning(f"Could not get row count for {table_name}: {str(count_error)}")
                    row_count = 0
                
                tables.append({
                    'name': table_name,
                    'columns': columns,
                    'row_count': row_count
                })
        
        return jsonify({
            'success': True,
            'tables': tables
        })
    
    except Exception as e:
        logger.error(f"Error getting source tables: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e),
            'guidance': 'Verify SOURCE_DB_URL is correctly configured and the database is accessible'
        }), 500


@auth_config_bp.route('/source-columns/<table_name>', methods=['GET'])
def get_source_columns(table_name):
    """Get columns from a specific SOURCE table."""
    try:
        engine = get_source_engine()
        inspector = inspect(engine)
        
        if table_name not in inspector.get_table_names():
            return jsonify({
                'success': False,
                'error': f'Table {table_name} not found'
            }), 404
        
        columns = []
        for col in inspector.get_columns(table_name):
            columns.append({
                'name': col['name'],
                'type': str(col['type']),
                'nullable': col['nullable']
            })
        
        return jsonify({
            'success': True,
            'table': table_name,
            'columns': columns
        })
    
    except Exception as e:
        logger.error(f"Error getting columns: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@auth_config_bp.route('/verify', methods=['POST'])
def verify_config():
    """Verify that auth config is valid by testing a connection."""
    try:
        config = AuthConfig.query.first()
        if not config:
            return jsonify({
                'success': False,
                'error': 'No configuration found'
            }), 400
        
        if not config.users_table or not config.username_field or not config.password_field:
            return jsonify({
                'success': False,
                'error': 'Users table configuration incomplete'
            }), 400
        
        engine = get_source_engine()
        
        # Test: Try to query users table
        try:
            with engine.connect() as conn:
                result = conn.execute(text(f'SELECT COUNT(*) as count FROM "{config.users_table}" LIMIT 1'))
                row_count = result.scalar() or 0
            
            return jsonify({
                'success': True,
                'message': 'Configuration verified successfully',
                'test_result': {
                    'table': config.users_table,
                    'row_count': row_count
                }
            })
        except Exception as test_error:
            return jsonify({
                'success': False,
                'error': f'Could not query {config.users_table}: {str(test_error)}'
            }), 400
    
    except Exception as e:
        logger.error(f"Error verifying config: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@auth_config_bp.route('/test-user-auth', methods=['POST'])
def test_user_auth():
    """Test authentication with a specific username/password."""
    try:
        data = request.get_json()
        username = data.get('username')
        password = data.get('password')
        
        if not username or not password:
            return jsonify({
                'success': False,
                'error': 'Username and password required'
            }), 400
        
        config = AuthConfig.query.first()
        if not config or not config.users_table:
            return jsonify({
                'success': False,
                'error': 'Auth configuration not complete'
            }), 400
        
        engine = get_source_engine()
        
        # Query user from SOURCE database
        try:
            with engine.connect() as conn:
                result = conn.execute(
                    text(f'''SELECT * FROM "{config.users_table}" WHERE "{config.username_field}" = :username LIMIT 1'''),
                    {'username': username}
                )
                user_row = result.first()
        except Exception as query_error:
            logger.error(f"Error querying user: {str(query_error)}")
            return jsonify({
                'success': False,
                'error': f'Database query error: {str(query_error)}'
            }), 500
        
        if not user_row:
            return jsonify({
                'success': False,
                'found': False,
                'error': 'User not found'
            }), 401
        
        user_row_dict = dict(user_row._mapping)
        
        # Check if user is active
        is_active_field = config.is_active_field
        if is_active_field and is_active_field in user_row_dict:
            if not user_row_dict[is_active_field]:
                return jsonify({
                    'success': False,
                    'found': True,
                    'active': False,
                    'error': 'User is not active'
                }), 401
        
        # Verify password
        stored_password_hash = user_row_dict.get(config.password_field)
        
        if config.password_hash_type == 'bcrypt':
            try:
                if isinstance(stored_password_hash, str):
                    stored_password_hash = stored_password_hash.encode()
                if not bcrypt.checkpw(password.encode(), stored_password_hash):
                    return jsonify({
                        'success': False,
                        'found': True,
                        'active': True,
                        'error': 'Invalid password'
                    }), 401
            except Exception as bcrypt_error:
                logger.error(f"Bcrypt error: {str(bcrypt_error)}")
                return jsonify({
                    'success': False,
                    'error': f'Password verification error: {str(bcrypt_error)}'
                }), 500
        elif config.password_hash_type == 'plaintext':
            if password != stored_password_hash:
                return jsonify({
                    'success': False,
                    'found': True,
                    'active': True,
                    'error': 'Invalid password'
                }), 401
        
        return jsonify({
            'success': True,
            'message': 'Authentication successful',
            'user': {
                'username': username,
                'found': True,
                'active': True
            }
        })
    
    except Exception as e:
        logger.error(f"Error testing auth: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@auth_config_bp.route('/change-user-password', methods=['POST'])
@require_auth
def change_user_password():
    """
    Change a user's password in the SOURCE database.
    Admin only endpoint for password reset functionality.
    """
    try:
        # Get user context from request
        ctx = current_user_context()
        user_id = ctx.get('user_id')
        is_admin = ctx.get('is_admin')
        
        if not user_id:
            return jsonify({'error': 'User not found'}), 401
        
        # Check if user is admin
        if not is_admin:
            return jsonify({'error': 'Access denied - admin role required'}), 403
        
        data = request.get_json()
        email = data.get('email', '').strip()
        new_password = data.get('newPassword', '').strip()
        
        if not email:
            return jsonify({'error': 'Email is required'}), 400
        
        if not new_password:
            return jsonify({'error': 'New password is required'}), 400
        
        if len(new_password) < 6:
            return jsonify({'error': 'Password must be at least 6 characters'}), 400
        
        # Get auth config
        config = AuthConfig.query.first()
        if not config or not config.configured:
            return jsonify({'error': 'Authentication not configured'}), 400
        
        if not config.users_table or not config.username_field or not config.password_field:
            return jsonify({'error': 'Authentication configuration incomplete'}), 400
        
        engine = get_source_engine()
        
        # Find user by email
        try:
            with engine.connect() as conn:
                result = conn.execute(
                    text(f'''SELECT * FROM "{config.users_table}" WHERE "{config.username_field}" = :email LIMIT 1'''),
                    {'email': email}
                )
                user_row = result.first()
        except Exception as query_error:
            return jsonify({'error': f'Database query error: {str(query_error)}'}), 500
        
        if not user_row:
            logger.warning(f"🔑 Password change attempt for non-existent user: {email}")
            return jsonify({'error': 'User not found'}), 404
        
        user_row_dict = dict(user_row._mapping)
        
        # Hash the new password
        if config.password_hash_type == 'bcrypt':
            new_password_hash = bcrypt.hashpw(new_password.encode(), bcrypt.gensalt()).decode()
        elif config.password_hash_type == 'plaintext':
            new_password_hash = new_password
        else:
            return jsonify({'error': f'Unsupported password hash type: {config.password_hash_type}'}), 400
        
        # Get the primary key column name
        pk_column = None
        if 'id' in user_row_dict:
            pk_column = 'id'
        else:
            for col in user_row_dict.keys():
                if col.endswith('_id'):
                    pk_column = col
                    break
        
        if not pk_column:
            return jsonify({'error': 'Could not identify user primary key'}), 500
        
        user_id = user_row_dict[pk_column]
        
        # Update password in SOURCE database
        try:
            with engine.connect() as conn:
                conn.execute(
                    text(f'''UPDATE "{config.users_table}" SET "{config.password_field}" = :new_password WHERE "{pk_column}" = :user_id'''),
                    {'new_password': new_password_hash, 'user_id': user_id}
                )
                conn.commit()
            
            logger.info(f"✅ Password changed successfully for user: {email}")
            return jsonify({
                'success': True,
                'message': f'Password changed successfully for user: {email}'
            })
        
        except Exception as update_error:
            logger.error(f"Error updating password: {str(update_error)}")
            return jsonify({'error': f'Failed to update password: {str(update_error)}'}), 500
    
    except Exception as e:
        logger.error(f"Error changing password: {str(e)}", exc_info=True)
        return jsonify({'error': str(e)}), 500


# ===================== TABLE ROLE ACCESS CONTROL =====================


@auth_config_bp.route('/table-role-access/tables', methods=['GET'])
def get_table_role_access_tables():
    """Get all source database tables with their role access configuration."""
    # Check if SOURCE database is configured
    check_result = _check_source_db_configured()
    if check_result:
        return check_result
    
    try:
        from ..models import TableRoleAccess
        
        engine = get_source_engine()
        inspector = inspect(engine)
        
        # Get all source database roles
        source_roles = _get_source_db_roles(engine)
        
        tables = []
        for table_name in sorted(inspector.get_table_names()):
            if not table_name.startswith('sqlite_') and table_name not in ['alembic_version']:
                # Get roles that have access to this table
                accesses = TableRoleAccess.query.filter_by(table_name=table_name).all()
                accessible_role_names = [a.role.name for a in accesses if a.role]
                
                # Map all source DB roles to access status
                role_access = []
                for role_name in source_roles:
                    role_access.append({
                        'role_name': role_name,
                        'has_access': role_name in accessible_role_names
                    })
                
                tables.append({
                    'table_name': table_name,
                    'role_access': role_access
                })
        
        return jsonify({
            'success': True,
            'tables': tables
        })
    
    except Exception as e:
        logger.error(f"Error getting table role access: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e),
            'guidance': 'Verify SOURCE_DB_URL is correctly configured and the database is accessible'
        }), 500


def _get_source_db_roles(engine) -> list:
    """Get all role names from source database (from roles table configured in auth config)."""
    try:
        config = AuthConfig.query.first()
        if not config or not config.roles_table or not config.role_name_field:
            logger.debug("Auth config not properly configured for roles")
            return []
        
        with engine.connect() as conn:
            # Query source database roles table
            result = conn.execute(text(f'SELECT DISTINCT "{config.role_name_field}" FROM "{config.roles_table}" ORDER BY "{config.role_name_field}"'))
            roles = [row[0] for row in result.fetchall() if row[0]]
            return roles
    except Exception as e:
        logger.warning(f"Could not fetch source DB roles: {e}")
        return []


@auth_config_bp.route('/table-role-access/roles', methods=['GET'])
def get_table_role_access_roles():
    """Get all roles from SOURCE database for table access control."""
    try:
        engine = get_source_engine()
        source_roles = _get_source_db_roles(engine)
        
        return jsonify({
            'success': True,
            'roles': [{'name': name} for name in source_roles]
        })
    except Exception as e:
        logger.error(f"Error getting source DB roles: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@auth_config_bp.route('/table-role-access/initialize', methods=['POST'])
@require_auth
def initialize_table_role_access():
    """Initialize table-role access: all roles have access to all tables by default."""
    try:
        from ..models import TableRoleAccess
        
        engine = get_source_engine()
        inspector = inspect(engine)
        
        # Get all source database roles
        source_roles = _get_source_db_roles(engine)
        if not source_roles:
            return jsonify({
                'success': False,
                'error': 'No roles found in source database. Please configure authentication first.'
            }), 400
        
        # Get or create roles in admin DB
        admin_roles = []
        for source_role_name in source_roles:
            role = Role.query.filter_by(name=source_role_name).first()
            if not role:
                # Auto-create role from source database
                role = Role(
                    name=source_role_name,
                    description=f"Source database role: {source_role_name}",
                    is_admin=False,
                    is_system_role=False
                )
                db.session.add(role)
                db.session.flush()
                logger.info(f"➕ Created new role '{source_role_name}' from source database")
            admin_roles.append(role)
        
        # Get all tables from source database
        table_names = [t for t in inspector.get_table_names() 
                      if not t.startswith('sqlite_') and t not in ['alembic_version']]
        
        initialized_count = 0
        
        # Create access records: each role has access to all tables
        for table_name in table_names:
            for role in admin_roles:
                # Check if this access record already exists
                existing = TableRoleAccess.query.filter_by(
                    table_name=table_name, 
                    role_id=role.id
                ).first()
                
                if not existing:
                    access = TableRoleAccess(table_name=table_name, role_id=role.id)
                    db.session.add(access)
                    initialized_count += 1
        
        db.session.commit()
        
        logger.info(f"✅ Initialized table-role access: {len(table_names)} tables × {len(admin_roles)} roles")
        
        return jsonify({
            'success': True,
            'message': f'Initialized {initialized_count} table-role access records',
            'tables_count': len(table_names),
            'roles_count': len(admin_roles)
        })
    
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error initializing table role access: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@auth_config_bp.route('/table-role-access/update', methods=['POST'])
@require_auth
def update_table_role_access():
    """Update table-role access configuration."""
    try:
        from ..models import TableRoleAccess
        
        data = request.get_json()
        table_name = data.get('table_name')
        role_name = data.get('role_name')
        has_access = data.get('has_access', False)
        
        if not table_name or not role_name:
            return jsonify({
                'success': False,
                'error': 'table_name and role_name are required'
            }), 400
        
        # Find or create the role in admin DB
        role = Role.query.filter_by(name=role_name).first()
        if not role:
            # Auto-create role from source database if it doesn't exist in admin DB
            role = Role(
                name=role_name,
                description=f"Source database role: {role_name}",
                is_admin=False,
                is_system_role=False
            )
            db.session.add(role)
            db.session.flush()
            logger.info(f"➕ Created new role '{role_name}' from source database")
        
        # Check if access record exists
        access = TableRoleAccess.query.filter_by(
            table_name=table_name, 
            role_id=role.id
        ).first()
        
        if has_access:
            # Grant access
            if not access:
                access = TableRoleAccess(table_name=table_name, role_id=role.id)
                db.session.add(access)
            db.session.commit()
            logger.info(f"✅ Granted access to table '{table_name}' for role '{role_name}'")
        else:
            # Revoke access
            if access:
                db.session.delete(access)
                db.session.commit()
            logger.info(f"✅ Revoked access to table '{table_name}' for role '{role_name}'")
        
        return jsonify({
            'success': True,
            'message': f'Access {"granted" if has_access else "revoked"}'
        })
    
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error updating table role access: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500
