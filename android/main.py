"""
MITSU Android — Futuristic holographic UI matching desktop version.
Portrait only. Same chat bubble style as PC.
"""
import os
import sys
import json
import math
import time
import random
import threading
from pathlib import Path
from datetime import datetime

os.environ['KIVY_LOG_LEVEL'] = 'warning'

from kivy.app import App
from kivy.clock import Clock
from kivy.core.window import Window
from kivy.graphics import Color, Line, Ellipse, Rectangle
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.scrollview import ScrollView
from kivy.uix.gridlayout import GridLayout
from kivy.uix.label import Label
from kivy.uix.textinput import TextInput
from kivy.uix.button import Button
from kivy.uix.widget import Widget
from kivy.metrics import dp, sp

sys.path.insert(0, str(Path(__file__).parent))
try:
    from core.emotions import detect_user_tone, get_mood, get_greeting, get_voice_params, PROACTIVE_MESSAGES
    from core.mobile_providers import call_ai, speak_mobile, recognize_speech
    from core.mobile_skills import execute_skill
    from core.mobile_memory import save_conversation, get_recent_conversations, format_conversation_context
except Exception as e:
    print(f"[Mitsu] Import error: {e}")
    PROACTIVE_MESSAGES = {"chill": [], "excited": [], "focused": [], "playful": []}
    def detect_user_tone(t): return "chill"
    def get_mood(m): return {"name": m, "prefixes": ["alright"], "reactions": {"success": ["nice"], "error": ["hmm"]}}
    def get_greeting(m, n): return f"hey {n}!"
    def get_voice_params(m): return {}
    def call_ai(t, m, context=None): return "I'm having trouble loading. Try again?"
    def speak_mobile(t, v=None, vid=None): pass
    def recognize_speech(): return None
    def execute_skill(s, **k): return "Skill unavailable"
    def save_conversation(u, r, m): pass
    def get_recent_conversations(n): return []
    def format_conversation_context(n): return ""

from kivy.properties import NumericProperty, BooleanProperty, ListProperty


# ═══════════════════════════════════════════════════════════════════════
# COLORS — Match desktop C class exactly
# ═══════════════════════════════════════════════════════════════════════
BG      = [0.043, 0.043, 0.043, 1]   # #0b0b0b
PANEL   = [0.067, 0.067, 0.067, 1]   # #111111
DARK    = [0.055, 0.055, 0.055, 1]   # #0e0e0e
DARK2   = [0.078, 0.078, 0.078, 1]   # #141414
BORDER  = [0.12, 0.12, 0.12, 1]      # #1e1e1e
BORDER_B=[0.22, 0.22, 0.22, 1]       # #383838
TEXT    = [0.91, 0.91, 0.91, 1]       # #e8e8e8
TEXT_DIM= [0.47, 0.47, 0.47, 1]      # #787878
WHITE   = [1.0, 1.0, 1.0, 1]
PRI     = [1.0, 1.0, 1.0, 1]
ENERGY  = [0.0, 0.73, 1.0, 1]        # #00b3ff
ENERGY_D= [0.0, 0.55, 0.8, 1]
GREEN   = [0.0, 0.73, 0.4, 1]
GREEN_D = [0.0, 0.45, 0.24, 1]
RED     = [0.85, 0.18, 0.18, 1]
RED_D   = [0.55, 0.12, 0.12, 1]

MOOD_COLORS = {
    "chill":    [0.0, 0.73, 1.0],
    "excited":  [1.0, 0.4, 0.0],
    "focused":  [0.9, 0.0, 0.0],
    "playful":  [0.6, 0.0, 1.0],
    "worried":  [1.0, 0.8, 0.0],
    "proud":    [0.8, 0.8, 0.8],
    "sleepy":   [0.4, 0.4, 0.6],
}

VOICES = [
    {"id": "en-US-AriaNeural", "name": "Aria", "style": "Friendly · US · Female"},
    {"id": "en-US-GuyNeural", "name": "Guy", "style": "Natural · US · Male"},
    {"id": "en-US-JennyNeural", "name": "Jenny", "style": "Warm · US · Female"},
    {"id": "en-US-TonyNeural", "name": "Tony", "style": "Calm · US · Male"},
    {"id": "en-GB-SoniaNeural", "name": "Sonia", "style": "Professional · UK · Female"},
    {"id": "en-GB-RyanNeural", "name": "Ryan", "style": "Deep · UK · Male"},
    {"id": "ru-RU-SvetlanaNeural", "name": "Natasha", "style": "Sweet · RU · Female"},
    {"id": "en-AU-WilliamNeural", "name": "William", "style": "Smooth · AU · Male"},
]


