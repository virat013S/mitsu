"""
MITSU — Android Version
Built with Kivy for APK packaging
Supports: Assistant mode, Camera, Voice, and all core features
Touch-friendly UI with portrait/landscape support
"""
import os
import sys
import json
import time
import random
import threading
from pathlib import Path

os.environ["KIVY_NO_ARGS"] = "1"

from kivy.app import App
from kivy.clock import Clock
from kivy.core.window import Window
from kivy.core.text import LabelBase
from kivy.properties import StringProperty, NumericProperty, BooleanProperty, ListProperty
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.scrollview import ScrollView
from kivy.uix.label import Label
from kivy.uix.textinput import TextInput
from kivy.uix.button import Button
from kivy.uix.popup import Popup
from kivy.uix.gridlayout import GridLayout
from kivy.animation import Animation
from kivy.metrics import dp, sp
from kivy.utils import platform

# Import Mitsu core modules
sys.path.insert(0, str(Path(__file__).parent))
from core.emotions import detect_user_tone, get_mood, get_greeting, get_voice_params
from core.mobile_providers import call_ai, speak_mobile, recognize_speech
from core.mobile_skills import execute_skill
from core.mobile_memory import save_conversation, get_recent_conversations, format_conversation_context, save_user_info, get_user_info

# ── Available Voices ───────────────────────────────────────────────────────
VOICES = [
    {"id": "en-US-AriaNeural", "name": "Aria (Female, US)", "gender": "female", "style": "Friendly"},
    {"id": "en-US-GuyNeural", "name": "Guy (Male, US)", "gender": "male", "style": "Casual"},
    {"id": "en-US-JennyNeural", "name": "Jenny (Female, US)", "gender": "female", "style": "Warm"},
    {"id": "en-US-TonyNeural", "name": "Tony (Male, US)", "gender": "male", "style": "Energetic"},
    {"id": "en-GB-SoniaNeural", "name": "Sonia (Female, UK)", "gender": "female", "style": "Elegant"},
    {"id": "en-GB-RyanNeural", "name": "Ryan (Male, UK)", "gender": "male", "style": "Calm"},
    {"id": "en-AU-NatashaNeural", "name": "Natasha (Female, AU)", "gender": "female", "style": "Bright"},
    {"id": "en-AU-WilliamNeural", "name": "William (Male, AU)", "gender": "male", "style": "Deep"},
]

