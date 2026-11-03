import pytest
from hypothesis import given
from hypothesis import strategies as st

from shoalscope_core.levels import Level, ProcessingAttributes, configuration_hash

HASH = "a" * 64


def attributes(**overrides: object) -> ProcessingAttributes:
    values: dict[str, object] = {
        "level": Level.L2A,
        "software_version": "0.0.0",
        "calibration_set": "file",
        "environment_profile": "file",
        "configuration_hash": HASH,
    }
    return ProcessingAttributes(**(values | overrides))  # type: ignore[arg-type]


def test_levels_map_to_storage_prefixes() -> None:
    assert [level.prefix for level in Level] == ["l0", "l1", "l1", "l2", "l2", "l3", "l3", "l4"]
    assert "MVBS" in Level.L3A.description
    assert all(level.description for level in Level)


def test_metadata_round_trip() -> None:
    original = attributes(level=Level.L4)
    metadata = original.to_metadata() | {"unrelated": 1}
    assert ProcessingAttributes.from_metadata(metadata) == original
    assert set(original.to_metadata()) == {
        "shoalscope_level",
        "shoalscope_software_version",
        "shoalscope_calibration_set",
        "shoalscope_environment_profile",
        "shoalscope_configuration_hash",
    }


def test_missing_metadata_is_an_error() -> None:
    with pytest.raises(KeyError):
        ProcessingAttributes.from_metadata({"shoalscope_level": "L2A"})


@pytest.mark.parametrize(
    ("overrides", "message"),
    [
        ({"software_version": ""}, "software_version"),
        ({"calibration_set": ""}, "calibration_set"),
        ({"configuration_hash": "ABC"}, "hexadecimal"),
    ],
)
def test_rejects_invalid_attributes(overrides: dict[str, object], message: str) -> None:
    with pytest.raises(ValueError, match=message):
        attributes(**overrides)


@given(
    st.dictionaries(
        st.text(min_size=1, max_size=5), st.integers() | st.text(max_size=5), max_size=6
    )
)
def test_configuration_hash_ignores_key_order(configuration: dict[str, object]) -> None:
    reordered = dict(reversed(list(configuration.items())))
    assert configuration_hash(configuration) == configuration_hash(reordered)
    assert len(configuration_hash(configuration)) == 64


def test_configuration_hash_changes_with_values() -> None:
    assert configuration_hash({"cell_s": 60}) != configuration_hash({"cell_s": 61})