def _colstr(c):
    """Convert [r,g,b,a] 0-1 to #rrggbb hex."""
    return '#{:02x}{:02x}{:02x}'.format(int(c[0]*255), int(c[1]*255), int(c[2]*255))


# ═══════════════════════════════════════════════════════════════════════
# HOLOGRAPHIC ORB — Same as desktop: hex frame, lattice, orbital rings
# ═══════════════════════════════════════════════════════════════════════
class HolographicOrb(Widget):
    tick = NumericProperty(0)
    mood_color = ListProperty([0.0, 0.73, 1.0])
    is_active = BooleanProperty(False)
    is_speaking = BooleanProperty(False)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.bind(size=self._redraw, pos=self._redraw)
        Clock.schedule_interval(lambda dt: setattr(self, 'tick', self.tick + 1), 1/30)
        self.bind(tick=self._redraw)

    def _redraw(self, *a):
        self.canvas.clear()
        with self.canvas:
            cx = self.center_x
            cy = self.center_y
            r = min(self.width, self.height) * 0.38
            t = self.tick
            mc = self.mood_color

            # ── Outer diffuse glow ──────────────────────────────
            for i in range(6):
                a = 0.025 * (6 - i) / 6
                Color(mc[0], mc[1], mc[2], a)
                gr = r * (1.2 + i * 0.12)
                Ellipse(pos=(cx - gr, cy - gr), size=(gr*2, gr*2))

            # ── Hexagonal frame ─────────────────────────────────
            ha = 0.15 if self.is_active else 0.07
            hr = r * 1.12
            pts = []
            for i in range(6):
                ang = math.radians(60*i - 30 + t*0.4)
                pts.extend([cx + math.cos(ang)*hr, cy + math.sin(ang)*hr*0.85])
            pts.extend(pts[:2])
            Color(mc[0], mc[1], mc[2], ha)
            Line(points=pts, width=1.0)

            # ── Inner hex (rotated) ────────────────────────────
            Color(mc[0], mc[1], mc[2], ha*0.4)
            pts2 = []
            for i in range(6):
                ang = math.radians(60*i + t*0.4)
                pts2.extend([cx + math.cos(ang)*hr*0.93, cy + math.sin(ang)*hr*0.93*0.85])
            pts2.extend(pts2[:2])
            Line(points=pts2, width=0.5)

            # ── Tick marks on hex edges ─────────────────────────
            Color(mc[0], mc[1], mc[2], ha*0.6)
            for i in range(6):
                p1x = cx + math.cos(math.radians(60*i-30+t*0.4))*hr
                p1y = cy + math.sin(math.radians(60*i-30+t*0.4))*hr*0.85
                p2x = cx + math.cos(math.radians(60*(i+1)-30+t*0.4))*hr
                p2y = cy + math.sin(math.radians(60*(i+1)-30+t*0.4))*hr*0.85
                for j in range(11):
                    f = j/10
                    mx = p1x + (p2x-p1x)*f
                    my = p1y + (p2y-p1y)*f
                    nx = p2y - p1y
                    ny = -(p2x - p1x)
                    nl = math.hypot(nx, ny)
                    if nl > 0: nx /= nl; ny /= nl
                    tl = 5 if j % 5 == 0 else 2.5
                    Line(points=[mx, my, mx+nx*tl, my+ny*tl], width=0.3)

            # ── Spherical lattice — latitude rings ──────────────
            la = 0.06 if self.is_active else 0.03
            for li in range(1, 8):
                frac = li / 8
                phi = frac * math.pi
                rr = math.sin(phi) * r
                yo = math.cos(phi) * r * 0.85
                lpts = []
                for deg in range(0, 361, 5):
                    rad = math.radians(deg + t*0.6 + li*15)
                    x = math.cos(rad) * rr
                    y = math.sin(rad) * rr * 0.85 - yo*0.85
                    fade = max(0.3, (y/r+1)/2)
                    aa = la * fade
                    if aa > 0.004:
                        lpts.extend([cx+x, cy+y])
                if len(lpts) >= 4:
                    Color(mc[0], mc[1], mc[2], la)
                    Line(points=lpts, width=0.25)

            # ── Longitude arcs ──────────────────────────────────
            for li in range(4):
                ang = li*45 + t*0.3
                rad = math.radians(ang)
                lpts = []
                for seg in range(0, 181, 5):
                    phi = math.radians(seg)
                    x = math.sin(phi)*math.cos(rad)*r
                    y = math.sin(phi)*math.sin(rad)*r*0.85
                    z = math.cos(phi)*r
                    depth = (z/r+1)/2
                    aa = la*max(0.2, depth)
                    if aa > 0.004:
                        lpts.extend([cx+x, cy-y])
                if len(lpts) >= 4:
                    Color(mc[0], mc[1], mc[2], la*0.5)
                    Line(points=lpts, width=0.2)

            # ── Orbital rings ───────────────────────────────────
            rings = [(1.22, 0.3, 0.5, 0.9), (1.12, 0.8, 0.2, 0.7), (1.32, 0.1, 0.9, 0.5)]
            for ri, (rf, tx, tz, w) in enumerate(rings):
                rrr = r * rf
                ra = t*(0.25+ri*0.12)
                ra_a = 0.1 if self.is_active else 0.04
                rpts = []
                for deg in range(0, 361, 4):
                    rad = math.radians(deg+ra)
                    x = math.cos(rad)*rrr
                    y = math.sin(rad)*rrr*math.cos(tx)
                    z = math.sin(rad)*rrr*math.sin(tz)
                    rpts.extend([cx+x, cy-y])
                if len(rpts) >= 4:
                    Color(mc[0], mc[1], mc[2], ra_a)
                    Line(points=rpts, width=w*0.6)

            # ── Core glow ───────────────────────────────────────
            for i in range(8):
                ca = 0.06*(8-i)/8
                if self.is_speaking:
                    ca *= 1.4 + 0.3*math.sin(t*0.3)
                Color(mc[0], mc[1], mc[2], min(1, ca))
                cr = r*(0.07+i*0.018)
                Ellipse(pos=(cx-cr, cy-cr), size=(cr*2, cr*2))

            # ── Core point ──────────────────────────────────────
            ca2 = 0.55 if self.is_active else 0.25
            if self.is_speaking:
                ca2 = 0.75 + 0.25*math.sin(t*0.5)
            Color(mc[0], mc[1], mc[2], ca2)
            Ellipse(pos=(cx-2.5, cy-2.5), size=(5, 5))

            # ── Vertex dots ─────────────────────────────────────
            for i in range(6):
                ang = math.radians(60*i-30+t*0.4)
                vx = cx + math.cos(ang)*hr
                vy = cy + math.sin(ang)*hr*0.85
                Color(mc[0], mc[1], mc[2], 0.2)
                Ellipse(pos=(vx-4, vy-4), size=(8, 8))
                Color(mc[0], mc[1], mc[2], 0.45)
                Ellipse(pos=(vx-1.5, vy-1.5), size=(3, 3))

            # ── Crosshair ───────────────────────────────────────
            crr = r * 1.22
            cg = r * 0.45
            ca3 = 0.05 if self.is_active else 0.025
            Color(mc[0], mc[1], mc[2], ca3)
            Line(points=[cx-crr, cy, cx-cg, cy], width=0.3)
            Line(points=[cx+cg, cy, cx+crr, cy], width=0.3)
            Line(points=[cx, cy-crr, cx, cy-cg], width=0.3)
            Line(points=[cx, cy+cg, cx, cy+crr], width=0.3)

            # ── Degree ticks ────────────────────────────────────
            for deg in range(0, 360, 45):
                rad = math.radians(deg)
                ix = cx + math.cos(rad)*(crr-3)
                iy = cy + math.sin(rad)*(crr-3)
                ox = cx + math.cos(rad)*crr
                oy = cy + math.sin(rad)*crr
                Color(mc[0], mc[1], mc[2], ca3)
                Line(points=[ix, iy, ox, oy], width=0.25)

            # ── Speaking waveform ───────────────────────────────
            if self.is_speaking:
                ww = r * 0.7
                wy = cy - r * 1.25
                wpts = []
                for wx in range(int(cx-ww), int(cx+ww), 3):
                    f = (wx-(cx-ww))/(ww*2)
                    amp = r*0.06*math.sin(f*math.pi)
                    val = amp*math.sin(t*0.4+f*12)
                    wpts.extend([wx, wy+val])
                if len(wpts) >= 4:
                    Color(mc[0], mc[1], mc[2], 0.25)
                    Line(points=wpts, width=1.0)


