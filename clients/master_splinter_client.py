"""The only module in ``api`` that imports ``master_splinter`` directly.

Keeping every other module behind this seam means the processors can be
tested against a stub client, and a future change to the library's internal
shape only has to be absorbed here.

"""

import random

from master_splinter.model.dive_state import DiveState
from master_splinter.model.splinter_decompression import (
    ambient_pressure_at_depth,
    tolerated_ambient_pressure,
)
from master_splinter.processors.altitude_analysis import (
    AltitudeReport,
    analyse_altitude_change,
)
from master_splinter.processors.dive_analysis import (
    DiveReport,
    analyse_profile,
)
from master_splinter.processors.dive_simulation import generate_dive_profile


def run_profile_analysis(
    boundaries,
    *,
    seed: int,
    gas_fraction: float,
    gf_low: float,
    gf_high: float,
    ppo2_limit: float,
    ascent_rate: float,
    surface_pressure: float,
) -> DiveReport:
    """Generates a profile from ``boundaries`` and analyses it.

    Seeding happens immediately before generation, matching
    ``cli/profile_analyser.py`` and ``master-splinter-web/src/glue.py``: the
    variation baked into the profile is drawn during generation, so nothing
    between the seed and the call may consume the random stream.

    """
    random.seed(seed)
    profile = generate_dive_profile(boundaries)

    state = DiveState.at_surface(
        gf_low=gf_low,
        gf_high=gf_high,
        gas_fraction=gas_fraction,
        surface_pressure=surface_pressure,
    )
    return analyse_profile(
        profile,
        state,
        ascent_rate=ascent_rate,
        ppo2_limit=ppo2_limit,
    )


def sample_ambient_pressure(depth: float, surface_pressure: float) -> float:
    """Ambient pressure at ``depth``, for enriching a reported sample."""
    return ambient_pressure_at_depth(depth, surface_pressure)


def sample_tolerated_pressure(tissues, gf_high: float) -> float:
    """Lowest ambient pressure the tissue set tolerates, at ``gf_high``."""
    return tolerated_ambient_pressure(tissues, gf_high)


def run_altitude_analysis(
    tissues,
    elevation_gain: float,
    *,
    surface_interval: float,
    gf_high: float,
    surface_pressure: float,
) -> AltitudeReport:
    """Decides whether an elevation change is safe on the given tissue set."""
    return analyse_altitude_change(
        tissues,
        elevation_gain,
        surface_interval=surface_interval,
        gf_high=gf_high,
        surface_pressure=surface_pressure,
    )
