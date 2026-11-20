"""Slit and bar position conversions, including pairs with one bar placed."""

from pathlib import Path

import pytest
import yaml

from lris2csu.geometry import BarConfig, BarPairConfig, CSUHardwareConfig

CONFIG = Path(__file__).resolve().parents[1] / "lris2csu" / "config" / "csu.yaml"
UM_PER_COUNT = 0.03942899


def csu(pairs: list[BarPairConfig]) -> CSUHardwareConfig:
    """Return a CSU of the given pairs."""
    return CSUHardwareConfig("eth0", pairs, None, None)


@pytest.fixture(name="mixed")
def fixture_mixed() -> CSUHardwareConfig:
    """Return one full pair, one with only a left bar and one with only a right bar."""
    return csu([
        BarPairConfig(1, left=BarConfig(10, offset_mm=18.48),
                      right=BarConfig(11, reversed=True, offset_mm=8.16)),
        BarPairConfig(2, left=BarConfig(20, reversed=True, offset_mm=10.32)),
        BarPairConfig(3, right=BarConfig(31, offset_mm=4.0)),
    ])


def test_shipped_config_round_trips_through_counts() -> None:
    """The shipped twelve pairs map slits to counts and back."""
    with CONFIG.open(encoding="utf-8") as stream:
        config = yaml.full_load(stream)["hardware"]
    slits = {pair: (130.0 + pair, 20.0) for pair in config.bar_pairs}
    counts = config.compute_bar_count_positions(slits)
    assert len(counts) == 24
    for pair, (position, width) in config.compute_pos_width_dict(counts).items():
        assert position == pytest.approx(slits[pair][0], abs=UM_PER_COUNT / 1000)
        assert width == pytest.approx(slits[pair][1], abs=UM_PER_COUNT / 500)


def test_full_pair_travel(mixed: CSUHardwareConfig) -> None:
    """Each bar travels from its own side, negated when reversed."""
    travel = mixed.compute_bar_mm_positions({1: (100.0, 20.0)})
    assert travel == {10: pytest.approx(90.0 - 18.48), 11: pytest.approx(-(260 - 110.0 - 8.16))}


def test_mm_round_trip_for_full_and_one_bar_pairs(mixed: CSUHardwareConfig) -> None:
    """Slits come back from bar positions for full and one-bar pairs alike."""
    slits = {1: (100.0, 20.0), 2: (155.0, 210.0), 3: (20.0, 40.0)}
    back = mixed.compute_pos_width_dict_mm(mixed.compute_bar_mm_positions(slits))
    assert back == {pair: pytest.approx(slit) for pair, slit in slits.items()}


def test_one_bar_pair_moves_only_its_bar(mixed: CSUHardwareConfig) -> None:
    """A pair with only a left bar commands that bar alone."""
    assert set(mixed.compute_bar_mm_positions({2: (155.0, 210.0)})) == {20}


@pytest.mark.parametrize("slit", [(30.0, 40.0), (130.0, 20.0)])
def test_slit_needing_a_missing_right_bar_is_rejected(mixed: CSUHardwareConfig,
                                                      slit: tuple[float, float]) -> None:
    """Pair 2 has no right bar, so its slit must end at 260 mm."""
    with pytest.raises(ValueError, match="no right bar"):
        mixed.compute_bar_mm_positions({2: slit})


def test_slit_needing_a_missing_left_bar_is_rejected(mixed: CSUHardwareConfig) -> None:
    """Pair 3 has no left bar, so its slit must start at 0 mm."""
    with pytest.raises(ValueError, match="no left bar"):
        mixed.compute_bar_mm_positions({3: (200.0, 20.0)})


@pytest.mark.parametrize("slit", [(5.0, 20.0), (255.0, 20.0), (100.0, -1.0)])
def test_slit_outside_the_opening_is_rejected(mixed: CSUHardwareConfig,
                                              slit: tuple[float, float]) -> None:
    """Edges past the opening and negative widths never reach a bar."""
    with pytest.raises(ValueError):
        mixed.compute_bar_count_positions({1: slit})


def test_unknown_pair_is_a_key_error(mixed: CSUHardwareConfig) -> None:
    """An unconfigured pair id raises KeyError, as before."""
    with pytest.raises(KeyError):
        mixed.compute_bar_mm_positions({9: (100.0, 20.0)})


def test_pair_without_bars_is_rejected() -> None:
    """A pair must have at least one bar."""
    with pytest.raises(ValueError):
        BarPairConfig(1)


def test_one_bar_pair_survives_yaml() -> None:
    """A pair with only a left bar dumps and loads."""
    loaded = yaml.full_load(yaml.dump(BarPairConfig(4, left=BarConfig(7, offset_mm=1.5))))
    assert loaded.right is None
    assert loaded.left.offset_mm == 1.5
