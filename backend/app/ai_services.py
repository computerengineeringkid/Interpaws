"""AI services for embeddings and generative recommendations."""

import asyncio
import json
import logging
import os
import re

import ollama
from sentence_transformers import SentenceTransformer


logger = logging.getLogger(__name__)

DEFAULT_OLLAMA_MODEL = "llama3.2:3b"  # Smaller model for faster M3 Pro inference
_EMBEDDING_MODEL_NAME = "all-MiniLM-L6-v2"
_embedding_model: SentenceTransformer | None = None
_embedding_model_lock = asyncio.Lock()

# Get Ollama host from environment, defaulting to the internal service name
ollama_host = os.getenv("OLLAMA_HOST", "http://ollama:11434")

# Initialize async Ollama client
ollama_client = ollama.AsyncClient(host=ollama_host)


async def get_embedding_model() -> SentenceTransformer:
    """Lazily load and cache the embedding model.

    Ensures only one initialization attempt occurs at a time using an asyncio lock.
    """

    global _embedding_model

    if _embedding_model is not None:
        return _embedding_model

    async with _embedding_model_lock:
        if _embedding_model is not None:
            return _embedding_model

        try:
            _embedding_model = SentenceTransformer(_EMBEDDING_MODEL_NAME)
        except (OSError, RuntimeError):
            logger.exception(
                "Failed to load embedding model '%s'. Ensure the model files are available.",
                _EMBEDDING_MODEL_NAME,
            )
            raise

    return _embedding_model


async def get_embedding(text: str) -> list[float]:
    """
    Generate an embedding for the given text.

    Args:
        text: The input text to encode.

    Returns:
        A list of floats representing the embedding vector.
    """
    model = await get_embedding_model()
    embedding = model.encode(text)
    return embedding.tolist()


async def get_ollama_recommendation(
    prompt: str,
    json_mode: bool = False,
    *,
    temperature: float = 0.3,
) -> str:
    """
    Get a recommendation from Ollama using the standard llama3 model.

    This is a placeholder function to ensure the Ollama connection works.

    Args:
        prompt: The prompt to send to the model.
        json_mode: If True, request the response in JSON format.

    Returns:
        The model's response as a string, or an error message if the service
        is unreachable.
    """
    chat_options = {}
    if json_mode:
        chat_options["format"] = "json"

    try:
        response = await asyncio.wait_for(
            ollama_client.chat(
                model=DEFAULT_OLLAMA_MODEL,
                messages=[
                    {
                        "role": "user",
                        "content": prompt,
                    },
                ],
                options={
                    "num_ctx": 2048,  # Smaller context window = faster
                    "temperature": temperature,  # Lower temp = faster, more deterministic
                    "num_predict": 512,  # Allow longer responses for reasoning
                },
                keep_alive="5m",  # Keep model loaded for faster subsequent calls
                **chat_options,
            ),
            timeout=90.0  # 90s for multi-turn agent reasoning with conversation memory
        )
    except asyncio.TimeoutError:
        return "I'm sorry, the AI is taking too long to respond. Please try again."
    except Exception as e:
        error_str = str(e).lower()
        if "connect" in error_str or "refused" in error_str or "unreachable" in error_str:
            print(f"Ollama connection error: {e}")
            return f"Unable to connect to AI service at {ollama_host}. Please ensure Ollama is running with the {DEFAULT_OLLAMA_MODEL} model."
        print(f"Ollama error: {e}")
        return "Sorry, I'm having trouble with the AI service right now. Please try again later."

    return response.get("message", {}).get("content", "")


def extract_json_payload(raw: str) -> dict | None:
    """Extract a JSON object from an LLM response using regex.

    The LLM may wrap JSON in prose or markdown fences. We use regex to find
    the first opening brace and the last closing brace to isolate the payload.
    """
    if not raw:
        return None

    # Use regex to find the JSON object: starts with { and ends with }
    # re.DOTALL allows . to match newlines
    match = re.search(r"\{.*\}", raw, re.DOTALL)
    
    if match:
        json_str = match.group()
        try:
            return json.loads(json_str)
        except (json.JSONDecodeError, TypeError):
            pass
            
    return None
