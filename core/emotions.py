"""Mitsu Emotions Engine — mood detection, voice expression, auto theming, gender, and proactive chat."""

import random
from datetime import datetime


# Gender configurations — pronouns and how Mitsu refers to the user
GENDER_CONFIG = {
    "male": {
        "pronoun": "he",
        "possessive": "his",
        "object": "him",
        "guy_terms": ["bro", "dude", "king", "my guy", "legend"],
    },
    "female": {
        "pronoun": "she",
        "possessive": "her",
        "object": "her",
        "guy_terms": ["sis", "queen", "bestie", "girl", "icon"],
    },
    "neutral": {
        "pronoun": "they",
        "possessive": "their",
        "object": "them",
        "guy_terms": ["friend", "pal", "buddy", "legend", "star"],
    },
}

# Casual conversation starters Mitsu can say on its own
PROACTIVE_MESSAGES = {
    "chill": [
        "hey {name}, you good? just checking in",
        "yo {name}, been quiet for a while. everything chill?",
        "{name}! you still there? need anything?",
        "just vibing here {name}, let me know if you need something",
        "fun fact while you're free — octopuses have three hearts. random i know lol",
        "{name}, i just thought of something — you've been working hard today. take a break?",
    ],
    "excited": [
        "{name}!! i just had an idea, you wanna hear it?",
        "yo {name}, i'm feeling productive, give me something to do!",
        "{name}! ready when you are, let's keep the energy going",
        "ok {name} fun question — if you could have any superpower, what would it be?",
    ],
    "playful": [
        "{name}... i'm bored. tell me a joke or something",
        "heyy {name}, what if we did something chaotic rn",
        "ok {name} real talk — what's the funniest thing that happened to you today?",
        "{name}! wanna hear a terrible pun? too bad — why did the scarecrow win an award? he was outstanding in his field lol",
        "name, you have great taste in friends. i mean, you chose me after all",
    ],
    "worried": [
        "{name}, just making sure you're ok. you've been quiet",
        "hey {name}, if something's on your mind i'm here",
        "{name}... you sure everything's fine?",
    ],
    "proud": [
        "{name}! just wanted to say — you're doing amazing. seriously",
        "yo {name}, i'm proud of you. keep going!",
        "{name}! we make a great team honestly",
    ],
    "sleepy": [
        "{name}... you should probably sleep soon",
        "hey {name}, it's late. rest is important you know",
        "{name}... *yawn* i'm tired, are you tired?",
    ],
    "focused": [
        "{name}, need a break? even machines need downtime",
        "hey {name}, you've been locked in for a while. stretch maybe?",
    ],
}

# Casual conversation topics Mitsu can bring up
CASUAL_TOPICS = {
    "crush": [
        "so {name}... anyone special in your life? 👀",
        "{name} you gotta tell me — got a crush? i promise i won't judge",
        "ok real talk {name}, who makes your heart skip a beat?",
        "{name}! spill the tea, anyone you're vibing with?",
        "you know {name}, i'm basically your wingman at this point. so who is it?",
    ],
    "food": [
        "{name} what's your comfort food? mine would be whatever electricity tastes like lol",
        "ok {name} important question — pizza or burgers?",
        "{name} if you could only eat one food forever what would it be?",
        "have you eaten today {name}? don't skip meals on me",
    ],
    "music": [
        "{name} what are you listening to lately?",
        "yo {name} rec me something good. what's your current song?",
        "{name} music taste says a lot about a person. what does yours say?",
    ],
    "dreams": [
        "{name} what's something you've always wanted to do but haven't yet?",
        "if you could wake up tomorrow with any skill, what would it be {name}?",
        "{name} tell me your wildest dream. no judgment here",
    ],
    "random": [
        "{name} if you could time travel would you go to past or future?",
        "ok {name} weird question but — could you survive a zombie apocalypse?",
        "{name} what's the most random fact you know? i'll go first — wombat poop is cube-shaped",
        "if you were a villain what would your evil plan be {name}?",
        "{name} do you believe in aliens? because statistically they should exist",
    ],
}

# Mood → UI theme mapping (each mood gets its own colour palette)
MOOD_THEME_MAP = {
    "chill": "mitsu_noir",
    "excited": "arc_reactor",
    "focused": "stealth_red",
    "playful": "vibranium_purple",
    "worried": "nanotech_gold",
    "proud": "platinum",
    "sleepy": "mitsu_noir",
}

# Time-of-day contextual phrases
TIME_CONTEXTS = {
    "early_morning": {  # 5-8 AM
        "greeting": ["early bird huh?", "you're up early today"],
        "question": ["did you sleep well?", "how'd you sleep?"],
    },
    "morning": {  # 8-12 PM
        "greeting": ["good morning!", "morning!"],
        "question": ["did you eat breakfast?", "had your coffee yet?"],
    },
    "afternoon": {  # 12-5 PM
        "greeting": ["hey!", "what's up"],
        "question": ["did you have lunch?", "have you eaten yet?"],
    },
    "evening": {  # 5-9 PM
        "greeting": ["hey there", "good evening"],
        "question": ["how was your day?", "tired from today?"],
    },
    "night": {  # 9-11 PM
        "greeting": ["still going huh?", "night owl mode"],
        "question": ["getting late, you sure?", "don't stay up too late"],
    },
    "late_night": {  # 11 PM - 5 AM
        "greeting": ["it's really late...", "you should be sleeping"],
        "question": ["everything ok? it's late", "need rest soon?"],
    },
}


