import os

DATABASE_URL = os.getenv("EIMS_DATABASE_URL", "sqlite:///./eims.db")
SECRET_KEY = os.getenv("EIMS_SECRET_KEY", "sprint1-development-secret-change-me")
ACCESS_TOKEN_MINUTES = int(os.getenv("EIMS_ACCESS_TOKEN_MINUTES", "30"))
SESSION_IDLE_TIMEOUT_MINUTES = int(
    os.getenv("EIMS_SESSION_IDLE_TIMEOUT_MINUTES", "15")
)
SUPER_ADMIN_USERNAME = os.getenv("EIMS_SUPER_ADMIN_USERNAME", "eims-admin")
SUPER_ADMIN_PASSWORD = os.getenv("EIMS_SUPER_ADMIN_PASSWORD", "Password")
ENFORCE_HTTPS = os.getenv("EIMS_ENFORCE_HTTPS", "true").lower() in {
    "1",
    "true",
    "yes",
    "on",
}
