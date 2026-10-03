import os

DATABASE_URL = os.getenv("EIMS_DATABASE_URL", "sqlite:///./eims.db")
SECRET_KEY = os.getenv("EIMS_SECRET_KEY", "sprint1-development-secret-change-me")
ACCESS_TOKEN_MINUTES = int(os.getenv("EIMS_ACCESS_TOKEN_MINUTES", "30"))
