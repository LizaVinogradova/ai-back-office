---
name: present
description: Create stunning, interactive HTML presentations that feel like next-generation experiences. Use when a user asks for a presentation, slide deck, pitch deck, slides, or anything presentation-related. Produces a single self-contained HTML file with animations, interactive elements, and cinematic transitions — no PowerPoint, no dependencies, just open in a browser.
---

# Present — Next-Generation HTML Presentations

Create presentations that make audiences say "how did they do that?" Single self-contained HTML file. No dependencies. Open in any browser.

## Workflow

### 1. Discover — Understand What They Need

Before writing a single line, clarify:

- **What's the presentation about?** Get the core message and key points.
- **Who's the audience?** Developers? Executives? Friends? A conference?
- **How many slides?** Ask or estimate from the content (~1 slide per key point + title + finale).
- **What's the vibe?** Offer starting points, then let them describe freely:
  - 🌑 **Dark Tech** — Dark background, subtle glows, monospace accents. Think Apple keynote meets hacker terminal.
  - 🏔️ **Minimal Zen** — Lots of whitespace, elegant typography, serene motion. Think calm confidence.
  - 🎨 **Bold Creative** — Vivid colors, playful animations, unexpected layouts. Think art gallery.
  - 🏢 **Corporate Sharp** — Clean, professional, data-forward. Think board meeting, but actually good.
  - 🌅 **Warm Narrative** — Earthy tones, storytelling flow, intimate feel. Think fireside talk.
  - ✨ **Custom** — "Describe it and I'll build it."

Do NOT start building until you understand the content and the feel. A few good questions save hours of revision.

### 2. Architect — Plan the Experience

Think of each slide as a **moment**, not a page. Plan:

- **Opening** — First impressions matter. Terminal boot sequences, dramatic reveals, animated typography. The audience should lean forward before the first word of content.
- **Content slides** — Each one needs a reason to exist. What's the single idea? What's the visual metaphor?
- **Interactive moments** — Where can the audience (or presenter) *do* something? These are the memorable peaks.
- **Closing** — Land the plane. Callback to the opening, clear CTA, or emotional resonance.

Share the slide plan with the user before building. Get buy-in on structure.

### 3. Build — Create the Presentation

Output a **single self-contained HTML file**. All CSS inline in `<style>`, all JS inline in `<script>`. No external dependencies except Google Fonts (loaded via `@import`).

#### Technical Foundation

- Keyboard navigation: Arrow keys + Space to advance, navigation dots on the side
- Slide counter (e.g., "3 / 15") in the corner
- Smooth transitions between slides (opacity, transform — not jarring cuts)
- Responsive for 16:9 screens (the standard presentation ratio)
- Background canvas effects (particles, stars, subtle motion) add depth without distraction

#### The Art: Interactive Elements

This is what separates these presentations from everything else. The following are **starting points, not limits**. Invent new interactions. Surprise the user. Go beyond what they imagined.

**Visual & Motion:**
- Animated typography — words that build, reveal, glitch, or transform
- Parallax layers — foreground/background moving at different speeds
- Particle systems — reactive to mouse movement or slide transitions
- Morphing shapes — SVG paths that transition between forms
- Cinematic reveals — elements that emerge from blur, scale, or rotation
- Progress visualizations — bars, rings, counters that animate on slide entry

**Interactive Elements:**
- Flip cards — click to reveal hidden content on the back
- Expandable sections — click to drill deeper into a topic
- Live code terminals — typing animations that simulate real code execution
- Comparison sliders — drag to compare before/after or two options
- Interactive timelines — scroll or click through chronological events
- Hover-reveal content — details that appear on mouse interaction
- Clickable diagrams — explore parts of a system by clicking nodes
- Chat mockups — simulated conversations that type out in real-time
- Data dashboards — animated charts, metrics that count up
- Voting/polling UI — interactive (visual only) audience engagement

**Audio & Sensory (use sparingly):**
- Ambient sound on slide transitions
- Click/tap sound feedback on interactive elements
- Voice-over integration points

**Structural Patterns:**
- Split layouts — text left, visual right (or vice versa)
- Full-bleed visuals — a slide that's entirely a visual moment
- The "zoom in" — start with the big picture, progressively dive deeper
- The "reveal" — build a complete picture piece by piece across multiple slides
- Quote slides — large typography, minimal decoration, maximum impact

### 4. Iterate — Refine With the User

After the first version:
- Send the file so they can open it immediately
- Ask what slides land and which need work
- Be ready to add, remove, reorder, or completely reimagine slides
- Each iteration should be a complete, working file

## Design Principles

- **No default gradients** — Gradients often look generic. Use solid colors with subtle glows, text-shadow, and box-shadow for depth. If the user specifically wants gradients, make them intentional and unique.
- **Typography is the hero** — Great presentations are 80% type. Use font weight, size, spacing, and color to create hierarchy. Pair a display font with a monospace accent.
- **Restraint over excess** — Every animation should earn its place. A single perfect transition beats ten flashy ones.
- **Contrast creates impact** — A quiet slide makes the next dramatic one hit harder. Vary the energy.
- **Interactive moments are peaks** — Place them strategically. Too many and nothing feels special. Too few and the audience goes passive.

## Ambition Level

The goal is not "a nice slide deck." The goal is an experience that makes people ask for the source file. Push creative boundaries. If you've seen it in every presentation tool, it's not enough. Think:

- "What if the slide itself was the demo?"
- "What if the transition told part of the story?"
- "What if the audience could explore, not just watch?"
- "What has nobody done in a presentation before?"

The user came to this skill because they want something extraordinary. Deliver that.
