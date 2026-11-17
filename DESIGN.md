---
name: PaperLens
description: A cool research atlas for reading scientific records and returning to their original evidence.
colors:
  ink: "#203844"
  muted: "#5b6e7c"
  brand: "#245f70"
  brand-dark: "#183e53"
  brand-soft: "#e7f1f2"
  page: "#f3f6f8"
  line: "#dce5e9"
  white: "#fff"
  success: "#2c7258"
  warning: "#8e6623"
  danger: "#a34848"
  brand-hover: "#194e60"
  focus: "#91bac8"
  field-line: "#cddae1"
  source-ink: "#52758b"
  source-bg: "#f6fafb"
  source-line: "#d9e7ec"
  source-active-ink: "#23556d"
  source-active-bg: "#e7f1f6"
  source-active-line: "#88b2c4"
typography:
  display:
    fontFamily: 'PaperLensHeading, "Noto Sans SC", sans-serif'
    fontSize: "31px"
    fontWeight: 680
    lineHeight: 1.35
    letterSpacing: "-0.025em"
  headline:
    fontFamily: 'PaperLensHeading, "Noto Sans SC", sans-serif'
    fontSize: "19px"
    fontWeight: 650
    lineHeight: 1.5
    letterSpacing: "-0.015em"
  title:
    fontFamily: 'PaperLensHeading, "Noto Sans SC", sans-serif'
    fontSize: "15px"
    fontWeight: 650
    lineHeight: 1.6
  body:
    fontFamily: '-apple-system, BlinkMacSystemFont, "Segoe UI", "PingFang SC", "Noto Sans SC", "Microsoft YaHei", sans-serif'
    fontSize: "14px"
    fontWeight: 400
    lineHeight: 1.6
  record:
    fontFamily: '-apple-system, BlinkMacSystemFont, "Segoe UI", "PingFang SC", "Noto Sans SC", "Microsoft YaHei", sans-serif'
    fontSize: "13px"
    fontWeight: 400
    lineHeight: 1.9
  label:
    fontFamily: '-apple-system, BlinkMacSystemFont, "Segoe UI", "PingFang SC", "Noto Sans SC", "Microsoft YaHei", sans-serif'
    fontSize: "12px"
    fontWeight: 600
    lineHeight: 1.6
  metadata:
    fontFamily: '-apple-system, BlinkMacSystemFont, "Segoe UI", "PingFang SC", "Noto Sans SC", "Microsoft YaHei", sans-serif'
    fontSize: "11px"
    fontWeight: 400
    lineHeight: 1.6
  fingerprint:
    fontFamily: 'ui-monospace, SFMono-Regular, Consolas, monospace'
    fontSize: "11px"
    fontWeight: 400
    lineHeight: 1.6
rounded:
  tag: "4px"
  source: "5px"
  compact: "6px"
  control: "7px"
  medium: "8px"
  result: "9px"
  container: "10px"
  sample: "11px"
  panel: "12px"
spacing:
  "6": "6px"
  "8": "8px"
  "10": "10px"
  "12": "12px"
  "16": "16px"
  "20": "20px"
  "22": "22px"
  "24": "24px"
