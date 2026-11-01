import os

import uvicorn


LOCAL_HOST = "127.0.0.1"
LOCAL_PORT = 8000


if __name__ == "__main__":
    os.environ.setdefault("EIMS_ENFORCE_HTTPS", "false")
    uvicorn.run(
        "app.main:app",
        host=LOCAL_HOST,
        port=LOCAL_PORT,
        reload=True,
    )
