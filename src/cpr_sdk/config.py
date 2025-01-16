import os
import subprocess
from typing import Optional
from pathlib import Path
from dotenv import load_dotenv, find_dotenv


def get_git_root() -> Optional[Path]:
    try:
        git_root = subprocess.check_output(
            ["git", "rev-parse", "--show-toplevel"], universal_newlines=True
        ).strip()
        return Path(git_root)
    except subprocess.CalledProcessError:
        # This exception is raised if the command returns a non-zero exit status
        # (i.e., we're not in a git repository)
        return None
    except FileNotFoundError:
        # This exception is raised if the 'git' command is not found
        print("Git command not found. Make sure Git is installed and in your PATH.")
        return None


load_dotenv(find_dotenv())

root_dir = get_git_root()

VESPA_URL: str = os.environ["VESPA_URL"]
VESPA_URL = VESPA_URL.rstrip("/")
