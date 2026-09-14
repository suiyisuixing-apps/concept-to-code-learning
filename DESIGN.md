---
name: "Concept-to-Code Learning"
description: "Warm paper, forest-green actions, and a local document-to-source learning workspace."
colors:
  ink: "#263e35"
  muted: "#5d6c63"
  rule: "#d9dfd6"
  green: "#236747"
  paper: "#fffefa"
  soft: "#edf2e9"
  canvas: "#f7f8f4"
  document-surface: "#f3f5ef"
  evidence-surface: "#fafbf7"
  action-hover: "#174b34"
  secondary-hover: "#e2eadc"
  field-fill: "#fff"
  field-border: "#7b8f7e"
  disabled-fill: "#e8ece5"
  disabled-ink: "#647068"
  selected-fill: "#e4ede0"
  selected-ink: "#214f36"
  citation-fill: "#f0f3ec"
  citation-ink: "#415745"
  code-fill: "#eaf0e4"
  code-ink: "#214834"
  link: "#1a6340"
  link-hover: "#103e28"
  notice-fill: "#e4efdf"
  notice-ink: "#285337"
  error-fill: "#f9e9e2"
  error-ink: "#833d27"
typography:
  headline:
    fontFamily: 'Inter, -apple-system, BlinkMacSystemFont, "Segoe UI", "PingFang SC", "Microsoft YaHei", sans-serif'
    fontSize: "20px"
    fontWeight: 700
    lineHeight: 1.35
    letterSpacing: "-0.025em"
  title:
    fontFamily: 'Inter, -apple-system, BlinkMacSystemFont, "Segoe UI", "PingFang SC", "Microsoft YaHei", sans-serif'
    fontSize: "16px"
    fontWeight: 700
    lineHeight: 1.65
  body:
    fontFamily: 'Inter, -apple-system, BlinkMacSystemFont, "Segoe UI", "PingFang SC", "Microsoft YaHei", sans-serif'
    fontSize: "14px"
    fontWeight: 400
    lineHeight: 1.65
  document-body:
    fontFamily: 'Inter, -apple-system, BlinkMacSystemFont, "Segoe UI", "PingFang SC", "Microsoft YaHei", sans-serif'
    fontSize: "14px"
    fontWeight: 400
    lineHeight: 1.95
  answer-body:
    fontFamily: 'Inter, -apple-system, BlinkMacSystemFont, "Segoe UI", "PingFang SC", "Microsoft YaHei", sans-serif'
    fontSize: "14px"
    fontWeight: 400
    lineHeight: 1.9
  label:
    fontFamily: 'Inter, -apple-system, BlinkMacSystemFont, "Segoe UI", "PingFang SC", "Microsoft YaHei", sans-serif'
    fontSize: "12px"
    fontWeight: 600
    lineHeight: 1.65
  primary-action:
    fontFamily: 'Inter, -apple-system, BlinkMacSystemFont, "Segoe UI", "PingFang SC", "Microsoft YaHei", sans-serif'
    fontSize: "13px"
    fontWeight: 600
    lineHeight: 1.65
  caption:
    fontFamily: 'Inter, -apple-system, BlinkMacSystemFont, "Segoe UI", "PingFang SC", "Microsoft YaHei", sans-serif'
    fontSize: "11px"
    fontWeight: 400
    lineHeight: 1.65
  fixture-label:
    fontFamily: 'Inter, -apple-system, BlinkMacSystemFont, "Segoe UI", "PingFang SC", "Microsoft YaHei", sans-serif'
    fontSize: "11px"
    fontWeight: 700
    lineHeight: 1.65
    letterSpacing: "0.07em"
  code:
    fontFamily: "ui-monospace, SFMono-Regular, Consolas, monospace"
    fontSize: "11px"
    fontWeight: 400
    lineHeight: 1.85
rounded:
  control: "8px"
  small: "4px"
  paper: "3px"
