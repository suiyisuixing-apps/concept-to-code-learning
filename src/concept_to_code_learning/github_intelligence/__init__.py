"""GitHub Intelligence extension boundary.

Member entrypoint installed by the Lead:
`concept_to_code_learning.github_intelligence.full.build_provider(settings)`.
Implements SourceProvider from full_learning/ports.py.
"""

from .full import GitHubSourceProvider, build_provider

__all__ = ["GitHubSourceProvider", "build_provider"]
