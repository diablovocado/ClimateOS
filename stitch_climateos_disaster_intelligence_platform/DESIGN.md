---
name: Tactical Climate Intelligence
colors:
  surface: '#0f131d'
  surface-dim: '#0f131d'
  surface-bright: '#353944'
  surface-container-lowest: '#0a0e17'
  surface-container-low: '#171c25'
  surface-container: '#1b2029'
  surface-container-high: '#262a34'
  surface-container-highest: '#31353f'
  on-surface: '#dfe2f0'
  on-surface-variant: '#bcc9cd'
  inverse-surface: '#dfe2f0'
  inverse-on-surface: '#2c303b'
  outline: '#869397'
  outline-variant: '#3d494c'
  surface-tint: '#4cd7f6'
  primary: '#4cd7f6'
  on-primary: '#003640'
  primary-container: '#06b6d4'
  on-primary-container: '#00424f'
  inverse-primary: '#00687a'
  secondary: '#b4c5ff'
  on-secondary: '#002a78'
  secondary-container: '#0053db'
  on-secondary-container: '#cdd7ff'
  tertiary: '#ffb690'
  on-tertiary: '#552100'
  tertiary-container: '#ff853c'
  on-tertiary-container: '#672a00'
  error: '#ffb4ab'
  on-error: '#690005'
  error-container: '#93000a'
  on-error-container: '#ffdad6'
  primary-fixed: '#acedff'
  primary-fixed-dim: '#4cd7f6'
  on-primary-fixed: '#001f26'
  on-primary-fixed-variant: '#004e5c'
  secondary-fixed: '#dbe1ff'
  secondary-fixed-dim: '#b4c5ff'
  on-secondary-fixed: '#00174b'
  on-secondary-fixed-variant: '#003ea8'
  tertiary-fixed: '#ffdbca'
  tertiary-fixed-dim: '#ffb690'
  on-tertiary-fixed: '#341100'
  on-tertiary-fixed-variant: '#783200'
  background: '#0f131d'
  on-background: '#dfe2f0'
  surface-variant: '#31353f'
typography:
  display-hero:
    fontFamily: Outfit
    fontSize: 48px
    fontWeight: '700'
    lineHeight: 56px
    letterSpacing: -0.02em
  display-hero-mobile:
    fontFamily: Outfit
    fontSize: 32px
    fontWeight: '700'
    lineHeight: 40px
    letterSpacing: -0.01em
  headline-lg:
    fontFamily: Outfit
    fontSize: 32px
    fontWeight: '600'
    lineHeight: 40px
    letterSpacing: -0.015em
  headline-lg-mobile:
    fontFamily: Outfit
    fontSize: 24px
    fontWeight: '600'
    lineHeight: 32px
    letterSpacing: -0.01em
  headline-md:
    fontFamily: Outfit
    fontSize: 24px
    fontWeight: '600'
    lineHeight: 32px
    letterSpacing: -0.01em
  headline-sm:
    fontFamily: Outfit
    fontSize: 18px
    fontWeight: '600'
    lineHeight: 26px
    letterSpacing: 0em
  body-lg:
    fontFamily: Inter
    fontSize: 16px
    fontWeight: '400'
    lineHeight: 24px
    letterSpacing: -0.01em
  body-md:
    fontFamily: Inter
    fontSize: 14px
    fontWeight: '400'
    lineHeight: 20px
    letterSpacing: 0em
  body-sm:
    fontFamily: Inter
    fontSize: 12px
    fontWeight: '400'
    lineHeight: 18px
    letterSpacing: 0.01em
  label-lg:
    fontFamily: JetBrains Mono
    fontSize: 14px
    fontWeight: '600'
    lineHeight: 20px
    letterSpacing: 0.02em
  label-md:
    fontFamily: JetBrains Mono
    fontSize: 12px
    fontWeight: '500'
    lineHeight: 16px
    letterSpacing: 0.04em
  label-sm:
    fontFamily: JetBrains Mono
    fontSize: 10px
    fontWeight: '500'
    lineHeight: 14px
    letterSpacing: 0.06em
