import os
from decouple import config

DATABASE_URL = config(
    "DATABASE_URL",
    default="sqlite+aiosqlite:///./cdss.db",
)