components:
  button-primary:
    backgroundColor: "{colors.brand}"
    textColor: "{colors.white}"
    rounded: "{rounded.control}"
    padding: "8px 14px"
  button-primary-hover:
    backgroundColor: "{colors.brand-hover}"
    textColor: "{colors.white}"
  button-secondary:
    backgroundColor: "{colors.white}"
    textColor: "{colors.ink}"
    rounded: "{rounded.control}"
    padding: "8px 14px"
  button-ghost:
    backgroundColor: "transparent"
    textColor: "{colors.ink}"
    rounded: "{rounded.control}"
    padding: "8px 14px"
  input:
    backgroundColor: "{colors.white}"
    textColor: "{colors.ink}"
    rounded: "{rounded.control}"
    padding: "10px 12px"
  input-search:
    backgroundColor: "{colors.white}"
    textColor: "{colors.ink}"
    rounded: "{rounded.medium}"
    padding: "14px 16px 14px 49px"
    height: "58px"
  navigation:
    backgroundColor: "{colors.brand-dark}"
    padding: "30px 18px 20px"
  tag:
    rounded: "{rounded.tag}"
    padding: "2px 7px"
  panel:
    backgroundColor: "{colors.white}"
    textColor: "{colors.ink}"
    rounded: "{rounded.panel}"
    padding: "24px"
  source-chip:
    backgroundColor: "{colors.source-bg}"
    textColor: "{colors.source-ink}"
    rounded: "{rounded.source}"
    padding: "3px 7px"
  source-chip-active:
    backgroundColor: "{colors.source-active-bg}"
    textColor: "{colors.source-active-ink}"
  evidence-inspector:
    backgroundColor: "{colors.white}"
    textColor: "{colors.ink}"
    rounded: "{rounded.container}"
---

# Design System: PaperLens

## Overview

**Creative North Star: "The Research Atlas"**

A cool research atlas gives scientific records the clarity of a reading sheet and keeps their sources close. Deep teal navigation anchors the workspace; blue-grey surroundings separate white reading surfaces. Restrained controls, compact metadata and generous paragraph leading support sustained inspection of Chinese interface text and original-language papers.

The hierarchy is practical and composed. Borders and tonal changes organize the interface, while small source chips connect a claim to an adjacent evidence inspector. This metaphor and its descriptive language record the implementer's delegated direction; they are not a separately approved visual composition. The current system is extracted from source code. Desktop and mobile captures and twelve Chromium engineering checks were obtained in GitHub Actions using controlled, labelled fixtures. Production authentication remains untested; real-paper/API/download receipts are a separate validation scope.

**Key Characteristics:**

- Deep teal navigation and white reading surfaces.
- Compact metadata beside readable scientific paragraphs.
- Source chips that lead to a dedicated evidence margin.
- Borders and tonal layers with selective neutral shadows.
- Clear textual states and visible keyboard focus.

## Colors

The palette combines muted teal with cool paper neutrals; ochre, green and red carry explicit feedback meanings. Frontmatter values are normative and match `website/web_assets/workspace.css`; the sidecar's eight-step tonal ramps are synthesized for inspection and are not a shipping CSS scale.

### Primary

- **Atlas Teal** (`brand`): primary actions, links, native selection controls and progress accents.
- **Deep Atlas Teal** (`brand-dark`): persistent navigation and the browser theme color.
- **Teal Wash** (`brand-soft`): the shared soft brand token; retain it as a supporting primitive rather than making it a second accent.
- **Pressed Teal** (`brand-hover`): the filled primary button's hover surface.
- **Source Blues** (`source-*`): pale evidence buttons with a darker border and text in hovered or selected states.
- **Focus Blue** (`focus`): the shared keyboard outline across links, buttons, fields and summaries.

### Neutral

- **Reading Ink** (`ink`): primary text on light surfaces.
- **Slate Annotation** (`muted`): supporting descriptions and metadata.
- **Cool Workspace** (`page`): the application background around reading sheets.
- **Paper White** (`white`): cards, fields, panels and the top bar.
- **Sheet Edge** (`line`): panel strokes, dividers and table boundaries.
- **Field Edge** (`field-line`): the stronger standard input stroke.

Feedback primitives remain semantic: **Review Green** (`success`) for a reviewed state, **Limit Ochre** (`warning`) for incomplete fields and **Error Red** (`danger`) for failure. Pair each with readable text. A successful structure state is not scientific verification.

**The Legible State Rule.** Always name a status in text; color and dots support the label.

## Typography

**Display Font:** self-hosted PaperLensHeading, an OFL-licensed Noto Sans SC weight-600 subset with compatible Latin glyphs. Heading typography is consistent across Chinese and English. **Body Font:** the platform sans-serif stack in frontmatter, with Chinese fallbacks. No browser request to a font service is made.