# ═══════════════════════════════════════════════════════════════════════
# CHAT BUBBLE — Exact match to desktop ChatBubbleWidget
# ═══════════════════════════════════════════════════════════════════════
class ChatBubble(BoxLayout):
    """Matches desktop: card with header (name+time) + message, rounded border."""
    def __init__(self, text, sender="ai", **kwargs):
        super().__init__(**kwargs)
        self.orientation = 'horizontal'
        self.size_hint_x = 1
        self.size_hint_y = None
        self.height = dp(80)  # will be updated
        self.spacing = 0
        self.padding = [0, 0, 0, 0]

        is_user = sender == "user"

        # Determine colors — match desktop C class
        if is_user:
            bg = _colstr(DARK2)         # #141414
            border = _colstr(BORDER_B)  # #383838
            text_c = _colstr(WHITE)
            name = "YOU"
        elif sender == "ai":
            bg = "#141414"
            border = _colstr(ENERGY)    # #00b3ff
            text_c = _colstr(PRI)
            name = "MITSU"
        elif sender == "error":
            bg = "#1a0a0a"
            border = _colstr(RED_D)
            text_c = _colstr(RED)
            name = "ERROR"
        else:
            bg = "#0f0a1a"
            border = "#6633cc"
            text_c = "#9966ff"
            name = "SYS"

        ts = time.strftime("%H:%M")

        # Spacer for alignment
        if is_user:
            self.add_widget(Widget(size_hint_x=0.05))

        # Card
        card = BoxLayout(orientation='vertical', size_hint_x=0.9 if is_user else 0.92)
        card.spacing = dp(2)
        card.padding = [dp(10), dp(6), dp(10), dp(6)]

        with card.canvas.before:
            # Background
            r, g, b = [int(border.lstrip('#')[i:i+2], 16)/255 for i in (0, 2, 4)]
            Color(r, g, b, 0.15)
            self._card_bg = Rectangle(pos=card.pos, size=card.size)
            # Border
            r2, g2, b2 = [int(border.lstrip('#')[i:i+2], 16)/255 for i in (0, 2, 4)]
            Color(r2, g2, b2, 0.6)
            self._card_border = Line(
                rectangle=(card.x, card.y, card.width, card.height),
                width=0.8, rounded_rectangle=(card.x, card.y, card.width, card.height, 8)
            )
            card.bind(pos=self._update_card, size=self._update_card)

        # Header row
        hdr = BoxLayout(size_hint_y=None, height=dp(16), spacing=dp(4))
        name_lbl = Label(
            text=f"[color={border}][b]{name}[/b][/color]",
            markup=True, font_size=sp(8), halign='left',
            size_hint_x=0.5,
            text_size=(None, None),
        )
        hdr.add_widget(name_lbl)
        ts_lbl = Label(
            text=f"[color=#787878]{ts}[/color]",
            markup=True, font_size=sp(7), halign='right',
            size_hint_x=0.5,
        )
        hdr.add_widget(ts_lbl)
        card.add_widget(hdr)

        # Message text
        msg_lbl = Label(
            text=f"[color=#ffffff]{text}[/color]",
            markup=True, font_size=sp(10), halign='left',
            valign='top', size_hint_y=None,
            text_size=(Window.width * 0.78, None),
        )
        msg_lbl.bind(texture_size=lambda inst, val: setattr(inst, 'height', val[1] + dp(4)))
        card.add_widget(msg_lbl)

        self.add_widget(card)

        # Spacer for alignment
        if not is_user:
            self.add_widget(Widget(size_hint_x=0.05))

        # Calculate final height
        Clock.schedule_once(self._calc_height, 0)

    def _calc_height(self, *args):
        h = dp(16) + dp(6) + dp(6)  # header + padding
        for child in self.children:
            if isinstance(child, BoxLayout):
                for c in child.children:
                    if hasattr(c, 'texture_size') and c.texture_size:
                        h += c.texture_size[1] + dp(2)
        self.height = max(h, dp(50))

    def _update_card(self, *args):
        for child in self.children:
            if isinstance(child, BoxLayout):
                with child.canvas.before:
                    child.canvas.before.clear()
                    Color(0.08, 0.08, 0.08, 0.95)
                    Rectangle(pos=child.pos, size=child.size)
                    Color(0.22, 0.22, 0.22, 0.5)
                    Line(
                        rounded_rectangle=(child.x, child.y, child.width, child.height, 8),
                        width=0.8
                    )


