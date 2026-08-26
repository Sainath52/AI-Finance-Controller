"""
Configuration settings for AI Finance Controller.
Supports Groq, OpenAI, and fallback heuristics.
"""

import os
from dotenv import load_dotenv

load_dotenv()

# Set this in your .env file: GROQ_API_KEY=gsk_...
GROQ_API_KEY = os.environ.get("GROQ_API_KEY", "")
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY", "")

# Default model for Groq-powered reasoning
GROQ_MODEL = os.environ.get("GROQ_MODEL", "openai/gpt-oss-120b")
