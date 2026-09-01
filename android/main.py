"""
MITSU — Android Version
Built with Kivy for APK packaging
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
from kivy.core.audio import SoundLoader
from kivy.core.text import LabelBase
from kivy.properties import StringProperty, NumericProperty, BooleanProperty, ListProperty
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.scrollview import ScrollView
from kivy.uix.label import Label
from kivy.uix.textinput import TextInput
from kivy.uix.button import Button
from kivy.uix.popup import Popup
from kivy.uix.image import Image
from kivy.animation import Animation
from kivy.metrics import dp, sp
from kivy.utils import platform

# Import Mitsu core modules
sys.path.insert(0, str(Path(__file__).parent))
from core.emotions import detect_user_tone, get_mood, get_greeting, get_voice_params
from core.mobile_providers import call_ai, speak_mobile, recognize_speech
from core.mobile_skills import execute_skill


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
        self valign = "top"
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
        "proud": ("🌟", C.ENERGY),
        "sleepy": ("😴", C.PRI_DIM),
    }

    def set_mood(self, mood_name):
        self.mood_name = mood_name
        emoji, color_hex = self.MOODS_VISUAL.get(mood_name, ("😌", C.GREEN))
        self.mood_emoji = emoji
        # Convert hex to rgba
        r = int(color_hex[1:3], 16) / 255
        g = int(color_hex[3:5], 16) / 255
        b = int(color_hex[5:7], 16) / 255
        self.mood_color = [r, g, b, 1]


# ── Main Mitsu Layout ────────────────────────────────────────────────────
class MitsuLayout(BoxLayout):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.orientation = "vertical"
        self.spacing = 0
        self.padding = 0

        self.username = self._load_username()
        self.current_mood = "chill"
        self.current_mood_data = get_mood("chill")
        self.is_listening = False
        self.is_speaking = False

        self._build_ui()
        self._show_greeting()

    def _load_username(self):
        try:
            user_file = Path.home() / ".mitsu" / "username.txt"
            if user_file.exists():
                return user_file.read_text().strip()
        except Exception:
            pass
        return ""

    def _save_username(self, name):
        try:
            user_file = Path.home() / ".mitsu" / "username.txt"
            user_file.parent.mkdir(parents=True, exist_ok=True)
            user_file.write_text(name)
        except Exception:
            pass

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
            size_hint_x=0.6,
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
            size_hint_x=0.2,
        )
        header.add_widget(self.state_label)
        self.add_widget(header)

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

        # ── Input Area ──────────────────────────────────────────────────
        input_area = BoxLayout(
            orientation="horizontal",
            size_hint_y=None,
            height=dp(56),
            padding=[dp(8), dp(8)],
            spacing=dp(8),
        )

        self.text_input = TextInput(
            hint_text="Type a message...",
            font_size=sp(14),
            background_color=(0.1, 0.1, 0.1, 1),
            foreground_color=(1, 1, 1, 1),
            hint_text_color=(0.4, 0.4, 0.4, 1),
            cursor_color=(1, 1, 1, 1),
            multiline=False,
            size_hint_x=0.7,
            padding=[dp(12), dp(10)],
            border=[0, 0, 0, 0],
        )
        self.text_input.bind(on_text_validate=self._on_send)
        input_area.add_widget(self.text_input)

        self.send_btn = Button(
            text="▸",
            font_size=sp(18),
            size_hint_x=0.15,
            background_color=(0.15, 0.15, 0.15, 1),
            color=(1, 1, 1, 1),
            border=[0, 0, 0, 0],
        )
        self.send_btn.bind(on_press=self._on_send)
        input_area.add_widget(self.send_btn)

        self.voice_btn = Button(
            text="🎤",
            font_size=sp(16),
            size_hint_x=0.15,
            background_color=(0.1, 0.15, 0.1, 1),
            color=(0, 1, 0.5, 1),
            border=[0, 0, 0, 0],
        )
        self.voice_btn.bind(on_press=self._on_voice)
        input_area.add_widget(self.voice_btn)

        self.add_widget(input_area)

    def _add_chat(self, text, sender="mitsu"):
        bubble = ChatBubble(text=text, sender=sender)
        self.chat_container.add_widget(bubble)
        Clock.schedule_once(lambda dt: self._scroll_to_bottom(), 0.1)

    def _scroll_to_bottom(self):
        self.chat_scroll.scroll_y = 0

    def _show_greeting(self):
        if self.username:
            greeting = get_greeting(self.current_mood, self.username)
            self._add_chat(f"[color=#00ff88]SYS:[/color] {greeting}", "system")
        else:
            self._add_chat("[color=#00ff88]SYS:[/color] Hey! I'm Mitsu. What's your name?", "system")

        self._add_chat("[color=#00ff88]SYS:[/color] Tap 🎤 for voice or type a message.", "system")

    def _on_send(self, *args):
        text = self.text_input.text.strip()
        if not text:
            return
        self.text_input.text = ""

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
                # Call AI
                response = call_ai(text, self.current_mood)

            # Update UI
            Clock.schedule_once(lambda dt: self._add_chat(response, "mitsu"), 0)
            Clock.schedule_once(lambda dt: self._set_state("idle"), 0)

            # Speak response
            voice_params = get_voice_params(self.current_mood)
            speak_mobile(response, voice_params)

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

        # Jokes
        if lower in ("joke", "tell me a joke", "/joke"):
            jokes = [
                "Why do programmers prefer dark mode? Because light attracts bugs!",
                "Why was the JavaScript developer sad? Because he didn't Node how to Express himself!",
                "What's a programmer's favorite hangout place? Foo Bar!",
                "Why do Java developers wear glasses? Because they can't C#!",
                "How many programmers does it take to change a light bulb? None — that's a hardware problem!",
            ]
            return random.choice(jokes)

        # Fun facts
        if lower in ("fact", "fun fact", "/fact", "random fact"):
            facts = [
                "Honey never spoils. Archaeologists found 3000-year-old honey in Egyptian tombs that was still edible.",
                "Octopuses have three hearts and blue blood.",
                "A day on Venus is longer than its year.",
                "Bananas are berries, but strawberries aren't.",
                "The first computer bug was an actual bug — a moth found in a Harvard computer in 1947.",
            ]
            return random.choice(facts)

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
        Window.size = (400, 700)
        return MitsuLayout()

    def on_pause(self):
        return True

    def on_resume(self):
        pass


if __name__ == "__main__":
    MitsuApp().run()
