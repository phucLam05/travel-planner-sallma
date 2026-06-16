import os
import re
import threading
import time
from typing import Any

from langchain_google_genai import ChatGoogleGenerativeAI

DEFAULT_TEXT_MODEL = "gemini-3.1-flash-lite"
MODEL_NAME_ENV = "SALLMA_TEXT_MODEL"
MODEL_CALL_LOCK = threading.Lock()
MODEL_MIN_INTERVAL_SECONDS = 0.0
NEXT_MODEL_CALL_AT = 0.0


def get_text_model_name(default: str = DEFAULT_TEXT_MODEL) -> str:
    return os.getenv(MODEL_NAME_ENV, default)


def configure_model_rate_limit(min_interval_seconds: float) -> None:
    global MODEL_MIN_INTERVAL_SECONDS
    MODEL_MIN_INTERVAL_SECONDS = max(0.0, float(min_interval_seconds))


def build_text_llm(model: str | None = None, temperature: float = 0.1, **kwargs: Any) -> ChatGoogleGenerativeAI:
    api_key = os.getenv("GOOGLE_API_KEY")
    if not api_key:
        raise RuntimeError("Missing GOOGLE_API_KEY for Gemini text generation.")

    return ChatGoogleGenerativeAI(
        model=model or get_text_model_name(),
        temperature=temperature,
        api_key=api_key,
        **kwargs,
    )


def extract_retry_delay_seconds(exc: Exception, attempt: int) -> float:
    message = str(exc)
    patterns = [
        r"wait (\d+(?:\.\d+)?) seconds",
        r"retry.*?in (\d+(?:\.\d+)?)s",
        r"seconds:\s*(\d+)",
    ]
    for pattern in patterns:
        match = re.search(pattern, message, re.IGNORECASE | re.DOTALL)
        if match:
            return float(match.group(1)) + 1.0
    return min(60.0, 5.0 * attempt)


def is_retryable_model_error(exc: Exception) -> bool:
    message = str(exc).lower()
    class_name = exc.__class__.__name__.lower()
    retry_markers = (
        "rate limit",
        "resource exhausted",
        "resource_exhausted",
        "quota",
        "too many requests",
        "429",
    )
    return class_name in {"ratelimiterror", "resourceexhausted", "toomanyrequests"} or any(
        marker in message for marker in retry_markers
    )


def invoke_with_retry(runnable: Any, messages: Any, max_attempts: int = 8) -> Any:
    global NEXT_MODEL_CALL_AT

    attempt = 0
    while True:
        try:
            with MODEL_CALL_LOCK:
                now = time.monotonic()
                if NEXT_MODEL_CALL_AT > now:
                    time.sleep(NEXT_MODEL_CALL_AT - now)
                NEXT_MODEL_CALL_AT = time.monotonic() + MODEL_MIN_INTERVAL_SECONDS
            return runnable.invoke(messages)
        except Exception as exc:
            attempt += 1
            if attempt >= max_attempts or not is_retryable_model_error(exc):
                raise
            time.sleep(extract_retry_delay_seconds(exc, attempt))
