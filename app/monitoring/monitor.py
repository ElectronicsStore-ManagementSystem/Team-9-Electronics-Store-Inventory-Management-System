
import logging
import os
import time

import httpx

from ..db import SessionLocal
from .service import record_availability_check


HEALTH_URL = os.getenv(
    "EIMS_HEALTH_URL",
    "http://127.0.0.1:8000/health",
)

CHECK_INTERVAL = int(
    os.getenv("EIMS_MONITOR_INTERVAL_SECONDS", "10")
)

REQUEST_TIMEOUT = float(
    os.getenv("EIMS_MONITOR_TIMEOUT_SECONDS", "5")
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)

logger = logging.getLogger(__name__)


def perform_check():
    is_available = False
    response_time_ms = None
    error_message = None

    start_time = time.monotonic()

    try:
        response = httpx.get(
            HEALTH_URL,
            timeout=REQUEST_TIMEOUT,
        )

        response_time_ms = (
            time.monotonic() - start_time
        ) * 1000

        is_available = response.status_code == 200

        if not is_available:
            error_message = (
                f"Health endpoint returned HTTP {response.status_code}"
            )

    except httpx.RequestError as error:
        response_time_ms = (
            time.monotonic() - start_time
        ) * 1000

        error_message = str(error)

    db = SessionLocal()

    try:
        record_availability_check(
            db=db,
            is_available=is_available,
            response_time_ms=response_time_ms,
            error_message=error_message,
        )

        if is_available:
            logger.info(
                "Application available (%.2f ms)",
                response_time_ms,
            )
        else:
            logger.warning(
                "Application unavailable: %s",
                error_message,
            )

    except Exception:
        db.rollback()
        logger.exception("Could not save availability check")

    finally:
        db.close()


def main():
    logger.info("Starting EIMS availability monitor")
    logger.info("Monitoring URL: %s", HEALTH_URL)
    logger.info("Check interval: %s seconds", CHECK_INTERVAL)

    while True:
        perform_check()
        time.sleep(CHECK_INTERVAL)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        logger.info("Availability monitor stopped")