spacing:
  micro: "4px"
  control-gap: "8px"
  compact: "12px"
  text-gap: "16px"
  pane-mobile: "18px"
  pane-medium: "20px"
  pane: "24px"
  pane-wide: "32px"
components:
  button-primary:
    backgroundColor: "{colors.green}"
    textColor: "white"
    typography: "{typography.primary-action}"
    rounded: "{rounded.control}"
    padding: "9px 14px"
    height: "42px"
  button-primary-hover:
    backgroundColor: "{colors.action-hover}"
  button-secondary:
    backgroundColor: "transparent"
    textColor: "{colors.green}"
    typography: "{typography.label}"
    rounded: "{rounded.control}"
    padding: "8px"
  button-pagination:
    backgroundColor: "transparent"
    textColor: "{colors.ink}"
    typography: "{typography.label}"
    rounded: "{rounded.control}"
    padding: "5px 10px"
  field:
    backgroundColor: "{colors.field-fill}"
    textColor: "{colors.ink}"
    rounded: "{rounded.control}"
    padding: "9px 11px"
    width: "100%"
  view-tab:
    backgroundColor: "transparent"
    textColor: "{colors.muted}"
    rounded: "{rounded.control}"
    padding: "5px 7px"
  view-tab-selected:
    backgroundColor: "{colors.selected-fill}"
    textColor: "{colors.selected-ink}"
  fixture-label:
    textColor: "{colors.ink}"
    typography: "{typography.fixture-label}"
    rounded: "{rounded.small}"
    padding: "4px 8px"
  document-page:
    backgroundColor: "{colors.paper}"
    textColor: "{colors.ink}"
    typography: "{typography.document-body}"
    rounded: "{rounded.paper}"
    padding: "24px 21px"
  document-citation:
    backgroundColor: "{colors.citation-fill}"
    textColor: "{colors.citation-ink}"
    rounded: "{rounded.small}"
    padding: "12px 15px"
  code-excerpt:
    backgroundColor: "{colors.code-fill}"
    textColor: "{colors.code-ink}"
    typography: "{typography.code}"
    rounded: "{rounded.small}"
    padding: "15px 12px"
---

# Design System: Concept-to-Code Learning

> Scope correction, 2026-09-14: the frontmatter tokens and detailed record below describe the archived Phase 0.5 surface. They are not the current UI specification. The current document/code workspace is recorded in [repository-workspace.md](docs/design/repository-workspace.md), and implemented in [App.jsx](apps/web/src/App.jsx), [workspace.css](apps/web/src/workspace.css), [conversation.css](apps/web/src/conversation.css) and [repository.css](apps/web/src/repository.css). Current behavior includes real four-format imports, model selection, folder-based source reading, annotations and revisioned notes. Verification and Fixture state must remain visibly accurate.

## Overview

**Creative North Star: "Warm paper learning workspace"**

The implemented interface is a quiet reading workspace: warm paper, forest-green actions, thin rules, native controls, and familiar sans-serif typography. Document text, explanations, and source details carry the visual weight. The book-and-code mark is a small inline outline SVG; there is no raster artwork, downloaded font, photographic layer, or approved visual comp.

This document captures the built Phase 0.5 React Operate surface. Its product authority is [README.md](README.md) and [product-scope.md](docs/product-scope.md); its visual authority is [styles.css](apps/web/src/styles.css), [App.jsx](apps/web/src/App.jsx), and the direction comment in [index.html](apps/web/index.html). The visible `FIXTURE` and `SCAFFOLD_DEMO` labels belong to this implementation. It offers synthetic Markdown pages, fixed explanations, a frozen FastAPI reference, and explicit local note creation. Planned imports, models, live search, generalized verification, and execution are outside this design record.

**Key Characteristics:**

- Warm paper surfaces separated by thin rules.
- Green actions and links with native form controls.
- Document, tutor, and evidence in one ordered reading workspace.
- Visible fixture and source states alongside the content they qualify.
- Personal text kept separate from the explanation, with an explicit save action.

