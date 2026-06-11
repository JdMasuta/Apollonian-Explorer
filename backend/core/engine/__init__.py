"""
Exact Apollonian generation engine (REVAMP_BLUEPRINT.md Milestone 1).

This package replaces the square-root-per-step Descartes/BFS pipeline with:

- ``inversive``: augmented curvature-center coordinates (Lagarias-Mallows-Wilks),
  in which every circle is an exact 4-vector and tangency is an exact inner
  product -- no floating-point tolerances anywhere.
- ``group``: the Apollonian group action. Reflections are integer-linear maps,
  so generation needs no square roots after seeding.
- ``seeds``: seed construction (named presets, Descartes quadruples, curvature
  triples, the Apollonian strip). The only square roots in the system are
  taken here, once, at seed time.
- ``walk``: duplicate-free spanning-tree enumeration of the packing via
  reduced words in the Apollonian group, with depth/curvature/count budgets.
- ``metrics``: research metrics (residue classes, prime bends, word data).
"""

from core.engine.inversive import Exact, InversiveCircle
from core.engine.group import reflect, reflection_coefficients
from core.engine.seeds import (
    PRESETS,
    complete_triple,
    is_descartes_quadruple,
    seed_from_preset,
    seed_from_quadruple,
    seed_from_triple,
    seed_strip,
)
from core.engine.walk import GeneratedCircle, WalkBudget, walk

__all__ = [
    "Exact",
    "InversiveCircle",
    "reflect",
    "reflection_coefficients",
    "PRESETS",
    "complete_triple",
    "is_descartes_quadruple",
    "seed_from_preset",
    "seed_from_quadruple",
    "seed_from_triple",
    "seed_strip",
    "GeneratedCircle",
    "WalkBudget",
    "walk",
]
