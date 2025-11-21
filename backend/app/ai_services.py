"""AI services for embeddings and generative recommendations."""

import os
import ollama
from sentence_transformers import SentenceTransformer

# Initialize the embedding model once as a global instance to be reused
embedding_model = SentenceTransformer("all-MiniLM-L6-v2")

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


async def get_ollama_recommendation(prompt: str) -> str:
    """
    Get a recommendation from Ollama using the qwen3:8b model.
    
    This is a placeholder function to ensure the Ollama connection works.
    
    Args:
        prompt: The prompt to send to the model.
    
    Returns:
        The model's response as a string.
    """
    response = await ollama_client.chat(
        model="qwen3:8b",
        messages=[
            {
                "role": "user",
                "content": prompt,
            },
        ],
    )
    return response["message"]["content"]
