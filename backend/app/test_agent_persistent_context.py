"""Tests for Persistent Context Pattern in InterpawsAgent.

Run (inside backend container or with PYTHONPATH set):
    python -m app.test_agent_persistent_context

This uses a monkeypatched LLM call to avoid external dependency.
"""

import asyncio
import json
from typing import Any

import pytest

from .agent.core import InterpawsAgent, CONVERSATION_MEMORY
from . import ai_services


@pytest.mark.asyncio
async def test_persistent_context_injected(monkeypatch):
    async def fake_get(prompt: str, json_mode: bool = False, temperature: Any = None):  # noqa: D401
        # Force a final_answer so the loop exits immediately
        return json.dumps({
            "thought": "Use provided entity names each turn",
            "action": "final_answer",
            "action_input": "Acknowledged context"
        })

    monkeypatch.setattr(ai_services, "get_ollama_recommendation", fake_get)

    agent = InterpawsAgent(db_session=None)
    session_id = "test-session-context-1"

    result = await agent.chat(
        user_message="Please suggest slots",
        context="Complaint about lethargy",
        session_id=session_id,
        complaint_text="Lethargy and loss of appetite",
        pet_name="JJ Junior",
        owner_name="Sam Rivera"
    )

    assert "response" in result, "Agent should return a response"
    assert session_id in CONVERSATION_MEMORY, "Conversation memory should store the session"
    history = CONVERSATION_MEMORY[session_id]
    system_entries = [h for h in history if h.get("role") == "system"]
    assert system_entries, "System prompt entry must exist"
    # Verify KNOWN ENTITIES block persisted
    assert any(
        "KNOWN ENTITIES" in e.get("content", "") and
        "JJ Junior" in e.get("content", "") and
        "Sam Rivera" in e.get("content", "")
        for e in system_entries
    ), "Pet and owner names should appear in system prompt KNOWN ENTITIES block"


def main():  # pragma: no cover - manual runner convenience
    asyncio.run(test_persistent_context_injected(pytest.MonkeyPatch()))
    print("✅ Persistent context test executed")


if __name__ == "__main__":  # pragma: no cover
    main()
