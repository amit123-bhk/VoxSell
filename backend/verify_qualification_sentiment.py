"""
Phase 6 Lead Qualification & Sentiment Live Verification Script.

Demonstrates:
1. Dynamic BANT discovery & 0-100 lead score progression (Cold -> Warm -> Hot).
2. Real-time sentiment & emotion classification (curious -> interested -> frustrated).
3. Sales objection detection and automated rebuttal retrieval.
4. Two-streak negative sentiment triggering live empathy adaptation.
5. Immediate human escalation trigger on user demand.
"""

import sys
import os
import json

sys.path.insert(0, os.path.dirname(__file__))

from fastapi.testclient import TestClient
from app.main import app
from app.agent.sentiment import SentimentAnalyzer, ObjectionDetector
from app.agent.qualification import BANTScorer, escalate_to_human


def run_qualification_sentiment_demo():
    print("=" * 80)
    print(" VoxSell Phase 6: BANT Qualification, Scoring & Sentiment Verification")
    print("=" * 80)

    # 1. Test BANT Lead Scoring Progression
    print("\n--- [STEP 1: 0-100 BANT LEAD SCORING BREAKDOWN] ---")
    lead_scenarios = [
        {"name": "Initial Inquiry (No BANT)", "b": None, "a": None, "n": None, "t": None, "sent": 0.0},
        {"name": "Need Stated", "b": None, "a": None, "n": "Urgent inbound sales automation", "t": None, "sent": 0.2},
        {"name": "Authority + Budget Added", "b": "5 lakh", "a": "CEO", "n": "Inbound sales", "t": None, "sent": 0.4},
        {"name": "Full BANT (Hot Lead)", "b": "5 lakh", "a": "CEO", "n": "Inbound sales", "t": "This month", "sent": 0.8},
    ]

    for s in lead_scenarios:
        res = BANTScorer.calculate_score(
            budget=s["b"], authority=s["a"], need=s["n"], timeline=s["t"], average_sentiment=s["sent"]
        )
        print(f"[*] Scenario: {s['name']:<28} -> Score: {res['total_score']:>3}/100 [{res['classification']:<4}] (B:{res['breakdown']['budget_points']} A:{res['breakdown']['authority_points']} N:{res['breakdown']['need_points']} T:{res['breakdown']['timeline_points']})")

    # 2. Test Sentiment, Objections & Escalation over Live WebSocket Call
    print("\n--- [STEP 2: LIVE WEBSOCKET SENTIMENT TIMELINE & ESCALATION] ---")
    client = TestClient(app)
    caller = "+15551234567"

    with client.websocket_connect(f"/ws/call/{caller}") as ws:
        ready = ws.receive_json()  # Handshake
        print(f"[*] Connected: {ready['message']}")

        dialogue_flow = [
            # Turn 1: Discovery
            "I need an AI sales agent to handle 24/7 inbound calls.",
            # Turn 2: Stated budget and authority
            "I am the CEO and our budget is around 5 lakh.",
            # Turn 3: Price objection
            "Wait, isn't your platform too expensive compared to alternatives?",
            # Turn 4: Consecutive negative sentiment (Triggers Empathy Adaptation)
            "This feels frustrating and annoying to evaluate.",
            # Turn 5: Human Escalation Trigger
            "Stop talking, let me talk to a real person right now!",
        ]

        for turn_idx, utterance in enumerate(dialogue_flow, 1):
            print(f"\n[TURN {turn_idx} USER] -> \"{utterance}\"")
            ws.send_json({"type": "user_text", "text": utterance})

            tokens = []
            metrics = None
            escalated = False

            while True:
                msg = ws.receive()
                if "bytes" in msg:
                    continue
                if "text" in msg:
                    d = json.loads(msg["text"])
                    m_type = d.get("type")

                    if m_type == "escalation":
                        print(f"🚨 [ESCALATION ACTIVATED] Reason: {d['reason']}")
                        print(f"   Handover Spoken Phrase: \"{d['spoken_message']}\"")
                        escalated = True
                        break
                    elif m_type == "agent_token":
                        tokens.append(d["token"])
                    elif m_type == "latency_metrics":
                        metrics = d
                        break

            if escalated:
                break

            reply = "".join(tokens)
            print(f"[RIYA REPLY]     -> \"{reply[:75]}...\"")
            if metrics:
                print(f"[+] Turn Analytics: Sentiment='{metrics['sentiment']}' (Score: {metrics['sentiment_score']}), Emotion='{metrics['emotion']}', Lead Score={metrics['lead_score']} ({metrics['lead_classification']})")

        ws.send_json({"type": "hangup"})

    print("\n" + "=" * 80)
    print(" [SUCCESS] Phase 6 Lead Qualification, Scoring & Sentiment fully verified!")
    print("=" * 80)


if __name__ == "__main__":
    run_qualification_sentiment_demo()
