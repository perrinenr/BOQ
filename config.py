import os
import sys
from pathlib import Path

from dotenv import load_dotenv


def application_directory() -> Path:
    """Return the folder containing the executable or Python sources."""
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent


def load_application_environment() -> Path:
    """Load .env from the application folder, then fall back to the current folder."""
    app_env = application_directory() / ".env"
    if app_env.exists():
        load_dotenv(app_env, override=False)
        return app_env

    current_env = Path.cwd() / ".env"
    if current_env.exists():
        load_dotenv(current_env, override=False)
        return current_env

    load_dotenv(override=False)
    return app_env
