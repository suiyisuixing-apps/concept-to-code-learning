# Documentation drift

Compare a source-cited document claim with a pinned, source-cited code observation.
Do not silently decide the document or the code is authoritative. An unresolved
conflict is NEEDS_CONFIRMATION, with recommended_owner and null resolution. Only
record CONFIRMED_DRIFT after supported review; RESOLVED requires a nonempty resolution
and evidence of the authorized change. Never modify original training or production
code as an automatic consequence. Detection is planned after Phase 0.
