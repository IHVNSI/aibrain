"""
Role hierarchy validation and enforcement.

Ensures that role assignments respect the Clientshot role structure:
- Workspace: Admin, Support
- Branch: Branch Admin, Branch Support, Admin, Support
- Parent Company: Central Admin, Regional Admin, Admin, Support, User
"""
import logging
from typing import List, Optional, Dict

from .extensions import db
from .models import Role, User, Company, Branch, UserRole

logger = logging.getLogger(__name__)


# Role definitions by entity type
ROLE_HIERARCHY = {
    "WORKSPACE": {
        "allowed_roles": ["Admin", "Support", "User"],
        "description": "Single company with no branches",
    },
    "BRANCH": {
        "allowed_roles": ["Branch Admin", "Branch Support", "Admin", "Support", "User"],
        "description": "Child entity within parent company",
    },
    "PARENT_COMPANY": {
        "allowed_roles": ["Central Admin", "Regional Admin", "Admin", "Support", "User"],
        "description": "Company with one or more branches",
    },
}

# Role hierarchy levels (for permission checks)
ROLE_LEVELS = {
    "Central Admin": 5,      # Highest: all branches in parent company
    "Regional Admin": 4,     # Multiple/specific branches in parent company
    "Branch Admin": 4,       # Single branch admin
    "Admin": 3,              # Admin within entity
    "Branch Support": 2,     # Branch support staff
    "Support": 2,            # Support staff
    "User": 1,               # Standard user
}


def get_valid_roles_for_entity(company_type: str) -> List[Role]:
    """Get list of valid roles for a given entity type (WORKSPACE/BRANCH/PARENT_COMPANY).
    
    Args:
        company_type: One of WORKSPACE, BRANCH, PARENT_COMPANY
        
    Returns:
        List of Role objects valid for this entity type
    """
    if company_type not in ROLE_HIERARCHY:
        logger.warning(f"Unknown company type: {company_type}")
        return []
    
    allowed_role_names = ROLE_HIERARCHY[company_type]["allowed_roles"]
    roles = Role.query.filter(Role.name.in_(allowed_role_names)).all()
    return roles


def validate_role_assignment(
    user: User,
    target_user: User,
    role: Role,
    company: Company,
    branch: Optional[Branch] = None,
) -> tuple[bool, str]:
    """
    Validate if user can assign role to target_user for given entity.
    
    Args:
        user: User attempting the assignment
        target_user: User receiving the role
        role: Role being assigned
        company: Company/workspace context
        branch: Branch context (if applicable)
        
    Returns:
        (is_valid, reason_if_invalid)
    """
    if not user or not target_user or not role or not company:
        return False, "Missing required parameters"
    
    # Get assigning user's roles
    user_role_names = [r.name for r in user.roles()]
    
    # Get valid roles for this entity
    entity_type = company.company_type
    valid_roles = get_valid_roles_for_entity(entity_type)
    valid_role_names = [r.name for r in valid_roles]
    
    # Check if role is valid for this entity type
    if role.name not in valid_role_names:
        return False, f"Role '{role.name}' is not valid for {entity_type} entity"
    
    # Central Admin: Can assign roles to any branch within parent company
    if "Central Admin" in user_role_names:
        if entity_type in ["BRANCH", "PARENT_COMPANY"]:
            # Central Admin can assign to branches or parent company
            if role.name in valid_role_names:
                return True, ""
        return False, "Central Admin can only assign roles within their parent company"
    
    # Regional Admin: Can only assign to their assigned branches
    if "Regional Admin" in user_role_names:
        if not branch:
            return False, "Regional Admin must specify a branch context"
        
        # Check if user is assigned to manage this branch
        assigned_branches = user.assigned_branches or []
        if isinstance(assigned_branches, str):
            try:
                import json
                assigned_branches = json.loads(assigned_branches)
            except:
                assigned_branches = []
        
        if branch.id not in assigned_branches:
            return False, f"Regional Admin not assigned to manage branch {branch.id}"
        
        if role.name in ["Branch Admin", "Branch Support", "Admin", "Support"]:
            return True, ""
        
        return False, f"Regional Admin cannot assign role '{role.name}'"
    
    # Branch Admin: Can assign roles within their branch only
    if "Branch Admin" in user_role_names:
        if entity_type != "BRANCH":
            return False, "Branch Admin can only assign roles within their branch"
        
        if user.branch_id != branch.id:
            return False, f"Branch Admin not assigned to branch {branch.id}"
        
        if role.name in ["Branch Admin", "Branch Support", "Admin", "Support"]:
            return True, ""
        
        return False, f"Branch Admin cannot assign role '{role.name}'"
    
    # Admin: Can assign roles within own entity only
    if "Admin" in user_role_names:
        if user.company_id != company.id:
            return False, "Admin can only assign roles within their company"
        
        if role.name in ["Admin", "Support"]:
            return True, ""
        
        return False, f"Admin cannot assign role '{role.name}'"
    
    # Support: Cannot assign roles
    if "Support" in user_role_names or "Branch Support" in user_role_names:
        return False, "Support staff cannot assign roles"
    
    return False, "User does not have permission to assign roles"


