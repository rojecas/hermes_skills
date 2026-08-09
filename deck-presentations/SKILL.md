---
name: deck-presentations
description: "Use when building HTML decks with TTS voice narration."
version: 1.0.0
category: creative
---

# Deck Presentations

Build self-narrating HTML presentation decks with auto-advance and TTS audio.

## When to Use

- Building a new presentation deck from scratch
- Adding narration/voice to an existing deck
- Adjusting slides, layout, or audio for an existing deck
- User asks for "presentación", "deck", "slides", or "diapositivas"

## Architecture

A deck is a single self-contained HTML file with companion MP3 audio files, all in one folder. The HTML includes:
- CSS styles (brand colors, typography, responsive layout)
- Slide content as `<div class="slide">` elements
- Inline JavaScript for navigation and audio control
- Hidden `<audio>` elements referencing local MP3 files

## Quick Start

```bash
mkdir -p ~/deck-audio
# Generate audio with text_to_speech tool → ~/deck-audio/slideN.mp3
# Upload HTML + MP3s + logo to a single folder on the share
```

## Slide Patterns

### Pattern 1: Hero (centered, warm background)
Best for: portada, cierre, personal slides
```html
<div class="slide hero" data-slide="N">
  <div class="tag green">TAG</div>
  <div class="accent-bar"></div>
  <h2 style="text-align:center;">Title</h2>
  <p style="text-align:center; max-width:680px;">Content</p>
</div>
```

### Pattern 2: Person Slide
Best for: introducing team members. Emoji icon + name + role centered on top, then first-person message below, max-width 680px centered.

### Pattern 3: Grid Cards (grid-3)
Best for: features, phases, comparisons. Three `<div class="card">` with `card-icon` + `h3` + `p`.

### Pattern 4: Grid-2
Best for: comparisons, before/after. Two cards side by side.

### Pattern 5: Flow
Best for: processes, workflows. Uses `.flow` and `.flow-step` classes.

## Voice Narration

Generate with `text_to_speech` tool. Guidelines:
- Always first person
- Warm, conversational tone
- Consistent rhythm across all slides
- Correct Spanish accent marks (qué, dónde, cómo)
- Edge TTS is free, no API key, neutral Latin American voice
- Edge MP3s lack duration metadata — never rely on `audio.duration`

## Auto-Advance JavaScript

```javascript
function show(n) {
  clearTimeout(advanceTimer);
  var a = document.getElementById('audio' + slideNumber);
  if (a) {
    a.currentTime = 0;
    a.onended = function() {
      updateBtn(num);
      advanceTimer = setTimeout(function() {
        if (current < total - 1) { nextSlide(); }
      }, 2000);
    };
    a.play();
  }
}

function toggleAudio(n) {
  var a = document.getElementById('audio' + n);
  if (a.paused) {
    a.onended = function() { /* advance after 2s */ };
    a.play();
  } else {
    a.onended = null;
    a.pause();
    clearTimeout(advanceTimer);
  }
}
```

**Critical rules:**
1. Only use `onended` event — NEVER duration-based timers
2. Always `clearTimeout` before creating new timer
3. Always null `onended` when pausing
4. 2-second delay between slides
5. Last slide does NOT auto-advance

## Audio Button

```html
<button class="audio-btn" id="btnN" onclick="toggleAudio(N)" title="Escuchar">▶</button>
```

```css
.audio-btn {
  position: absolute; bottom: 20%; right: 10%;
  width: 48px; height: 48px; border-radius: 50%;
  border: 2px solid var(--green); background: var(--white);
  color: var(--green); font-size: 20px; cursor: pointer;
  z-index: 10; box-shadow: var(--shadow);
}
audio { display: none; }
```

## INASC Branding

```css
:root {
  --green: #00b33f; --green-dark: #009933; --green-soft: #e8f8ed;
  --bg: #eeeeee; --white: #ffffff; --text: #212529;
  --text-muted: #666666; --text-light: #999999;
}
body { font-family: 'Titillium Web', sans-serif; }
```

Logo source: PPTX `ppt/media/image2.png` → `logo.png`.

## File Organization

```
folder/
├── demo-andrew-deck.html
├── logo.png
├── slide0.mp3 ... slideN.mp3
```

## Pitfalls

- **Slide numbering**: HTML `data-slide` starts at 0, counter shows 1-based. Keep in sync.
- **MP3 metadata**: Edge TTS MP3s lack duration — don't use `audio.duration`.
- **Browser cache**: Ctrl+Shift+R after every HTML update.
- **Unicode in JS**: Use `innerHTML = '&#9654;'`, never literal ▶/⏸.
- **Slide insertion**: Renumber ALL subsequent comments and data-slide values.
- **No split layouts**: Prefer hero + grid for centered, symmetric design.
- **Privacy**: Don't include private user comments in public slides.
- **Consistent tone**: All narration = same person, same voice, same rhythm.

## Verification

1. Open HTML from share, counter shows correct total
2. ▶ plays audio, button becomes ⏸
3. Audio ends → advances after 2 seconds
4. ⏸ pauses → no advance, timer cleared
5. Keyboard arrows work
6. Browser console: no JS errors