## Colors

The palette combines paper neutrals with a restrained forest-green action color. The frontmatter records the values; the role names below explain their use.

### Primary

- **Forest Green** (`green`) supplies filled actions, text actions, carets, the local-state dot, and keyboard outlines. `action-hover` darkens filled buttons; `secondary-hover` adds a pale green fill to outlined actions and pagination.
- **Source Link Green** (`link`) identifies underlined source links, with `link-hover` for hover. The repository title uses the same link color at heading size.
- **Selected View** (`selected-fill`, `selected-ink`) marks the pressed learning/notes control with a quiet tonal fill.

### Neutral

- **Reading Ink** (`ink`) carries body text and headings. **Muted Ink** (`muted`) carries context, metadata, and helper text.
- **Warm Paper** (`paper`) carries the header, tutor pane, and document sheet. **Canvas** (`canvas`), **Document Surface** (`document-surface`), and **Evidence Surface** (`evidence-surface`) distinguish adjacent regions without elevation.
- **Soft Green Paper** (`soft`) is the fixture banner fill. **Fine Rule** (`rule`) divides panes and sections.
- **Field Fill** (`field-fill`) and **Field Boundary** (`field-border`) keep editable controls recognizable at rest. The question textarea has the source-declared near-paper exception (`#fdfefa`).
- Citation and code pairs (`citation-fill` / `citation-ink`, `code-fill` / `code-ink`) separate quoted evidence from explanatory prose. Disabled, notice, and error pairs preserve their implemented state vocabulary; warm rust is reserved for errors.

**The Visible State Rule.** Keep the field boundary, focus outline, disabled treatment, and textual state labels together. A green verification label describes the frozen source; the adjacent `NOT_RUN` label still describes its execution state.

The six color custom properties in the current stylesheet are `--ink`, `--muted`, `--rule`, `--green`, `--paper`, and `--soft`. Other frontmatter colors name observed literal values; they do not imply that additional CSS variables exist. Sidecar tonal ramps are generated swatch previews, not implemented color scales.

## Typography

**Interface and reading font:** the exact Inter-first system fallback stack is recorded in the frontmatter. There is no bundled font or webfont request. Rendering uses the first installed family in that stack, including the declared Chinese fallbacks. The finish review accepted this familiar sans treatment for the Operate surface.

**Code font:** the platform monospace stack in `typography.code` carries snippets and immutable source identifiers. The interface does not use display typography or a separate decorative heading face.

### Hierarchy

- **Headline:** the app name uses `headline`; the “Learning” span drops to regular weight (400). At the small breakpoint the heading becomes smaller (16px) and has a bounded width (220px).
- **Pane titles:** `title` provides a compact, bold label for the three working regions. The question label is slightly larger (17px, weight 600); answer headings are larger again (19px, weight 700, line height 1.5).
- **Reading:** `document-body` provides generous paragraph leading. Its document heading uses a medium weight (600), a larger size (19px), and a line height of 1.6; on small screens its size becomes 20px.
- **Explanation:** `answer-body` preserves line breaks and caps line length (72ch). General prose uses `body`.
- **Labels and metadata:** `label` and `caption` cover compact UI text. Source identifiers and footer metadata range from 10px to 12px as declared in the source. Keep small metadata subordinate to reading text.
- **Code:** `code` preserves literal whitespace; long code scrolls inside its own block. Pagination uses tabular numerals.

There is no strict modular type ratio or invented font scale. Labels remain readable Chinese phrases; uppercase is retained for machine states such as `FIXTURE`.

## Layout

The workspace is centered with a maximum width (1800px) and a minimum height of `calc(100vh - 169px)`. At the default desktop width it uses three grid tracks: `minmax(260px, 29fr) minmax(370px, 40fr) minmax(275px, 31fr)`. The wider middle pane owns asking, reading the explanation, and saving a note. Pane padding is `0 24px 26px`; each title row is 69px high with a bottom divider and 23px of following space. These tracks are the current surface composition, not a mandate for future unrelated pages.

