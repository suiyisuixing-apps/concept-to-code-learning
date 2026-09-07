from app import can_view_profile


def test_profile_requires_active_user():
    assert can_view_profile(is_active=True) is True
    assert can_view_profile(is_active=False) is False
