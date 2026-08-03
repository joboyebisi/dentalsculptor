---
name: Clinical Precision
colors:
  surface: '#faf8ff'
  surface-dim: '#d2d9f4'
  surface-bright: '#faf8ff'
  surface-container-lowest: '#ffffff'
  surface-container-low: '#f2f3ff'
  surface-container: '#eaedff'
  surface-container-high: '#e2e7ff'
  surface-container-highest: '#dae2fd'
  on-surface: '#131b2e'
  on-surface-variant: '#434652'
  inverse-surface: '#283044'
  inverse-on-surface: '#eef0ff'
  outline: '#747783'
  outline-variant: '#c4c6d3'
  surface-tint: '#365aaf'
  primary: '#00286a'
  on-primary: '#ffffff'
  primary-container: '#0f3d91'
  on-primary-container: '#8eadff'
  inverse-primary: '#b2c5ff'
  secondary: '#006b5f'
  on-secondary: '#ffffff'
  secondary-container: '#6df5e1'
  on-secondary-container: '#006f64'
  tertiary: '#3a0084'
  on-tertiary: '#ffffff'
  tertiary-container: '#5500bb'
  on-tertiary-container: '#be9fff'
  error: '#ba1a1a'
  on-error: '#ffffff'
  error-container: '#ffdad6'
  on-error-container: '#93000a'
  primary-fixed: '#dae2ff'
  primary-fixed-dim: '#b2c5ff'
  on-primary-fixed: '#001848'
  on-primary-fixed-variant: '#174296'
  secondary-fixed: '#71f8e4'
  secondary-fixed-dim: '#4fdbc8'
  on-secondary-fixed: '#00201c'
  on-secondary-fixed-variant: '#005048'
  tertiary-fixed: '#eaddff'
  tertiary-fixed-dim: '#d2bbff'
  on-tertiary-fixed: '#25005a'
  on-tertiary-fixed-variant: '#5a00c6'
  background: '#faf8ff'
  on-background: '#131b2e'
  surface-variant: '#dae2fd'
typography:
  display-lg:
    fontFamily: Inter
    fontSize: 48px
    fontWeight: '700'
    lineHeight: 56px
    letterSpacing: -0.02em
  headline-lg:
    fontFamily: Inter
    fontSize: 32px
    fontWeight: '600'
    lineHeight: 40px
    letterSpacing: -0.01em
  headline-md:
    fontFamily: Inter
    fontSize: 24px
    fontWeight: '600'
    lineHeight: 32px
  title-lg:
    fontFamily: Inter
    fontSize: 18px
    fontWeight: '600'
    lineHeight: 28px
  body-lg:
    fontFamily: Inter
    fontSize: 16px
    fontWeight: '400'
    lineHeight: 24px
  body-md:
    fontFamily: Inter
    fontSize: 14px
    fontWeight: '400'
    lineHeight: 20px
  label-md:
    fontFamily: JetBrains Mono
    fontSize: 12px
    fontWeight: '500'
    lineHeight: 16px
    letterSpacing: 0.05em
  label-sm:
    fontFamily: Inter
    fontSize: 11px
    fontWeight: '600'
    lineHeight: 14px
rounded:
  sm: 0.125rem
  DEFAULT: 0.25rem
  md: 0.375rem
  lg: 0.5rem
  xl: 0.75rem
  full: 9999px
spacing:
  base: 4px
  xs: 4px
  sm: 8px
  md: 16px
  lg: 24px
  xl: 40px
  gutter: 16px
  margin-page: 32px
  panel-width: 320px
---

## Brand & Style
The design system is engineered for a high-stakes medical and academic environment. It adopts a **Modern Corporate** aesthetic infused with **Minimalist** and **Glassmorphic** influences to mimic the precision of surgical tools and the clarity of scientific journals. 

The personality is authoritative yet assistive, prioritizing information density without sacrificing cognitive ease. To represent the "AI Co-Creation" principle, AI-driven elements utilize translucent layers and subtle motion, while standard research tools remain grounded in solid, structural forms. This visual distinction ensures the educator always perceives where their agency ends and machine assistance begins.