# ═══════════════════════════════════════════════════════════════════════
# TYPING INDICATOR
# ═══════════════════════════════════════════════════════════════════════
class TypingBubble(BoxLayout):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.orientation = 'horizontal'
        self.size_hint_x = 1
        self.size_hint_y = None
        self.height = dp(50)
        self.add_widget(Widget(size_hint_x=0.05))

        card = BoxLayout(size_hint_x=0.92, padding=[dp(10), dp(8)])
        with card.canvas.before:
            Color(0.08, 0.08, 0.08, 0.95)
            Rectangle(pos=card.pos, size=card.size)
            Color(0, 0.73, 1, 0.3)
            Line(
                rounded_rectangle=(card.x, card.y, card.width, card.height, 8),
                width=0.8
            )
            card.bind(pos=self._upd, size=self._upd)

        dots = Label(
            text="[color=#00b3ff]▌[/color]",
            markup=True, font_size=sp(12),
        )
        card.add_widget(dots)
        self.add_widget(card)
        self.add_widget(Widget(size_hint_x=0.05))

    def _upd(self, *args):
        for child in self.children:
            if isinstance(child, BoxLayout):
                with child.canvas.before:
                    child.canvas.before.clear()
                    Color(0.08, 0.08, 0.08, 0.95)
                    Rectangle(pos=child.pos, size=child.size)
                    Color(0, 0.73, 1, 0.3)
                    Line(
                        rounded_rectangle=(child.x, child.y, child.width, child.height, 8),
                        width=0.8
                    )


