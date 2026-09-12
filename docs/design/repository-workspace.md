# Repository learning workspace

Updated: 2026-09-12. Mode: **Operate / Read** — explore a repository, inspect source,
and understand its underlying knowledge beside the existing learning conversation.

Status: integrated reading, selection, annotation, model-request and citation flows
verified; model semantic quality **PARTIALLY VERIFIED**. Source integrity does not
prove an explanation correct. The independent finish verdict is **ship**, scoped to
the two listed visual fixes scored resolved. See the
[delivery review](../delivery/lead/REPOSITORY_WORKSPACE_REVIEW.md) for evidence and limits.

## Inherited visual world

This is a scoped extension of the incumbent forest-ink and paper workspace. The
forest-green header, light reading surfaces, quiet separators and existing controls
remain the visual authority; root `DESIGN.md` is historical. This brief records only
the repository surface. No new product raster assets were introduced.

Compact sans-serif controls frame monospace source text. Desktop code uses a 12px
size with 24px line spacing, increasing to 13px on wide screens. Subtle syntax
colours aid scanning without changing source text. Pale green marks selected code;
small amber gutter dots identify annotated lines. The active file combines a green
fill, stronger filename weight and a thin 1px inset side rule. Empty-state copy
starts with the useful heading and guidance; decorative eyebrow copy was removed.

## Layout and responsive behaviour

The top-level 文档 / 代码库 switch preserves PDF, PPTX, DOCX and Markdown reading,
with separate reading positions for the two material types. On desktop, the code
workspace gives roughly 1.6 shares to source and 1 to the conversation. A collapsible
202px folder rail sits within the source area; the file reader shows repository,
path, line count, licence, fixed commit and read-only state. Long lines scroll
horizontally while the line-number gutter stays visible.

The rail narrows to 164px at intermediate widths and grows to 230px above 1500px.
At 760px and below, source and conversation stack vertically. The source area is
62dvh with a 340px minimum; the conversation below is 86dvh with a 550px minimum.
The folder rail can be collapsed to make more room for code. The header reflows,
file metadata wraps, and scrolling reaches the conversation and composer.

## Selection, conversation and records

The signature interaction begins with an exact source selection: drag across code,
click a line number, or Shift-click to extend from the anchor line. Selection spans
count Unicode code points within the reading block, preserving Chinese and emoji
offsets. Arrow keys move between file rows or line-number controls; left/right
arrows collapse or expand folder rows. Selected code appears in the composer with
actions to bring it into the question, write an annotation or clear the reference.
The generated question asks about the code and its underlying knowledge and remains
editable.

The right pane reuses 对话 / 批注 / 笔记, the actual model catalogue, model-service
settings, explanation levels, progressive answers, stop and retry controls. Code
mode names the current-file context; document-specific source and search settings
remain in document mode. Annotations retain their quote, allow editing and return
to the source. Notes retain the frozen explanation and source snapshot and support
editing personal text and export. Saved code citations derive file/line labels from
that snapshot without fetching source merely to display the note. Opening a citation
locates its fixed-version file and line range; a separate link opens GitHub.

## Empty, loading and error states

Adding a repository opens an inline address/name-search panel. With no repositories,
the reader offers 添加 GitHub 仓库; with repositories but no open file, it directs
the reader to the tree. The empty conversation offers three question suggestions
once a code file is open. Directory loading, empty folders, unmatched searches,
pagination and directory retry have explicit text. File loading has a status strip;
read errors preserve the current readable file and offer retry, dismissal and a
fixed-version GitHub link. Unsupported files remain visible in the tree. Model
connection failures and empty annotation lists use the existing inline states.

## Source and evidence boundaries

This entry reads public GitHub repositories and stores files locally. It adds no
private-account connection, source editing, GitHub commits or repository execution.
The separately authorized local-source workflow remains in document mode. Directory
and file reads are on demand; truncated trees fall back to incremental directory
loading, and search explicitly identifies its already-loaded-directory scope.

The AI receives bounded current-file/selection context and at most two statically
resolved related-file excerpts, each up to about 4,000 characters. This is not an
entire-repository context claim. Binary, non-UTF-8, over-1-MiB, excessively long-line
or unconfirmed-licence files use the GitHub fallback. Saved references retain their
commit even when a repository is added again at a newer version.

Recorded validation includes 486 Python tests, 37 frontend tests and an integrated
flow with two existing local models. The visual verdict resolved only empty-state
eyebrows and the active-row side rule. Desktop captures are native 1280 × 720 browser
screenshots; narrow captures use a 375px content viewport inside a QA frame and
lossless crops of native screenshots. They establish CSS responsiveness, not
physical-phone acceptance. Capture provenance is in
`.impeccable/review/CAPTURES.md`; model correctness remains partially verified.
