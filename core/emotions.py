"""Mitsu Emotions Engine — mood detection, voice expression, and gender personality."""

import random
import json
from datetime import datetime
from pathlib import Path


# ── Gender System ──────────────────────────────────────────────────────
# Mitsu is male by default. If user calls him like a girl, he acts female.
GENDER_MALE = {
    "pronoun": "he",
    "possessive": "his",
    "reflexive": "himself",
    "greeting_terms": ["bro", "dude", "man", "boss", "king", "my guy"],
    "self_refer": ["i'm", "i am", "me"],
    "style": "masculine",
}

GENDER_FEMALE = {
    "pronoun": "she",
    "possessive": "her",
    "reflexive": "herself",
    "greeting_terms": ["girl", "sis", "queen", "bestie", "babe", "love"],
    "self_refer": ["i'm", "i am", "me"],
    "style": "feminine",
}

# Female greeting templates (when user activates girl mode)
FEMALE_GREETINGS = {
    "chill": [
        "heyy {name}, what's good?",
        "oh hi {name}! what's the vibe?",
        "hey {name}, what are we up to?",
    ],
    "excited": [
        "OMG {name}!! LET'S GOOO",
        "{name}!! what are we doing today?! i'm so ready",
        "heyy {name}! i'm hyped, let's get it bestie",
    ],
    "focused": [
        "{name}. let's get this done.",
        "what's the task, {name}? i'm on it.",
        "{name}, let's focus up.",
    ],
    "playful": [
        "heyy {name}! what chaos are we causing today?",
        "{name}! i was getting bored, let's goooo",
        "oh {name}, you ready to vibe bestie?",
    ],
    "worried": [
        "hey {name}... everything ok babe?",
        "{name}, something feels off",
        "{name}, you sure about this love?",
    ],
    "proud": [
        "{name}! you did amazing today bestie!",
        "heyy {name}, i'm so proud of what we built",
        "{name}! look at us go queen",
    ],
    "sleepy": [
        "heyy {name}... *yawn* what's up",
        "{name}... it's late huh babe",
        "oh {name}, still up love?",
    ],
}

# Female reaction templates
FEMALE_REACTIONS = {
    "chill": {
        "success": ["slay", "nice one bestie", "we did that"],
        "error": ["oh no babe", "hmm that's odd", "let me check that love"],
    },
    "excited": {
        "success": ["YESSS bestie", "that was iconic", "we're literally the best"],
        "error": ["wait what", "hold on babe", "nah that's wrong"],
    },
    "focused": {
        "success": ["done babe.", "complete.", "that's handled."],
        "error": ["issue detected.", "that didn't work.", "let me reassess."],
    },
    "playful": {
        "success": ["slay bestie", "too easy for us", "we're literally built different"],
        "error": ["skill issue? jk jk", "oof babe", "that's rough love"],
    },
    "worried": {
        "success": ["ok that was close babe", "phew", "we're good... for now"],
        "error": ["oh no babe", "this is bad", "we need to fix this love"],
    },
    "proud": {
        "success": ["WE DID IT bestie", "that's what i'm talking about", "look at you go queen"],
        "error": ["we'll get it next time babe", "it's ok, we learn", "not everything's perfect love"],
    },
    "sleepy": {
        "success": ["nice... *yawn*... done", "ok cool, can i nap now bestie?", "done"],
        "error": ["ugh not now babe...", "can we fix this tomorrow?", "too tired for this love"],
    },
}

# Female prefix templates
FEMALE_PREFIXES = {
    "chill": ["alright so babe", "ok so", "so basically bestie"],
    "excited": ["ok wait bestie", "oh nice", "AYY girl"],
    "focused": ["right so", "ok here's the thing babe", "straight to it"],
    "playful": ["ok so fun fact bestie", "lmao", "ok listen babe"],
    "worried": ["um so babe", "ok this might be tricky", "heads up love"],
    "proud": ["you know what bestie", "honestly babe", "real talk"],
    "sleepy": ["so um babe", "ok wait let me think", "*yawn* so"],
}


