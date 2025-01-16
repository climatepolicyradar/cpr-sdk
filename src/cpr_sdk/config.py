import os
from typing import Optional
from dotenv import load_dotenv, find_dotenv


load_dotenv(find_dotenv())

VESPA_URL: Optional[str] = os.environ.get("VESPA_URL")
if VESPA_URL is not None:
    VESPA_URL = VESPA_URL.rstrip("/")
