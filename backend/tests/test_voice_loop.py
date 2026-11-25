"""
Unit and integration tests for Phase 2 voice loop components:
SentenceChunker, StreamingLLM, and WebSocket call routing.
"""

import pytest
from app.voice.tts import SentenceChunker
from app.agent.llm import StreamingLLMAgent


def test_sentence_chunker_punctuation_split():
    """
    Assert SentenceChunker yields speakable sentence slices on '.', '?', '!' punctuation.
    """
    chunker = SentenceChunker()
    tokens = ["Hello ", "there! ", "How ", "are ", "you ", "doing ", "today?"]

    yielded_chunks = []
    for token in tokens:
        chunk = chunker.add_token(token)
        if chunk:
            yielded_chunks.append(chunk)

    remaining = chunker.flush()
    if remaining:
        yielded_chunks.append(remaining)

    assert len(yielded_chunks) == 2
    assert yielded_chunks[0] == "Hello there!"
    assert yielded_chunks[1] == "How are you doing today?"


def test_sentence_chunker_flush_unpunctuated():
    """
    Assert SentenceChunker flushes trailing tokens when stream ends without ending punctuation.
    """
    chunker = SentenceChunker()
    chunker.add_token("We can schedule a ")
    chunker.add_token("quick demo tomorrow")
    flushed = chunker.flush()
    assert flushed == "We can schedule a quick demo tomorrow"


@pytest.mark.asyncio
async def test_streaming_llm_fallback_generator():
    """
    Assert StreamingLLMAgent falls back gracefully to structured simulated response
    when API keys are unconfigured.
    """
    agent = StreamingLLMAgent(api_key=None)
    messages = [{"role": "user", "content": "Tell me about VoxSell"}]

    tokens = []
    first_latency = None

    async for chunk in agent.stream_reply(messages):
        tokens.append(chunk["token"])
        if chunk["first_token_latency_ms"] is not None and first_latency is None:
            first_latency = chunk["first_token_latency_ms"]

    full_text = "".join(tokens)
    assert len(full_text) > 0
    assert "Riya" in full_text
    assert first_latency is not None
    assert first_latency >= 0.0
