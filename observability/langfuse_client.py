import os
import streamlit as st


class _NoOpSpan:
    def start_generation(self, **kwargs):
        return _NoOpSpan()

    def start_span(self, **kwargs):
        return _NoOpSpan()

    def update(self, **kwargs):
        return None

    def end(self):
        return None


class _NoOpLangfuse(_NoOpSpan):
    def start_trace(self, **kwargs):
        return _NoOpSpan()

    def flush(self):
        return None


def get_secret(key: str):
    # Works locally and on Streamlit Cloud without crashing in non-Streamlit runs.
    try:
        if key in st.secrets:
            return st.secrets[key]
    except Exception:
        pass
    return os.getenv(key)


try:
    from langfuse import Langfuse
except Exception as e:
    Langfuse = None
    print(f"Langfuse unavailable, observability disabled: {e}")


def _build_langfuse():
    if Langfuse is None:
        return _NoOpLangfuse()

    public_key = get_secret("LANGFUSE_PUBLIC_KEY")
    secret_key = get_secret("LANGFUSE_SECRET_KEY")
    host = get_secret("LANGFUSE_HOST")

    # If keys are not configured, keep app functionality and skip observability.
    if not public_key or not secret_key or not host:
        print("Langfuse keys missing, observability disabled.")
        return _NoOpLangfuse()

    try:
        return Langfuse(
            public_key=public_key,
            secret_key=secret_key,
            host=host,
        )
    except Exception as e:
        print(f"Failed to initialize Langfuse, observability disabled: {e}")
        return _NoOpLangfuse()


langfuse = _build_langfuse()
