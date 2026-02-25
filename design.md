# Data Derby — Design System & UI Blueprint
### Premier League Match Prediction App

> Mobile-first · Data-driven · Professional analytics  
> A complete specification for frontend engineering handoff.

---

## Table of Contents

1. [Product Positioning](#1-product-positioning)
2. [Color System](#2-color-system)
3. [Typography System](#3-typography-system)
4. [Spacing & Layout System](#4-spacing--layout-system)
5. [Core Components](#5-core-components)
6. [Prediction Visualisation Strategy](#6-prediction-visualisation-strategy)
7. [Screen Structure](#7-screen-structure)
8. [Design Constraints](#8-design-constraints)

---

## 1. Product Positioning

### Target Audience
Premier League enthusiasts aged 18–40 who are passionate about football analytics — casual fans seeking quick match previews, data-savvy supporters who enjoy statistical deep-dives, and fantasy football players who want analytical backup for their decisions. Deliberately positioned away from gambling products.

### Visual Tone

| Category | Descriptor |
|---|---|
| Primary Aesthetic | Modern Sports Analytics — premium dark-mode with vibrant data accents |
| Design Vocabulary | Clean, bold typography; confident data visualisations; structured card layouts |
| Colour Character | Deep navy backgrounds with electric blue primary and emerald green success states |
| Motion Language | Purposeful micro-animations for data loading; no decorative motion |
| Imagery Style | Minimal — data is the visual hero; crests and avatars used sparingly |

### Emotional Feel
Confident without arrogance. Premium and analytical — like using a professional sports intelligence tool, not a betting app. Every design decision should reinforce the feeling that the user is accessing expert-grade insight: **intelligent, fast, and trustworthy**.

---

## 2. Color System

> Palette derived from the GoalGalaxy reference designs. Deep space navy as foundation — dark enough to make data visualisations pop while maintaining premium readability.

| Token | Hex | Usage |
|---|---|---|
| `--color-bg` | `#0c0f29` | Page/app background — the darkest layer |
| `--color-surface` | `#121845` | Card backgrounds, modals, panels |
| `--color-surface-elevated` | `#1a2260` | Hover states, tooltips, chip backgrounds |
| `--color-primary` | `#097aff` | CTAs, active states, links, selected filters |
| `--color-accent-green` | `#00D68F` | Win probability, positive trends, success states |
| `--color-accent-amber` | `#F5A623` | Draw outcomes, neutral/caution, yellow card indicators |
| `--color-error` | `#FF3B5C` | Loss probability, error alerts, form validation failures |
| `--color-text-primary` | `#ffffff` | Headings, primary data values, player names |
| `--color-text-secondary` | `#8891B8` | Labels, supporting copy, metadata |
| `--color-border` | `#1e2a6e` | Card borders, dividers, input outlines (default) |
| `--color-border-active` | `#097aff` | Focused inputs, selected components, active cards |

### Why This Palette Works
Dark backgrounds (`#0c0f29` / `#121845`) dramatically increase the perceived brightness of probability bars and score displays — making data feel alive. The navy family creates clear depth layers (BG → Surface → Elevated) without shadows alone. Blue and green as primary data colours align with Premier League visual culture while remaining distinct from betting-product reds and golds.

---

## 3. Typography System

### Font Family
**Primary:** `Inter` (Google Fonts)  
Fallback: `-apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif`

Inter is chosen for its exceptional legibility at small sizes, its tabular number variant (`Inter Var`) which prevents layout shift when probability numbers update, and its modern geometric character.

> ⚠️ Use `font-variant-numeric: tabular-nums` on **all** probability percentages and xG values.

### Type Scale

| Token | Size / Weight | Usage |
|---|---|---|
| Display / Hero | `48px / 700` | Primary probability %, match score headline |
| H1 — Screen Title | `24px / 700` | Screen-level headings ("Match Prediction") |
| H2 — Section Title | `20px / 600` | Card headings, section labels |
| H3 — Sub-section | `17px / 600` | Field labels, team names, stat headers |
| Body Large | `15px / 400` | Primary descriptive copy, match context |
| Body Default | `14px / 400` | Most body text, list items, input values |
| Body Small / Caption | `12px / 400` | Supporting metadata, timestamps, footnotes |
| Label / Overline | `11px / 600` | All-caps category labels, chip text |
| Mono Numeric | `28–48px / 700` | xG display, probability % — uses `tabular-nums` |

### Hierarchy Logic
The scale follows a 1.25 modular ratio anchored at 14px body. Numbers that carry prediction data (xG, win %) are treated as display elements — given the highest visual weight. Line height is `1.5×` for body text, `1.2×` for headings and numerics.

---

## 4. Spacing & Layout System

### Base Unit: 8px Grid
All spacing, padding, margin, and component sizing uses multiples of 8px.

```
--space-1:  4px   Micro gap (icon + label)
--space-2:  8px   Compact padding, chip inner padding
--space-3:  12px  Close element relationships
--space-4:  16px  Default component padding
--space-5:  20px  Standard section padding
--space-6:  24px  Card padding (default)
--space-8:  32px  Section spacing between content blocks
--space-10: 40px  Screen-level vertical padding (safe area)
--space-12: 48px  Separation between distinct sections
```

### Card System

| Property | Value |
|---|---|
| Card Padding | `20px` horizontal / `20px` vertical |
| Card Background | `#121845` |
| Card Border | `1px solid #1e2a6e` |
| Card Border Radius | `16px` |
| Card Shadow | `0 4px 24px rgba(0,0,0,0.32)` |
| Card Max Width | `420px` mobile / `560px` tablet |

### Border Radius System

```
--radius-sm:   8px     Chips, tags, small badges
--radius-md:   12px    Input fields, dropdowns, secondary cards
--radius-lg:   16px    Primary cards, prediction result panels
--radius-xl:   24px    Bottom sheet panels, modal overlays
--radius-full: 9999px  Pills, toggle buttons, avatar frames
```

### Layout Grid
- **Mobile:** Single-column, `16px` horizontal margins, full-bleed cards, max-width `420px`
- **Tablet (768px+):** Two-column optional for team selector side-by-side
- **Desktop (1024px+):** Centered container max-width `960px` with optional sidebar

---

## 5. Core Components

### 5.1 Team Selector

| Property | Spec |
|---|---|
| Purpose | Select a Home team and Away team from Premier League clubs |
| Layout | Two selector cards side-by-side with centred "VS" divider. Each card: Club Crest (48×48px, `border-radius: 50%`) + Club Name (H3) + optional League Position badge |
| Default State | Placeholder text "Select Team", dashed border (`#1e2a6e`), empty crest slot with football icon |
| Selected State | Background → `#1a2260`. Border → solid `#097aff` (2px). Blue glow: `box-shadow: 0 0 0 3px rgba(9,122,255,0.25)` |
| Hover | Shadow deepens, border brightens to `#097aff` at 60% opacity. `cursor: pointer` |
| Disabled | Opacity `0.45`, `cursor: not-allowed`, no hover effect |
| Dropdown | Full-screen bottom sheet on mobile. Search input + scrollable list of 20 clubs. List item height: `56px` |
| Validation | If same team selected for both — Away selector auto-clears with inline error: *"Away team cannot match home team"*. Predict button stays disabled |

---

### 5.2 Predict Button

| Property | Spec |
|---|---|
| Purpose | Primary CTA — triggers prediction API call and reveals result card |
| Layout | Full-width pill (`border-radius: 9999px`), height `56px`. Left icon: ⚡. Label: "Generate Prediction" (Body Large, Bold, white) |
| Default | Background: `#097aff`. Shadow: `0 8px 20px rgba(9,122,255,0.4)` |
| Hover | Background lightens 8% → `#2d8fff`. Shadow intensifies. `transform: scale(1.02)` |
| Disabled | Background: `#1e2a6e`. Text: `#4a5280`. No shadow. `cursor: not-allowed`. Opacity: `0.6` |
| Loading | Spinner replaces label (24px, white). Width locked. Not interactable |
| Active / Press | `transform: scale(0.97)`. Shadow collapses |
| Success | Button fades out → result card fades/slides in from below |

---

### 5.3 Prediction Result Card

| Property | Spec |
|---|---|
| Purpose | Displays win/draw/loss probabilities, expected goals (xG), and predicted outcome |
| Layout | Full-width card (`radius-lg`), `24px` padding. Sections: Match Header → xG Row → Probability Bars → Outcome Badge → Confidence Footer |
| Match Header | Home crest + name (left) · "vs" centred in `14px / #8891B8` · Away crest + name (right) |
| xG Row | Three columns: Home xG (large mono, left) · "xG" label (small caps, centre) · Away xG (large mono, right). Values animate `0 → final` via `easeOutCubic` (600ms) |
| Outcome Badge | Centred pill badge. Colour = outcome type (green/amber/blue). E.g. *"PREDICTED: HOME WIN — 68%"* in SemiBold |
| Confidence Footer | `12px` grey text: *"Based on last 10 matches · Powered by GoalGalaxy Analytics"*. Divider above |
| Entry Animation | Slides up `20px` + fades in over `350ms` (`easeOutQuint`) after loading completes |

---

### 5.4 Probability Bar

| Property | Spec |
|---|---|
| Purpose | Visualises % likelihood of Home Win, Draw, and Away Win |
| Layout | Each bar: Label (left, `80px` fixed) → Track → Percentage (right, `48px` fixed). Row height: `40px`. 3 rows with `12px` gap |
| Track | Background: `#1e2a6e`. Height: `10px`. `border-radius: 9999px` |
| Home Win Fill | `#00D68F` (Emerald) |
| Draw Fill | `#F5A623` (Amber) |
| Away Win Fill | `#097aff` (Blue) |
| Dominant Emphasis | Highest bar: full opacity, Bold label + value. Other bars: `opacity: 0.6`, secondary text colour |
| Animation | Width `0% → final` over `800ms`, staggered `0ms / 150ms / 300ms` delay, `easeOutExpo`. Counter increments in sync |
| Accessibility | `role="progressbar"`, `aria-valuenow`, `aria-label="Home win probability: 68%"` |

---

### 5.5 Loading State

| Property | Spec |
|---|---|
| Purpose | Communicates prediction is being computed. Maintains layout stability |
| Approach | Skeleton screens matching exact layout of the Prediction Result Card |
| Skeleton Shapes | Crest placeholders: `48×48px` rounded. Text bars: various widths, `10–14px` tall, `border-radius: 6px` |
| Shimmer | Gradient sweeps left-to-right: `#1e2a6e → #2a3580 → #1e2a6e`. Duration: `1.5s` infinite |
| Label | *"Analysing match data..."* in Body Small / `#8891B8`. Animated ellipsis |
| Timeout | After `8s` → *"This is taking longer than expected..."* + Cancel option |

---

### 5.6 Error Alert

| Property | Spec |
|---|---|
| Purpose | Communicates API failures, network errors, or validation issues |
| Layout | Full-width card, `16px` radius. Left border accent: `4px solid #FF3B5C`. `16px` padding. Icon + title + message + Retry button |
| Icon | Exclamation circle, `24px`, `#FF3B5C` |
| Title | *"Unable to generate prediction"* — Body Large, Bold, white |
| Default Message | *"We couldn't reach the prediction engine. Please check your connection and try again."* |
| Retry Button | Secondary outlined: `1px border #097aff`, text Primary Blue, transparent background |
| Inline Validation | Small `#FF3B5C` text directly below the relevant selector (does not replace full card) |
| Entry Animation | Horizontal shake: `3px × 2` over `150ms` on mount |

---

## 6. Prediction Visualisation Strategy

### Expected Goals (xG)
Display as large mono-numeric values — minimum `40px`, ideally `48px` — using `font-variant-numeric: tabular-nums`. Home xG left-aligned, Away xG right-aligned, flanking a centred "xG" label in small caps. The higher value receives a subtle emerald underline. Values animate from `0.00` to final using `easeOutCubic` over `600ms`.

### Probability Bars
The dominant outcome bar renders at full colour intensity with bold label and value text. The other two bars are visually de-emphasised (`opacity: 0.6`). All three bars animate simultaneously with a `150ms` stagger from `0 → final` width using `easeOutExpo` — creating a satisfying data-reveal moment.

> ⚠️ The sum of all three values must always display as `100%`. Apply rounding correction to the smallest bar to prevent float-point percentage drift.

### Outcome Emphasis
After bars settle, the predicted outcome badge appears with a `200ms` delay. It is the most visually dominant element in the result card. Visual hierarchy: **Bars → Badge → xG Detail** — mirroring how an expert analyst would read the data.

### Animation Philosophy
Animations serve data comprehension, not decoration.

| Animation | Purpose |
|---|---|
| Skeleton shimmer | Manages expectation during load |
| Bar fill | Creates a data-reveal narrative |
| xG counter | Simulates computation |
| Card entry (slide + fade) | Maintains spatial orientation |

All animations complete within `800ms`. Once data is displayed, the interface is fully static and readable. All animations must be disabled via `@media (prefers-reduced-motion: reduce)`.

---

## 7. Screen Structure

### Main Prediction Screen — Top → Bottom

```
┌─────────────────────────────────────────┐
│  App Bar                                │  h: 56px
│  Logo (left) · Title (centre) · Avatar  │
├─────────────────────────────────────────┤
│  ↕ 32px (--space-8)                     │
├─────────────────────────────────────────┤
│  Screen Title                           │
│  H1: "Match Predictor"                  │
│  Subtitle: supporting copy              │
├─────────────────────────────────────────┤
│  ↕ 16px (--space-4)                     │
├─────────────────────────────────────────┤
│  League Filter  (optional)              │  h: 36px chips, horizontal scroll
│  [ Premier League ]  Championship  ...  │
├─────────────────────────────────────────┤
│  ↕ 16px (--space-4)                     │
├─────────────────────────────────────────┤
│  Team Selector Module                   │  h: ~120px
│  ┌──────────┐  VS  ┌──────────┐         │
│  │ Home     │      │ Away     │         │
│  └──────────┘      └──────────┘         │
├─────────────────────────────────────────┤
│  ↕ 20px (--space-5)                     │
├─────────────────────────────────────────┤
│  Match Context Row  (when both selected)│  h: auto
│  Venue pill · Date · H2H mini-stat      │
├─────────────────────────────────────────┤
│  ↕ 24px (--space-6)                     │
├─────────────────────────────────────────┤
│  ⚡ Generate Prediction                 │  h: 56px, full-width pill
├─────────────────────────────────────────┤
│  ↕ 32px (--space-8)  ← Input/Output gap │
├─────────────────────────────────────────┤
│  Prediction Result Card                 │  slides in on generate
│  ┌─────────────────────────────────┐    │
│  │ Home ⚽  vs  ⚽ Away            │    │
│  │                                 │    │
│  │  2.1 xG          1.4 xG         │    │
│  │                                 │    │
│  │ Home Win  ████████░░░░  68%     │    │
│  │ Draw      ████░░░░░░░░  22%     │    │
│  │ Away Win  ██░░░░░░░░░░  10%     │    │
│  │                                 │    │
│  │   [ PREDICTED: HOME WIN 68% ]   │    │
│  │ ─────────────────────────────── │    │
│  │ Based on last 10 matches        │    │
│  └─────────────────────────────────┘    │
├─────────────────────────────────────────┤
│  ↕ 24px (--space-6)                     │
├─────────────────────────────────────────┤
│  Extended Stats Accordion  (optional)   │  collapsed by default
│  ▶ More Statistics                      │
├─────────────────────────────────────────┤
│  ↕ 40px (--space-10)  ← safe area       │
├─────────────────────────────────────────┤
│  Bottom Tab Bar  (if applicable)        │  h: 64px + safe area inset
│  Predict · My Team · Leaderboard · ⚙️   │
└─────────────────────────────────────────┘
```

### Alignment Logic
All content is **left-aligned** except the VS divider (centred) and the Outcome Badge (centred). Safe area insets respected via `env(safe-area-inset-*)`. The result card slides up from below, keeping team selectors visible above the fold for quick re-selection.

---

## 8. Design Constraints

### Hard Rules

| Constraint | Specification |
|---|---|
| **Mobile-First** | Designed for `375px` minimum. Primary target: `390px` (iPhone 14). Progressive enhancement at `768px` and `1024px` |
| **No Gambling Aesthetics** | No odds formatting (e.g. `3/1`), no green felt, no bet-slip patterns, no currency on predictions. Percentages and xG only. Avoid red/gold combinations |
| **Data First** | Every element that doesn't directly support data comprehension must justify its presence. No hero images or decorative illustrations in the prediction flow |
| **Accessibility** | WCAG AA minimum: `4.5:1` contrast for body text, `3:1` for large text. All interactive elements: visible focus state (`outline: 2px solid #097aff, offset: 3px`) |
| **Performance** | Skeleton loaders prevent CLS. Team crests as SVG wherever possible. No GIF animations. Inter preloaded via `<link rel="preload">` |
| **Tabular Numerics** | `font-variant-numeric: tabular-nums` on all numeric elements. Inter must load before numbers display |
| **Touch Targets** | Minimum `44×44px` for all interactive elements (Apple HIG / WCAG 2.5.5) |
| **Colour Independence** | All outcomes communicated by colour AND text/icon. Colour-blind users must be able to distinguish outcomes |
| **Dark Mode Only** | Single-mode dark theme. Simplifies implementation and maintains premium aesthetic consistently |

### Engineering Handoff Checklist

- [ ] All spacing values mapped to CSS custom properties (`--space-1` through `--space-12`)
- [ ] All colours as CSS custom properties on `:root`
- [ ] Animation durations as CSS custom properties (`--duration-fast: 200ms`, `--duration-normal: 350ms`, `--duration-slow: 600ms`)
- [ ] Implement `@media (prefers-reduced-motion: reduce)` to disable all transitions
- [ ] Inter loaded via Google Fonts with `display: swap` — fallback to `system-ui`
- [ ] Probability values must always sum to exactly `100%` — apply rounding correction to smallest value
- [ ] Team selector dropdown supports keyboard navigation (arrow keys, Enter, Escape)
- [ ] Prediction result card announced via `aria-live: polite` when it appears
- [ ] All interactive elements have `:focus-visible` styles distinct from `:hover`
- [ ] `env(safe-area-inset-*)` applied to bottom navigation and screen padding

---

*premier leauge predictor Design System v1.0 — For frontend engineering handoff*