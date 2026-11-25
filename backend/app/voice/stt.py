"""
Deepgram Live Streaming Speech-to-Text (STT) Client.

Streams 16kHz linear PCM audio chunks over a persistent WebSocket connection to Deepgram Nova-2,
yielding interim and final transcripts with ~300ms silence endpointing.
"""

import asyncio
import json
import logging
from typing import AsyncGenerator, Dict, Any, Optional
import websockets
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

from app.config import get_settings

logger = logging.getLogger("voxsell.voice.stt")
settings = get_settings()

DEEPGRAM_WS_URL = (
    "wss://api.deepgram.com/v1/listen?"
    "encoding=linear16"
    "&sample_rate=16000"
    "&channels=1"
    "&model=nova-2"
    "&smart_format=true"
    "&interim_results=true"
    "&endpointing=300"
    "&vad_events=true"
)


class DeepgramLiveSTT:
    """
    Manages live bi-directional streaming STT with Deepgram via WebSockets.
    """

    def __init__(self, api_key: Optional[str] = None):
        raw = api_key or settings.DEEPGRAM_API_KEY
        self.api_key = raw if raw and not raw.startswith("your_") else None
        self.ws: Optional[websockets.WebSocketClientProtocol] = None
        self._connected = False
        self._closing = False

    async def connect(self) -> None:
        """
        Establishes the WebSocket connection to Deepgram's streaming transcription API.
        """
        if not self.api_key:
            logger.info("DEEPGRAM_API_KEY is placeholder or not configured. Running in simulated voice loop mode.")
            self._connected = False
            return

        headers = {"Authorization": f"Token {self.api_key}"}
        try:
            connect_kwargs = {"ping_interval": 10, "ping_timeout": 5}
            try:
                self.ws = await websockets.connect(
                    DEEPGRAM_WS_URL,
                    additional_headers=headers,
                    **connect_kwargs
                )
            except TypeError:
                self.ws = await websockets.connect(
                    DEEPGRAM_WS_URL,
                    extra_headers=headers,
                    **connect_kwargs
                )
            self._connected = True
            logger.info("Successfully connected to Deepgram Live STT WebSocket.")
        except Exception as e:
            logger.warning(f"Could not connect to external Deepgram STT ({e}). Running in simulated fallback mode.")
            self._connected = False

    async def send_audio(self, pcm_chunk: bytes) -> None:
        """
        Transmits raw 16kHz PCM audio bytes to Deepgram.
        """
        if self._connected and self.ws and not self.ws.closed:
            try:
                await self.ws.send(pcm_chunk)
            except Exception as e:
                logger.warning(f"Error sending audio chunk to Deepgram: {e}")
        else:
            logger.debug(f"Simulating audio buffer ingestion: {len(pcm_chunk)} bytes")

    async def stream_transcripts(self) -> AsyncGenerator[Dict[str, Any], None]:
        """
        Listens for Deepgram WebSocket frames and yields structured transcript events.

        Yields:
            dict with keys:
                - type: 'interim' | 'final' | 'speech_started'
                - text: transcript text string
                - is_speech_final: boolean indicating endpointing silence trigger
        """
        if not self._connected or not self.ws:
            return

        try:
            async for message in self.ws:
                if self._closing:
                    break

                try:
                    data = json.loads(message)
                except json.JSONDecodeError:
                    continue

                msg_type = data.get("type")

                # Early barge-in detection trigger from VAD
                if msg_type == "SpeechStarted":
                    yield {
                        "type": "speech_started",
                        "text": "",
                        "is_speech_final": False,
                    }
                    continue

                if msg_type == "Results":
                    channel = data.get("channel", {})
                    alternatives = channel.get("alternatives", [{}])
                    if not alternatives:
                        continue

                    transcript = alternatives[0].get("transcript", "").strip()
                    if not transcript:
                        continue

                    is_final = data.get("is_final", False)
                    speech_final = data.get("speech_final", False)

                    if speech_final or is_final:
                        yield {
                            "type": "final",
                            "text": transcript,
                            "is_speech_final": speech_final,
                            "confidence": alternatives[0].get("confidence", 0.0),
                        }
                    else:
                        yield {
                            "type": "interim",
                            "text": transcript,
                            "is_speech_final": False,
                            "confidence": alternatives[0].get("confidence", 0.0),
                        }

        except websockets.exceptions.ConnectionClosed as e:
            logger.info(f"Deepgram WebSocket connection closed: {e}")
        except Exception as e:
            logger.error(f"Error reading transcripts from Deepgram: {e}", exc_info=True)
        finally:
            self._connected = False

    async def close(self) -> None:
        """
        Gracefully closes the Deepgram streaming WebSocket.
        """
        self._closing = True
        if self.ws and not self.ws.closed:
            try:
                # Deepgram protocol: sending empty json tells server to finalize
                await self.ws.send(json.dumps({"type": "CloseStream"}))
                await asyncio.sleep(0.05)
                await self.ws.close()
            except Exception as e:
                logger.debug(f"Error during Deepgram socket closure: {e}")
            finally:
                self._connected = False
                logger.info("Deepgram Live STT connection closed.")
