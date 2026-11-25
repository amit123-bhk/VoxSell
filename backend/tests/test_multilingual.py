"""
Tests for Phase 4 Multilingual Support:
- Language & code-mixing detection (English, Hindi, Hinglish, Punjabi)
- Dynamic mid-call language switching
- Conversational tests in English, Hindi, and Hinglish
"""

import pytest
from app.voice.language import LanguageDetector
from app.agent.llm import StreamingLLMAgent


def test_language_detector_english():
    """Assert English text in Latin script is detected as ('en', 'latin')."""
    text = "Could you please explain your pricing tiers and features?"
    lang, script = LanguageDetector.detect_language(text)
    assert lang == "en"
    assert script == "latin"


def test_language_detector_hindi_devanagari():
    """Assert Devanagari Hindi text is detected as ('hi', 'devanagari')."""
    text = "नमस्ते, मुझे आपके सॉफ्टवेयर की कीमत और प्लान्स के बारे में जानना है।"
    lang, script = LanguageDetector.detect_language(text)
    assert lang == "hi"
    assert script == "devanagari"


def test_language_detector_hinglish_code_mixing():
    """Assert Romanized Hindi/English code-mixing is detected as ('hinglish', 'latin')."""
    text = "Haanji mujhe starter plan ki pricing aur features bataiye."
    lang, script = LanguageDetector.detect_language(text)
    assert lang == "hinglish"
    assert script == "latin"


def test_language_detector_punjabi():
    """Assert Punjabi / Punglish is detected accurately."""
    text = "Sat Sri Akaal ji, ki tussi saanu ek demo de sakde ho?"
    lang, script = LanguageDetector.detect_language(text)
    assert lang == "pa"


def test_prompt_directive_generation():
    """Assert language directives enforce language and script rules."""
    en_dir = LanguageDetector.get_prompt_directive("en", "latin")
    assert "ENGLISH" in en_dir

    hi_dir = LanguageDetector.get_prompt_directive("hi", "devanagari")
    assert "HINDI" in hi_dir
    assert "Devanagari" in hi_dir

    hinglish_dir = LanguageDetector.get_prompt_directive("hinglish", "latin")
    assert "HINGLISH" in hinglish_dir
    assert "Roman/Latin" in hinglish_dir


@pytest.mark.asyncio
async def test_english_conversation_turn():
    """Assert agent speaks English when user speaks English."""
    agent = StreamingLLMAgent(api_key=None)
    user_msg = "Hello, what are your enterprise features?"

    lang, script = LanguageDetector.detect_language(user_msg)
    directive = LanguageDetector.get_prompt_directive(lang, script)

    tokens = []
    async for chunk in agent.stream_reply(
        [{"role": "user", "content": user_msg}],
        lang_directive=directive,
        lang_code=lang,
    ):
        tokens.append(chunk["token"])

    reply = "".join(tokens)
    assert "Riya" in reply
    assert "sales" in reply.lower()


@pytest.mark.asyncio
async def test_hindi_conversation_turn():
    """Assert agent speaks Hindi (Devanagari) when user speaks Hindi."""
    agent = StreamingLLMAgent(api_key=None)
    user_msg = "नमस्ते, मुझे अपनी टीम के लिए बात करनी है।"

    lang, script = LanguageDetector.detect_language(user_msg)
    directive = LanguageDetector.get_prompt_directive(lang, script)

    tokens = []
    async for chunk in agent.stream_reply(
        [{"role": "user", "content": user_msg}],
        lang_directive=directive,
        lang_code=lang,
    ):
        tokens.append(chunk["token"])

    reply = "".join(tokens)
    assert "नमस्ते" in reply
    assert "रिया" in reply


@pytest.mark.asyncio
async def test_hinglish_conversation_turn():
    """Assert agent speaks conversational Hinglish (Latin script) when user speaks Hinglish."""
    agent = StreamingLLMAgent(api_key=None)
    user_msg = "Haanji, aapka starter plan kitne ka padega?"

    lang, script = LanguageDetector.detect_language(user_msg)
    directive = LanguageDetector.get_prompt_directive(lang, script)

    tokens = []
    async for chunk in agent.stream_reply(
        [{"role": "user", "content": user_msg}],
        lang_directive=directive,
        lang_code=lang,
    ):
        tokens.append(chunk["token"])

    reply = "".join(tokens)
    assert "Haanji" in reply
    assert "Riya" in reply
    assert "conversion" in reply.lower()


@pytest.mark.asyncio
async def test_dynamic_mid_call_language_switching():
    """
    Assert the agent dynamically switches reply languages across turns within the same call:
    Turn 1: English -> Replies in English
    Turn 2: User switches to Hinglish -> Agent immediately switches to Hinglish
    Turn 3: User switches to Hindi -> Agent immediately switches to Hindi
    """
    agent = StreamingLLMAgent(api_key=None)
    turns = [
        ("Hi there, I need a voice agent for inbound calls.", "en", "sales"),
        ("Accha, kya aap mujhe pricing bata sakte hain?", "hinglish", "Haanji"),
        ("बहुत बढ़िया, मुझे एक डेमो देखना है।", "hi", "नमस्ते"),
    ]

    for utterance, expected_lang, expected_keyword in turns:
        lang, script = LanguageDetector.detect_language(utterance)
        assert lang == expected_lang, f"Failed language detection for '{utterance}'"

        directive = LanguageDetector.get_prompt_directive(lang, script)
        tokens = []
        async for chunk in agent.stream_reply(
            [{"role": "user", "content": utterance}],
            lang_directive=directive,
            lang_code=lang,
        ):
            tokens.append(chunk["token"])

        reply = "".join(tokens)
        assert expected_keyword in reply, f"Failed turn in {lang}. Expected '{expected_keyword}' in: '{reply}'"
