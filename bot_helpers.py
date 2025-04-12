import os
import logging
import re
from datetime import datetime
from typing import Dict, List, Optional, Set

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# User state constants
STATE_IDLE = "IDLE"
STATE_ADDING_FRIEND_NAME = "ADDING_FRIEND_NAME"
STATE_ADDING_FRIEND_BIRTHDAY = "ADDING_FRIEND_BIRTHDAY"
STATE_ADDING_CUSTOM_DAY = "ADDING_CUSTOM_DAY"

# Callback query data identifiers
PREF_WEEK_BEFORE = "pref_week"
PREF_DAY_BEFORE = "pref_day"
PREF_ON_DAY = "pref_on_day"
PREF_CUSTOM = "pref_custom"
PREF_DONE = "pref_done"
ADD_CUSTOM_DAY = "add_custom"
REMOVE_CUSTOM_DAY = "remove_custom"
DONE_CUSTOM_DAYS = "done_custom"
DELETE_FRIEND = "delete_friend_"

# Bot token
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")