# ═══════════════════════════════════════════════════════════════════════
# SETUP SCREEN
# ═══════════════════════════════════════════════════════════════════════
class SetupScreen(BoxLayout):
    def __init__(self, on_complete, **kwargs):
        super().__init__(**kwargs)
        self.orientation = "vertical"
        self.spacing = dp(10)
        self.padding = [dp(24), dp(30), dp(24), dp(20)]
        self.on_complete = on_complete
        self.selected_voice = VOICES[0]["id"]
        self._voice_buttons = []

        with self.canvas.before:
            Color(*BG)
            self._bg = Rectangle(pos=self.pos, size=self.size)
            self.bind(pos=self._updbg, size=self._updbg)

        # ── Logo ───────────────────────────────────────────────
        logo_w = Widget(size_hint_y=None, height=dp(100))
        with logo_w.canvas:
            ccx, ccy = Window.width//2, dp(50)
            Color(1, 1, 1, 0.12)
            Ellipse(pos=(ccx-dp(40), ccy-dp(40)), size=(dp(80), dp(80)))
            Color(1, 1, 1, 0.85)
            ml, mr = ccx-dp(20), ccx+dp(20)
            mt, mb = ccy-dp(20), ccy+dp(20)
            mm = ccy
            lw = dp(2.5)
            Line(points=[ml, mb, ml, mt], width=lw)
            Line(points=[ml, mt, ccx, mm], width=lw)
            Line(points=[ccx, mm, mr, mt], width=lw)
            Line(points=[mr, mt, mr, mb], width=lw)
        self.add_widget(logo_w)

        self.add_widget(Label(
            text="[color=#ffffff][b]M I T S U[/b][/color]",
            markup=True, font_size=sp(20), size_hint_y=None, height=dp(30),
        ))
        self.add_widget(Label(
            text="[color=#787878]Your AI companion[/color]",
            markup=True, font_size=sp(11), size_hint_y=None, height=dp(20),
        ))

        # ── Divider ────────────────────────────────────────────
        div = Widget(size_hint_y=None, height=dp(1))
        with div.canvas:
            Color(0.12, 0.12, 0.12, 1)
            Rectangle(pos=div.pos, size=(Window.width-dp(48), dp(1)))
        self.add_widget(div)

        # ── Name ───────────────────────────────────────────────
        self.add_widget(Label(
            text="[color=#787878]What should I call you?[/color]",
            markup=True, font_size=sp(12), halign='left',
            size_hint_y=None, height=dp(26),
            text_size=(Window.width-dp(48), None),
        ))

        self.name_input = TextInput(
            hint_text="Enter your name",
            font_size=sp(15), size_hint_y=None, height=dp(48),
            background_color=(0.06, 0.06, 0.06, 1),
            foreground_color=(1, 1, 1, 1),
            hint_text_color=(0.3, 0.3, 0.3, 1),
            cursor_color=(1, 1, 1, 1),
            multiline=False, padding=[dp(12), dp(10)],
            border=[0, 0, 0, 0],
        )
        self.add_widget(self.name_input)

        # ── Voice ──────────────────────────────────────────────
        self.add_widget(Label(
            text="[color=#787878]Choose a voice:[/color]",
            markup=True, font_size=sp(12), halign='left',
            size_hint_y=None, height=dp(26),
            text_size=(Window.width-dp(48), None),
        ))

        voice_scroll = ScrollView(size_hint_y=None, height=dp(180), do_scroll_x=False)
        voice_grid = GridLayout(cols=1, size_hint_y=None, spacing=dp(5))
        voice_grid.bind(minimum_height=voice_grid.setter("height"))

        for v in VOICES:
            btn = Button(
                text=f"  {v['name']}  —  {v['style']}",
                size_hint_y=None, height=dp(42),
                font_size=sp(11), halign='left',
                background_color=(0.08, 0.08, 0.08, 1),
                color=(0.6, 0.6, 0.6, 1),
                border=[0, 0, 0, 0],
            )
            btn.voice_id = v["id"]
            btn.bind(on_press=lambda b, vid=v["id"]: self._sel_voice(vid))
            self._voice_buttons.append(btn)
            voice_grid.add_widget(btn)

        voice_scroll.add_widget(voice_grid)
        self.add_widget(voice_scroll)

        # ── Start ──────────────────────────────────────────────
        start_btn = Button(
            text="▸  START",
            font_size=sp(14), size_hint_y=None, height=dp(50),
            background_color=(0, 0.55, 0.3, 1),
            color=(1, 1, 1, 1), bold=True, border=[0, 0, 0, 0],
        )
        start_btn.bind(on_press=self._on_start)
        self.add_widget(start_btn)

        self._upd_voice_hl()

    def _updbg(self, *args):
        self._bg.pos = self.pos
        self._bg.size = self.size

    def _sel_voice(self, vid):
        self.selected_voice = vid
        self._upd_voice_hl()

    def _upd_voice_hl(self):
        for b in self._voice_buttons:
            if b.voice_id == self.selected_voice:
                b.background_color = (0, 0.25, 0.15, 1)
                b.color = (0, 1, 0.5, 1)
            else:
                b.background_color = (0.08, 0.08, 0.08, 1)
                b.color = (0.6, 0.6, 0.6, 1)

    def _on_start(self, *args):
        name = self.name_input.text.strip()
        if not name:
            self.name_input.hint_text = "Please enter your name!"
            return
        d = Path.home() / ".mitsu"
        d.mkdir(parents=True, exist_ok=True)
        (d / "username.txt").write_text(name)
        (d / "voice.txt").write_text(self.selected_voice)
        self.on_complete(name, self.selected_voice)


