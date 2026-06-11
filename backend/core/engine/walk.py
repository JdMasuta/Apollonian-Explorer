"""
Duplicate-free enumeration of an Apollonian packing.

Reference: REVAMP_BLUEPRINT.md Phase 2.0 / Milestone 1.

The Apollonian group is the free product ℤ/2 ∗ ℤ/2 ∗ ℤ/2 ∗ ℤ/2 on the four
swap reflections S₁..S₄. A *reduced word* never repeats the generator just
applied, and reduced words are in bijection with the circles of the packing.
Walking that tree therefore enumerates every circle exactly once:

- no hashing, no float-tolerance deduplication (the legacy generator's
  O(n²) weak point — ISSUES.md Issue #3 disappears structurally),
- O(1) exact arithmetic per circle (four scalar additions per coordinate).

Budgets make the walk output-sensitive: by depth (word length), curvature
(resolution), and total count. Curvature pruning cuts whole subtrees, which
is what viewport-driven generation (Milestone 2) builds on.
"""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass
from typing import Iterator, Optional, Tuple

from core.engine.group import Quartet, reflect
from core.engine.inversive import InversiveCircle


@dataclass(frozen=True)
class WalkBudget:
    """Limits for a packing walk. ``None`` disables a limit.

    Attributes:
        max_depth: maximum reduced-word length (generation).
        max_curvature: prune circles with curvature above this bound, along
            with their entire subtree. In a packing walk, curvatures are
            non-decreasing along reduced words once positive, so subtree
            pruning is sound for bounded packings.
        max_circles: hard cap on the number of circles yielded (including
            the four seed circles).
    """

    max_depth: Optional[int] = None
    max_curvature: Optional[float] = None
    max_circles: Optional[int] = None


@dataclass(frozen=True)
class GeneratedCircle:
    """A circle produced by the walk, with its provenance.

    Attributes:
        circle: the exact inversive-coordinate vector.
        generation: reduced word length (0 for the four seed circles).
        word: the reduced word as a string of generator indices '0'-'3'
            (most recent generator last); '' for seed circles.
        seed_index: for seed circles, their index 0-3 in the root quartet;
            for generated circles, the quartet slot the reflection replaced
            (equal to the last letter of ``word``).
    """

    circle: InversiveCircle
    generation: int
    word: str
    seed_index: int


def walk(seed: Quartet, budget: WalkBudget = WalkBudget(max_depth=5)) -> Iterator[GeneratedCircle]:
    """Breadth-first spanning-tree walk of the packing.

    Yields every circle of the packing reachable within the budget exactly
    once, starting with the four seed circles, in generation order.

    Args:
        seed: root quartet of mutually tangent circles (see core.engine.seeds).
        budget: walk limits; the default stops at generation 5.

    Yields:
        GeneratedCircle records in BFS (generation) order.
    """
    count = 0
    for index, circle in enumerate(seed):
        if budget.max_circles is not None and count >= budget.max_circles:
            return
        yield GeneratedCircle(circle=circle, generation=0, word="", seed_index=index)
        count += 1

    if budget.max_depth is not None and budget.max_depth <= 0:
        return

    # Queue entries: (quartet, last generator applied or -1, depth, word).
    queue: deque[Tuple[Quartet, int, int, str]] = deque()
    queue.append((seed, -1, 0, ""))

    while queue:
        quartet, last, depth, word = queue.popleft()
        for j in range(4):
            if j == last:
                continue  # reduced words only: never undo the last reflection
            new_circle = reflect(quartet, j)

            if budget.max_curvature is not None:
                if float(new_circle.curvature) > budget.max_curvature:
                    continue  # prune the whole subtree below this reflection

            if budget.max_circles is not None and count >= budget.max_circles:
                return
            new_word = word + str(j)
            yield GeneratedCircle(
                circle=new_circle, generation=depth + 1, word=new_word, seed_index=j
            )
            count += 1

            if budget.max_depth is None or depth + 1 < budget.max_depth:
                members = list(quartet)
                members[j] = new_circle
                queue.append(((members[0], members[1], members[2], members[3]), j, depth + 1, new_word))