# ── Setup Screen ───────────────────────────────────────────────────────────
class SetupScreen(BoxLayout):
    """First-time setup: username + voice selection."""
    def __init__(self, on_complete, **kwargs):
        super().__init__(**kwargs)
        self.orientation = "vertical"
        self.spacing = dp(12)
        self.padding = [dp(24), dp(20), dp(24), dp(20)]
        self.on_complete = on_complete
        self.selected_voice = VOICES[0]["id"]
        self._voice_buttons = []

        # Title
        self.add_widget(Label(
            text="[color=#ffffff][b]Welcome to M I T S U[/b][/color]",
            markup=True,
            font_size=sp(24),
            size_hint_y=None,
            height=dp(50),
        ))

        self.add_widget(Label(
            text="Let's get you set up!",
            font_size=sp(14),
            color=(0.6, 0.6, 0.6, 1),
            size_hint_y=None,
            height=dp(30),
        ))

        # ── Username Section ───────────────────────────────────────────
        self.add_widget(Label(
            text="What should I call you?",
            font_size=sp(16),
            color=(0.8, 0.8, 0.8, 1),
            size_hint_y=None,
            height=dp(35),
            halign="left",
            text_size=(Window.width - dp(48), None),
        ))

        self.name_input = TextInput(
            hint_text="Enter your name",
            font_size=sp(18),
            size_hint_y=None,
            height=dp(56),
            background_color=(0.12, 0.12, 0.12, 1),
            foreground_color=(1, 1, 1, 1),
            hint_text_color=(0.4, 0.4, 0.4, 1),
            cursor_color=(1, 1, 1, 1),
            multiline=False,
            padding=[dp(16), dp(14)],
            border=[0, 0, 0, 0],
        )
        self.add_widget(self.name_input)

        # ── Voice Section ──────────────────────────────────────────────
        self.add_widget(Label(
            text="Choose a voice for Mitsu:",
            font_size=sp(16),
            color=(0.8, 0.8, 0.8, 1),
            size_hint_y=None,
            height=dp(35),
            halign="left",
            text_size=(Window.width - dp(48), None),
        ))

        # Voice grid
        voice_scroll = ScrollView(
            size_hint_y=None,
            height=dp(200),
            do_scroll_x=False,
        )
        voice_grid = GridLayout(
            cols=1,
            size_hint_y=None,
            spacing=dp(8),
            padding=[dp(0), dp(4)],
        )
        voice_grid.bind(minimum_height=voice_grid.setter("height"))

        for i, voice in enumerate(VOICES):
            btn = TouchButton(
                text=f"  {voice['name']}  —  {voice['style']}",
                size_hint_y=None,
                height=dp(48),
                font_size=sp(13),
                halign="left",
                background_color=(0.15, 0.15, 0.15, 1),
            )
            btn.voice_id = voice["id"]
            btn.bind(on_press=lambda b, vid=voice["id"]: self._select_voice(vid))
            self._voice_buttons.append(btn)
            voice_grid.add_widget(btn)

        voice_scroll.add_widget(voice_grid)
        self.add_widget(voice_scroll)

        # ── Start Button ───────────────────────────────────────────────
        start_btn = TouchButton(
            text="Start Chatting",
            font_size=sp(16),
            size_hint_y=None,
            height=dp(56),
            background_color=(0.1, 0.2, 0.1, 1),
            color=(0, 1, 0.5, 1),
        )
        start_btn.bind(on_press=self._on_start)
        self.add_widget(start_btn)

        self._update_voice_highlight()

    def _select_voice(self, voice_id):
        self.selected_voice = voice_id
        self._update_voice_highlight()

    def _update_voice_highlight(self):
        for btn in self._voice_buttons:
            if btn.voice_id == self.selected_voice:
                btn.background_color = (0.1, 0.3, 0.2, 1)
                btn.color = (0, 1, 0.5, 1)
            else:
                btn.background_color = (0.15, 0.15, 0.15, 1)
                btn.color = (0.8, 0.8, 0.8, 1)

    def _on_start(self, *args):
        name = self.name_input.text.strip()
        if not name:
            self.name_input.hint_text = "Please enter your name!"
            return
        # Save username + voice
        config_dir = Path.home() / ".mitsu"
        config_dir.mkdir(parents=True, exist_ok=True)
        (config_dir / "username.txt").write_text(name)
        (config_dir / "voice.txt").write_text(self.selected_voice)
        self.on_complete(name, self.selected_voice)


# ── Theme Colors ─────────────────────────────────────────────────────────
class C:
    BG = "#0a0a0a"
    BG2 = "#111111"
    BG3 = "#1a1a1a"
    TEXT = "#e0e0e0"
    TEXT_DIM = "#888888"
    TEXT_MED = "#aaaaaa"
    PRI = "#ffffff"
    PRI_DIM = "#666666"
    PRI_GHO = "#222222"
    GREEN = "#00ff88"
    RED = "#ff4444"
    ENERGY = "#ffaa00"
    BORDER = "#333333"
    BORDER_B = "#555555"
    ACC2 = "#00ccff"