# ═══════════════════════════════════════════════════════════════════════
# MAIN LAYOUT
# ═══════════════════════════════════════════════════════════════════════
class MitsuLayout(FloatLayout):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.username = self._load("username.txt", "")
        self.selected_voice = self._load("voice.txt", "en-US-AriaNeural")
        self.current_mood = "chill"
        self.is_listening = False
        self.is_speaking = False
        self._last_input_at = time.time()
        self._proactive_timer = None
        self._orb = None
        self._chat_cont = None
        self._scroll = None
        self._status_lbl = None
        self._mood_lbl = None
        self._input = None
        self._typing_bubble = None

        with self.canvas.before:
            Color(*BG)
            self._bg = Rectangle(pos=self.pos, size=self.size)
            self.bind(pos=self._updbg, size=self._updbg)

        if self.username:
            self._build()
            self._greet()
            self._start_proactive()
        else:
            self._show_setup()

    def _updbg(self, *args):
        self._bg.pos = self.pos
        self._bg.size = self.size

    def _load(self, name, default=""):
        try:
            f = Path.home() / ".mitsu" / name
            if f.exists(): return f.read_text().strip()
        except: pass
        return default

    def _show_setup(self):
        self.clear_widgets()
        self.add_widget(SetupScreen(on_complete=self._on_setup_done))

    def _on_setup_done(self, name, voice):
        self.username = name
        self.selected_voice = voice
        self.clear_widgets()
        self._build()
        self._greet()
        self._start_proactive()

    def _build(self):
        self.clear_widgets()
        root = BoxLayout(orientation='vertical')

        # ── Header ─────────────────────────────────────────────
        hdr = BoxLayout(size_hint_y=None, height=dp(44), padding=[dp(12), 0])
        with hdr.canvas.before:
            Color(0.055, 0.055, 0.055, 1)
            Rectangle(pos=hdr.pos, size=hdr.size)
            Color(0.12, 0.12, 0.12, 1)
            Line(points=[hdr.x, hdr.y, hdr.right, hdr.y], width=0.5)
            hdr.bind(pos=self._updhdr, size=self._updhdr)

        self._status_lbl = Label(
            text="[color=#00cc66]●[/color]  ONLINE",
            markup=True, font_size=sp(9), halign='left', size_hint_x=0.35,
        )
        hdr.add_widget(self._status_lbl)

        hdr.add_widget(Label(
            text="[color=#ffffff][b]M I T S U[/b][/color]",
            markup=True, font_size=sp(12),
        ))

        self._mood_lbl = Label(
            text="[color=#787878]mood:[/color] [color=#00b3ff]chill[/color]",
            markup=True, font_size=sp(8), halign='right', size_hint_x=0.35,
        )
        hdr.add_widget(self._mood_lbl)
        root.add_widget(hdr)

        # ── Orb ────────────────────────────────────────────────
        orb_area = FloatLayout(size_hint_y=None, height=dp(200))
        self._orb = HolographicOrb()
        orb_area.add_widget(self._orb)
        name_lbl = Label(
            text=f"[color=#ffffff55]{self.username}[/color]",
            markup=True, font_size=sp(9),
            pos_hint={'center_x': 0.5, 'top': 0.92},
            size_hint=(None, None), size=(dp(150), dp(16)),
        )
        orb_area.add_widget(name_lbl)
        root.add_widget(orb_area)

        # ── Chat ───────────────────────────────────────────────
        self._scroll = ScrollView(do_scroll_x=False)
        self._chat_cont = BoxLayout(
            orientation='vertical', size_hint_y=None,
            spacing=dp(6), padding=[dp(6), dp(6)],
        )
        self._chat_cont.bind(minimum_height=self._chat_cont.setter('height'))
        self._scroll.add_widget(self._chat_cont)
        root.add_widget(self._scroll)

        # ── Input ──────────────────────────────────────────────
        inp_area = BoxLayout(size_hint_y=None, height=dp(56), spacing=dp(6),
                             padding=[dp(8), dp(5)])
        with inp_area.canvas.before:
            Color(0.055, 0.055, 0.055, 1)
            Rectangle(pos=inp_area.pos, size=inp_area.size)
            Color(0.12, 0.12, 0.12, 1)
            Line(points=[inp_area.x, inp_area.top, inp_area.right, inp_area.top], width=0.5)
            inp_area.bind(pos=self._updinpa, size=self._updinpa)

        self._input = TextInput(
            hint_text="Type a message to MITSU…",
            font_size=sp(13), size_hint_x=0.65,
            background_color=(0.055, 0.055, 0.055, 1),
            foreground_color=(1, 1, 1, 1),
            hint_text_color=(0.47, 0.47, 0.47, 1),
            cursor_color=(0, 0.73, 1, 1),
            multiline=False, padding=[dp(8), dp(8)],
            border=[0, 0, 0, 0],
        )
        self._input.bind(on_text_validate=self._send)
        inp_area.add_widget(self._input)

        voice_btn = Button(
            text="🎤", font_size=sp(16), size_hint_x=None, width=dp(38),
            background_color=(0.055, 0.055, 0.055, 1),
            color=(0, 0.73, 1, 1), border=[0, 0, 0, 0],
        )
        voice_btn.bind(on_press=self._voice)
        inp_area.add_widget(voice_btn)

        send_btn = Button(
            text="▸", font_size=sp(16), size_hint_x=None, width=dp(38),
            background_color=(0, 0, 0, 0),
            color=(0, 0.73, 1, 1), bold=True,
            border=[0, 0, 0, 0],
        )
        with send_btn.canvas.before:
            Color(0, 0.73, 1, 0.13)
            Rectangle(pos=send_btn.pos, size=send_btn.size)
            Color(0, 0.73, 1, 0.4)
            Line(
                rounded_rectangle=(send_btn.x, send_btn.y, send_btn.width, send_btn.height, 4),
                width=0.8
            )
            send_btn.bind(pos=self._updsnd, size=self._updsnd)
        send_btn.bind(on_press=self._send)
        inp_area.add_widget(send_btn)

        root.add_widget(inp_area)
        self.add_widget(root)

    def _updhdr(self, *args):
        with self.children[0].canvas.before.children[-3]:
            pass  # handled by bind

    def _updinpa(self, *args):
        pass

    def _updsnd(self, *args):
        pass

    # ── Chat logic ─────────────────────────────────────────────
    def _add_bubble(self, text, sender="ai"):
        if not self._chat_cont:
            return
        bubble = ChatBubble(text, sender=sender)
        self._chat_cont.add_widget(bubble)
        Clock.schedule_once(lambda dt: self._scroll_to_end(), 0.1)

    def _scroll_to_end(self):
        if self._scroll:
            self._scroll.scroll_y = 0

    def _greet(self):
        g = get_greeting(self.current_mood, self.username)
        self._add_bubble(g, "ai")

    def _send(self, *args):
        if not self._input:
            return
        txt = self._input.text.strip()
        if not txt:
            return
        self._input.text = ""
        self._process(txt)

    def _voice(self, *args):
        if self.is_listening:
            return
        self.is_listening = True
        self._set_status("listening")
        threading.Thread(target=self._listen_th, daemon=True).start()

    def _listen_th(self):
        try:
            txt = recognize_speech()
            if txt:
                Clock.schedule_once(lambda dt: self._process(txt), 0)
            else:
                Clock.schedule_once(lambda dt: self._set_status("online"), 0)
        except Exception as e:
            print(f"[Mitsu] Voice error: {e}")
            Clock.schedule_once(lambda dt: self._set_status("online"), 0)
        finally:
            self.is_listening = False

    def _process(self, txt):
        self._add_bubble(txt, "user")
        self._set_status("thinking")
        self._last_input_at = time.time()

        # Detect gender from message
        from core.emotions import detect_gender
        detect_gender(message=txt)

        mood = detect_user_tone(txt)
        if mood != self.current_mood:
            self.current_mood = mood
            mc = MOOD_COLORS.get(mood, ENERGY)
            if self._orb:
                self._orb.mood_color = mc
            if self._mood_lbl:
                hx = ''.join(f'{int(c*255):02x}' for c in mc[:3])
                self._mood_lbl.text = f"[color=#787878]mood:[/color] [color=#{hx}]{mood}[/color]"

        # Typing indicator
        self._typing_bubble = TypingBubble()
        self._chat_cont.add_widget(self._typing_bubble)
        Clock.schedule_once(lambda dt: self._scroll_to_end(), 0.1)

        threading.Thread(target=self._ai_th, args=(txt,), daemon=True).start()

    def _ai_th(self, txt):
        try:
            from core.languages import get_lang_manager
            lang_ctx = get_lang_manager().get_lang_context()
            ctx = format_conversation_context(5)
            full_ctx = f"{lang_ctx}\n\n{ctx}" if ctx else lang_ctx
            resp = call_ai(txt, self.current_mood, context=full_ctx)
            save_conversation("user", txt, self.current_mood)
            save_conversation("mitsu", resp, self.current_mood)
            Clock.schedule_once(lambda dt: self._on_resp(resp), 0)
        except Exception as e:
            print(f"[Mitsu] AI error: {e}")
            Clock.schedule_once(lambda dt: self._on_resp("Something went wrong. Try again?"), 0)

    def _on_resp(self, txt):
        # Remove typing indicator
        if self._typing_bubble and self._typing_bubble.parent:
            self._chat_cont.remove_widget(self._typing_bubble)
            self._typing_bubble = None
        self._add_bubble(txt, "ai")
        self._set_status("online")
        threading.Thread(target=self._speak_th, args=(txt,), daemon=True).start()

    def _speak_th(self, txt):
        try:
            self.is_speaking = True
            Clock.schedule_once(lambda dt: self._set_speaking(True), 0)
            speak_mobile(txt, vid=self.selected_voice)
        except Exception as e:
            print(f"[Mitsu] TTS error: {e}")
        finally:
            self.is_speaking = False
            Clock.schedule_once(lambda dt: self._set_speaking(False), 0)

    def _set_speaking(self, v):
        if self._orb:
            self._orb.is_speaking = v

    def _set_status(self, state):
        if not self._status_lbl:
            return
        m = {
            "online": "[color=#00cc66]●[/color]  ONLINE",
            "listening": "[color=#ffaa00]●[/color]  LISTENING",
            "thinking": "[color=#00b3ff]●[/color]  THINKING",
            "speaking": "[color=#00ff88]●[/color]  SPEAKING",
        }
        self._status_lbl.text = m.get(state, m["online"])
        if self._orb:
            self._orb.is_active = state in ("listening", "thinking", "speaking")

    def _start_proactive(self):
        if self._proactive_timer:
            self._proactive_timer.cancel()
        interval = random.randint(60, 120)
        self._proactive_timer = threading.Timer(interval, self._maybe_proactive)
        self._proactive_timer.daemon = True
        self._proactive_timer.start()

    def _maybe_proactive(self):
        elapsed = time.time() - self._last_input_at
        if elapsed > 60 and random.random() < 0.5:
            mood = self.current_mood
            if mood in PROACTIVE_MESSAGES and PROACTIVE_MESSAGES[mood]:
                msg = random.choice(PROACTIVE_MESSAGES[mood]).replace("{name}", self.username)
                Clock.schedule_once(lambda dt, m=msg: self._add_bubble(m, "ai"), 0)
        self._start_proactive()


# ═══════════════════════════════════════════════════════════════════════
# APP
# ═══════════════════════════════════════════════════════════════════════
class MitsuApp(App):
    def build(self):
        self.title = "MITSU"
        Window.clearcolor = BG
        return MitsuLayout()

    def on_pause(self):
        return True


if __name__ == "__main__":
    MitsuApp().run()
