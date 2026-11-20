"""CSU bar and bar pair configuration and the slit geometry it implies, without hardware access.

A pair is the left and right bar of one row. A pair may have only one bar
placed; its slit then runs from that bar's edge to the far end of the opening.
"""
# The YAML keys id and reversed are constructor arguments
# pylint: disable=redefined-builtin

from logging import getLogger
from typing import Any

import yaml

# Slack when matching a one-bar pair's slit edge to the end of the opening
EDGE_TOLERANCE_MM = 1e-6

PosWidth = dict[int, tuple[float, float]]


class CSUHardwareConfig:
    """The bar pairs of the CSU and the conversions between slits and bar positions."""

    yaml_tag = '!CSUHardwareConfig'

    def __init__(self, ethercat_device: str, bar_pairs: list["BarPairConfig"],
                 left_brake: Any, right_brake: Any) -> None:
        self.ethercat_device = ethercat_device
        self.bar_pairs = {x.id: x for x in bar_pairs}
        self.left_brake = left_brake
        self.right_brake = right_brake
        self.opening_width_mm = 260

    @classmethod
    def from_yaml(cls, loader: Any, node: yaml.Node) -> "CSUHardwareConfig":
        """Build from a !CSUHardwareConfig YAML node."""
        # Construct mapping from the YAML node
        values: dict[str, Any] = loader.construct_mapping(node, deep=True)
        return cls(**values)

    @classmethod
    def to_yaml(cls, dumper: yaml.Dumper, data: "CSUHardwareConfig") -> yaml.MappingNode:
        """Represent as a !CSUHardwareConfig YAML node."""
        # Convert the Python object into a mapping
        mapping = {
            'ethercat_device': data.ethercat_device,
            'bar_pairs': data.bar_pairs,
            'left_brake': data.left_brake,
            'right_brake': data.right_brake,
        }
        return dumper.represent_mapping(cls.yaml_tag, mapping)

    @property
    def bar_configs(self) -> dict[int, "BarConfig"]:
        """Return every placed bar keyed by bus id."""
        return {b.bus_id: b for bp in self.bar_pairs.values() for b in (bp.left, bp.right)
                if b is not None}

    def bar_by_dev_id(self, id: int) -> "BarConfig":
        """Return the bar at a bus id."""
        return self.bar_configs[id]

    def validate_slits(self, pos_width_dict: PosWidth) -> None:
        """Raise if any requested (position, width) slit cannot be formed.

        Raises:
            KeyError: a pair id is not configured.
            ValueError: a slit has negative width, leaves the opening, or needs a bar
                that is not placed.
        """
        for id, (position, width) in pos_width_dict.items():
            if id not in self.bar_pairs:
                raise KeyError(f"No bar pair with id {id} found in the bar pair configuration.")
            bar_pair = self.bar_pairs[id]
            left_edge, right_edge = position - width / 2.0, position + width / 2.0
            if width < 0:
                raise ValueError(f"Bar pair {id}: width {width} mm is negative")
            opening = self.opening_width_mm
            if left_edge < -EDGE_TOLERANCE_MM or right_edge > opening + EDGE_TOLERANCE_MM:
                raise ValueError(f"Bar pair {id}: slit {left_edge:g}..{right_edge:g} mm leaves the "
                                 f"0..{self.opening_width_mm} mm opening")
            if bar_pair.left is None and abs(left_edge) > EDGE_TOLERANCE_MM:
                raise ValueError(f"Bar pair {id} has no left bar, so its slit must start at 0 mm")
            if bar_pair.right is None and abs(right_edge - opening) > EDGE_TOLERANCE_MM:
                raise ValueError(f"Bar pair {id} has no right bar, so its slit must end at "
                                 f"{self.opening_width_mm} mm")

    def compute_bar_mm_positions(self, pos_width_dict: PosWidth) -> dict[int, float]:
        """Return each placed bar's travel in mm for the requested slits.

        Args:
            pos_width_dict: A dictionary keyed on bar pair id with a tuple (position, width) in mm.

        Returns:
            A dictionary with bus_id as keys and travel in mm as values, negated for a reversed bar.
            For the left side, travel = position - width/2 - offset_mm.
            For the right side, travel = opening - (position + width/2) - offset_mm.
        """
        self.validate_slits(pos_width_dict)
        ret = {}
        for id, (position, width) in pos_width_dict.items():
            bar_pair = self.bar_pairs[id]

            # Compute the absolute physical positions in mm for left and right.
            # lower left is origin
            if bar_pair.left is not None:
                left_mm = (position - width / 2.0) - bar_pair.left.offset_mm
                ret[bar_pair.left.bus_id] = bar_pair.left.direction * left_mm
            if bar_pair.right is not None:
                right_mm = position + width / 2.0
                right_travel_mm = self.opening_width_mm - right_mm - bar_pair.right.offset_mm
                ret[bar_pair.right.bus_id] = bar_pair.right.direction * right_travel_mm
        return ret

    def compute_bar_count_positions(self, pos_width_dict: PosWidth) -> dict[int, int]:
        """Return each placed bar's position in encoder counts for the requested slits.

        Args:
            pos_width_dict: A dictionary keyed on bar pair id with a tuple (position, width) in mm.

        Returns:
            A dictionary with bus_id as keys and the travel of compute_bar_mm_positions,
            converted with the bar's um_per_count, as values.
        """
        configs = self.bar_configs
        return {bus_id: int(round(mm * 1000 / abs(configs[bus_id].um_per_count)))
                for bus_id, mm in self.compute_bar_mm_positions(pos_width_dict).items()}

    def compute_pos_width_dict_mm(self, bar_mm_positions: dict[int, float]) -> PosWidth:
        """Inverse of compute_bar_mm_positions; skip a pair whose placed bar is not in the input."""
        ret = {}
        for id, pair in self.bar_pairs.items():
            try:
                left_edge = 0.0 if pair.left is None else (
                    pair.left.direction * bar_mm_positions[pair.left.bus_id] + pair.left.offset_mm)
                right_edge = float(self.opening_width_mm) if pair.right is None else (
                    -(pair.right.direction * bar_mm_positions[pair.right.bus_id]
                      - self.opening_width_mm + pair.right.offset_mm))
            except KeyError:
                continue
            width = right_edge - left_edge
            position = (left_edge + right_edge) / 2
            ret[id] = (position, width)
        return ret

    def compute_pos_width_dict(self, bar_positions: dict[int, int]) -> PosWidth:
        """Inverse of compute_bar_count_positions."""
        configs = self.bar_configs
        return self.compute_pos_width_dict_mm(
            {bus_id: counts * abs(configs[bus_id].um_per_count) / 1000
             for bus_id, counts in bar_positions.items() if bus_id in configs})


