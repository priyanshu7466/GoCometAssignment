import time
import functools
from google.genai.errors import APIError

def retry_on_429(max_retries=3, initial_delay=15):
    """
    Decorator to automatically retry Gemini API calls when hitting the
    Free Tier 429 RESOURCE_EXHAUSTED rate limit.
    """
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            delay = initial_delay
            for attempt in range(max_retries):
                try:
                    return func(*args, **kwargs)
                except APIError as e:
                    if "429" in str(e) and attempt < max_retries - 1:
                        print(f"[Rate Limit] Hit Gemini free tier limit. Waiting {delay}s before retry {attempt + 1}/{max_retries}...")
                        time.sleep(delay)
                        delay *= 1.5  # Exponential backoff
                    else:
                        raise e
        return wrapper
    return decorator
