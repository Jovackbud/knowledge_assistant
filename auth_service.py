from database_utils import get_user_profile # Use the real function
import logging

logger = logging.getLogger(__name__)

def fetch_user_access_profile(user_email: str):
    """
    Fetches the user's access profile from the local database.
    """
    logger.info(f"AuthService: Attempting to fetch profile for {user_email} from DB.")
    profile = get_user_profile(user_email) # Call the function from database_utils
    if profile:
        logger.info(f"AuthService: Profile found for {user_email}.")
        # Log structure for debugging? Be careful with sensitive info
        logger.debug(f"AuthService: Profile data for {user_email}: {profile}")
    else:
        logger.info(f"AuthService: No profile found for {user_email}.")
    return profile

def fetch_user_access_profile_stub(user_email:str):
    "A stub function for testing purposes that bypasses the database and returns a hardcoded profile"
    print(f"AuthService: Fetching user's access profile stub for {user_email}")
    if user_email == "teststaff@example.com":
        return{
            "user_email": "teststaff@example.com",
            "is_board_member": False,
            "is_executive_management": False,
            "roles_in_departments": [],
            "roles_in_projects": [],
            "can_access_staff_docs": True
        }
    elif user_email == "no_access_user@example.com":
        return {
            "user_email":"no_access_user@example.com",
            "can_access_staff_docs": False
        }
    elif user_email == "board_member@example.com":
        return {
            "user_email":"board_member@example.com",
            "is_board_member": True,
            "can_access_staff_docs": True
        }
    return None
