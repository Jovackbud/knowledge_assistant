import logging
from typing import Dict, Optional
from database_utils import get_user_profile

logger = logging.getLogger(__name__)


def fetch_user_access_profile(user_email: str) -> Optional[Dict]:
    """Fetch user profile with enhanced validation"""
    try:
        profile = get_user_profile(user_email)
        if not profile:
            logger.warning(f"No profile found for {user_email}")
            return None

        # Validate required fields
        required = ['can_access_staff_docs', 'roles_in_departments', 'roles_in_projects']
        if any(field not in profile for field in required):
            logger.error(f"Invalid profile structure for {user_email}")
            return None

        return profile
    except Exception as e:
        logger.error(f"Auth error: {e}", exc_info=True)
        return None


def fetch_user_access_profile_stub(user_email: str) -> Dict:
    """Testing stub with validated structure"""
    return {
        "user_email": user_email,
        "is_board_member": False,
        "is_executive_management": False,
        "roles_in_departments": [],
        "roles_in_projects": [],
        "can_access_staff_docs": True
    }