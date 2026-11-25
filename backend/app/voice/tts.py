"""
Streaming Text-to-Speech (TTS) module with real-time sentence boundary detection.

Splits incoming LLM token stream into natural acoustic sentence chunks and streams
16kHz linear PCM audio bytes back via Deepgram Aura or Cartesia.
"""

import asyncio
import logging
import re
import time
from typing import AsyncGenerator, Optional, Tuple
import httpx

from app.config import get_settings

logger = logging.getLogger("voxsell.voice.tts")
settings = get_settings()

# Sentence termination patterns (periods, questions, exclamations, colons, or long clauses)
SENTENCE_SPLIT_REGEX = re.compile(r'([.?!]+(?:\s+|$))')
CLAUSE_SPLIT_REGEX = re.compile(r'([,;:]\s+)')


class SentenceChunker:
    """
    Accumulates streaming tokens and yields speakable sentence slices as soon as
    natural linguistic boundaries are detected.
    """

    def __init__(self, min_clause_words: int = 6):
        self.buffer = ""
        self.min_clause_words = min_clause_words

    def add_token(self, token: str) -> Optional[str]:
        """
        Appends token to buffer. If a complete sentence or substantial clause is formed,
        returns the chunk and trims buffer. Otherwise returns None.
        """
        self.buffer += token

        # Check full sentence boundaries: '.', '?', '!'
        match = SENTENCE_SPLIT_REGEX.search(self.buffer)
        if match:
            end_pos = match.end()
            sentence = self.buffer[:end_pos].strip()
            self.buffer = self.buffer[end_pos:]
            return sentence if sentence else None

        # If buffer is getting long, split on clause boundaries (',', ';') to maintain low latency
        words = self.buffer.split()
        if len(words) >= self.min_clause_words:
            clause_match = CLAUSE_SPLIT_REGEX.search(self.buffer)
            if clause_match:
                end_pos = clause_match.end()
                clause = self.buffer[:end_pos].strip()
                self.buffer = self.buffer[end_pos:]
                return clause if clause else None

        return None

    def flush(self) -> Optional[str]:
        """
        Flushes remaining buffer content on end of turn.
        """
        remaining = self.buffer.strip()
        self.buffer = ""
        return remaining if remaining else None


class StreamingTTS:
    """
    Synthesizes text into 16kHz linear PCM audio chunks using Deepgram Aura streaming.
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        voice_id: Optional[str] = None,
    ):
        raw = api_key or settings.TTS_API_KEY or settings.DEEPGRAM_API_KEY
        self.api_key = raw if raw and not raw.startswith("your_") else None
        self.voice_id = voice_id or settings.TTS_VOICE_ID or "aura-asteria-en"
        self.http_client = httpx.AsyncClient(timeout=10.0)

    async def _generate_simulated_pcm(
        self, text: str, start_time: float, cancel_event: Optional[asyncio.Event]
    ) -> AsyncGenerator[Tuple[bytes, Optional[float]], None]:
        """Generates simulated 16kHz linear PCM frames with gentle audio modulation."""
        import math
        sample_rate = 16000
        words = len(text.split())
        duration_s = max(0.4, min(words * 0.28, 4.0))
        total_samples = int(sample_rate * duration_s)
        chunk_samples = 1600  # 100ms chunks (3200 bytes)
        first_byte_emitted = False

        for i in range(0, total_samples, chunk_samples):
            if cancel_event and cancel_event.is_set():
                break

            await asyncio.sleep(0.08)
            latency_ms = (time.perf_counter() - start_time) * 1000.0 if not first_byte_emitted else None
            first_byte_emitted = True

            current_chunk_len = min(chunk_samples, total_samples - i)
            pcm_bytes = bytearray(current_chunk_len * 2)
            for j in range(current_chunk_len):
                sample_idx = i + j
                val = int(800 * (math.sin(2 * math.pi * 320 * sample_idx / sample_rate) + 0.5 * math.sin(2 * math.pi * 440 * sample_idx / sample_rate)))
                pcm_bytes[2*j] = val & 0xFF
                pcm_bytes[2*j + 1] = (val >> 8) & 0xFF

            yield bytes(pcm_bytes), latency_ms

    async def synthesize_stream(
        self,
        text: str,
        lang_code: str = "en",
        cancel_event: Optional[asyncio.Event] = None,
    ) -> AsyncGenerator[Tuple[bytes, Optional[float]], None]:
        """
        Converts text into audio stream chunks with multilingual voice routing.

        Yields:
            Tuple of:
                - audio_bytes: 16kHz linear16 PCM chunk
                - time_to_first_byte_ms: float (emitted on first chunk, None thereafter)
        """
        text = text.strip()
        if not text:
            return

        start_time = time.perf_counter()
        first_byte_emitted = False

        # Resolve voice model based on detected language
        target_voice = settings.TTS_VOICE_MAP.get(lang_code, self.voice_id)
        logger.debug(f"Routing TTS synthesis for lang='{lang_code}' using voice='{target_voice}'")

        # Fallback simulation if no Deepgram key is configured
        if not self.api_key:
            logger.debug(f"[Simulated TTS] Synthesizing: '{text}'")
            async for pcm, lat in self._generate_simulated_pcm(text, start_time, cancel_event):
                yield pcm, lat
            return

        # Real Deepgram Aura streaming TTS
        url = (
            f"https://api.deepgram.com/v1/speak"
            f"?model={target_voice}&encoding=linear16&sample_rate=16000"
        )
        headers = {
            "Authorization": f"Token {self.api_key}",
            "Content-Type": "application/json",
        }
        payload = {"text": text}

        try:
            async with self.http_client.stream(
                "POST", url, headers=headers, json=payload
            ) as response:
                if response.status_code != 200:
                    err_msg = await response.aread()
                    logger.warning(f"Deepgram Aura TTS error ({response.status_code}). Switching to simulated voice stream.")
                    async for pcm, lat in self._generate_simulated_pcm(text, start_time, cancel_event):
                        yield pcm, lat
                    return

                async for chunk in response.aiter_bytes(chunk_size=2048):
                    if cancel_event and cancel_event.is_set():
                        logger.info("Deepgram TTS stream interrupted by user barge-in.")
                        break

                    latency_ms = None
                    if not first_byte_emitted:
                        latency_ms = (time.perf_counter() - start_time) * 1000.0
                        first_byte_emitted = True
                        logger.debug(f"TTS First Byte Latency: {latency_ms:.2f}ms for chunk: '{text[:20]}...'")

                    yield chunk, latency_ms

        except Exception as e:
            logger.warning(f"Error connecting to Deepgram TTS ({e}). Yielding simulated audio.")
            async for pcm, lat in self._generate_simulated_pcm(text, start_time, cancel_event):
                yield pcm, lat

    async def close(self) -> None:
        """Close underlying HTTP client."""
        await self.http_client.aclose()
