"""AI services for embeddings and generative recommendations."""

import asyncio
import json
import logging
import os
import re
import time
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional

from google import genai
from google.genai import types
from sentence_transformers import SentenceTransformer


logger = logging.getLogger(__name__)

# Gemini configuration
GEMINI_MODEL = "gemini-2.5-flash"
_EMBEDDING_MODEL_NAME = "all-MiniLM-L6-v2"
_embedding_model: SentenceTransformer | None = None
_embedding_model_lock = asyncio.Lock()

# Initialize Gemini client
google_api_key = os.getenv("GOOGLE_API_KEY", "")
gemini_client = genai.Client(api_key=google_api_key) if google_api_key else None


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
    Get a recommendation from Gemini 2.5 Flash.

    This function maintains the same interface as the old Ollama version
    for compatibility with the rest of the codebase.

    Args:
        prompt: The prompt to send to the model.
        json_mode: If True, request the response in JSON format.
        temperature: Controls randomness (0.0 = deterministic, 1.0 = creative).

    Returns:
        The model's response as a string, or an error message if the service
        is unreachable.
    """
    if not gemini_client:
        return "Error: GOOGLE_API_KEY is not configured. Please set it in your environment."

    try:
        # Build generation config
        config = types.GenerateContentConfig(
            temperature=temperature,
            max_output_tokens=1024,
        )
        
        # Add JSON response format if requested
        if json_mode:
            config.response_mime_type = "application/json"

        # Call Gemini API
        response = await asyncio.wait_for(
            asyncio.to_thread(
                gemini_client.models.generate_content,
                model=GEMINI_MODEL,
                contents=prompt,
                config=config,
            ),
            timeout=60.0
        )
        
        # Extract text from response
        if response and response.text:
            return response.text
        else:
            return "I'm sorry, I couldn't generate a response. Please try again."

    except asyncio.TimeoutError:
        logger.error("Gemini API timeout")
        return "I'm sorry, the AI is taking too long to respond. Please try again."
    except Exception as e:
        error_str = str(e).lower()
        logger.error(f"Gemini API error: {e}")
        if "api_key" in error_str or "unauthorized" in error_str or "invalid" in error_str:
            return "Error: Invalid or missing GOOGLE_API_KEY. Please check your configuration."
        if "quota" in error_str or "rate" in error_str:
            return "Error: API rate limit exceeded. Please wait a moment and try again."
        return "Sorry, I'm having trouble with the AI service right now. Please try again later."


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


# =============================================================================
# AGENTIC CHAT WITH FUNCTION CALLING
# =============================================================================

# Session memory with TTL (1 hour expiry)
SESSION_TTL_SECONDS = 3600
_conversation_memory: Dict[str, Dict[str, Any]] = {}


def _cleanup_expired_sessions():
    """Remove sessions older than TTL."""
    now = time.time()
    expired = [
        sid for sid, data in _conversation_memory.items()
        if now - data.get("last_access", 0) > SESSION_TTL_SECONDS
    ]
    for sid in expired:
        del _conversation_memory[sid]


def get_conversation_history(session_id: str) -> List[Dict[str, str]]:
    """Get conversation history for a session, creating if needed."""
    _cleanup_expired_sessions()

    if session_id not in _conversation_memory:
        _conversation_memory[session_id] = {
            "messages": [],
            "last_access": time.time()
        }
    else:
        _conversation_memory[session_id]["last_access"] = time.time()

    return _conversation_memory[session_id]["messages"]


def save_to_conversation(session_id: str, role: str, content: str):
    """Save a message to conversation history (keeps last 20 messages)."""
    if session_id not in _conversation_memory:
        _conversation_memory[session_id] = {
            "messages": [],
            "last_access": time.time()
        }

    _conversation_memory[session_id]["messages"].append({
        "role": role,
        "content": content
    })
    _conversation_memory[session_id]["last_access"] = time.time()

    # Keep only last 20 messages
    if len(_conversation_memory[session_id]["messages"]) > 20:
        _conversation_memory[session_id]["messages"] = \
            _conversation_memory[session_id]["messages"][-20:]


@dataclass
class AgenticResponse:
    """Response from the agentic chat loop."""
    text: str
    tool_calls_made: List[Dict[str, Any]] = field(default_factory=list)
    tool_results: Dict[str, Any] = field(default_factory=dict)


async def agentic_chat(
    user_message: str,
    session_id: str,
    system_prompt: str,
    tools: List[types.Tool],
    tool_executor: Callable[[str, Dict[str, Any]], Any],
    max_tool_rounds: int = 5,
) -> AgenticResponse:
    """
    Run an agentic chat loop with Gemini function calling.

    Args:
        user_message: The user's input message
        session_id: Session ID for conversation memory
        system_prompt: System instructions for the agent
        tools: List of Gemini Tool definitions
        tool_executor: Async function that executes tools: (name, args) -> result
        max_tool_rounds: Maximum number of tool call rounds to prevent infinite loops

    Returns:
        AgenticResponse with the final text and tool call history
    """
    if not gemini_client:
        return AgenticResponse(
            text="Error: GOOGLE_API_KEY is not configured. Please set it in your environment."
        )

    # Get conversation history and add user message
    history = get_conversation_history(session_id)

    # Build contents for Gemini
    contents = []

    # Add conversation history
    for msg in history:
        role = "user" if msg["role"] == "user" else "model"
        contents.append(types.Content(
            role=role,
            parts=[types.Part.from_text(text=msg["content"])]
        ))

    # Add current user message
    contents.append(types.Content(
        role="user",
        parts=[types.Part.from_text(text=user_message)]
    ))

    tool_calls_made = []
    tool_results = {}

    try:
        for round_num in range(max_tool_rounds):
            # Call Gemini with tools
            response = await asyncio.wait_for(
                asyncio.to_thread(
                    gemini_client.models.generate_content,
                    model=GEMINI_MODEL,
                    contents=contents,
                    config=types.GenerateContentConfig(
                        system_instruction=system_prompt,
                        tools=tools,
                        temperature=0.7,
                        max_output_tokens=2048,
                    ),
                ),
                timeout=60.0
            )

            # Check if response has function calls
            if not response.candidates:
                return AgenticResponse(
                    text="I'm sorry, I couldn't generate a response. Please try again.",
                    tool_calls_made=tool_calls_made,
                    tool_results=tool_results
                )

            candidate = response.candidates[0]

            # Check for function calls in the response
            function_calls = []
            text_parts = []

            for part in candidate.content.parts:
                if hasattr(part, 'function_call') and part.function_call:
                    function_calls.append(part.function_call)
                elif hasattr(part, 'text') and part.text:
                    text_parts.append(part.text)

            # If no function calls, we're done - return the text
            if not function_calls:
                final_text = " ".join(text_parts) if text_parts else ""
                if not final_text:
                    final_text = "I've completed the action."

                # Save to conversation history
                save_to_conversation(session_id, "user", user_message)
                save_to_conversation(session_id, "assistant", final_text)

                return AgenticResponse(
                    text=final_text,
                    tool_calls_made=tool_calls_made,
                    tool_results=tool_results
                )

            # Execute function calls
            function_responses = []
            for fc in function_calls:
                func_name = fc.name
                func_args = dict(fc.args) if fc.args else {}

                logger.info(f"Executing tool: {func_name} with args: {func_args}")
                tool_calls_made.append({"name": func_name, "args": func_args})

                try:
                    result = await tool_executor(func_name, func_args)
                    tool_results[func_name] = result
                except Exception as e:
                    logger.error(f"Tool execution error: {e}")
                    result = {"error": str(e)}
                    tool_results[func_name] = result

                function_responses.append(types.Part.from_function_response(
                    name=func_name,
                    response=result if isinstance(result, dict) else {"result": result}
                ))

            # Add the model's function call to contents
            contents.append(types.Content(
                role="model",
                parts=[types.Part.from_function_call(
                    name=fc.name,
                    args=dict(fc.args) if fc.args else {}
                ) for fc in function_calls]
            ))

            # Add function responses to contents
            contents.append(types.Content(
                role="user",
                parts=function_responses
            ))

        # Max rounds exceeded
        save_to_conversation(session_id, "user", user_message)
        final_text = "I've processed your request."
        save_to_conversation(session_id, "assistant", final_text)

        return AgenticResponse(
            text=final_text,
            tool_calls_made=tool_calls_made,
            tool_results=tool_results
        )

    except asyncio.TimeoutError:
        logger.error("Gemini API timeout during agentic chat")
        return AgenticResponse(
            text="I'm sorry, the AI is taking too long to respond. Please try again."
        )
    except Exception as e:
        logger.error(f"Agentic chat error: {e}")
        error_str = str(e).lower()
        if "api_key" in error_str or "unauthorized" in error_str:
            return AgenticResponse(
                text="Error: Invalid or missing GOOGLE_API_KEY. Please check your configuration."
            )
        if "quota" in error_str or "rate" in error_str:
            return AgenticResponse(
                text="Error: API rate limit exceeded. Please wait a moment and try again."
            )
        return AgenticResponse(
            text="Sorry, I'm having trouble processing your request. Please try again."
        )
