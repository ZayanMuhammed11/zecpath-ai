"""
Shared Redis connection factory for Zecpath ATS API.
"""

from redis import Redis
from config.settings import REDIS_URL
from utils.logger import get_logger

logger = get_logger(__name__)


def get_redis() -> Redis:
    """
    Create and return a Redis connection from the configured REDIS_URL.

    Returns:
        Redis: A connected Redis client instance with decode_responses enabled.
    """
    logger.debug("Creating Redis connection from URL: %s", REDIS_URL)
    return Redis.from_url(REDIS_URL, decode_responses=True)
def get_redis_binary() -> Redis:
    """
    Return a Redis connection without decode_responses.
    Required for RQ Job.fetch() which reads pickled binary data.
    """
    return Redis.from_url(REDIS_URL, decode_responses=False)