# Design System

## Theme

Mitsu Noir: pure black canvas, white energy. Minimal, premium, brutalist.
No colored frills — white light on black void. Like a high-end dark mode UI.

## Color Palette

- Workspace: `#000000` (pure black)
- Primary surface: `#0A0A0A` (near-black)
- Raised surface: `#1A1A1A` (elevated)
- Structural border: `#2A2A2A` (subtle gray)
- Bright border: `#444444` (visible gray)
- Primary energy: `#FFFFFF` (pure white)
- Energy glow: `#F0F0F0` (bright white)
- Primary text: `#FFFFFF` (white)
- Secondary text: `#999999` (medium gray)
- Dim telemetry: `#555555` (muted)
- Success: `#00FF88`
- Warning: `#FFFFFF` (bold)
- Error: `#FF2244`

## Typography

- **Primary UI:** Space Grotesk, weight 400 for body copy and 500/600 for headings, navigation, buttons, settings, dialogue, and popup titles.
- **Technical data:** JetBrains Mono, weight 400/500 for timestamps, metrics, coordinates, identifiers, terminal output, and status readouts.
- Avoid novelty sci-fi fonts and excessive bold weights. The minimal motion, spacing, and contrast carry the identity.

## Components

- Structural panels use thin gray-tinted borders and pure black fills.
- Interactive controls retain compact radii and clear active, hover, focus, and disabled states.
- The reactor visualization is a white pulse on black — minimal, elegant.
- Overlays are opaque enough for legibility and avoid decorative blur.

## Layout

The normal application keeps its existing three-panel console and centered reactor HUD. The first-run introduction temporarily owns the full application viewport, assembles content from the center outward, and then hands off to the centered initialization overlay.

## Motion

Use staged opacity, scale, and position reveals with exponential easing. Avoid bounce, strobing, or continuous decorative movement. The first-run sequence may be cinematic because it occurs once; routine launches should enter the console directly unless the user explicitly enables replay on every launch.
