# Generated evidence

`demo/` is ignored by Git and contains only regenerated synthetic Smoke Demo outputs.
Every generated file is marked FIXTURE / SCAFFOLD_DEMO. A complete successful run
replaces that output directory; a failed attempt clears the prior demo output so stale
success cannot be mistaken for the latest result. Do not store manual content there.
Execution reports outside `demo/` must distinguish local checks, remote CI, and
pending human actions. Never include credentials or real learner/enterprise data.