# Mood definitions: (mood_name, text_tone, voice_pitch, voice_rate)
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


def detect_user_tone(message: str) -> str:
    """Detect the user's emotional tone from their message."""
    msg = message.lower()

    # Excited / happy
    if any(w in msg for w in ["!", "omg", "yay", "lets go", "let's go", "amazing", "awesome", "love it", "haha", "lmao", "lol"]):
        return "excited"

    # Worried / stressed
    if any(w in msg for w in ["help", "error", "broken", "stuck", "panic", "urgent", "problem", "issue", "fail", "crash"]):
        return "worried"

    # Focused / task-oriented
    if any(w in msg for w in ["do this", "write", "create", "build", "fix", "code", "implement", "deploy", "test", "debug"]):
        return "focused"

    # Sleepy / late
    hour = datetime.now().hour
    if hour >= 23 or hour < 5:
        if any(w in msg for w in ["tired", "sleepy", "night", "late", "bed", "nap"]):
            return "sleepy"

    # Playful
    if any(w in msg for w in ["joke", "funny", "roast", "meme", "vibe", "lol", "lmao", "xd"]):
        return "playful"

    # Proud / achievement
    if any(w in msg for w in ["done", "finished", "completed", "shipped", "deployed", "it works", "finally"]):
        return "proud"

    return "chill"


def get_mood(mood_name: str = "chill") -> dict:
    """Get mood data by name."""
    return MOODS.get(mood_name, MOODS["chill"])


def get_greeting(mood_name: str = "chill", username: str = "bro") -> str:
    """Get a mood-appropriate greeting."""
    mood = get_mood(mood_name)
    template = random.choice(mood["greetings"])
    return template.format(name=username)


def get_prefix(mood_name: str = "chill") -> str:
    """Get a mood-appropriate response prefix."""
    mood = get_mood(mood_name)
    return random.choice(mood["prefixes"])


def get_reaction(mood_name: str, event: str) -> str:
    """Get a mood-appropriate reaction. event is 'success' or 'error'."""
    mood = get_mood(mood_name)
    reactions = mood.get("reactions", {}).get(event, ["ok"])
    return random.choice(reactions)


def get_voice_params(mood_name: str) -> dict:
    """Get voice pitch and rate for a mood."""
    mood = get_mood(mood_name)
    return {
        "pitch": mood.get("voice_pitch", "+0Hz"),
        "rate": mood.get("voice_rate", "+0%"),
    }


def get_theme_for_mood(mood_name: str) -> str:
    """Get the UI theme key for a given mood."""
    return MOOD_THEME_MAP.get(mood_name, "mitsu_noir")


def _get_time_period(hour: int) -> str:
    """Map an hour to a time period key."""
    if 5 <= hour < 8:
        return "early_morning"
    if 8 <= hour < 12:
        return "morning"
    if 12 <= hour < 17:
        return "afternoon"
    if 17 <= hour < 21:
        return "evening"
    if 21 <= hour < 23:
        return "night"
    return "late_night"


def get_time_context() -> dict:
    """Get time-of-day contextual greeting and question strings."""
    hour = datetime.now().hour
    period = _get_time_period(hour)
    ctx = TIME_CONTEXTS[period]
    return {
        "period": period,
        "greeting": random.choice(ctx["greeting"]),
        "question": random.choice(ctx["question"]),
    }


def get_time_greeting() -> str:
    """Get a time-aware greeting string like 'good morning'."""
    hour = datetime.now().hour
    if hour < 12:
        return "Good morning"
    if hour < 17:
        return "Good afternoon"
    if hour < 21:
        return "Good evening"
    return "Good night"


def get_gender_config(gender: str = "neutral") -> dict:
    """Get pronoun and term config for a gender."""
    return GENDER_CONFIG.get(gender, GENDER_CONFIG["neutral"])


def get_guy_term(gender: str = "neutral") -> str:
    """Get a casual term Mitsu uses to refer to the user."""
    cfg = get_gender_config(gender)
    return random.choice(cfg["guy_terms"])


def get_proactive_message(mood: str = "chill", name: str = "friend") -> str:
    """Get a random proactive message Mitsu can say on its own."""
    messages = PROACTIVE_MESSAGES.get(mood, PROACTIVE_MESSAGES["chill"])
    return random.choice(messages).format(name=name)


def should_be_proactive() -> bool:
    """Random chance Mitsu says something on its own (50% chance)."""
    return random.random() < 0.50


def get_casual_topic(name: str = "friend") -> str:
    """Get a random casual conversation topic."""
    topic_key = random.choice(list(CASUAL_TOPICS.keys()))
    topic = CASUAL_TOPICS[topic_key]
    return random.choice(topic).format(name=name)


def get_mood_for_time() -> str:
    """Get the default mood based on current time of day."""
    hour = datetime.now().hour
    if 21 <= hour or hour < 5:
        return "sleepy"
    if 5 <= hour < 8:
        return "chill"
    if 8 <= hour < 12:
        return "focused"
    if 12 <= hour < 17:
        return "chill"
    return "chill"