rounded:
  sm: 0.125rem
  DEFAULT: 0.25rem
  md: 0.375rem
  lg: 0.5rem
  xl: 0.75rem
  full: 9999px
spacing:
  gutter: 1rem
  gutter-tablet: 0.75rem
  gutter-mobile: 0.5rem
  margin: 1.5rem
  margin-mobile: 0.75rem
  space-xs: 0.25rem
  space-sm: 0.5rem
  space-md: 1rem
  space-lg: 1.5rem
  space-xl: 2.5rem
---

## Brand & Style

This design system establishes a high-stakes, mission-critical operational atmosphere built for operators, analysts, and emergency incident commanders. The design style combines dark tactical glassmorphism with high-density data instrumentation inspired by aerospace head-up displays and high-precision developer software. 

Visual principles prioritize instant situational awareness, low-latency comprehension, and high emotional composure during crisis events. The interface relies on an obsidian void canvas, precise optical borders, luminous status telemetry, and semi-translucent operational surfaces that preserve geographic and satellite map context beneath active command overlays.

## Colors

The palette is tuned specifically for pitch-black command environments, mobile disaster deployment, and WCAG AAA readability against dark void grounds.

### Foundation & Surfaces
- **Canvas Base (`#070B14`):** Deep Obsidian void; prevents eye fatigue while providing total contrast for active telemetry.
- **Card Surface (`#0D1526`):** Frosted tactical midnight; layered at 75–85% opacity with backdrop blur.
- **Surface Highlight Border (`rgba(255, 255, 255, 0.08)`):** Micro-etched boundary edge line across all panels.

### Brand & Accents
- **Primary Cyber Cyan (`#06B6D4`):** High-energy beacon used for interactive focal states, radar rings, selected nodes, and real-time synchronization pulses.
- **Tactical Cobalt (`#2563EB`):** Mission control system framing, deep structural hierarchy, and structural actions.

### Incident Severity Tier (WCAG AAA Calibrated)
- **Critical / Threat Alpha (`#EF4444`):** Wildfire fronts, flash inundation, structural failure.
- **Warning / Tier 2 (`#F97316`):** Rapid escalation, uncontained perimeter, extreme thermal risk.
- **Advisory / Tier 1 (`#F59E0B`):** Environmental anomaly, air quality deterioration, wind shear.
- **Nominal / Clear (`#22C55E`):** Evacuation corridor clear, stable telemetry, contained sector.

## Typography

The typographical architecture operates on three distinct functional planes:

1. **Strategic & High-Impact (Outfit):** Delivers instantaneous visual comprehension for major metric counters, risk indices, incident titles, and dashboard widget headers.
2. **Contextual Narrative & Reports (Inter):** Handles dense textual incident feeds, standard operating procedure documents, and collaborative command communications with balanced line heights.
3. **Telemetry & Sensor Data (JetBrains Mono):** Reserved for raw physical and geospatial instrumentation: GPS coordinates (MGRS/lat-long), barometric pressure, wind vectors, timestamps (UTC/Zulu), sensor packet hashes, and AI model confidence scores. Monospaced character alignment guarantees tabular stability during live numeric updates.

## Layout & Spacing

The layout is built upon a 12-column dynamic fluid tactical grid with a strict 4px base increment. The interface optimizes screen real estate for maximum situational awareness.

- **Desktop (1440px+):** Tri-panel architecture with a persistent telemetry rail (320px fixed), a fluid center GIS command canvas, and a collapsible tactical operations panel (380px fixed). Gutters sit at `1rem`, outer margins at `1.5rem`.
- **Tablet (768px - 1439px):** Split HUD with sliding drawer sheets for incident streams. Gutters reduce to `0.75rem`.
- **Mobile (<768px):** Single-column stacked stack. Persistent bottom-docked emergency thumb action bar (64px) with snap-sheet telemetry panels. Outer margins drop to `0.75rem` to maximize spatial map rendering.