def can_user_access_entity(user: User, company: Company, branch: Optional[Branch] = None) -> bool:
    """
    Check if user can access (view/modify) an entity.
    
    Args:
        user: User attempting access
        company: Company/workspace context
        branch: Branch context (if applicable)
        
    Returns:
        True if user can access this entity
    """
    # Admin users bypass all checks (backward compatibility)
    if user.is_admin():
        return True
    
    # User must be assigned to company
    if user.company_id != company.id and company not in user.companies:
        return False
    
    # If branch context, user must be assigned to it (or be a higher-level admin)
    if branch:
        user_role_names = [r.name for r in user.roles()]
        
        # Central Admin: Can access any branch in their parent company
        if "Central Admin" in user_role_names:
            if branch.company_id == company.id:
                return True
        
        # Regional Admin: Can access assigned branches
        if "Regional Admin" in user_role_names:
            assigned_branches = user.assigned_branches or []
            if isinstance(assigned_branches, str):
                try:
                    import json
                    assigned_branches = json.loads(assigned_branches)
                except:
                    assigned_branches = []
            if branch.id in assigned_branches:
                return True
        
        # Branch-scoped users: must be in that branch
        if user.branch_id == branch.id:
            return True
        
        return False
    
    return True


def get_user_accessible_entities(user: User) -> Dict[str, list]:
    """
    Get all entities (workspaces, parent companies, branches) a user can access.
    
    Args:
        user: User
        
    Returns:
        Dict with keys: workspaces, parent_companies, branches
    """
    user_role_names = [r.name for r in user.roles()]
    result = {"workspaces": [], "parent_companies": [], "branches": []}
    
    # Admin users see everything
    if user.is_admin():
        result["workspaces"] = Company.query.filter_by(company_type="WORKSPACE", is_active=True).all()
        result["parent_companies"] = Company.query.filter_by(company_type="PARENT_COMPANY", is_active=True).all()
        result["branches"] = Branch.query.filter_by(is_active=True).all()
        return result
    
    # Central Admin: sees all branches in parent company + parent company
    if "Central Admin" in user_role_names:
        if user.company_id:
            parent = Company.query.get(user.company_id)
            if parent:
                result["parent_companies"].append(parent)
                result["branches"] = Branch.query.filter_by(company_id=parent.id, is_active=True).all()
    
    # Regional Admin: sees assigned branches only
    elif "Regional Admin" in user_role_names:
        assigned_branches = user.assigned_branches or []
        if isinstance(assigned_branches, str):
            try:
                import json
                assigned_branches = json.loads(assigned_branches)
            except:
                assigned_branches = []
        
        if assigned_branches:
            result["branches"] = Branch.query.filter(
                Branch.id.in_(assigned_branches),
                Branch.is_active == True
            ).all()
    
    # Regular users: see only their assigned entity
    else:
        if user.company_id:
            company = Company.query.get(user.company_id)
            if company:
                if company.company_type == "WORKSPACE":
                    result["workspaces"].append(company)
                elif company.company_type == "PARENT_COMPANY":
                    result["parent_companies"].append(company)
        
        if user.branch_id:
            branch = Branch.query.get(user.branch_id)
            if branch:
                result["branches"].append(branch)
    
    return result


def assign_role_to_user(
    user: User,
    role: Role,
    company: Company,
    branch: Optional[Branch] = None,
    assigned_branches: Optional[List[int]] = None,
) -> tuple[bool, str]:
    """
    Assign a role to a user in the given context.
    
    Args:
        user: User receiving the role
        role: Role to assign
        company: Company/workspace context
        branch: Branch context (if applicable)
        assigned_branches: List of branch IDs (for Regional Admin role)
        
    Returns:
        (success, message)
    """
    try:
        # Validate role is appropriate for entity type
        valid_roles = get_valid_roles_for_entity(company.company_type)
        if role not in valid_roles:
            return False, f"Role '{role.name}' not valid for {company.company_type}"
        
        # Check if assignment already exists
        existing = UserRole.query.filter_by(user_id=user.id, role_id=role.id).first()
        if existing:
            return False, "User already has this role"
        
        # Assign role
        user_role = UserRole(user_id=user.id, role_id=role.id)
        db.session.add(user_role)
        
        # If Regional Admin, store assigned branches
        if role.name == "Regional Admin" and assigned_branches:
            import json
            user.assigned_branches = json.dumps(assigned_branches)
        
        db.session.commit()
        logger.info(f"✓ Assigned role '{role.name}' to user {user.username}")
        return True, f"Role '{role.name}' assigned successfully"
    
    except Exception as e:
        db.session.rollback()
        logger.error(f"Failed to assign role: {e}")
        return False, f"Failed to assign role: {str(e)}"


def validate_role_hierarchy(company: Company) -> List[str]:
    """
    Validate role hierarchy consistency for a company.
    
    Args:
        company: Company to validate
        
    Returns:
        List of validation warnings/errors (empty if valid)
    """
    issues = []
    
    if company.company_type not in ROLE_HIERARCHY:
        issues.append(f"Unknown company_type: {company.company_type}")
        return issues
    
    required_roles = ROLE_HIERARCHY[company.company_type]["allowed_roles"]
    existing_roles = set()
    
    # Check all users in this company for role validity
    users = User.query.filter_by(company_id=company.id).all()
    for user in users:
        user_role_names = [r.name for r in user.roles()]
        for role_name in user_role_names:
            if role_name not in required_roles:
                issues.append(f"User {user.username} has invalid role '{role_name}' for {company.company_type}")
            existing_roles.add(role_name)
    
    return issues
