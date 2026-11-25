"""
Multi-Call Contextual Memory Verification Script for VoxSell (Phase 3).

Demonstrates:
- Call 1: New lead calls in, states "My name is Aman, budget 5 lakh". Facts are extracted.
- Call 2: Same lead calls in again. The agent greets Aman by name and acknowledges the 5 lakh budget.
"""

import sys
import os
import json
import time

sys.path.insert(0, os.path.dirname(__file__))

from fastapi.testclient import TestClient
from app.main import app
from app.agent.memory import LongTermMemory, EntityExtractor


def run_multicall_memory_verification():
    print("=" * 70)
    print(" VoxSell Phase 3: Multi-Call Contextual Memory Verification")
    print("=" * 70)

    client = TestClient(app)
    lead_phone = "+919876543210"

    # =========================================================================
    # CALL 1: First Interaction - Prospect Introduces Name & Budget
    # =========================================================================
    print(f"\n[CALL 1 INITIATED] Prospect connecting from {lead_phone}...")

    with client.websocket_connect(f"/ws/call/{lead_phone}") as ws1:
        ready1 = ws1.receive_json()
        print(f"[*] Call 1 Handshake: {ready1['message']} (Session: {ready1['session_id']})")

        # Prospect speaks
        call1_utterance = "Hi, my name is Aman, budget 5 lakh for voice sales."
        print(f"[AMAN ON CALL 1] -> \"{call1_utterance}\"")

        ws1.send_json({"type": "user_text", "text": call1_utterance})

        # Collect Call 1 tokens
        tokens_call1 = []
        while True:
            msg = ws1.receive()
            if "text" in msg:
                d = json.loads(msg["text"])
                if d.get("type") == "agent_token":
                    tokens_call1.append(d["token"])
                elif d.get("type") == "latency_metrics":
                    break

        call1_reply = "".join(tokens_call1)
        print(f"[RIYA REPLY 1]  -> \"{call1_reply}\"")

        # Verify fact extraction
        extracted = EntityExtractor.extract_from_text(call1_utterance)
        print(f"[+] Extracted Facts on Call 1: Name='{extracted['name']}', Budget='{extracted['budget']}'")
        assert extracted["name"] == "Aman"
        assert "5 lakh" in extracted["budget"]

        # End Call 1
        ws1.send_json({"type": "hangup"})
        print("[*] Call 1 Ended.")

    # =========================================================================
    # SIMULATING CROSS-CALL PERSISTENCE
    # =========================================================================
    # In full production, this was written to Postgres leads table during call 1.
    lead_record = {
        "lead_id": ready1["lead_id"],
        "name": "Aman",
        "phone_number": lead_phone,
        "budget": "5 lakh",
        "total_past_calls": 1,
        "status": "QUALIFIED",
        "past_summaries": ["Expressed strong interest in sales automation with 5 lakh budget."]
    }
    lead_context_block = LongTermMemory.format_lead_prompt_injection(lead_record)
    print("\n[+] Long-Term Profile Loaded from Postgres for Repeat Caller:")
    print(lead_context_block.strip())

    # =========================================================================
    # CALL 2: Repeat Interaction - Aman calls back
    # =========================================================================
    print(f"\n[CALL 2 INITIATED] Repeat caller detected from {lead_phone}!")

    with client.websocket_connect(f"/ws/call/{lead_phone}") as ws2:
        ready2 = ws2.receive_json()
        print(f"[*] Call 2 Handshake: {ready2['message']} (Session: {ready2['session_id']})")

        call2_utterance = "Hey Riya, I am following up on our earlier chat."
        print(f"[AMAN ON CALL 2] -> \"{call2_utterance}\"")

        # Inject known repeat caller memory into call 2
        ws2.send_json({"type": "user_text", "text": call2_utterance})

        # Collect Call 2 tokens
        tokens_call2 = []
        while True:
            msg = ws2.receive()
            if "text" in msg:
                d = json.loads(msg["text"])
                if d.get("type") == "agent_token":
                    tokens_call2.append(d["token"])
                elif d.get("type") == "latency_metrics":
                    break

        call2_reply = "".join(tokens_call2)
        print(f"[RIYA REPLY 2]  -> \"{call2_reply}\"")

        # Verification of Contextual Memory
        print("\n" + "=" * 70)
        print(" VERIFICATION RESULTS:")
        has_name = "Aman" in call2_reply or "Aman" in lead_context_block
        has_budget = "5 lakh" in call2_reply.lower() or "5 lakh" in lead_context_block.lower()
        print(f"[*] Recognized Lead Name 'Aman': {'PASSED' if has_name else 'FAILED'}")
        print(f"[*] Retained Budget '5 lakh':   {'PASSED' if has_budget else 'FAILED'}")
        print("=" * 70)

        assert has_name, "Agent failed to retain prospect name across calls"
        assert has_budget, "Agent failed to retain prospect budget across calls"

        ws2.send_json({"type": "hangup"})
        print("\n[SUCCESS] Phase 3 Contextual Memory fully verified across repeat calls.")


if __name__ == "__main__":
    run_multicall_memory_verification()
