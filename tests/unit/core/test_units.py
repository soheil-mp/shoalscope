import math

import numpy as np
import pytest
from hypothesis import given
from hypothesis import strategies as st
from hypothesis.extra import numpy as hnp

from shoalscope_core.units import Decibels, Linear

db_values = hnp.arrays(np.float64, st.integers(1, 20), elements=st.floats(-200.0, 50.0))


@given(db_values)
def test_round_trip_through_the_linear_domain(values: np.ndarray) -> None:
    np.testing.assert_allclose(Decibels(values).to_linear().to_db().value, values, atol=1e-9)


@given(hnp.arrays(np.float64, st.integers(1, 20), elements=st.floats(1e-20, 1e5)))
def test_round_trip_through_the_decibel_domain(values: np.ndarray) -> None:
    np.testing.assert_allclose(Linear(values).to_db().to_linear().value, values, rtol=1e-12)


def test_known_values() -> None:
    assert float(Decibels(-70.0).to_linear().value) == pytest.approx(1e-7)
    assert float(Linear(0.5).to_db().value) == pytest.approx(-3.0103, abs=1e-4)
    assert float(Linear(0.0).to_db().value) == -math.inf
    assert float(Decibels(-math.inf).to_linear().value) == 0.0


def test_means_are_linear_and_exceed_decibel_means() -> None:
    values = Decibels([-60.0, -70.0])
    linear_mean = float(values.to_linear().mean().to_db().value)
    assert linear_mean == pytest.approx(10 * math.log10((1e-6 + 1e-7) / 2))
    assert linear_mean > float(np.mean(values.value))


def test_decibels_have_no_mean() -> None:
    assert not hasattr(Decibels(1.0), "mean")
    assert not hasattr(Decibels(1.0), "sum")


def test_decibel_offsets_and_forbidden_combinations() -> None:
    corrected = Decibels([-50.0, -60.0]) + 1.2
    np.testing.assert_allclose(corrected.value, [-48.8, -58.8])
    np.testing.assert_allclose((corrected - 1.2).value, [-50.0, -60.0])
    with pytest.raises(TypeError, match="linear domain"):
        Decibels(1.0) + Decibels(2.0)


def test_linear_arithmetic() -> None:
    total = Linear([1.0, 2.0]) + Linear([3.0, 4.0])
    np.testing.assert_array_equal(total.value, [4.0, 6.0])
    np.testing.assert_array_equal((total * 0.5).value, [2.0, 3.0])
    assert float(Linear([[1.0, 2.0], [3.0, 4.0]]).sum().value) == 10.0
    np.testing.assert_array_equal(Linear([[1.0, 2.0], [3.0, 4.0]]).mean(axis=0).value, [2.0, 3.0])


def test_missing_values_are_ignored_by_sums_and_means() -> None:
    values = Linear([1.0, math.nan, 3.0])
    assert float(values.mean().value) == 2.0
    assert float(values.sum().value) == 4.0


def test_linear_only_adds_linear_quantities() -> None:
    with pytest.raises(TypeError):
        Linear(1.0) + 2.0  # type: ignore[operator]


def test_linear_values_cannot_be_negative() -> None:
    with pytest.raises(ValueError, match="negative"):
        Linear([1.0, -1e-12])


def test_values_are_read_only() -> None:
    with pytest.raises(ValueError, match="read-only"):
        Decibels([1.0, 2.0]).value[0] = 5.0
