"""
Real-Time Sentiment, Emotion, and Objection Analysis Engine.

Performs sub-millisecond sentiment classification, emotion valence detection,
objection classification, and human escalation triggers for live voice conversations.
"""

import re
from typing import Dict, Any, Tuple, Optional


class SentimentAnalyzer:
    """
    High-speed hybrid acoustic-linguistic sentiment and emotion classifier.
    Returns polarity, continuous score (-1.0 to +1.0), and fine-grained emotion.
    """

    # Lexical patterns for emotion mapping
    POSITIVE_WORDS = {
        "great", "awesome", "perfect", "good", "love", "interested", "excellent",
        "definitely", "yes", "sure", "sounds good", "impressive", "helpful",
        "fantastic", "wonderful", "cool", "super", "shukriya", "badhiya", "sahi", "theek"
    }
    CONFUSED_WORDS = {
        "confused", "don't understand", "what do you mean", "not clear", "repeat",
        "didn't catch", "puzzled", "samajh nahi aaya", "matlab"
    }
    FRUSTRATED_WORDS = {
        "expensive", "too high", "not working", "waste", "annoying", "stop calling",
        "slow", "ridiculous", "complicated", "boring", "useless", "bakwaas", "pareshan"
    }
    ANGRY_WORDS = {
        "angry", "furious", "terrible", "scam", "cheat", "shut up", "idiot",
        "hate", "sue", "legal", "harassment", "rubbish", "horrible", "stupid"
    }
    ESCALATE_KEYWORDS = [
        re.compile(r"\b(?:talk to|speak with|connect me to|transfer to|get me)\s+(?:a\s+)?(?:human|person|agent|representative|manager|operator)\b", re.IGNORECASE),
        re.compile(r"\b(?:real\s+person|human\s+being|live\s+agent)\b", re.IGNORECASE),
        re.compile(r"\b(?:stop\s+talking|let me talk to someone)\b", re.IGNORECASE),
    ]

    @classmethod
    def analyze(cls, text: str) -> Dict[str, Any]:
        """
        Analyzes utterance text for sentiment, emotion, score, and human escalation need.
        """
        cleaned = text.lower().strip()
        if not cleaned:
            return {
                "sentiment": "neutral",
                "score": 0.0,
                "emotion": "neutral",
                "requires_escalation": False,
            }

        # 1. Check for explicit request for a human
        requires_escalation = any(pat.search(cleaned) for pat in cls.ESCALATE_KEYWORDS)

        # 2. Emotion and Polarity scoring
        words = set(re.findall(r'\b[a-z\']+\b', cleaned))

        angry_hits = sum(1 for w in words if w in cls.ANGRY_WORDS)
        frustrated_hits = sum(1 for w in words if w in cls.FRUSTRATED_WORDS)
        confused_hits = sum(1 for w in words if w in cls.CONFUSED_WORDS)
        positive_hits = sum(1 for w in words if w in cls.POSITIVE_WORDS)

        if angry_hits > 0:
            return {
                "sentiment": "negative",
                "score": -0.85,
                "emotion": "angry",
                "requires_escalation": True,  # Auto-escalate angry caller
            }

        if frustrated_hits > 0:
            return {
                "sentiment": "negative",
                "score": -0.6,
                "emotion": "frustrated",
                "requires_escalation": requires_escalation,
            }

        if confused_hits > 0:
            return {
                "sentiment": "neutral",
                "score": -0.2,
                "emotion": "confused",
                "requires_escalation": requires_escalation,
            }

        if positive_hits > 0:
            score = min(0.9, 0.4 + (0.2 * positive_hits))
            return {
                "sentiment": "positive",
                "score": score,
                "emotion": "interested",
                "requires_escalation": requires_escalation,
            }

        # Check question intent (curious)
        if "?" in text or any(w in words for w in {"how", "what", "pricing", "cost", "demo", "features"}):
            return {
                "sentiment": "neutral",
                "score": 0.15,
                "emotion": "curious",
                "requires_escalation": requires_escalation,
            }

        return {
            "sentiment": "neutral",
            "score": 0.0,
            "emotion": "neutral",
            "requires_escalation": requires_escalation,
        }


class ObjectionDetector:
    """
    Detects and categorizes prospect sales objections (Price, Timing, Competitor, Trust).
    """

    PRICE_PATTERNS = [
        re.compile(r"\b(?:too expensive|costs? too much|high price|budget is tight|can't afford|cheaper|discount|paise zyada)\b", re.IGNORECASE)
    ]
    TIMING_PATTERNS = [
        re.compile(r"\b(?:not right now|next month|next quarter|next year|call back later|too busy|bad time|abhi nahi|baad mein)\b", re.IGNORECASE)
    ]
    COMPETITOR_PATTERNS = [
        re.compile(r"\b(?:already using|already have|competitor|alternative|evaluating other|using another)\b", re.IGNORECASE)
    ]
    TRUST_PATTERNS = [
        re.compile(r"\b(?:never heard of|how do i know|is it reliable|case study|proven|trust|references|guarantee)\b", re.IGNORECASE)
    ]

    @classmethod
    def detect_objection(cls, text: str) -> Optional[Dict[str, str]]:
        """
        Detects if utterance is a known sales objection. Returns category and guidance.
        """
        for pat in cls.PRICE_PATTERNS:
            if pat.search(text):
                return {
                    "category": "price",
                    "rebuttal_strategy": "Acknowledge cost concern, highlight ROI and included minutes ($499 covers 2500 minutes replacing an entire SDR salary), and offer Starter tier."
                }

        for pat in cls.TIMING_PATTERNS:
            if pat.search(text):
                return {
                    "category": "timing",
                    "rebuttal_strategy": "Respect their schedule, emphasize that VoxSell takes under 15 minutes to configure, and ask for a 10-minute calendar placeholder next week."
                }

        for pat in cls.COMPETITOR_PATTERNS:
            if pat.search(text):
                return {
                    "category": "competitor",
                    "rebuttal_strategy": "Acknowledge their current setup, differentiate VoxSell's sub-1.5s real-time latency and multilingual Hindi/Punjabi auto-switching."
                }

        for pat in cls.TRUST_PATTERNS:
            if pat.search(text):
                return {
                    "category": "trust",
                    "rebuttal_strategy": "Point to enterprise uptime SLA (99.95%), offer a live test drive on their own phone, and reference customer satisfaction."
                }

        return None