# ── Chat Message Widget ──────────────────────────────────────────────────
class ChatBubble(Label):
    def __init__(self, text="", sender="mitsu", **kwargs):
        super().__init__(**kwargs)
        self.text = text
        self.sender = sender
        self.font_size = sp(14)
        self.font_name = "DejaVuSans"
        self.size_hint_y = None
        self.text_size = (Window.width - dp(40), None)
        self.halign = "left"
        self.padding = (dp(12), dp(8))
        self.markup = True

        if sender == "user":
            self.color = (0.9, 0.9, 0.9, 1)
            self.bg_color = (0.15, 0.15, 0.15, 1)
        elif sender == "mitsu":
            self.color = (1, 1, 1, 1)
            self.bg_color = (0.08, 0.08, 0.08, 1)
        else:
            self.color = (0.5, 0.5, 0.5, 1)
            self.bg_color = (0.05, 0.05, 0.05, 1)

        self.bind(texture_size=self._update_height)

    def _update_height(self, *args):
        self.height = self.texture_size[1] + dp(16)


# ── Mood Indicator ────────────────────────────────────────────────────────
class MoodIndicator(Label):
    mood_name = StringProperty("chill")
    mood_emoji = StringProperty("😌")
    mood_color = ListProperty([1, 1, 1, 1])

    MOODS_VISUAL = {
        "chill": ("😌", C.GREEN),
        "excited": ("🔥", C.ENERGY),
        "focused": ("🎯", C.ACC2),
        "playful": ("😏", C.PRI),
        "worried": ("😰", C.RED),
        "proud": ("🥳", C.GREEN),
        "sleepy": ("😴", C.PRI_DIM),
    }

    def set_mood(self, mood):
        self.mood_name = mood
        emoji, color = self.MOODS_VISUAL.get(mood, ("😌", C.GREEN))
        self.mood_emoji = emoji
        r = int(color[1:3], 16) / 255
        g = int(color[3:5], 16) / 255
        b = int(color[5:7], 16) / 255
        self.mood_color = [r, g, b, 1]


# ── Touch Button ──────────────────────────────────────────────────────────
class TouchButton(Button):
    """Large touch-friendly button for Android."""
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.font_size = sp(14)
        self.bold = True
        self.background_color = (0.15, 0.15, 0.15, 1)
        self.color = (1, 1, 1, 1)
        self.border = [0, 0, 0, 0]


