"""Repository-level Clean Architecture dependency tests."""

import pytest

from validation.architecture.check_boundaries import boundary_violations


@pytest.mark.contract
def test_clean_architecture_dependencies() -> None:
    assert boundary_violations() == []