**Label/Mono Font:** the same sans-serif stack for labels and metadata; the system monospace stack for PDF fingerprints.

The type is quiet, compact and suitable for mixed Chinese interface text and long English paper titles. Sizes are explicitly tuned per role rather than following a fixed modular ratio. Headings use the self-hosted weight-600 face; other text depends on the installed body-font stack.

### Hierarchy

- **Display:** the discovery heading uses the `display` role. Other page headings use a slightly smaller size (30px); paper titles use a longer leading (25px/1.5). Mobile discovery and paper headings become 26px and 21px respectively.
- **Headline:** the base section heading uses `headline`; compact card headings use smaller observed variants (16–18px).
- **Title:** `title` supplies the base third-level heading. Dense sample and job titles use smaller contextual variants (12–13px).
- **Body:** `body` is the application default. Research record paragraphs use `record` with preserved line breaks and a maximum measure (76ch).
- **Label:** `label` is a field label; button labels use medium emphasis (550). Metadata uses the smallest observed text role (11px).
- **Fingerprint:** `fingerprint` wraps long hashes with breaks instead of forcing the surrounding panel wider.

**The Reading Measure Rule.** Preserve the record paragraph's comfortable measure and generous leading; allow titles, identifiers and source text to wrap.

## Layout

Desktop layout has a fixed navigation rail (226px), a top bar (70px) and a content region capped at 1460px. Standard content padding is 34px 38px 50px. Repeated small gaps and padding come from the observed spacing entries in frontmatter; the stylesheet does not expose a named spacing scale.

Primary content and contextual evidence use a two-column grid. The detail evidence margin is 340px wide with a 22px gap and is sticky 20px below the viewport edge. Discovery uses a 285px side panel; exports use 310px. Library and comparison tables retain horizontal scrolling when their minimum readable width exceeds the viewport.

- At **1600px and above**, navigation expands to 244px and content gains wider padding (43px 54px 60px).
- At **1150px and below**, navigation contracts to 204px, content padding reduces (29px 25px 45px) and secondary columns narrow.
- At **950px and below**, the main two-column grids become one column, the decorative evidence preview is hidden and the actual evidence inspector becomes static in document flow. The compact connection label is hidden.
- At **720px and below**, navigation becomes an off-canvas drawer with a visible menu button. The top bar is 60px tall; content padding is 25px 18px 35px. The search field and submit button stack; metadata wraps; review fields become one column. The library table continues to scroll rather than compressing each column beyond readability.

The homepage search priority is a confirmed surface decision. Its exact composition lives in `.impeccable/surfaces/website-web-assets-workspace-html.md`, rather than becoming a mandatory layout for every screen.

## Elevation & Depth

Use borders and changes of surface tone for routine hierarchy. Panels and reading sheets rest without shadows. Neutral shadows distinguish the raised toast, the open mobile drawer and the main search field. The sidecar records exact values because the frontmatter schema has no shadow field.

### Shadow Vocabulary

- **Toast:** `0 12px 40px rgb(0 0 0 / 10%)`, from the shared shadow variable.
- **Search field:** `0 2px 5px rgb(0 0 0 / 3%)`, a very slight separation within the search panel.
- **Mobile drawer:** `8px 0 32px rgb(0 0 0 / 20%)`, only while the navigation drawer is open.

**The Flat Reading Rule.** Keep ordinary reading surfaces flat; reserve shadows for the existing raised or input roles.

## Shapes

The form language uses gently rounded rectangles with thin borders. Small tags have the tightest corners, source chips are slightly softer and controls use the shared control radius. Larger panels use the broadest corners. The frontmatter records the observed radius vocabulary; these are extracted sizes rather than CSS custom properties.

