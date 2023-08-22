import logging
import subprocess
from typing import Optional

LOGGER = logging.getLogger(__name__)


def poll_subprocess(
    subprocess: subprocess.Popen,
    timeout: Optional[int] = 30,
    logger: Optional[logging.Logger] = None,
):
    returncode = subprocess.poll()

    logger = logger or LOGGER

    try:
        stdout_data, stderr_data = subprocess.communicate(timeout=timeout)

    except subprocess.TimeoutExpired:
        subprocess.terminate()
        stdout_data, stderr_data = subprocess.communicate()
        # More specifically?
        returncode = -1

    if stdout_data:
        logger.info(stdout_data.decode("UTF-8"))
    if stderr_data:
        logger.info(stderr_data.decode("UTF-8"))

    return returncode
