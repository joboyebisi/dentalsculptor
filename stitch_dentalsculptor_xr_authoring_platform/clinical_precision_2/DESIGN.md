---
name: Clinical Precision
colors:
  surface: '#fcf8f8'
  surface-dim: '#ddd9d9'
  surface-bright: '#fcf8f8'
  surface-container-lowest: '#ffffff'
  surface-container-low: '#f7f3f3'
  surface-container: '#f1eded'
  surface-container-high: '#ebe7e7'
  surface-container-highest: '#e5e2e2'
  on-surface: '#1c1b1c'
  on-surface-variant: '#46464b'
  inverse-surface: '#313030'
  inverse-on-surface: '#f4f0f0'
  outline: '#77767b'
  outline-variant: '#c7c6cb'
  surface-tint: '#F8F9FA'
  primary: '#000000'
  on-primary: '#ffffff'
  primary-container: '#1a1b20'
  on-primary-container: '#83838a'
  inverse-primary: '#c7c6cd'
  secondary: '#005ac1'
  on-secondary: '#ffffff'
  secondary-container: '#4d8efe'
  on-secondary-container: '#00285c'
  tertiary: '#000000'
  on-tertiary: '#ffffff'
  tertiary-container: '#211a14'
  on-tertiary-container: '#8c8279'
  error: '#ba1a1a'
  on-error: '#ffffff'
  error-container: '#ffdad6'
  on-error-container: '#93000a'
  primary-fixed: '#e3e2e9'
  primary-fixed-dim: '#c7c6cd'
  on-primary-fixed: '#1a1b20'
  on-primary-fixed-variant: '#46464c'
  secondary-fixed: '#d8e2ff'
  secondary-fixed-dim: '#adc6ff'
  on-secondary-fixed: '#001a41'
  on-secondary-fixed-variant: '#004494'
  tertiary-fixed: '#ede0d6'
  tertiary-fixed-dim: '#d0c4bb'
  on-tertiary-fixed: '#211a14'
  on-tertiary-fixed-variant: '#4d453e'
  background: '#fcf8f8'
  on-background: '#1c1b1c'
  surface-variant: '#e5e2e2'
  surface-background: '#FFFFFF'
  data-gray: '#404040'
  border-subtle: '#E2E4E9'
  clinical-blue-light: '#E8F0FE'
typography:
  headline-lg:
    fontFamily: Inter
    fontSize: 40px
    fontWeight: '700'
    lineHeight: 48px
    letterSpacing: -0.02em
  headline-lg-mobile:
    fontFamily: Inter
    fontSize: 32px
    fontWeight: '700'
    lineHeight: 40px
    letterSpacing: -0.02em
  headline-md:
    fontFamily: Inter
    fontSize: 24px
    fontWeight: '600'
    lineHeight: 32px
    letterSpacing: -0.01em
  body-lg:
    fontFamily: Inter
    fontSize: 18px
    fontWeight: '400'
    lineHeight: 28px
  body-md:
    fontFamily: Inter
    fontSize: 16px
    fontWeight: '400'
    lineHeight: 24px
  body-sm:
    fontFamily: Inter
    fontSize: 14px
    fontWeight: '400'
    lineHeight: 20px
  label-caps:
    fontFamily: Inter
    fontSize: 12px
    fontWeight: '600'
    lineHeight: 16px
    letterSpacing: 0.05em
  data-mono:
    fontFamily: JetBrains Mono
    fontSize: 14px
    fontWeight: '500'
    lineHeight: 20px
rounded:
  sm: 0.125rem
  DEFAULT: 0.25rem
  md: 0.375rem
  lg: 0.5rem
  xl: 0.75rem
  full: 9999px
spacing:
  unit: 4px
  gutter: 24px
  margin-sm: 16px
  margin-md: 32px
  margin-lg: 64px
  container-max: 1280px
---

## Brand & Style
The design system is engineered for the intersection of cutting-edge biotechnology and rigorous academic research. It evokes a "medical-grade" reliability—sterile but not cold, futuristic but grounded in institutional authority. 

