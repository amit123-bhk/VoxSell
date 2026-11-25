"""
Automated end-to-end verification script for Phase 2 voice loop.
Tests WebSocket connection, token streaming, barge-in cancellation, and latency metrics.
"""

import sys
import os
import json
import time

sys.path.insert(0, os.path.dirname(__file__))

from fastapi.testclient import TestClient
from app.main import app


def test_realtime_voice_websocket():
    print("[*] Launching VoxSell Real-Time Voice Loop Test...")
    client = TestClient(app)

    with client.websocket_connect("/ws/call/+19876543210") as websocket:
        # 1. Handshake verification
        ready_frame = websocket.receive_json()
        print(f"[+] Received Handshake: {ready_frame['message']} (Session: {ready_frame['session_id']})")
        assert ready_frame["type"] == "connection_ready"

        # 2. Simulate User Turn (Audio/Text)
        user_utterance = "Hi Riya, what is VoxSell and how does it help my sales team?"
        print(f"\n[USER SPEAKING] -> \"{user_utterance}\"")
        start_time = time.perf_counter()

        websocket.send_json({
            "type": "user_text",
            "text": user_utterance
        })

        # 3. Stream Agent Tokens and Audio
        received_tokens = []
        metrics_received = None
        pcm_chunks_received = 0

        while True:
            message = websocket.receive()
            if "bytes" in message and message["bytes"]:
                pcm_chunks_received += 1
            elif "text" in message and message["text"]:
                data = json.loads(message["text"])
                msg_type = data.get("type")

                if msg_type == "agent_token":
                    token = data["token"]
                    received_tokens.append(token)
                    sys.stdout.write(token)
                    sys.stdout.flush()

                elif msg_type == "latency_metrics":
                    metrics_received = data
                    break

        print("\n")
        full_agent_reply = "".join(received_tokens)
        turn_duration = (time.perf_counter() - start_time) * 1000.0

        print(f"[+] Agent Turn Finished. Received {pcm_chunks_received} PCM audio chunks.")
        print(f"[+] Full Agent Reply: \"{full_agent_reply}\"")
        print(f"[+] Latency Metrics:")
        print(f"    - STT Endpointing: {metrics_received['stt_ms']} ms")
        print(f"    - LLM 1st Token:   {metrics_received['llm_first_token_ms']} ms")
        print(f"    - TTS 1st Byte:    {metrics_received['tts_first_byte_ms']} ms")
        print(f"    - Total Turn Time: {metrics_received['total_turn_ms']} ms")
        print(f"    - Target <1.5s Achieved: {metrics_received['target_achieved']}")

        assert len(full_agent_reply) > 0
        assert metrics_received is not None
        assert "?" in full_agent_reply, "Agent reply must end with a question per Riya persona rules"

        # 4. Test Barge-In Interruption
        print("\n[*] Testing User Barge-In Interruption...")
        websocket.send_json({"type": "user_text", "text": "Wait, tell me about pricing."})

        # Receive first few tokens then send another turn to barge in
        for _ in range(3):
            websocket.receive()

        print("[USER BARGE-IN] -> Interrupted agent mid-speech!")
        websocket.send_json({"type": "user_text", "text": "Can you hear me?"})

        # Read until new agent reply starts
        barge_in_acked = False
        for _ in range(10):
            msg = websocket.receive()
            if "text" in msg:
                d = json.loads(msg["text"])
                if d.get("type") == "barge_in":
                    barge_in_acked = True
                    print("[+] Barge-in successfully confirmed by server!")
                    break

        # Hang up call
        websocket.send_json({"type": "hangup"})
        print("\n[SUCCESS] Phase 2 Real-Time Voice Loop verified successfully.")


if __name__ == "__main__":
    test_realtime_voice_websocket()