# Register the representer and constructor with PyYAML
yaml.add_representer(CSUHardwareConfig, CSUHardwareConfig.to_yaml)
yaml.add_constructor('!CSUHardwareConfig', CSUHardwareConfig.from_yaml)


class BarPairConfig:
    """The left and right bar of one row; either may be None when that bar is not placed."""

    yaml_tag = '!BarPairConfig'

    def __init__(self, id: int, left: "BarConfig | None" = None,
                 right: "BarConfig | None" = None) -> None:
        if left is None and right is None:
            raise ValueError(f"Bar pair {id} needs at least one bar")
        self.id = id
        self.left = left  # Expected to be a BarConfig instance
        self.right = right  # Expected to be a BarConfig instance

    def __repr__(self) -> str:
        return f"BarPairConfig(id={self.id}, left={self.left}, right={self.right})"

    @classmethod
    def from_yaml(cls, loader: Any, node: yaml.Node) -> "BarPairConfig":
        """Build from a !BarPairConfig YAML node."""
        values: dict[str, Any] = loader.construct_mapping(node, deep=True)
        return cls(**values)

    @classmethod
    def to_yaml(cls, dumper: yaml.Dumper, data: "BarPairConfig") -> yaml.MappingNode:
        """Represent as a !BarPairConfig YAML node."""
        mapping = {'id': data.id, 'left': data.left, 'right': data.right}
        return dumper.represent_mapping(cls.yaml_tag, mapping)

# Register the representer and constructor with PyYAML
yaml.add_representer(BarPairConfig, BarPairConfig.to_yaml)
yaml.add_constructor('!BarPairConfig', BarPairConfig.from_yaml)


class BarConfig:  # pylint: disable=too-many-instance-attributes
    """One bar's bus id, motion settings, scale, direction and offset."""

    yaml_tag = '!BarConfig'

    # pylint: disable-next=too-many-arguments,too-many-positional-arguments
    def __init__(self, bus_id: int, speed: int = 0, torque_limit: float = 0,
                 um_per_count: float = 1.0, reversed: bool = False,
                 offset_mm: float = 0, use_ssi_encoder: bool = False) -> None:
        self.bus_id = bus_id
        self.speed = speed
        self.torque_limit = torque_limit
        self.um_per_count = um_per_count
        self.reversed = reversed
        self.offset_mm = offset_mm
        self.use_ssi_encoder = use_ssi_encoder
        assert self.um_per_count!=0
        if self.um_per_count<0:
            assert reversed, 'If um_per_count is negative, reversed must be True'
        if reversed and self.um_per_count>0:
            getLogger(__name__).warning(
                'Inverting um_per_count (%s) for bus_id %s as reversed is set. '
                'Consider defining with a negative for better clarity.', um_per_count, bus_id)
            self.um_per_count=-self.um_per_count

    @property
    def direction(self) -> int:
        """Return -1 for a reversed bar, else 1."""
        return -1 if self.um_per_count < 0 else 1

    def __repr__(self) -> str:
        return (f"BarMotor(bus_id={self.bus_id}, speed={self.speed}, "
                f"torque_limit={self.torque_limit}, um_per_count={self.um_per_count}, "
                f"reversed={self.reversed} offset_mm={self.offset_mm} "
                f"use_ssi_encoder={self.use_ssi_encoder})")

    @classmethod
    def from_yaml(cls, loader: Any, node: yaml.Node) -> "BarConfig":
        """Build from a !BarConfig YAML node."""
        # Create a dictionary from the YAML node.
        values: dict[str, Any] = loader.construct_mapping(node, deep=True)
        # Manual initialization from parameters.
        return cls(**values)

    @classmethod
    def to_yaml(cls, dumper: yaml.Dumper, data: "BarConfig") -> yaml.MappingNode:
        """Represent as a !BarConfig YAML node."""
        # Convert the BarMotor instance back into a YAML mapping.
        mapping = {
            'bus_id': data.bus_id,
            'speed': data.speed,
            'torque_limit': data.torque_limit,
            'um_per_count': data.um_per_count,
            'reversed': data.reversed,
            'offset_mm': data.offset_mm,
            'use_ssi_encoder': data.use_ssi_encoder,
        }
        return dumper.represent_mapping(cls.yaml_tag, mapping)


# Register the representer and constructor with PyYAML.
yaml.add_representer(BarConfig, BarConfig.to_yaml)
yaml.add_constructor('!BarConfig', BarConfig.from_yaml)