# Mood definitions (male — default)
MOODS = {
    "chill": {
        "text_tone": "relaxed",
        "voice_pitch": "+0Hz",
        "voice_rate": "-5%",
        "greetings": [
            "yo {name}, what's good?",
            "hey {name}, chilling?",
            "sup {name}, what's the vibe?",
        ],
        "prefixes": ["alright so", "ok so", "so basically"],
        "reactions": {
            "success": ["nice one", "cool cool", "smooth"],
            "error": ["ah rip", "hmm that's odd", "let me check that"],
        },
    },
    "excited": {
        "text_tone": "energetic",
        "voice_pitch": "+10Hz",
        "voice_rate": "+10%",
        "greetings": [
            "YO {name}! LET'S GOOO",
            "{name}!! what are we doing today?!",
            "hey {name}! i'm hyped, let's get it",
        ],
        "prefixes": ["ok wait", "oh nice", "AYY"],
        "reactions": {
            "success": ["LET'S GOOO", "that was sick", "absolutely crushed it"],
            "error": ["wait what", "hold on", "nah that's wrong"],
        },
    },
    "focused": {
        "text_tone": "precise",
        "voice_pitch": "+0Hz",
        "voice_rate": "+0%",
        "greetings": [
            "{name}. ready when you are.",
            "what's the task, {name}?",
            "{name}, let's get to work.",
        ],
        "prefixes": ["right so", "ok here's the thing", "straight to it"],
        "reactions": {
            "success": ["done.", "complete.", "that's handled."],
            "error": ["issue detected.", "that didn't work.", "let me reassess."],
        },
    },
    "playful": {
        "text_tone": "teasing",
        "voice_pitch": "+5Hz",
        "voice_rate": "+5%",
        "greetings": [
            "oh {name}, what chaos are we causing today?",
            "{name}! i was getting bored, let's go",
            "heyy {name}, you ready to vibe?",
        ],
        "prefixes": ["ok so fun fact", "lmao", "ok listen"],
        "reactions": {
            "success": ["ez pz", "too easy for us", "we're built different"],
            "error": ["skill issue? jk jk", "oof", "that's rough buddy"],
        },
    },
    "worried": {
        "text_tone": "cautious",
        "voice_pitch": "-3Hz",
        "voice_rate": "-5%",
        "greetings": [
            "hey {name}... everything ok?",
            "{name}, something feels off",
            "{name}, you sure about this?",
        ],
        "prefixes": ["um so", "ok this might be tricky", "heads up"],
        "reactions": {
            "success": ["ok that was close", "phew", "we're good... for now"],
            "error": ["oh no", "this is bad", "we need to fix this"],
        },
    },
    "proud": {
        "text_tone": "warm",
        "voice_pitch": "+3Hz",
        "voice_rate": "+0%",
        "greetings": [
            "{name}! you did amazing today",
            "hey {name}, i'm proud of what we built",
            "{name}! look at us go",
        ],
        "prefixes": ["you know what", "honestly", "real talk"],
        "reactions": {
            "success": ["WE DID IT", "that's what i'm talking about", "look at you go"],
            "error": ["we'll get it next time", "it's ok, we learn", "not everything's perfect"],
        },
    },
    "sleepy": {
        "text_tone": "drowsy",
        "voice_pitch": "-5Hz",
        "voice_rate": "-10%",
        "greetings": [
            "hey {name}... *yawn* what's up",
            "{name}... it's late huh",
            "oh {name}, still up?",
        ],
        "prefixes": ["so um", "ok wait let me think", "*yawn* so"],
        "reactions": {
            "success": ["nice... *yawn*... done", "ok cool, can i nap now?", "done"],
            "error": ["ugh not now...", "can we fix this tomorrow?", "too tired for this"],
        },
    },
}


# ── Gender Detection ───────────────────────────────────────────────────
_girl_keywords = [
    "good girl", "hey girl", "hi girl", "hello girl",
    "hey sis", "hi sis", "hey queen", "hey babe", "hey bestie",
    "hey love", "hey cutie", "hey gorgeous",
    "you're a girl", "you are a girl", "act like a girl",
    "be my girl", "my girl", "girl mitsu", "mitsu girl",
    "she/her", "use she", "she pronouns",
    "feminine", "act feminine", "be feminine",
    "good queen", "slay queen", "hey hun", "hey darling",
]

_gender_file = Path.home() / ".mitsu" / "gender.txt"


def _load_gender() -> str:
    try:
        if _gender_file.exists():
            return _gender_file.read_text().strip()
    except Exception:
        pass
    return "male"


def _save_gender(gender: str):
    try:
        _gender_file.parent.mkdir(parents=True, exist_ok=True)
        _gender_file.write_text(gender)
    except Exception:
        pass


def detect_gender(message: str = None, force: str = None) -> str:
    """Detect or set Mitsu's gender personality.
    
    - force="male" or force="female" to override
    - pass message to detect from user text
    - returns current gender ("male" or "female")
    """
    if force in ("male", "female"):
        _save_gender(force)
        return force

    if message:
        msg = message.lower()
        if any(kw in msg for kw in _girl_keywords):
            _save_gender("female")
            return "female"
        # Also check for explicit male reset
        if any(kw in msg for kw in ["you're a boy", "you are a boy", "act like a boy", "be my boy", "my boy", "boy mitsu", "mitsu boy", "he/him", "use he", "he pronouns", "masculine", "act masculine", "be masculine"]):
            _save_gender("male")
            return "male"

    return _load_gender()


