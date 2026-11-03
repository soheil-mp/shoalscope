"""Decibel and linear quantities that cannot be averaged in the wrong domain.

Acoustic quantities live in two domains: logarithmic (``Sv``, ``TS``, in dB) and linear
(``sv`` in m-1, ``sigma_bs`` in m2). Averaging must happen in the linear domain; the mean of
decibel values is biased low whenever the values vary (MacLennan, Fernandes & Dalen 2002). The
two wrappers here make the rule a type error:

* :class:`Decibels` converts to linear and supports adding a gain or offset, but has **no**
  ``mean``.
* :class:`Linear` supports sums and means, and converts back with :meth:`Linear.to_db`.

Names in code and tables carry their unit as a suffix: ``range_m``, ``sv_db``,
``sv_linear_per_m``, ``ts_db``, ``sigma_bs_m2``, ``nasc_m2_per_nmi2``, ``speed_mps``.

Both wrappers hold a float64 NumPy array of any shape (a scalar is a 0-d array).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Self

import numpy as np

if TYPE_CHECKING:
    from numpy.typing import ArrayLike, NDArray

__all__ = ["Decibels", "Linear"]


def _array(values: ArrayLike) -> NDArray[np.float64]:
    array = np.array(values, dtype=np.float64)
    array.setflags(write=False)
    return array


@dataclass(frozen=True, slots=True, eq=False)
class Decibels:
    """A logarithmic quantity, ``10 * log10(linear / reference)``.

    Examples:
    --------
    >>> Decibels(-70.0).to_linear().value
    array(1.e-07)
    """

    value: NDArray[np.float64]

    def __init__(self, value: ArrayLike) -> None:
        """Wrap decibel values; ``-inf`` stands for a linear value of zero."""
        object.__setattr__(self, "value", _array(value))

    def to_linear(self) -> Linear:
        """The same quantity in the linear domain."""
        return Linear(np.power(10.0, self.value / 10.0))

    def __add__(self, offset: object) -> Self:
        """Apply a gain or offset in dB (for example a calibration correction).

        Raises:
            TypeError: If ``offset`` is not a plain number; quantities combine in the linear
                domain, never by adding decibels.
        """
        if isinstance(offset, bool) or not isinstance(offset, (int, float)):
            msg = "add a plain dB offset; combine quantities in the linear domain"
            raise TypeError(msg)
        return type(self)(self.value + offset)

    def __sub__(self, offset: float) -> Self:
        """Remove a gain or offset in dB."""
        return self + -offset


@dataclass(frozen=True, slots=True, eq=False)
class Linear:
    """A non-negative linear quantity such as ``sv`` (m-1) or ``sigma_bs`` (m2).

    Examples:
    --------
    >>> float(Linear([1e-6, 1e-7]).mean().to_db().value.round(2))
    -62.6
    """

    value: NDArray[np.float64]

    def __init__(self, value: ArrayLike) -> None:
        """Wrap linear values; negative values are rejected, NaN marks a missing value.

        Raises:
            ValueError: If a value is negative.
        """
        array = _array(value)
        if np.any(array < 0):
            msg = "linear acoustic quantities cannot be negative"
            raise ValueError(msg)
        object.__setattr__(self, "value", array)

    def to_db(self) -> Decibels:
        """The same quantity in decibels; zero becomes ``-inf``."""
        with np.errstate(divide="ignore"):
            return Decibels(10.0 * np.log10(self.value))

    def mean(self, axis: int | tuple[int, ...] | None = None) -> Linear:
        """Mean over ``axis`` (all values by default), ignoring missing values."""
        return Linear(np.nanmean(self.value, axis=axis))

    def sum(self, axis: int | tuple[int, ...] | None = None) -> Linear:
        """Sum over ``axis`` (all values by default), ignoring missing values."""
        return Linear(np.nansum(self.value, axis=axis))

    def __add__(self, other: Linear) -> Linear:
        """Add two linear quantities, for example the echoes of two scatterers."""
        if not isinstance(other, Linear):
            return NotImplemented
        return Linear(self.value + other.value)

    def __mul__(self, factor: float) -> Linear:
        """Scale by a non-negative factor, for example a sample thickness."""
        return Linear(self.value * factor)
