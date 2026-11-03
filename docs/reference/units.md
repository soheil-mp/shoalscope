# Units and decibels

Module: `shoalscope_core.units`. Symbols and units follow MacLennan, Fernandes & Dalen (2002).

## Names carry their unit

| Quantity | Name in code and tables | Unit |
| :-- | :-- | :-- |
| Range from the transducer | `range_m` | m |
| Volume backscattering strength | `sv_db` | dB re 1 m⁻¹ |
| Volume backscattering coefficient | `sv_linear_per_m` | m⁻¹ |
| Target strength | `ts_db` | dB re 1 m² |
| Backscattering cross-section | `sigma_bs_m2` | m² |
| Nautical area scattering coefficient | `nasc_m2_per_nmi2` | m² nmi⁻² |
| Speed | `speed_mps` | m s⁻¹ |
| Frequency | `frequency_hz` | Hz |

## Average in the linear domain

The mean of decibel values is biased low whenever the values vary: two pings at −60 and
−70 dB average to −62.6 dB, not −65 dB. Two wrappers make the rule part of the types:

| Type | Can do | Cannot do |
| :-- | :-- | :-- |
| `Decibels` | `to_linear()`; add or subtract a plain dB offset (a calibration correction) | `mean`, `sum`, adding another quantity |
| `Linear` | `mean()`, `sum()` (missing values ignored), add another `Linear`, scale; `to_db()` | hold negative values |

```python
from shoalscope_core.units import Decibels

pings = Decibels([-60.0, -70.0])
pings.to_linear().mean().to_db().value  # -62.6
```

Echo integration (`shoalscope_proc.integration`) converts Sv with `Decibels.to_linear()` before
it sums over range and averages over pings.