The aesthetic is **Modern Corporate** with a heavy emphasis on **High-Contrast Minimalism**. It utilizes stark whites and deep navies to create a laboratory-clear information hierarchy. Visual clutter is eliminated in favor of precise alignment and "breathable" negative space, suggesting an environment where data integrity and clarity are paramount. The emotional response should be one of absolute confidence, safety, and technological sophistication.

## Colors
This palette is anchored by a deep "Midnight Navy" (`#191A1F`) used for primary text and structural elements, contrasted against a "Bright Sterile White" (`#FFFFFF`) background. 

- **Primary:** The dark navy provides an authoritative, academic weight.
- **Secondary:** A vibrant "Google Blue" (`#4285F4`) is used sparingly for interactive cues, primary actions, and progress indicators.
- **Neutrals:** Medium grays are reserved for supporting data and secondary metadata. 
- **Functional Tinting:** Soft blue washes (`#E8F0FE`) are used to highlight selected states or grouped medical data without breaking the high-contrast aesthetic.

## Typography
The typography utilizes **Inter** for its exceptional legibility and neutral, modern character. Headlines are bold and tightly tracked to command attention, while body text maintains generous leading for long-form research reading.

A secondary font, **JetBrains Mono**, is introduced for technical data strings, specimen IDs, and laboratory values. This creates a clear visual distinction between "human narrative" and "technical data." High contrast (Navy on White) must be maintained at all times to meet AAA accessibility standards for medical software.

## Layout & Spacing
The layout follows a **Rigid Grid System** based on a 4px baseline unit. This "Clinical Precision" approach ensures that every element feels intentionally placed.

- **Desktop:** A 12-column fixed grid (1280px max-width) centered on the screen.
- **Tablet:** 8-column fluid grid with 32px margins.
- **Mobile:** 4-column fluid grid with 16px margins.

Spacing should be used to group related medical observations. Use generous vertical margins (`margin-lg`) between major sections to prevent cognitive overload, but tight, precise internal padding (`unit` x 4) within data cards to maintain a high information density where necessary.

## Elevation & Depth
To maintain a "medical-grade" flat aesthetic, depth is achieved through **Tonal Layers** and **Precise Outlines** rather than heavy shadows.

- **Surface Levels:** The primary background is White. Secondary containers (sidebars, data panels) use a very subtle light gray or blue-tinted wash.
- **Outlines:** Use 1px solid borders (`#E2E4E9`) to define containers. This mimics the look of printed charts and technical diagrams.
- **Focused Elevation:** Only use shadows for temporary overlay elements like tooltips or dropdowns. These shadows must be "Ambient"—very low opacity (5-10%), large blur (16px), and zero offset to feel like a soft glow rather than a traditional drop shadow.

## Shapes
This design system uses a **Soft (4px)** roundedness. This small radius is critical: it is enough to make the UI feel modern and approachable, but sharp enough to retain a serious, scientific, and architectural rigor. 

Avoid "Pill" shapes entirely, except for status indicators (chips) that need to stand out from the rigid rectangular grid of data. Large containers like cards should strictly follow the `rounded-lg` (8px) rule.

## Components

- **Buttons:** Primary buttons are solid `#191A1F` with White text. Secondary buttons are outlined with 1px `#191A1F`. Hover states should involve a subtle shift to `#4285F4` to signal interactivity.
- **Input Fields:** Use 1px `#E2E4E9` borders. On focus, the border transitions to 2px `#4285F4`. Labels should always be visible above the field in `label-caps` style.
- **Cards:** White background with a 1px `#E2E4E9` border. No shadow. Headers within cards should have a subtle bottom border to separate metadata from content.
- **Chips/Status:** Use low-saturation background tints (e.g., light green for 'Stable', light red for 'Critical') with high-contrast dark text.
- **Data Tables:** Row-based layouts with subtle `1px` horizontal dividers. No vertical dividers. Header rows should be styled in `label-caps` with a light gray background wash.
- **Progress Bars:** Use the secondary blue (`#4285F4`) against a light blue track. The edges must be sharp (0px) or minimally rounded (2px) to match the technical aesthetic.