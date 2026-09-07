"""Synthetic service-layer helper; no HTTP framework or server is started."""


def can_view_profile(*, is_active: bool) -> bool:
    """Only an active user may view their profile."""
    return is_active
