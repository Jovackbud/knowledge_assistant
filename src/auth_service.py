import logging
from typing import Dict, Optional, Any
from database_utils import get_user_profile, add_or_update_user_profile
from config import DEFAULT_HIERARCHY_LEVEL

logger = logging.getLogger(__name__)


def fetch_user_access_profile(user_email: str) -> Optional[Dict[str, Any]]:
    """
    Fetch user profile with attributes for the advanced hybrid RBAC/ABAC.
    """
    if not user_email or not isinstance(user_email, str) or "@" not in user_email:
        logger.warning(f"Attempted to fetch profile with invalid email: '{user_email}'.")
        return None

    try:
        profile = get_user_profile(user_email)
        if not profile:
            return None  # get_user_profile already logs this

        # Validate structure and types for fields used in RAG logic
        # get_user_profile should already ensure these types or provide defaults
        required_fields_types = {
            "user_hierarchy_level": int,
            "departments": list,
            "projects_membership": list,
            "contextual_roles": dict
        }

        for field, expected_type in required_fields_types.items():
            if field not in profile:
                logger.error(
                    f"Profile for {user_email} is missing critical field: '{field}'. This indicates an issue in get_user_profile or DB schema. Profile: {profile}")
                return None
            if not isinstance(profile[field], expected_type):
                logger.error(
                    f"Profile field '{field}' for {user_email} has incorrect type. Expected {expected_type}, got {type(profile[field])}. Profile: {profile}")
                # Attempt to fix critical fields, otherwise fail
                if field == "user_hierarchy_level":
                    profile[field] = DEFAULT_HIERARCHY_LEVEL
                elif field == "departments" or field == "projects_membership":
                    profile[field] = []
                elif field == "contextual_roles":
                    profile[field] = {}
                else:
                    return None  # Unknown critical field type mismatch

        logger.info(f"Successfully fetched and validated profile for {user_email}.")
        return profile
    except Exception as e:
        logger.error(f"Error fetching or validating profile for {user_email}: {e}", exc_info=True)
        return None


def get_or_create_test_user_profile(user_email: str) -> Optional[Dict[str, Any]]:
    """
    Testing utility: Fetches/creates a default profile. Not for production.
    Uses simplified logic to assign attributes based on email string for demo purposes.
    """
    profile = fetch_user_access_profile(user_email)
    if profile:
        return profile

    logger.warning(f"Test user profile for {user_email} not found, creating a heuristic-based one.")
    from config import KNOWN_DEPARTMENT_TAGS, ROLE_SPECIFIC_FOLDER_TAGS

    departments = []
    if "hr" in user_email and KNOWN_DEPARTMENT_TAGS: departments.append(KNOWN_DEPARTMENT_TAGS[0])
    if "it" in user_email and len(KNOWN_DEPARTMENT_TAGS) > 1: departments.append(KNOWN_DEPARTMENT_TAGS[1])

    projects_membership = []
    if "alpha" in user_email: projects_membership.append("PROJECT_ALPHA")
    if "beta" in user_email: projects_membership.append("PROJECT_BETA")

    hierarchy_level = DEFAULT_HIERARCHY_LEVEL
    if "manager" in user_email: hierarchy_level = 1
    if "exec" in user_email: hierarchy_level = 2
    if "board" in user_email: hierarchy_level = 3

    contextual_roles = {}
    sample_role = list(ROLE_SPECIFIC_FOLDER_TAGS.values())[0] if ROLE_SPECIFIC_FOLDER_TAGS else "LEAD_ROLE"
    if "lead.project_alpha" in user_email:
        contextual_roles["PROJECT_ALPHA"] = [sample_role]
    if "admin.hr" in user_email and departments:
        contextual_roles[departments[0]] = ["ADMIN_ROLE"]

    default_profile_data = {
        "user_email": user_email,
        "user_hierarchy_level": hierarchy_level,
        "departments": departments,
        "projects_membership": projects_membership,
        "contextual_roles": contextual_roles,
    }
    if add_or_update_user_profile(user_email, default_profile_data):
        logger.info(f"Created test user profile for {user_email}.")
        return fetch_user_access_profile(user_email)

    logger.error(f"Failed to create DB profile for {user_email} in get_or_create_test_user_profile.")
    return None