Circular user avatars and tiny state dots are the main exceptions. The PaperLens logo is geometric SVG. Interface icons use Lucide-derived inline SVG paths with rounded line caps and joins (1.7px stroke, usually 19px; button icons 16px). Keep the ISC attribution in `third_party/LUCIDE_LICENSE.txt`. The documented surface ships no raster imagery.

## Components

### Buttons

Compact and direct, with medium-weight labels and a minimum standard height (39px). Primary buttons use Atlas Teal and Paper White; secondary buttons use white, Reading Ink and a Sheet Edge stroke. Ghost buttons omit the visible border. Standard padding and radius are in frontmatter; the small variant uses 6px 11px padding and 33px minimum height.

Primary hover deepens the teal. Secondary hover uses a cool light fill and a stronger stroke; ghost hover uses a light tonal wash. Shared hover transitions are short (160ms). Focus uses the shared outline (3px, offset 3px); disabled controls use reduced opacity (.5) and a not-allowed cursor.

### Inputs / Fields

Fields are white with a single Field Edge stroke, the shared control radius, 10px 12px padding and 41px minimum height. Labels remain outside the field. Textareas have a generous line-height (1.7) and vertical resizing. The search field is deliberately larger (58px tall, 52px on mobile) and reserves left padding for a search icon. Errors appear in readable adjacent feedback surfaces.

### Navigation

The deep teal rail carries pale labels, an icon and optional counts. Navigation items have 8px corners, 10px 14px padding and 46px minimum height. Hover lightens the dark surface; the current page reverses to a pale teal sheet with dark text and stronger weight. Current-page state is expressed by `aria-current`. Mobile uses the same rail as a drawer with `aria-expanded` on its menu trigger; a closed mobile drawer is inert and hidden from assistive technology. Escape closes it and restores focus to the menu trigger.

### Chips / Tags

Tags are compact, noninteractive annotations with 4px corners and 2px 7px padding. Subject tags have a green-tinted fill. Source chips are interactive evidence locators with 5px corners, 3px 7px padding and a thin blue stroke. Their hover and selected states deepen the text and border while preserving the pale surface. Keep original page and evidence identifiers visible in the label.

### Cards / Containers

General panels use Paper White, a Sheet Edge border, 12px corners and 24px padding, reducing to 19px on mobile. Dense result cards, table wrappers, record sections and evidence panels use the smaller observed container radii. Do not add shadows to these reading surfaces. Adjacent record sections share borders and only round the outside corners.

### Evidence Inspector

A dedicated white reading margin holds the source page, field, block, character offsets, quoted text, original-PDF action and fingerprint. Its header is a faintly tinted band; its quote has a pale blue-grey inset. The inspector is sticky on wide layouts and appears in flow after the record on narrow layouts. Selecting a source chip changes the inspected snippet while retaining the automatic result.

### Feedback and Motion

Notices pair a tinted surface with explicit text. Inline error boxes provide a retry action where appropriate. Loading uses muted skeleton bars with a 1.4s ease-in-out opacity alternation; job progress uses the brand accent. The toast is a compact raised message with status semantics.

CSS disables animations, transitions and document smooth scrolling when reduced motion is requested. The evidence-selection handler checks the same reduced-motion preference and requests instant scrolling when it is enabled. No rendered motion review is claimed here.

## Do's and Don'ts

### Do:

- **Do** use deep teal for navigation and white sheets for reading.
- **Do** preserve readable wrapping, paragraph leading and the evidence margin's relationship to the record.
- **Do** pair every feedback color with a clear textual state.
- **Do** keep source chips, original page references and PDF fingerprints available during review.
- **Do** preserve the visible keyboard outline and CSS reduced-motion treatment.

### Don't:

- **Don't** add decorative shadows to ordinary panels or record sections.
- **Don't** use a success tint to imply scientific correctness.
- **Don't** hide missing-field or error labels behind color alone.
- **Don't** replace the geometric SVG and licensed line icons with unrelated imagery.
- **Don't** describe this code-derived system as a user-approved composition or a visually validated desktop/mobile build.
