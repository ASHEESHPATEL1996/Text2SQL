import logging
import os
from contextlib import contextmanager

from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)


class MockObservation:
    def update(self, *args, **kwargs):
        return self

    def end(self):
        pass

    @contextmanager
    def start_as_current_observation(self, *args, **kwargs):
        yield MockObservation()


class MockLangfuse:
    def __init__(self, *args, **kwargs):
        pass

    @contextmanager
    def start_as_current_observation(self, *args, **kwargs):
        yield MockObservation()

    def flush(self):
        pass


def get_secret(key: str):
    try:
        import streamlit as st

        if key in st.secrets:
            return st.secrets[key]
    except Exception:
        pass
    return os.getenv(key)


try:
    from langfuse import Langfuse as RealLangfuse

    _pk = get_secret("LANGFUSE_PUBLIC_KEY")
    _sk = get_secret("LANGFUSE_SECRET_KEY")
    _host = get_secret("LANGFUSE_HOST") or os.getenv("LANGFUSE_BASE_URL")

    if not _pk or not _sk:
        logger.warning(
            "Langfuse keys missing (LANGFUSE_PUBLIC_KEY / LANGFUSE_SECRET_KEY); "
            "tracing disabled until set in .env or Streamlit secrets."
        )
        langfuse = MockLangfuse()
    else:
        init_kw = {"public_key": _pk, "secret_key": _sk}
        if _host:
            init_kw["host"] = _host
        langfuse = RealLangfuse(**init_kw)
except Exception as e:
    logger.warning("Langfuse client unavailable (%s); using mock.", e)
    langfuse = MockLangfuse()
