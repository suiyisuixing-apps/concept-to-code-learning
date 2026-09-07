# Document grounding

PPTX: retain one-based slide. DOCX: retain heading path and one-based paragraph.
PDF: retain one-based physical page; do not infer printed page labels. Keep file,
source_type, slide/page/section/paragraph and quote_hash fields. Hash the cited UTF-8
passage exactly, without whitespace normalization; separately hash the input file.
Preserve multiple sources when deduplicating. Empty/image-only material is unsupported
without OCR, which is out of scope. Missing or ambiguous sources need confirmation.
Markdown is a synthetic Phase 0 fixture only.