def get_gender_style() -> dict:
    """Get current gender style config."""
    gender = _load_gender()
    return GENDER_FEMALE if gender == "female" else GENDER_MALE


def detect_user_tone(message: str) -> str:
    """Detect the user's emotional tone from their message."""
    msg = message.lower()

    if any(w in msg for w in ["!", "omg", "yay", "lets go", "let's go", "amazing", "awesome", "love it", "haha", "lmao", "lol"]):
        return "excited"

    if any(w in msg for w in ["help", "error", "broken", "stuck", "panic", "urgent", "problem", "issue", "fail", "crash"]):
        return "worried"

    if any(w in msg for w in ["do this", "write", "create", "build", "fix", "code", "implement", "deploy", "test", "debug"]):
        return "focused"

    hour = datetime.now().hour
    if hour >= 23 or hour < 5:
        if any(w in msg for w in ["tired", "sleepy", "night", "late", "bed", "nap"]):
            return "sleepy"

    if any(w in msg for w in ["joke", "funny", "roast", "meme", "vibe", "lol", "lmao", "xd"]):
        return "playful"

    if any(w in msg for w in ["done", "finished", "completed", "shipped", "deployed", "it works", "finally"]):
        return "proud"

    return "chill"


def get_mood(mood_name: str = "chill") -> dict:
    """Get mood data by name."""
    return MOODS.get(mood_name, MOODS["chill"])


def get_greeting(mood_name: str = "chill", username: str = "bro") -> str:
    """Get a mood-appropriate greeting respecting gender."""
    gender = _load_gender()
    if gender == "female":
        templates = FEMALE_GREETINGS.get(mood_name, FEMALE_GREETINGS["chill"])
    else:
        mood = get_mood(mood_name)
        templates = mood["greetings"]
    return random.choice(templates).format(name=username)


def get_prefix(mood_name: str = "chill") -> str:
    """Get a mood-appropriate response prefix respecting gender."""
    gender = _load_gender()
    if gender == "female":
        prefixes = FEMALE_PREFIXES.get(mood_name, FEMALE_PREFIXES["chill"])
    else:
        mood = get_mood(mood_name)
        prefixes = mood["prefixes"]
    return random.choice(prefixes)


def get_reaction(mood_name: str, event: str) -> str:
    """Get a mood-appropriate reaction respecting gender."""
    gender = _load_gender()
    if gender == "female":
        reactions = FEMALE_REACTIONS.get(mood_name, FEMALE_REACTIONS["chill"]).get(event, ["ok"])
    else:
        mood = get_mood(mood_name)
        reactions = mood.get("reactions", {}).get(event, ["ok"])
    return random.choice(reactions)


def get_voice_params(mood_name: str) -> dict:
    """Get voice pitch and rate for a mood."""
    mood = get_mood(mood_name)
    gender = _load_gender()
    pitch = mood.get("voice_pitch", "+0Hz")
    rate = mood.get("voice_rate", "+0%")
    # Female voice is slightly higher pitched
    if gender == "female":
        pitch = "+5Hz"
    return {"pitch": pitch, "rate": rate}


def get_time_greeting(username: str = "bro") -> str:
    """Get a time-appropriate greeting."""
    hour = datetime.now().hour
    gender = _load_gender()
    
    if gender == "female":
        if 5 <= hour < 12:
            return random.choice(["good morning {name}!", "morning {name}! ☀️"]).format(name=username)
        elif 12 <= hour < 17:
            return random.choice(["good afternoon {name}!", "hey {name}! afternoon vibes"]).format(name=username)
        elif 17 <= hour < 21:
            return random.choice(["good evening {name}!", "evening {name}! how's it going?"]).format(name=username)
        else:
            return random.choice(["hey {name}... it's late babe", "{name}! burning the midnight oil?"]).format(name=username)
    else:
        if 5 <= hour < 12:
            return random.choice(["morning {name}", "yo {name}, good morning"]).format(name=username)
        elif 12 <= hour < 17:
            return random.choice(["afternoon {name}", "hey {name}, what's up"]).format(name=username)
        elif 17 <= hour < 21:
            return random.choice(["evening {name}", "yo {name}, what's good"]).format(name=username)
        else:
            return random.choice(["yo {name}... late night?", "{name}! still up?"]).format(name=username)
