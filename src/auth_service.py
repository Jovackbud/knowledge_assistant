import logging
from typing import Dict, Optional, Any
from .database_utils import get_user_profile, add_or_update_user_profile, delete_user_profile
from .config import DEFAULT_HIERARCHY_LEVEL

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
        "user_hierarchy_level": int,
        "departments": list,
        "projects_membership": list,
        "contextual_roles": dict
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
    if "user_hierarchy_level" not in profile_data:
        profile_data["user_hierarchy_level"] = DEFAULT_HIERARCHY_LEVEL
        logger.info(f"Setting default user_hierarchy_level for '{target_email}'.")
    if "departments" not in profile_data:
        profile_data["departments"] = []
        logger.info(f"Setting default departments for '{target_email}'.")
    if "projects_membership" not in profile_data:
        profile_data["projects_membership"] = []
        logger.info(f"Setting default projects_membership for '{target_email}'.")
    if "contextual_roles" not in profile_data:
        profile_data["contextual_roles"] = {}
        logger.info(f"Setting default contextual_roles for '{target_email}'.")
    
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