import numpy as np

from backend.api.services.cointegration_service import CointegrationService


def test_compute_mean_reversion_infinite_half_life():
    """When the AR(1) fit produces a non-positive lambda, half-life should be infinite and speed zero."""
    # Create a monotonically increasing series so that diffs are constant
    N = 100
    spread = np.arange(N).astype(float)

    svc = CointegrationService()
    mr = svc._compute_mean_reversion_metrics(spread)

    assert "half_life" in mr and "speed" in mr and "hurst" in mr
    # half-life must be infinite for non-mean-reverting series per implementation
    assert np.isinf(mr["half_life"]), f"expected infinite half_life, got {mr['half_life']}"
    # speed should be explicitly zero
    assert mr["speed"] == 0.0
