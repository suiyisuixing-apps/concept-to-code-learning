"""Expected-output example used by the Phase 0 runner."""

from app import can_view_profile

active = can_view_profile(is_active=True)
inactive = can_view_profile(is_active=False)
assert active is True
assert inactive is False
print(f"active={active} inactive={inactive}")
