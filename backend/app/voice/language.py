"""
Multilingual Language & Code-Mixing Detection Engine.

Detects English, Hindi (Devanagari & Romanized Hinglish), and Punjabi (Gurmukhi & Punglish)
in real-time to enable instantaneous mid-call language switching.
"""

import re
from typing import Dict, Any, Tuple


class LanguageDetector:
    """
    Sub-millisecond hybrid language detector using Unicode range analysis
    and Indic conversational phoneme lexicon matching.
    """

    # Unicode ranges
    DEVANAGARI_REGEX = re.compile(r'[\u0900-\u097F]')
    GURMUKHI_REGEX = re.compile(r'[\u0A00-\u0A7F]')

    # Romanized Hinglish keywords and n-grams
    HINGLISH_KEYWORDS = {
        "kya", "hai", "hain", "mujhe", "aapka", "aap", "hum", "kaise", "chahiye",
        "batao", "bataiye", "kitna", "kitne", "hoga", "shukriya", "dhanyawad",
        "namaste", "haan", "haanji", "theek", "accha", "bilkul", "kaam", "nahi",
        "matlab", "baat", "pata", "bolo", "karo", "karna", "lena", "dijiye",
        "kripya", "samajh", "bhi", "lekin", "par", "sirf", "sab", "yeh", "woh"
    }

    # Romanized Punglish (Punjabi) keywords
    PUNGLISH_KEYWORDS = {
        "ki", "haal", "tussi", "saanu", "daso", "dasso", "sat", "sri", "akaal",
        "paaji", "veere", "kidda", "kiddan", "chahida", "chahidi", "karange",
        "hunda", "hundi", "karde", "ethe", "othe", "tuhanu", "mera", "meri"
    }

    @classmethod
    def detect_language(cls, text: str) -> Tuple[str, str]:
        """
        Detects primary language code and display label from text.

        Returns:
            Tuple of (lang_code, script_type):
                - ('en', 'latin')
                - ('hi', 'devanagari')
                - ('hinglish', 'latin')
                - ('pa', 'gurmukhi')
                - ('pa', 'latin')
        """
        cleaned = text.strip()
        if not cleaned:
            return "en", "latin"

        # 1. Native Script Checks
        if cls.DEVANAGARI_REGEX.search(cleaned):
            return "hi", "devanagari"

        if cls.GURMUKHI_REGEX.search(cleaned):
            return "pa", "gurmukhi"

        # 2. Romanized Indic Code-Mixing Checks (Latin Script)
        words = re.findall(r'\b[a-zA-Z]+\b', cleaned.lower())
        if not words:
            return "en", "latin"

        hinglish_hits = sum(1 for w in words if w in cls.HINGLISH_KEYWORDS)
        punglish_hits = sum(1 for w in words if w in cls.PUNGLISH_KEYWORDS)

        total_words = len(words)

        if punglish_hits > 0 and punglish_hits >= hinglish_hits:
            return "pa", "latin"

        if hinglish_hits > 0 or (total_words <= 4 and hinglish_hits >= 1):
            return "hinglish", "latin"

        if hinglish_hits / total_words >= 0.15:
            return "hinglish", "latin"

        return "en", "latin"

    @classmethod
    def get_prompt_directive(cls, lang_code: str, script_type: str) -> str:
        """
        Generates strict conversational instructions for the LLM to mirror
        the exact language and script of the caller.
        """
        if lang_code == "hi" and script_type == "devanagari":
            return (
                "\n[LANGUAGE ADAPTATION - HINDI]: "
                "The caller is speaking in Hindi. You MUST reply strictly in natural, professional Hindi written in Devanagari script (e.g. 'नमस्ते! मैं वॉक्ससेल से रिया बात कर रही हूँ। क्या आप अपनी बिक्री टीम के लिए एआई वॉयस एजेंट की तलाश कर रहे हैं?'). "
                "Keep your reply strictly 1 to 2 sentences and always end with a question in Hindi."
            )
        elif lang_code == "hinglish":
            return (
                "\n[LANGUAGE ADAPTATION - HINGLISH]: "
                "The caller is speaking in Hinglish (Hindi written in Roman/Latin script). You MUST reply strictly in natural, conversational Hinglish using Roman/Latin script (e.g. 'Haanji, humara starter plan $499 se shuru hota hai. Kya aapko 5 concurrent lines kaafi rahengi?'). "
                "DO NOT use Devanagari script. Keep your reply strictly 1 to 2 sentences and always end with a question in Hinglish."
            )
        elif lang_code == "pa":
            if script_type == "gurmukhi":
                return (
                    "\n[LANGUAGE ADAPTATION - PUNJABI]: "
                    "The caller is speaking in Punjabi. Reply strictly in warm Punjabi written in Gurmukhi script. "
                    "Keep your reply strictly 1 to 2 sentences and always end with a question in Punjabi."
                )
            else:
                return (
                    "\n[LANGUAGE ADAPTATION - PUNGLISH]: "
                    "The caller is speaking in Romanized Punjabi (Punglish). Reply strictly in warm conversational Punjabi using Roman/Latin script (e.g. 'Sat Sri Akaal ji! Main Riya gall kar rahi haan. Ki tussi sales calls automate karna chahunde ho?'). "
                    "Keep your reply strictly 1 to 2 sentences and always end with a question."
                )
        else:
            return (
                "\n[LANGUAGE ADAPTATION - ENGLISH]: "
                "The caller is speaking in English. Reply strictly in clear, professional English. "
                "Keep your reply strictly 1 to 2 sentences and always end with a question in English."
            )
