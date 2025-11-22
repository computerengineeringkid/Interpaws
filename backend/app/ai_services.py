"""AI services for embeddings and generative recommendations."""

import os
import ollama
from sentence_transformers import SentenceTransformer
import asyncio

# Initialize the embedding model once as a global instance to be reused
embedding_model = SentenceTransformer("all-MiniLM-L6-v2")

DEFAULT_OLLAMA_MODEL = "qwen2.5:7b"  # Back to 7B - more reliable even if slower

# Get Ollama host from environment
ollama_host = os.getenv("OLLAMA_HOST", "http://localhost:11434")

# Initialize async Ollama client
ollama_client = ollama.AsyncClient(host=ollama_host)


def get_embedding(text: str) -> list[float]:
    """
    Generate an embedding for the given text.
    
    Args:
        text: The input text to encode.
    
    Returns:
        A list of floats representing the embedding vector.
    """
    embedding = embedding_model.encode(text)
    return embedding.tolist()


async def get_ollama_recommendation(prompt: str, json_mode: bool = False) -> str:
    """
    Get a recommendation from Ollama using the standard qwen2.5:7b model.

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
                    "temperature": 0.3,  # Lower temp = faster, more deterministic
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