| CSS condition | Implemented behavior |
| --- | --- |
| `min-width: 1500px` | Pane side padding grows to 32px; document padding becomes 30px. Tracks become `minmax(300px, 29fr) minmax(420px, 40fr) minmax(320px, 31fr)`. |
| `max-width: 1050px` | Two tracks use `minmax(230px, 1fr) minmax(340px, 1.45fr)`. Evidence spans both columns below them, with a top rule and no left rule. Its content is capped at 800px. Pane side padding becomes 20px; the fixture banner wraps. |
| `max-width: 640px` | The workspace becomes a vertical flex column in document → tutor → evidence order. Panes use `0 18px 24px`; title rows become 60px high with 19px below. The header and banner use 18px side padding. The footer stacks. The local connection text is hidden while `FIXTURE` remains visible. |

The document sheet has a minimum height (335px) on larger screens; the small layout removes that minimum and uses padding (23px). The question textarea has a minimum height (94px); other textareas begin at 72px and resize vertically. Question controls stay in one flex row; the difficulty container occupies at most 55% of that row. Document actions wrap if needed. Source paths and hashes wrap anywhere, while literal code uses contained horizontal scrolling.

Spacing is intentionally compact around metadata and looser around reading and task transitions. The frontmatter names recurring observed dimensions; there is no enforced eight-point spacing grid. Header padding is `20px 30px`, with a short fixture strip below. The note form and answer begin after thin section rules.

The supplied review captures are unmodified JPEG viewport images: desktop (1425×990) and mobile (375×812), from reported CSS viewports of 1440×1000 and 390×844. They document the built layout, not an exact-pixel reference comp. The finish verdict closes its two material findings with `ship`; its stated fixture, interaction, and runtime evidence limits still apply. The captures and verdict are local acceptance evidence in the intentionally ignored `.impeccable/review/` directory, so they are not available in a fresh repository clone.

## Elevation & Depth

The current stylesheet defines no box shadows, gradients, blur layers, or lifted-card transitions. Adjacent paper tones, fine one-pixel rules, and a brighter document sheet provide separation. Buttons change background color over a short transition (`0.18s ease-out`); there is no spatial motion. The reduced-motion media query disables transitions and requests automatic scrolling behavior.

**The Paper Separation Rule.** Preserve the implemented tonal surfaces and thin rules when extending this workspace. Elevation is not part of its current visual vocabulary.

## Shapes

Controls use the shared `--radius` value represented by `rounded.control`. Tags, citations, code blocks, and messages use the smaller radius; the document sheet has the shallowest corner. Borders are thin (1px), with stronger field boundaries than decorative separators. The local-state dot is the only fully round status form (7px diameter).

The identity mark is source-authored inline SVG with a 32-unit view box, unfilled paths, rounded caps and joins, and a stroke width (1.7). Its displayed size is 35×35px on larger screens and 26×30px at the small breakpoint. Keep its current source path; no raster asset or font icon is required.

## Components

### Buttons

Filled green actions are compact and direct. The main ask action uses `button-primary`; the document's secondary action uses `button-secondary`. Shared base buttons use padding (9px 14px), a transparent one-pixel border, and medium-bold text (600). Document actions override this to padding (8px) and smaller text (12px), and grow evenly within their row. Secondary borders use the source value (`#a7b8a7`).

Hover darkens filled actions or softly fills secondary actions. Disabled buttons use the recorded muted state pair, a rule-colored border, and the native unavailable cursor. There is no custom active transform. Asking is disabled while busy or the question is blank; selection explanation additionally requires selected text. A nearby Chinese hint explains how to recover from a blank question. Saving requires an answer, a nonblank title, and no in-flight ask or save.

