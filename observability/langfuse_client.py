import os
import streamlit as st

# Define mock classes first
class MockSpan:
    def update(self, *args, **kwargs):
        return self
    def end(self):
        pass
    def start_span(self, *args, **kwargs):
        return MockSpan()
    def start_generation(self, *args, **kwargs):
        return MockSpan()

class MockTrace(MockSpan):
    def start_trace(self, *args, **kwargs):
        return MockTrace()
    def flush(self):
        pass

class Langfuse:
    def __init__(self, *args, **kwargs):
        pass
    def start_trace(self, *args, **kwargs):
        return MockTrace()
    def flush(self):
        pass

# Try to import real Langfuse, fall back to mock if it fails
try:
    from langfuse import Langfuse as RealLangfuse
    Langfuse = RealLangfuse
except Exception:
    # Use mock Langfuse if import fails (pydantic compatibility issue)
    pass

def get_secret(key: str):
    # Works locally + Streamlit Cloud
    try:
        if key in st.secrets:
            return st.secrets[key]
    except Exception:
        pass
    return os.getenv(key)


try:
    langfuse = Langfuse(
        public_key=get_secret("LANGFUSE_PUBLIC_KEY"),
        secret_key=get_secret("LANGFUSE_SECRET_KEY"),
        host=get_secret("LANGFUSE_HOST")
    )
except Exception:
    # Fall back to mock if initialization fails
    langfuse = Langfuse()