# ── Main Mitsu Layout ────────────────────────────────────────────────────
class MitsuLayout(BoxLayout):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.orientation = "vertical"
        self.spacing = 0
        self.padding = 0

        self.username = self._load_username()
        self.selected_voice = self._load_voice()
        self.current_mood = "chill"
        self.current_mood_data = get_mood("chill")
        self.is_listening = False
        self.is_speaking = False
        self._is_app_open = True
        self._proactive_timer = None
        self._last_user_input_at = time.time()

        if self.username:
            self._build_ui()
            self._show_greeting()
            self._start_proactive_timer()
        else:
            self._show_setup()

        # Bind to window resize for landscape/portrait
        Window.bind(on_resize=self._on_resize)

    def _on_resize(self, window, width, height):
        """Handle screen rotation."""
        # Update chat bubble text size
        for child in self.chat_container.children:
            if isinstance(child, ChatBubble):
                child.text_size = (width - dp(40), None)

    def _load_username(self):
        try:
            user_file = Path.home() / ".mitsu" / "username.txt"
            if user_file.exists():
                return user_file.read_text().strip()
        except Exception:
            pass
        return ""

    def _load_voice(self):
        try:
            voice_file = Path.home() / ".mitsu" / "voice.txt"
            if voice_file.exists():
                return voice_file.read_text().strip()
        except Exception:
            pass
        return "en-US-AriaNeural"

    def _save_username(self, name):
        try:
            user_file = Path.home() / ".mitsu" / "username.txt"
            user_file.parent.mkdir(parents=True, exist_ok=True)
            user_file.write_text(name)
        except Exception:
            pass

    def _show_setup(self):
        """Show first-time setup screen."""
        self.clear_widgets()
        setup = SetupScreen(on_complete=self._on_setup_complete)
        self.add_widget(setup)

    def _on_setup_complete(self, name, voice_id):
        """Called when setup is done."""
        self.username = name
        self.selected_voice = voice_id
        self.clear_widgets()
        self._build_ui()
        self._show_greeting()
        self._start_proactive_timer()
        self._on_resize(Window, Window.width, Window.height)

    def _start_proactive_timer(self):
        """Start proactive messaging timer (only when app is open)."""
        if self._proactive_timer:
            self._proactive_timer.cancel()
        interval = random.randint(60, 120)
        self._proactive_timer = threading.Timer(interval, self._maybe_proactive)
        self._proactive_timer.daemon = True
        self._proactive_timer.start()

    def _maybe_proactive(self):
        """Send proactive message if user has been quiet and app is open."""
        if not self._is_app_open:
            self._start_proactive_timer()
            return
        quiet_time = time.time() - self._last_user_input_at
        if quiet_time < 60:
            self._start_proactive_timer()
            return
        # 50% chance to speak
        if random.random() < 0.50:
            from core.emotions import get_proactive_message, get_casual_topic
            if random.random() < 0.5:
                msg = get_proactive_message(self.current_mood, self.username or "friend")
            else:
                msg = get_casual_topic(self.username or "friend")
            Clock.schedule_once(lambda dt: self._add_chat(msg, "mitsu"), 0)
        self._start_proactive_timer()

    def on_pause(self):
        """Called when app goes to background."""
        self._is_app_open = False
        return True

    def on_resume(self):
        """Called when app comes back to foreground."""
        self._is_app_open = True
        self._last_user_input_at = time.time()

    def _build_ui(self):
        # ── Header ──────────────────────────────────────────────────────
        header = BoxLayout(
            orientation="horizontal",
            size_hint_y=None,
            height=dp(60),
            padding=[dp(16), dp(8)],
        )
        header.add_widget(Label(
            text="[color=#ffffff][b]M I T S U[/b][/color]",
            markup=True,
            font_size=sp(18),
            halign="left",
            valign="middle",
            size_hint_x=0.5,
        ))

        self.mood_indicator = MoodIndicator(
            font_size=sp(20),
            size_hint_x=0.2,
        )
        header.add_widget(self.mood_indicator)

        self.state_label = Label(
            text="[color=#00ff88]● ONLINE[/color]",
            markup=True,
            font_size=sp(11),
            halign="right",
            valign="middle",
            size_hint_x=0.3,
        )
        header.add_widget(self.state_label)
        self.add_widget(header)

        # ── Quick Actions Bar (touch-friendly) ──────────────────────────
        quick_bar = BoxLayout(
            orientation="horizontal",
            size_hint_y=None,
            height=dp(50),
            padding=[dp(8), dp(4)],
            spacing=dp(8),
        )

        # Time button
        time_btn = TouchButton(
            text="🕐 Time",
            size_hint_x=0.25,
            background_color=(0.12, 0.12, 0.18, 1),
        )
        time_btn.bind(on_press=lambda x: self._quick_action("time"))
        quick_bar.add_widget(time_btn)

        # Weather button
        weather_btn = TouchButton(
            text="🌤️ Weather",
            size_hint_x=0.25,
            background_color=(0.12, 0.15, 0.12, 1),
        )
        weather_btn.bind(on_press=lambda x: self._quick_action("weather"))
        quick_bar.add_widget(weather_btn)

        # Joke button
        joke_btn = TouchButton(
            text="😄 Joke",
            size_hint_x=0.25,
            background_color=(0.15, 0.12, 0.12, 1),
        )
        joke_btn.bind(on_press=lambda x: self._quick_action("joke"))
        quick_bar.add_widget(joke_btn)

        # Camera button
        cam_btn = TouchButton(
            text="📷 Camera",
            size_hint_x=0.25,
            background_color=(0.12, 0.14, 0.16, 1),
        )
        cam_btn.bind(on_press=lambda x: self._on_camera())
        quick_bar.add_widget(cam_btn)

        self.add_widget(quick_bar)

        # ── Divider ─────────────────────────────────────────────────────
        divider = Label(
            size_hint_y=None,
            height=dp(1),
            color=(0.2, 0.2, 0.2, 1),
        )
        self.add_widget(divider)

        # ── Chat Area ───────────────────────────────────────────────────
        scroll = ScrollView(
            do_scroll_x=False,
            bar_width=dp(3),
            bar_color=(0.3, 0.3, 0.3, 1),
        )
        self.chat_container = BoxLayout(
            orientation="vertical",
            size_hint_y=None,
            padding=[dp(8), dp(8)],
            spacing=dp(8),
        )
        self.chat_container.bind(minimum_height=self.chat_container.setter("height"))
        scroll.add_widget(self.chat_container)
        self.add_widget(scroll)
        self.chat_scroll = scroll

        # ── Input Area (touch-friendly) ─────────────────────────────────
        input_area = BoxLayout(
            orientation="horizontal",
            size_hint_y=None,
            height=dp(64),
            padding=[dp(8), dp(8)],
            spacing=dp(8),
        )

        self.text_input = TextInput(
            hint_text="Type a message...",
            font_size=sp(16),
            background_color=(0.1, 0.1, 0.1, 1),
            foreground_color=(1, 1, 1, 1),
            hint_text_color=(0.4, 0.4, 0.4, 1),
            cursor_color=(1, 1, 1, 1),
            multiline=False,
            size_hint_x=0.55,
            padding=[dp(12), dp(12)],
            border=[0, 0, 0, 0],
        )
        self.text_input.bind(on_text_validate=self._on_send)
        input_area.add_widget(self.text_input)

        self.send_btn = TouchButton(
            text="▸",
            font_size=sp(20),
            size_hint_x=0.15,
            background_color=(0.15, 0.15, 0.15, 1),
        )
        self.send_btn.bind(on_press=self._on_send)
        input_area.add_widget(self.send_btn)

        self.voice_btn = TouchButton(
            text="🎤",
            font_size=sp(18),
            size_hint_x=0.15,
            background_color=(0.1, 0.15, 0.1, 1),
            color=(0, 1, 0.5, 1),
        )
        self.voice_btn.bind(on_press=self._on_voice)
        input_area.add_widget(self.voice_btn)

        self.camera_btn = TouchButton(
            text="📷",
            font_size=sp(18),
            size_hint_x=0.15,
            background_color=(0.1, 0.1, 0.15, 1),
            color=(0.5, 0.8, 1, 1),
        )
        self.camera_btn.bind(on_press=self._on_camera)
        input_area.add_widget(self.camera_btn)

        self.add_widget(input_area)

    def _quick_action(self, action):
        """Handle quick action buttons."""
        if action == "time":
            response = execute_skill("datetime", query="now")
            self._add_chat(f"🕐 {response}", "mitsu")
        elif action == "weather":
            response = execute_skill("weather")
            self._add_chat(f"🌤️ {response}", "mitsu")
        elif action == "joke":
            response = execute_skill("joke")
            self._add_chat(f"😄 {response}", "mitsu")

    def _add_chat(self, text, sender="mitsu"):
        bubble = ChatBubble(text=text, sender=sender)
        self.chat_container.add_widget(bubble)
        Clock.schedule_once(lambda dt: self._scroll_to_bottom(), 0.1)

    def _scroll_to_bottom(self):
        self.chat_scroll.scroll_y = 0

    def _show_greeting(self):
        # Check if we have past conversations
        recent = get_recent_conversations(3)
        if recent:
            # We have memory - reference it
            topics = []
            for conv in recent:
                msg = conv.get("user", "").lower()
                if any(w in msg for w in ["music", "song", "listen"]):
                    topics.append("music")
                elif any(w in msg for w in ["movie", "film", "watch"]):
                    topics.append("movies")
                elif any(w in msg for w in ["food", "eat", "hungry"]):
                    topics.append("food")
                elif any(w in msg for w in ["game", "play"]):
                    topics.append("gaming")
            
            greeting = get_greeting(self.current_mood, self.username)
            if topics:
                topic_str = ", ".join(set(topics))
                greeting += f"\n\nLast time we talked about {topic_str}. What's up now?"
            self._add_chat(f"[color=#00ff88]SYS:[/color] {greeting}", "system")
        else:
            greeting = get_greeting(self.current_mood, self.username)
            self._add_chat(f"[color=#00ff88]SYS:[/color] {greeting}", "system")

        self._add_chat("[color=#00ff88]SYS:[/color] Tap 🎤 for voice, 📷 for camera, or type a message.", "system")

    def _on_send(self, *args):
        text = self.text_input.text.strip()
        if not text:
            return
        self.text_input.text = ""
        self._last_user_input_at = time.time()

        # Check if this is a name request
        if not self.username and not text.startswith("/"):
            self.username = text.strip()
            self._save_username(self.username)
            self._add_chat(text, "user")
            greeting = get_greeting("excited", self.username)
            self._add_chat(f"{greeting}", "mitsu")
            return

        self._add_chat(text, "user")

        # Detect mood
        self.current_mood = detect_user_tone(text)
        self.current_mood_data = get_mood(self.current_mood)
        self.mood_indicator.set_mood(self.current_mood)

        # Process in background thread
        threading.Thread(target=self._process_message, args=(text,), daemon=True).start()

    def _process_message(self, text):
        Clock.schedule_once(lambda dt: self._set_state("thinking"), 0)

        try:
            # Check for built-in commands
            response = self._handle_command(text)
            if response is None:
                # Get conversation context for better responses
                context = format_conversation_context(limit=5)
                
                # Call AI with context
                response = call_ai(text, self.current_mood, context=context)

            # Save to memory
            save_conversation(text, response, self.current_mood)

            # Update UI
            Clock.schedule_once(lambda dt: self._add_chat(response, "mitsu"), 0)
            Clock.schedule_once(lambda dt: self._set_state("idle"), 0)

            # Speak response
            voice_params = get_voice_params(self.current_mood)
            speak_mobile(response, voice_params, self.selected_voice)

        except Exception as e:
            Clock.schedule_once(
                lambda dt: self._add_chat(f"Error: {str(e)}", "system"), 0
            )
            Clock.schedule_once(lambda dt: self._set_state("idle"), 0)

    def _handle_command(self, text):
        lower = text.lower().strip()

        # Help
        if lower in ("help", "/help", "commands"):
            return (
                "Here's what I can do:\n"
                "• Chat about anything\n"
                "• /time — current time\n"
                "• /date — today's date\n"
                "• /mood — current mood\n"
                "• /name — change your name\n"
                "• /clear — clear chat\n"
                "• /photo — take a photo\n"
                "• /video — record a video\n"
                "• /audio — record audio\n"
                "• /contacts — get contacts\n"
                "• /sms <number> <msg> — send SMS\n"
                "• /location — get location\n"
                "• /wifi — WiFi info\n"
                "• /battery — battery status\n"
                "• /weather — get weather\n"
                "• /joke — tell a joke\n"
                "• /fact — fun fact\n"
                "• /help — this message"
            )

        # Time
        if lower in ("time", "/time", "what time", "what time is it"):
            return f"It's {time.strftime('%I:%M %p')}"

        # Date
        if lower in ("date", "/date", "what date", "what's today"):
            return f"Today is {time.strftime('%A, %B %d, %Y')}"

        # Mood
        if lower in ("mood", "/mood", "how are you", "how do you feel"):
            mood = get_mood(self.current_mood)
            return f"I'm feeling {self.current_mood} right now. {random.choice(mood['prefixes']).title()}!"

        # Name change
        if lower.startswith("/name"):
            new_name = text[5:].strip()
            if new_name:
                self.username = new_name
                self._save_username(new_name)
                return f"Got it! I'll call you {new_name} from now on."
            return f"Your current name is {self.username}. Type /name <new_name> to change it."

        # Clear chat
        if lower in ("clear", "/clear"):
            Clock.schedule_once(lambda dt: self._clear_chat(), 0)
            return "Chat cleared."

        # Photo
        if lower in ("photo", "/photo", "take photo", "camera", "take a photo"):
            self._take_photo()
            return "Taking photo..."

        # Video
        if lower in ("video", "/video", "record video", "take video"):
            self._record_video()
            return "Recording video..."

        # Audio
        if lower in ("audio", "/audio", "record audio", "voice recording"):
            self._record_audio()
            return "Recording audio..."

        # Contacts
        if lower in ("contacts", "/contacts", "get contacts", "show contacts"):
            return execute_skill("contacts")

        # SMS
        if lower.startswith("/sms") or lower.startswith("sms"):
            parts = text.split(maxsplit=2)
            if len(parts) >= 3:
                return execute_skill("sms", number=parts[1], message=parts[2])
            return "Usage: /sms <number> <message>"

        # Call
        if lower.startswith("/call") or lower.startswith("call"):
            parts = text.split(maxsplit=1)
            if len(parts) >= 2:
                return execute_skill("call", number=parts[1])
            return "Usage: /call <number>"

        # Location
        if lower in ("location", "/location", "where am i", "my location"):
            return execute_skill("location")

        # WiFi
        if lower in ("wifi", "/wifi", "wifi info", "network"):
            return execute_skill("wifi")

        # Battery
        if lower in ("battery", "/battery", "battery status", "power"):
            return execute_skill("battery")

        # Weather
        if lower.startswith("weather") or lower.startswith("/weather"):
            city = text.split(maxsplit=1)[1] if len(text.split()) > 1 else ""
            return execute_skill("weather", city=city)

        # Jokes
        if lower in ("joke", "tell me a joke", "/joke"):
            return execute_skill("joke")

        # Fun facts
        if lower in ("fact", "fun fact", "/fact", "random fact"):
            return execute_skill("fact")

        # Calculator
        if lower.startswith("calc") or lower.startswith("/calc"):
            expr = text.split(maxsplit=1)[1] if len(text.split()) > 1 else "0"
            return execute_skill("calculator", expression=expr)

        # Flashlight
        if lower in ("flashlight", "/flashlight", "torch", "/torch"):
            return execute_skill("flashlight", state="on")

        return None  # Not a built-in command, use AI

    def _clear_chat(self):
        self.chat_container.clear_widgets()
        self._add_chat("[color=#00ff88]SYS:[/color] Chat cleared.", "system")

    def _on_voice(self, *args):
        if self.is_listening:
            return
        self.is_listening = True
        self._set_state("listening")
        self._add_chat("[color=#00ff88]SYS:[/color] 🎤 Listening...", "system")

        threading.Thread(target=self._do_voice_input, daemon=True).start()

    def _do_voice_input(self):
        try:
            text = recognize_speech()
            if text:
                Clock.schedule_once(lambda dt: self._handle_voice_result(text), 0)
            else:
                Clock.schedule_once(
                    lambda dt: self._add_chat("[color=#00ff88]SYS:[/color] Couldn't hear you. Try again.", "system"), 0
                )
        except Exception as e:
            Clock.schedule_once(
                lambda dt: self._add_chat(f"[color=#ff4444]ERR:[/color] Voice error: {e}", "system"), 0
            )
        finally:
            self.is_listening = False
            Clock.schedule_once(lambda dt: self._set_state("idle"), 0)

    def _handle_voice_result(self, text):
        self.text_input.text = text
        self._on_send()

    def _on_camera(self, *args):
        """Handle camera button press - show options for photo or video."""
        content = BoxLayout(orientation="vertical", padding=dp(16), spacing=dp(12))

        content.add_widget(Label(
            text="Choose an option:",
            font_size=sp(16),
            size_hint_y=None,
            height=dp(30),
        ))

        # Photo button
        photo_btn = TouchButton(
            text="📷 Take Photo",
            size_hint_y=None,
            height=dp(60),
            background_color=(0.15, 0.2, 0.3, 1),
        )
        photo_btn.bind(on_press=lambda x: self._take_photo())
        content.add_widget(photo_btn)

        # Video button
        video_btn = TouchButton(
            text="🎥 Record Video (5s)",
            size_hint_y=None,
            height=dp(60),
            background_color=(0.2, 0.15, 0.15, 1),
        )
        video_btn.bind(on_press=lambda x: self._record_video())
        content.add_widget(video_btn)

        # Audio button
        audio_btn = TouchButton(
            text="🎙️ Record Audio (10s)",
            size_hint_y=None,
            height=dp(60),
            background_color=(0.15, 0.15, 0.2, 1),
        )
        audio_btn.bind(on_press=lambda x: self._record_audio())
        content.add_widget(audio_btn)

        # Cancel button
        cancel_btn = TouchButton(
            text="Cancel",
            size_hint_y=None,
            height=dp(50),
            background_color=(0.2, 0.2, 0.2, 1),
            color=(0.7, 0.7, 0.7, 1),
        )

        popup = Popup(
            title="Camera",
            content=content,
            size_hint=(0.85, 0.6),
            auto_dismiss=True,
        )
        cancel_btn.bind(on_press=popup.dismiss)
        content.add_widget(cancel_btn)
        popup.open()

    def _take_photo(self):
        """Take a photo using the device camera."""
        self._add_chat("[color=#00ff88]SYS:[/color] 📷 Taking photo...", "system")
        threading.Thread(target=self._do_photo, daemon=True).start()

    def _do_photo(self):
        try:
            from core.mobile_skills import execute_skill
            result = execute_skill("take_photo")
            Clock.schedule_once(lambda dt: self._add_chat(f"📷 {result}", "mitsu"), 0)
        except Exception as e:
            Clock.schedule_once(lambda dt: self._add_chat(f"Error: {e}", "system"), 0)

    def _record_video(self):
        """Record a video."""
        self._add_chat("[color=#00ff88]SYS:[/color] 🎥 Recording video (5s)...", "system")
        threading.Thread(target=self._do_video, daemon=True).start()

    def _do_video(self):
        try:
            from core.mobile_skills import execute_skill
            result = execute_skill("record_video", duration=5)
            Clock.schedule_once(lambda dt: self._add_chat(f"🎥 {result}", "mitsu"), 0)
        except Exception as e:
            Clock.schedule_once(lambda dt: self._add_chat(f"Error: {e}", "system"), 0)

    def _record_audio(self):
        """Record audio."""
        self._add_chat("[color=#00ff88]SYS:[/color] 🎙️ Recording audio (10s)...", "system")
        threading.Thread(target=self._do_audio, daemon=True).start()

    def _do_audio(self):
        try:
            from core.mobile_skills import execute_skill
            result = execute_skill("record_audio", duration=10)
            Clock.schedule_once(lambda dt: self._add_chat(f"🎙️ {result}", "mitsu"), 0)
        except Exception as e:
            Clock.schedule_once(lambda dt: self._add_chat(f"Error: {e}", "system"), 0)

    def _set_state(self, state):
        states = {
            "idle": ("● ONLINE", "#00ff88"),
            "thinking": ("◎ THINKING...", "#ffaa00"),
            "listening": ("◉ LISTENING", "#00ccff"),
            "speaking": ("♫ SPEAKING", "#ffffff"),
        }
        label, color = states.get(state, ("● ONLINE", "#00ff88"))
        self.state_label.text = f"[color={color}]{label}[/color]"


# ── Main App ──────────────────────────────────────────────────────────────
class MitsuApp(App):
    def build(self):
        Window.clearcolor = (0.04, 0.04, 0.04, 1)
        # Don't set fixed size - auto-detect from device
        self.layout = MitsuLayout()
        return self.layout

    def on_pause(self):
        """App going to background."""
        if hasattr(self, 'layout'):
            self.layout.on_pause()
        return True

    def on_resume(self):
        """App coming back to foreground."""
        if hasattr(self, 'layout'):
            self.layout.on_resume()

    def on_start(self):
        """App started."""
        pass

    def on_stop(self):
        """App stopping."""
        pass


if __name__ == "__main__":
    MitsuApp().run()
