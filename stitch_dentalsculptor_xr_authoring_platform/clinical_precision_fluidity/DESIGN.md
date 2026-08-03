---
name: Clinical Precision & Fluidity
colors:
  surface: '#f7f9fb'
  surface-dim: '#d8dadc'
  surface-bright: '#f7f9fb'
  surface-container-lowest: '#ffffff'
  surface-container-low: '#f2f4f6'
  surface-container: '#eceef0'
  surface-container-high: '#e6e8ea'
  surface-container-highest: '#e0e3e5'
  on-surface: '#191c1e'
  on-surface-variant: '#434652'
  inverse-surface: '#2d3133'
  inverse-on-surface: '#eff1f3'
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
  tertiary: '#511b00'
  on-tertiary: '#ffffff'
  tertiary-container: '#752a00'
  on-tertiary-container: '#fe9261'
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
  tertiary-fixed: '#ffdbcd'
  tertiary-fixed-dim: '#ffb596'
  on-tertiary-fixed: '#360f00'
  on-tertiary-fixed-variant: '#7b2f04'
  background: '#f7f9fb'
  on-background: '#191c1e'
  surface-variant: '#e0e3e5'
  ai-purple: '#7C3AED'
  research-indigo: '#4F46E5'
  border-subtle: '#E2E8F0'
  panel-bg: '#FFFFFF'
  text-main: '#0F172A'
typography:
  display-lg:
    fontFamily: Inter
    fontSize: 32px
    fontWeight: '600'
    lineHeight: 40px
    letterSpacing: -0.02em
  headline-md:
    fontFamily: Inter
    fontSize: 20px
    fontWeight: '600'
    lineHeight: 28px
  body-md:
    fontFamily: Inter
    fontSize: 14px
    fontWeight: '400'
    lineHeight: 20px
  label-mono:
    fontFamily: JetBrains Mono
    fontSize: 12px
    fontWeight: '500'
    lineHeight: 16px
    letterSpacing: 0.05em
  label-caps:
    fontFamily: Inter
    fontSize: 11px
    fontWeight: '700'
    lineHeight: 12px
    letterSpacing: 0.08em
  body-sm:
    fontFamily: Inter
    fontSize: 13px
    fontWeight: '400'
    lineHeight: 18px
rounded:
  sm: 0.125rem
  DEFAULT: 0.25rem
  md: 0.375rem
  lg: 0.5rem
  xl: 0.75rem
  full: 9999px
spacing:
  sidebar-width: 240px
  property-panel-width: 300px
  gutter: 12px
  margin-page: 24px
  unit-xs: 4px
  unit-sm: 8px
  unit-md: 16px
---

## Brand & Style

The design system is engineered for the intersection of medical accuracy and advanced 3D computation. It targets dental surgeons, researchers, and lab technicians who require a tool that feels like a high-end surgical instrument: reliable, precise, and devoid of visual noise.

The aesthetic combines **Minimalism** with **Glassmorphism**. It utilizes a "light-mode first" architecture to maintain a clinical, sterile atmosphere, using high-contrast borders and generous whitespace to organize high-density data. The UI behaves like a professional workstation—inspired by CAD software and modern developer tools—where the interface recedes to let the 3D dental models and research data take center stage.

## Colors

The palette is anchored in **Medical Blue (#0F3D91)** to establish trust and authority. Functional color-coding is used sparingly but strictly:
- **Teal** is used for success states and biological "safe" zones.
- **AI Purple** identifies automated 3D sculpting suggestions and generative features.
- **Research Indigo** highlights bibliographic citations and data analytics.

Backgrounds utilize a cool gray scale to reduce eye strain during long research sessions. The `#F8FAFC` base provides a soft contrast against pure white cards and property panels, creating a clear hierarchy of containment.

## Typography

The system uses **Inter** for all functional and narrative text to ensure maximum legibility at small sizes. To support the "Pascal Editor" level of precision, **JetBrains Mono** is introduced for technical readouts, 3D coordinates, and medical IDs.

**Hierarchy Rules:**
- **Labels:** Use `label-caps` for panel headers and metadata categories.
- **Data Points:** Use `label-mono` for all numerical inputs and coordinate displays (X, Y, Z axes).
- **Mobile scaling:** Headlines above 24px should scale down by 15% on mobile devices to preserve screen real estate for the 3D viewport.

## Layout & Spacing

The layout follows a **Fixed-Panel Fluid Viewport** model. A global 12px gutter defines the separation between UI modules.

- **The Workbench:** A central fluid container for the 3D viewport.
- **Linear Sidebar:** A fixed 240px left-hand navigation for project structure and high-level views.
- **Property Panels:** Fixed 300px right-hand panels for granular 3D manipulation, mimicking the Figma inspector style.

On tablet devices, sidebars collapse into icons to prioritize the canvas. On mobile, the interface reflows into a single-column view with the 3D viewer occupying the top 50% of the screen and properties presented in expandable bottom sheets.

## Elevation & Depth

This system eschews traditional soft shadows in favor of **Tonal Layers** and **Glassmorphism** for a modern, clinical feel.

1.  **Base Layer:** `#F8FAFC` background.
2.  **Surface Layer:** Pure white (`#FFFFFF`) with a 1px `#E2E8F0` border. Shadows are restricted to a subtle 2px blur with 5% opacity to indicate interactivity.
3.  **Overlay Layer (Apple Vision Pro Style):** Floating modals and contextual 3D tooltips use a background blur (20px) with a semi-transparent white tint (70% opacity) and a high-contrast white inner stroke to simulate glass.

## Shapes

The shape language is **Soft (0.25rem / 4px)**. This choice strikes a balance between the "sharpness" of medical precision and the approachability of a modern web application.

- **Input Fields/Buttons:** 4px radius.
- **Cards/Panels:** 8px radius (`rounded-lg`).
- **Floating Overlays:** 12px radius (`rounded-xl`) to emphasize their distinct, non-structural nature.

## Components

### Buttons & Inputs
- **Primary Action:** Solid `#0F3D91` with white text. 4px radius.
- **Technical Inputs:** Compact height (28px-32px). Use mono font for numerical values. Border-bottom only focus state for a "clean sheet" aesthetic.

### Property Panels (Figma-style)
- Use accordion-style collapsible headers with `label-caps` typography.
- Group related controls (e.g., Transform, Material, Mesh) with subtle `#E2E8F0` horizontal dividers.

### Project Cards
- High-density information. Include a 16:9 thumbnail of the 3D model, status tags (AI-Assisted, Research-Verified), and timestamp metadata.

### Glassmorphic Overlays
- Tooltips that appear within the 3D viewer must use the backdrop-blur treatment to ensure they are legible regardless of the model's color or complexity behind them.

### Sidebars
- Linear-style navigation using 20px monochrome icons. Active states should use a subtle vertical bar on the left in Primary Blue, rather than full-width background highlights.