from shoalscope_core.tables import NASC_CELLS


def test_nasc_contract_has_unique_named_columns() -> None:
    names = NASC_CELLS.names
    assert len(names) == len(set(names))
    assert NASC_CELLS.partition_by_day in names
    nasc = next(c for c in NASC_CELLS.columns if c.name == "nasc_m2_per_nmi2")
    assert (nasc.type, nasc.unit) == ("double", "m2 nmi-2")