Keyboard focus uses a solid green outline (2px) with an offset (4px) on buttons, links, inputs, textareas, and selects. The focusable document page has the same outline; its source does not set the offset. Preserve native semantics and labels.

### Inputs / Fields

Fields are full-width, lightly rounded, white, and visibly bordered. Their default padding is `field.padding`; text and caret use the reading and action colors. Labels sit above their controls. The question field uses the near-paper fill noted in Colors, a line height (1.75), and the larger minimum height from Layout. The native select is 42px high. Placeholder text uses the source value (`#657369`).

The personal-note title and text are distinct controls beneath the answer. Asking again does not clear the personal-text state. Error and confirmation paragraphs are colocated in the tutor pane, with `role="alert"` and `role="status"` respectively. The UI does not define field-specific error borders or custom select menus.

### Navigation and Fixture Tag

Pagination is an outlined, transparent button pair with a page count between them. Boundary pages disable the corresponding button; enabled hover receives the secondary tonal fill. Its border (`#aebbb0`) is distinct from the stronger editable-field boundary.

The learning/notes switch is a labelled navigation region containing native buttons with `aria-pressed`. Selected buttons use the recorded selected pair; unselected buttons remain transparent with muted text. They use compact padding (5px 7px), smaller type (11px, weight 500), and a short gap (3px). There is no separate hover fill on these controls in the current stylesheet.

`FIXTURE` is a static outlined status tag, not an action or filter. It uses the `fixture-label` tokens and a one-pixel border (`#9dab9d`); its type shrinks to 9px on small screens. The adjoining banner states the synthetic content and missing model/import/search connections, and retains `SCAFFOLD_DEMO` when it wraps.

### Document Sheet and Citations

The sheet is a focusable reading article with a paper fill, fine border, shallow corner, and roomy leading. Mouse or keyboard text selection in this article populates a separate editable passage field. Paging clears the old selection. The page and passage follow the current question context.

Document citations use a softly filled blockquote, a compact source label, and preserved quotation line breaks. They recur beneath answers and inside saved notes. Do not style quotations as generated explanation text; their visible document name and page number are part of the reading pattern.

### Source Evidence and Saved Notes

The evidence panel leads with a repository link and visible source state, then a compact definition list for repository, commit, file, symbol, lines, and license. The list has a short label column (48px) and a wrapping value column; at the medium breakpoint the label column becomes 65px. Source code is a literal, unhighlighted monospace block using `code-excerpt`, with a local scrollbar and a nearby source link. A disclosure contains verification method and excerpt hash. The fixed-source verification text and unexecuted status stay distinct.

Saved notes are vertically separated articles with thin bottom rules, a title, personal text, a native disclosure for explanation and sources, and a small timestamp. The returned note is prepended to the displayed list after explicit saving; existing entries remain. This is the current append-only note presentation, with no overwrite, score, mastery badge, or automatic-save control.

## Do's and Don'ts

### Do:

- **Do** preserve warm paper surfaces, green actions, thin rules, and the source-declared native font fallback stack.
- **Do** keep document, tutor, and evidence in their current reading order as this workspace collapses.
- **Do** retain visible field boundaries, keyboard outlines, native labels, and text alongside status colors.
- **Do** keep literal code scrollable within its block and wrap long source metadata within its pane.
- **Do** keep fixture scope, fixed-source verification, and execution status legible beside their relevant content.
- **Do** preserve personal text across questions and add a note only through the explicit save action.

### Don't:

- **Don't** present the fixed explanation or frozen source as a live model response, live search, or executed snippet.
- **Don't** replace existing personal-note text or imply that saving happens automatically.
- **Don't** introduce imported fonts, raster illustrations, gradients, shadows, or motion as if they were part of the current system.
- **Don't** replace editable-field borders with the lighter decorative rule color.
- **Don't** promote planned product capabilities or this specific three-pane composition into unsupported global design rules.
