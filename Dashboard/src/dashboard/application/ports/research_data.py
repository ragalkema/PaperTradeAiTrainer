"""Ports keep the desktop UI independent from bounded-context internals."""

from typing import Protocol

from dashboard.application.view_models import DashboardSnapshot


class DashboardDataPort(Protocol):
    """Read-only, bounded query used by periodic dashboard refreshes."""

    def snapshot(self) -> DashboardSnapshot:
        """Return the latest bounded snapshot without fabricating absent data."""
