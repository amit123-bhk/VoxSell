"""
Phase 4 Multilingual Verification Script for VoxSell.

Demonstrates:
1. English conversation turn
2. Hindi (Devanagari) conversation turn
3. Hinglish (Roman/Latin code-mixing) conversation turn
4. Dynamic mid-call language switching within a single continuous session
"""

import sys
import os
import json

sys.path.insert(0, os.path.dirname(__file__))

from fastapi.testclient import TestClient
from app.main import app
from app.voice.language import LanguageDetector


def run_multilingual_verification():
    print("=" * 75)
    print(" VoxSell Phase 4: Multilingual & Code-Mixing Live Verification")
    print("=" * 75)

    client = TestClient(app)

    # =========================================================================
    # TEST 1: English Conversation
    # =========================================================================
    print("\n--- [TEST 1: ENGLISH CONVERSATION] ---")
    en_input = "Hello Riya, could you explain how VoxSell automates sales calls?"
    lang, script = LanguageDetector.detect_language(en_input)
    print(f"[*] User: \"{en_input}\"")
    print(f"[+] Detected: Language='{lang}', Script='{script}'")
    assert lang == "en"

    # =========================================================================
    # TEST 2: Hindi (Devanagari) Conversation
    # =========================================================================
    print("\n--- [TEST 2: HINDI (DEVANAGARI) CONVERSATION] ---")
    hi_input = "नमस्ते, मुझे अपनी बिक्री टीम के लिए सॉफ्टवेयर की जानकारी चाहिए।"
    lang, script = LanguageDetector.detect_language(hi_input)
    print(f"[*] User: \"{hi_input}\"")
    print(f"[+] Detected: Language='{lang}', Script='{script}'")
    assert lang == "hi"
    assert script == "devanagari"

    # =========================================================================
    # TEST 3: Hinglish (Romanized Hindi-English Code-Mixing)
    # =========================================================================
    print("\n--- [TEST 3: HINGLISH CODE-MIXING CONVERSATION] ---")
    hinglish_input = "Haanji Riya, kya aap mujhe starter plan ki pricing bata sakti hain?"
    lang, script = LanguageDetector.detect_language(hinglish_input)
    print(f"[*] User: \"{hinglish_input}\"")
    print(f"[+] Detected: Language='{lang}', Script='{script}'")
    assert lang == "hinglish"
    assert script == "latin"

    # =========================================================================
    # TEST 4: Live WebSocket Dynamic Mid-Call Language Switching
    # =========================================================================
    print("\n--- [TEST 4: DYNAMIC MID-CALL LANGUAGE SWITCHING OVER WEBSOCKET] ---")
    lead_id = "+918888899999"

    with client.websocket_connect(f"/ws/call/{lead_id}") as ws:
        ws.receive_json()  # Handshake

        dialogue_sequence = [
            ("Hi, I want to learn more about your voice agent platform.", "en"),
            ("Accha, iski monthly pricing kya padegi?", "hinglish"),
            ("बहुत अच्छा, क्या आप मुझे एक डेमो दिखा सकते हैं?", "hi"),
        ]

        for utterance, expected_lang in dialogue_sequence:
            print(f"\n[USER SPEAKING] ({expected_lang.upper()}) -> \"{utterance}\"")
            ws.send_json({"type": "user_text", "text": utterance})

            tokens = []
            metrics = None
            while True:
                msg = ws.receive()
                if "text" in msg:
                    d = json.loads(msg["text"])
                    if d.get("type") == "agent_token":
                        tokens.append(d["token"])
                    elif d.get("type") == "latency_metrics":
                        metrics = d
                        break

            reply = "".join(tokens)
            print(f"[RIYA REPLY]    -> \"{reply}\"")
            print(f"[+] Turn Metrics: Detected='{metrics['language']}', Latency={metrics['total_turn_ms']}ms (<1.5s: {metrics['target_achieved']})")
            assert metrics["language"] == expected_lang

        ws.send_json({"type": "hangup"})

    print("\n" + "=" * 75)
    print(" [SUCCESS] Phase 4 Multilingual & Code-Mixing verified across all dialects!")
    print("=" * 75)


if __name__ == "__main__":
    run_multilingual_verification()
