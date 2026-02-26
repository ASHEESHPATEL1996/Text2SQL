import os
import streamlit as st
from langfuse import Langfuse


def get_secret(key: str):
    # Works locally + Streamlit Cloud
    if key in st.secrets:
        return st.secrets[key]
    return os.getenv(key)


langfuse = Langfuse(
    public_key=get_secret("LANGFUSE_PUBLIC_KEY"),
    secret_key=get_secret("LANGFUSE_SECRET_KEY"),
    host=get_secret("LANGFUSE_HOST")
)
