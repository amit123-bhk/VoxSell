"""
Tests for Phase 3 Contextual Memory:
- Short-term rolling summary in Redis
- Entity extraction from user turns
- Long-term memory injection across repeat calls
- Two-call simulation (Call 1: Name & Budget -> Call 2: Remembers Aman & 5 lakh)
"""

import pytest
from app.agent.memory import ShortTermMemory, LongTermMemory, EntityExtractor
from app.agent.llm import StreamingLLMAgent


def test_entity_extraction_name_and_budget():
    """
    Assert EntityExtractor identifies Name ('Aman') and Budget ('5 lakh') from raw utterance.
    """
    utterance = "Hi, my name is Aman, budget 5 lakh for sales automation."
    facts = EntityExtractor.extract_from_text(utterance)

    assert facts["name"] == "Aman"
    assert "5 lakh" in facts["budget"].lower()


@pytest.mark.asyncio
async def test_short_term_memory_rolling_summary():
    """
    Assert ShortTermMemory keeps last 20 turns and compresses older turns into rolling summary.
    """
    memory = ShortTermMemory()
    call_id = "test_call_rolling_123"

    # Add 25 turns (13 user + 12 agent)
    for i in range(25):
        role = "user" if i % 2 == 0 else "assistant"
        await memory.add_turn(call_id, role, f"Message turn {i}")

    context = await memory.get_context_messages(call_id)

    # First message should be the rolling summary
    assert context[0]["role"] == "system"
    assert "CONVERSATION SUMMARY" in context[0]["content"]
    assert "Message turn 0" in context[0]["content"]

    # Raw turns should be capped under 20
    raw_turns = [m for m in context if m["role"] != "system"]
    assert len(raw_turns) <= 20


def test_long_term_prompt_injection_formatting():
    """
    Assert format_lead_prompt_injection creates a structured block with repeat caller history.
    """
    lead_profile = {
        "lead_id": "lead-abc-123",
        "phone_number": "+19876543210",
        "name": "Aman",
        "company": "Aman Tech",
        "lead_score": 75,
        "status": "QUALIFIED",
        "budget": "5 lakh",
        "total_past_calls": 1,
        "past_summaries": ["Discussed enterprise voice agent."],
        "objections": ["Implementation timeline"],
    }

    block = LongTermMemory.format_lead_prompt_injection(lead_profile)

    assert "WHAT YOU KNOW ABOUT THIS LEAD" in block
    assert "Prospect Name: Aman" in block
    assert "Known Budget: 5 lakh" in block
    assert "Past Objections: Implementation timeline" in block
    assert "GREETING DIRECTIVE" in block


@pytest.mark.asyncio
async def test_multi_call_memory_simulation():
    """
    Simulates Call 1 and Call 2 from the same lead:
    Call 1: User introduces themselves as 'Aman' with budget '5 lakh'.
    Call 2: LongTermMemory passes known facts, and agent greets Aman remembering budget.
    """
    # --- CALL 1: First Inbound Call ---
    call1_utterance = "Hi Riya, my name is Aman, budget 5 lakh."
    extracted = EntityExtractor.extract_from_text(call1_utterance)

    assert extracted["name"] == "Aman"
    assert "5 lakh" in extracted["budget"].lower()

    # Simulate persisting to lead store
    lead_db_record = {
        "name": extracted["name"],
        "budget": extracted["budget"],
        "total_past_calls": 1,
        "status": "QUALIFIED",
    }

    # --- CALL 2: Repeat Inbound Call from Aman ---
    call2_lead_block = LongTermMemory.format_lead_prompt_injection(lead_db_record)
    assert "Prospect Name: Aman" in call2_lead_block
    assert "Known Budget: 5 lakh" in call2_lead_block

    # Streaming LLM receives the long-term context
    llm = StreamingLLMAgent(api_key=None)
    call2_messages = [{"role": "user", "content": "Hello again, Riya!"}]

    response_tokens = []
    async for chunk in llm.stream_reply(call2_messages, lead_context=call2_lead_block):
        response_tokens.append(chunk["token"])

    call2_reply = "".join(response_tokens)

    # Verify agent remembered Aman and his 5 lakh budget
    assert "Aman" in call2_reply, f"Expected agent to greet Aman by name. Got: {call2_reply}"
    assert "5 lakh" in call2_reply.lower(), f"Expected agent to reference 5 lakh budget. Got: {call2_reply}"