## Colors
The palette is rooted in medical reliability. The **Primary Medical Blue** is used for core navigation and critical actions. **Teal** serves as a secondary accent for health and biological indicators. 

Distinct functional zones are color-coded:
- **AI Functions (Purple):** Reserved for generative features, automated synthesis, and smart suggestions.
- **Research Features (Indigo):** Applied to data tracking, citations, and longitudinal studies.
- **Semantic Colors:** Success (Emerald), Warning (Amber), and Error (Rose) follow standard clinical alerting patterns.

Surface colors utilize a "Paper and Glass" approach: pure white for primary content cards and subtle slate for the background to reduce eye strain during long research sessions.

## Typography
This design system utilizes **Inter** for its exceptional legibility and neutral, professional tone. A high-contrast scale ensures that hierarchical relationships in complex medical data are immediately apparent.

For technical data, code snippets, or precise dental measurements, **JetBrains Mono** is introduced as a label font to provide a "computational" feel and improve character differentiation. All headings use tighter letter spacing to maintain a compact, "engineered" look suitable for desktop interfaces.

## Layout & Spacing
The layout follows a **structured multi-panel model** typical of professional IDEs (like Linear or Figma). 
- **Global Navigation:** A slim vertical rail (64px) for top-level context switching.
- **Sidebar:** A 280px–320px collapsible panel for resource trees and file navigation.
- **Stage:** The primary work area, utilizing a fluid grid with centered constraints for document reading.
- **Properties Panel:** A right-aligned 320px panel for contextual metadata and AI controls.

Spacing follows a strict 4px/8px baseline grid. Content should feel dense but breathing, achieved through generous external margins (32px) and tight internal gutters (16px).

## Elevation & Depth
Depth is used to signify the "stability" of information:
- **Level 0 (Background):** #F8FAFC. The foundation.
- **Level 1 (Cards/Panels):** Pure white with a 1px border (#E2E8F0). No shadow. This is for standard research data.
- **Level 2 (Floating/Active):** Subtle, highly diffused shadow (0px 4px 12px rgba(15, 23, 42, 0.05)). Used for active toolbars and property panels.
- **Level 3 (AI Overlays):** Uses a backdrop-filter (blur: 12px) with a semi-transparent purple-tinted background. This creates a "glassmorphic" effect that differentiates AI co-creation tools from static data.

## Shapes
The shape language is **Soft (0.25rem)**. This provides a clean, modern aesthetic that feels approachable while maintaining the precision of a medical instrument. 

- **Inputs and Buttons:** 4px (Soft) radius to keep the UI feeling structured.
- **Large Container Cards:** 8px (Large) radius.
- **Status Pills:** Fully rounded (pill-shaped) to distinguish them from interactive buttons.
- **Selection Highlights:** Sharp 2px radius for high-precision indications in data tables.

## Components

### Buttons & Controls
- **Primary:** Solid Medical Blue (#0F3D91) with white text. 4px radius.
- **AI Action:** Gradient border (Purple to Teal) or solid Purple (#7C3AED) with a subtle glow effect on hover.
- **Ghost:** No background, #475569 text, appearing only on hover to minimize visual noise in dense panels.

### Data-Rich Tables
- **Header:** #F8FAFC background, uppercase label-sm typography, 1px bottom border.
- **Row:** 40px height, subtle background shift on hover. High-contrast Primary Text for values.

### Property Panels
- Use "Accordion" groupings to manage high information density. 
- Labels are right-aligned or top-aligned in `label-sm` style to maximize space for input fields.

### AI Co-Creation Cards
- Featured with a thin #7C3AED left-accent border.
- Backgrounds use a very faint purple tint (98% lightness) to signify the content was synthesized by AI and requires educator verification.

### Toolbars
- Floating horizontal bars with 8px padding. 
- Icons are 20px, stroke-based (1.5px weight), ensuring they remain legible at small scales.