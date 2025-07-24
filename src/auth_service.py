import logging
from typing import Dict, Optional, Any
from .database_utils import get_user_profile, add_or_update_user_profile, delete_user_profile
from .config import (
    UserProfile,
    DEFAULT_HIERARCHY_LEVEL, HIERARCHY_LEVEL_KEY, DEPARTMENTS_KEY, 
    PROJECTS_KEY, CONTEXTUAL_ROLES_KEY, USER_EMAIL_KEY
)

logger = logging.getLogger(__name__)


# The new, simplified function in src/auth_service.py
def fetch_user_access_profile(user_email: str) -> Optional[UserProfile]:
    """
    Fetch user profile with attributes for the advanced hybrid RBAC/ABAC.
    Relies on get_user_profile to return a well-formed profile or None.
    """
    if not user_email or not isinstance(user_email, str) or "@" not in user_email:
        logger.warning(f"Attempted to fetch profile with invalid email: '{user_email}'.")
        return None

    try:
        profile = get_user_profile(user_email)
        if not profile:
            return None  # get_user_profile already logs this

        logger.info(f"Successfully fetched and validated profile for {user_email}.")
        return profile
    except Exception as e:
        logger.error(f"Error fetching profile for {user_email}: {e}", exc_info=True)
        return None


def update_user_permissions_by_admin(target_email: str, new_permissions: Dict[str, Any]) -> Dict[str, Any]:
    """
    Updates user permissions by an admin.
    Fetches an existing profile or creates a new one, validates and applies new permissions,
    ensures default values for essential fields, and saves the profile.
    """
    logger.info(f"Admin attempting to update permissions for user '{target_email}' with data: {new_permissions}")

    if not target_email or not isinstance(target_email, str) or "@" not in target_email:
        logger.error(f"Invalid target_email provided for permission update: '{target_email}'")
        return {"error": "Invalid target email provided."}

    profile_data = get_user_profile(target_email)
    is_new_profile = False
    if not profile_data:
        is_new_profile = True
        profile_data = {"user_email": target_email}
        logger.info(f"No existing profile found for '{target_email}'. Creating a new one.")

    allowed_permission_keys = {
        HIERARCHY_LEVEL_KEY: int,
        DEPARTMENTS_KEY: list,
        PROJECTS_KEY: list,
        CONTEXTUAL_ROLES_KEY: dict
    }

    # Update profile with new permissions
    for key, value in new_permissions.items():
        if key in allowed_permission_keys:
            expected_type = allowed_permission_keys[key]
            if isinstance(value, expected_type):
                profile_data[key] = value
                logger.info(f"Updating '{key}' for '{target_email}'.")
            else:
                logger.warning(
                    f"Invalid type for permission key '{key}' for user '{target_email}'. Expected {expected_type}, got {type(value)}. Skipping this key."
                )
        else:
            logger.warning(f"Invalid permission key '{key}' provided for user '{target_email}'. Skipping this key.")

    # Ensure essential fields have default values if not provided, especially for new profiles
    # For existing profiles, these will only apply if the field is missing (which shouldn't happen with get_user_profile's current design)
    # or if it was an invalid key in new_permissions and we want to ensure a default.
    if HIERARCHY_LEVEL_KEY not in profile_data:
        profile_data[HIERARCHY_LEVEL_KEY] = DEFAULT_HIERARCHY_LEVEL
        logger.info(f"Setting default {HIERARCHY_LEVEL_KEY} for '{target_email}'.")
    if DEPARTMENTS_KEY not in profile_data:
        profile_data[DEPARTMENTS_KEY] = []
        logger.info(f"Setting default {DEPARTMENTS_KEY} for '{target_email}'.")
    if PROJECTS_KEY not in profile_data:
        profile_data[PROJECTS_KEY] = []
        logger.info(f"Setting default {PROJECTS_KEY} for '{target_email}'.")
    if CONTEXTUAL_ROLES_KEY not in profile_data:
        profile_data[CONTEXTUAL_ROLES_KEY] = {}
        logger.info(f"Setting default {CONTEXTUAL_ROLES_KEY} for '{target_email}'.")
    
    # Ensure user_email is always present and correct
    profile_data["user_email"] = target_email

    try:
        if add_or_update_user_profile(target_email, profile_data):
            logger.info(f"Successfully updated profile for '{target_email}'. Profile: {profile_data}")
            # Fetch the latest profile to return the actual state from DB
            updated_profile = get_user_profile(target_email)
            return {"message": "User permissions updated successfully.", "updated_profile": updated_profile}
        else:
            logger.error(f"Failed to update profile for '{target_email}' using add_or_update_user_profile.")
            return {"error": "Failed to save user profile to database."}
    except Exception as e:
        logger.error(f"Exception during profile update for '{target_email}': {e}", exc_info=True)
        return {"error": f"An unexpected error occurred: {str(e)}"}
    

def remove_user_by_admin(target_email: str) -> Dict[str, Any]:
    logger.info(f"Admin attempting to remove user '{target_email}'.")
    if not target_email or not isinstance(target_email, str) or "@" not in target_email:
        logger.error(f"Invalid target_email provided for user removal: '{target_email}'")
        return {"error": "Invalid target email provided for removal."}

    if delete_user_profile(target_email): # Assuming delete_user_profile returns True on success
        return {"message": f"User '{target_email}' removed successfully."}
    else:
        # This could mean user not found, or a DB error
        # Check logs from delete_user_profile for specifics
        return {"error": f"Failed to remove user '{target_email}'. User might not exist or database error occurred."}