
import os

from dotenv import load_dotenv
from langchain_groq import ChatGroq

load_dotenv()


def get_llm():
    """Create the chat model. The key and the model name come from the .env file."""
    api_key = os.getenv("GROQ_API_KEY")
    model = os.getenv("GROQ_MODEL")

    missing = [
        name for name, value in (("GROQ_API_KEY", api_key), ("GROQ_MODEL", model))
        if value is None
    ]
    if missing:
        raise RuntimeError(f"Missing in .env: {', '.join(missing)}")

    return ChatGroq(model=model, temperature=0, max_retries=2)

def message_text(message):
    """Return the plain text of a model reply."""
    content = message.content

    if isinstance(content, str):
        return content

    parts = []
    for block in content:
        if isinstance(block, str):
            parts.append(block)
        elif isinstance(block, dict) and block.get("type") == "text":
            parts.append(block.get("text", ""))
    return "".join(parts)
