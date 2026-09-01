import getpass
import os
from typing import Tuple


def get_credentials() -> Tuple[str, str]:
    """Get username and password from environment variables. If missing, prompt the user."""
    username = os.environ.get("CONTRACTIONDBUSERNAME")
    password = os.environ.get("CONTRACTIONDBPASSWORD")

    if username is None:
        username = input("Username: ")
    if password is None:
        password = getpass.getpass()

    return username, password