## Elevation & Depth

Visual hierarchy uses a dark glassmorphic stack that retains situational geospatial map visibility underneath active HUD overlays.

- **Level 0 (Map & Spatial Basemap):** Deep obsidian vector or satellite layer at canvas foundation `#070B14`.
- **Level 1 (Docked Consoles & System Panels):** Card background `#0D1526` at 85% opacity, `backdrop-filter: blur(16px)`, surrounded by a 1px uniform outer keyline of `rgba(255, 255, 255, 0.08)`. Minimal ambient shadow: `0 8px 32px rgba(0, 0, 0, 0.6)`.
- **Level 2 (Popovers, Focus Drawers & Tactical Flyouts):** Surface `#121D33` at 90% opacity, `backdrop-filter: blur(24px)`, bordered with `rgba(6, 182, 212, 0.25)`. Elevation shadow: `0 16px 48px rgba(0, 0, 0, 0.8)`.
- **Level 3 (Modal Emergency Alerts & Action Intercepts):** Surface `#161F30` at 96% opacity, high-contrast glow perimeter matched to incident severity (e.g., `0 0 24px rgba(239, 68, 68, 0.35)` for Level Alpha warnings).

## Shapes

The design system enforces a precision-machined shape language using compact corner geometry (`roundedness: 1`). 

- Default interactive elements, cards, and input fields use `0.25rem` (4px) radii to evoke tactical avionics hardware.
- Structural floating panels and tactical command sheets scale to `0.5rem` (`rounded-lg`, 8px).
- Specialized sensor indicators, telemetry badges, and live pulse dots utilize rounded circular geometry to denote continuous scanning status.

## Components

### Buttons & Operational Triggers
- **Primary Tactical:** Solid Electric Cyber Cyan background (`#06B6D4`), dark obsidian text (`#070B14`), font `JetBrains Mono` weight 600, uppercase letter-spaced. Hover state introduces a luminous outer bloom: `box-shadow: 0 0 16px rgba(6, 182, 212, 0.45)`.
- **Secondary System:** Transparent midnight fill with 1px border `rgba(255, 255, 255, 0.12)`, text in off-white (`#F8FAFC`). Hover transitions border to Tactical Cobalt (`#2563EB`) with subtle cyan edge illumination.
- **Emergency Action Trigger:** Solid Crimson (`#EF4444`) with white typography, accompanied by an animated ambient beacon halo for active incident declaration.

### Cards & Tactical Panels
- Engineered with `#0D1526` glass surfaces, 12px padding, and 1px borders of `rgba(255, 255, 255, 0.08)`.
- Card headers feature an upper status rail housing monospaced node identifiers (e.g., `SYS_NODE // 09A`) along with real-time signal latency badges.

### Chips & Severity Status Indicators
- Structured with `JetBrains Mono` at 10px uppercase, `0.25rem` corner radius, internal padding `2px 8px`.
- Configured in pill or micro-rectangular frames with a subtle 10% translucent background fill and a solid 1px saturated border matched to the severity level (Emerald, Amber, Flare Orange, or Crimson).

### Telemetry Inputs & Parameter Controls
- Background fill `#090E1A` with a recessed inner inset line.
- Inactive border `rgba(255, 255, 255, 0.1)`. Focus state illuminates with a 1px Electric Cyan boundary and zero-offset ring `0 0 0 1px #06B6D4`.
- Text input utilizes `JetBrains Mono` for precise character tracking.

### Specialized Tactical Modules
- **Incident Scanners:** Real-time waveform telemetry graphs accompanied by live timestamp readouts.
- **Geo-Target Crosshairs:** Vector-rendered reticles showcasing real-time coordinate changes with confidence ratings rendered in Cyber Cyan.