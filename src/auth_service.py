import logging
from typing import Dict, Optional, Any, cast
from .database_utils import get_user_profile, add_or_update_user_profile, delete_user_profile
from .config import (
    UserProfile,
    DEFAULT_HIERARCHY_LEVEL, HIERARCHY_LEVEL_KEY, DEPARTMENTS_KEY, 
    PROJECTS_KEY, CONTEXTUAL_ROLES_KEY, USER_EMAIL_KEY,
    IS_ADMIN_KEY, PermissionsModel
)

logger = logging.getLogger(__name__)


def fetch_user_access_profile(user_email: str) -> Optional[UserProfile]:
    """
    Fetch user profile with attributes for the advanced hybrid RBAC/ABAC.
    Relies on get_user_profile to return a well-formed profile or None.
    """
    if not user_email or not isinstance(user_email, str) or "@" not in user_email:
        logger.warning(f"Attempted to fetch profile with invalid email: '{user_email}'.")
        return None
    user_email = user_email.lower()
    try:
        profile = get_user_profile(user_email)
        if not profile:
            return None  # get_user_profile already logs this

        logger.info(f"Successfully fetched and validated profile for {user_email}.")
        return profile
    except Exception as e:
        logger.error(f"Error fetching profile for {user_email}: {e}", exc_info=True)
        return None


def update_user_permissions_by_admin(target_email: str, new_permissions: PermissionsModel) -> Dict[str, Any]:
    """
    Updates user permissions by an admin. This version uses a robust, explicit
    merge strategy to prevent bugs with partial updates.
    """
    target_email = target_email.lower()
    
    # 1. Convert the Pydantic model to a dict, but this time, KEEP the None values.
    # This lets us know which fields the user didn't fill out on the form.
    permissions_from_form = new_permissions.model_dump()

    logger.info(f"Admin attempting to update permissions for user '{target_email}' with form data: {permissions_from_form}")

    if not target_email or not isinstance(target_email, str) or "@" not in target_email:
        logger.error(f"Invalid target_email provided for permission update: '{target_email}'")
        return {"error": "Invalid target email provided."}

    # 2. Get the user's current state from the database.
    existing_profile = get_user_profile(target_email)

    # 3. Build the final profile with an explicit merge strategy.
    if existing_profile:
        # --- UPDATE an existing user ---
        logger.info(f"Found existing profile for '{target_email}'. Merging changes.")
        final_profile = existing_profile.copy() # Start with the old profile
        
        # For each possible permission, decide whether to use the new value from the form
        # or keep the old one. A value of None from the form means "no change".
        if permissions_from_form.get(HIERARCHY_LEVEL_KEY) is not None:
            final_profile[HIERARCHY_LEVEL_KEY] = permissions_from_form[HIERARCHY_LEVEL_KEY]
        
        if permissions_from_form.get(DEPARTMENTS_KEY) is not None:
            final_profile[DEPARTMENTS_KEY] = permissions_from_form[DEPARTMENTS_KEY]

        if permissions_from_form.get(PROJECTS_KEY) is not None:
            final_profile[PROJECTS_KEY] = permissions_from_form[PROJECTS_KEY]

        if permissions_from_form.get(CONTEXTUAL_ROLES_KEY) is not None:
            final_profile[CONTEXTUAL_ROLES_KEY] = permissions_from_form[CONTEXTUAL_ROLES_KEY]

        if permissions_from_form.get(IS_ADMIN_KEY) is not None:
            final_profile[IS_ADMIN_KEY] = permissions_from_form[IS_ADMIN_KEY]
    else:
        # --- CREATE a new user ---
        logger.info(f"No existing profile for '{target_email}'. Creating new profile from form data.")
        # For a new user, we use the form data and fill in any missing pieces with defaults.
        final_profile = {
            USER_EMAIL_KEY: target_email,
            HIERARCHY_LEVEL_KEY: permissions_from_form.get(HIERARCHY_LEVEL_KEY, DEFAULT_HIERARCHY_LEVEL),
            DEPARTMENTS_KEY: permissions_from_form.get(DEPARTMENTS_KEY, []),
            PROJECTS_KEY: permissions_from_form.get(PROJECTS_KEY, []),
            CONTEXTUAL_ROLES_KEY: permissions_from_form.get(CONTEXTUAL_ROLES_KEY) or {},
            IS_ADMIN_KEY: permissions_from_form.get(IS_ADMIN_KEY, False)
        }

    # 4. Save the fully constructed final profile to the database.
    try:
        if add_or_update_user_profile(target_email, cast(UserProfile, final_profile)):
            logger.info(f"Successfully committed final profile for '{target_email}': {final_profile}")
            # Fetch the latest profile to return the actual state from DB
            updated_profile = get_user_profile(target_email)
            return {"message": "User permissions updated successfully.", "updated_profile": updated_profile}
        else:
            logger.error(f"Failed to save final profile for '{target_email}'.")
            return {"error": "Failed to save user profile to database."}
    except Exception as e:
        logger.error(f"Exception during profile save for '{target_email}': {e}", exc_info=True)
        return {"error": f"An unexpected error occurred: {str(e)}"}
    

def remove_user_by_admin(target_email: str) -> Dict[str, Any]:
    target_email = target_email.lower()
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