"""
Duplicate-free enumeration of an Apollonian packing.

Reference: REVAMP_BLUEPRINT.md Phase 2.0 / Milestone 1-2.

The Apollonian group is the free product ℤ/2 ∗ ℤ/2 ∗ ℤ/2 ∗ ℤ/2 on the four
swap reflections S₁..S₄. A *reduced word* never repeats the generator just
applied, and reduced words are in bijection with the circles of the packing.
Walking that tree therefore enumerates every circle exactly once:

- no hashing, no float-tolerance deduplication (the legacy generator's
  O(n²) weak point — ISSUES.md Issue #3 disappears structurally),
- O(1) exact arithmetic per circle (four scalar additions per coordinate).

Float mirrors: alongside each exact quartet the walk maintains a parallel
float quadruple, updated with the same ℤ-linear reflection. Every emitted
circle therefore carries float center/radius/curvature computed with plain
double arithmetic — no SymPy ``evalf`` in the loop (the per-circle evalf was
the depth-10 CPU burner, DEBUG_LOG ERR-014). Exact vectors remain the source
of truth; floats are presentation/pruning aids only.

Budgets make the walk output-sensitive: by depth (word length), curvature or
radius (resolution), and total count. Radius pruning cuts whole subtrees,
which is what viewport-driven generation (Milestone 2) builds on.
"""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass
from typing import Iterator, Optional, Tuple

from core.engine.group import Quartet, reflect
from core.engine.inversive import InversiveCircle

#: Float mirror of an inversive vector: (cocurvature, curvature, kx, ky).
FloatVec = Tuple[float, float, float, float]
FloatQuartet = Tuple[FloatVec, FloatVec, FloatVec, FloatVec]


@dataclass(frozen=True)
class WalkBudget:
    """Limits for a packing walk. ``None`` disables a limit.

    Attributes:
        max_depth: maximum reduced-word length (generation).
        max_curvature: prune circles with curvature above this bound, along
            with their entire subtree. In a packing walk, curvatures are
            non-decreasing along reduced words once positive, so subtree
            pruning is sound for bounded packings.
        min_radius: resolution bound — prune circles with radius below this
            (model units), along with their subtree. Equivalent to
            ``max_curvature = 1/min_radius`` but expressed in the units the
            rendering layer uses. Lines (zero curvature) are never pruned.
        max_circles: hard cap on the number of circles yielded (including
            the four seed circles).
    """

    max_depth: Optional[int] = None
    max_curvature: Optional[float] = None
    min_radius: Optional[float] = None
    max_circles: Optional[int] = None


@dataclass(frozen=True)
class GeneratedCircle:
    """A circle produced by the walk, with provenance and float mirrors.

    Attributes:
        circle: the exact inversive-coordinate vector (source of truth).
        generation: reduced word length (0 for the four seed circles).
        word: the reduced word as a string of generator indices '0'-'3'
            (most recent generator last); '' for seed circles.
        seed_index: for seed circles, their index 0-3 in the root quartet;
            for generated circles, the quartet slot the reflection replaced
            (equal to the last letter of ``word``).
        curvature_f: float curvature (0.0 for lines).
        x_f, y_f: float center; ``None`` for lines.
        r_f: float radius; ``None`` for lines.
    """

    circle: InversiveCircle
    generation: int
    word: str
    seed_index: int
    curvature_f: float = 0.0
    x_f: Optional[float] = None
    y_f: Optional[float] = None
    r_f: Optional[float] = None


def _float_vec(circle: InversiveCircle) -> FloatVec:
    """Float mirror of an exact vector. The only place float(exact) happens
    (once per seed circle, not per generated circle)."""
    return (
        float(circle.cocurvature),
        float(circle.curvature),
        float(circle.kx),
        float(circle.ky),
    )


def _reflect_float(quartet: FloatQuartet, j: int) -> FloatVec:
    """The reflection Sⱼ on the float mirror: vⱼ' = 2(vₐ+v_b+v_c) − vⱼ."""
    vj = quartet[j]
    others = [quartet[m] for m in range(4) if m != j]
    return (
        2.0 * (others[0][0] + others[1][0] + others[2][0]) - vj[0],
        2.0 * (others[0][1] + others[1][1] + others[2][1]) - vj[1],
        2.0 * (others[0][2] + others[1][2] + others[2][2]) - vj[2],
        2.0 * (others[0][3] + others[1][3] + others[2][3]) - vj[3],
    )


def _record(
    circle: InversiveCircle,
    vec: FloatVec,
    generation: int,
    word: str,
    seed_index: int,
) -> GeneratedCircle:
    """Build a GeneratedCircle with float mirrors derived from ``vec``."""
    b_f = vec[1]
    if circle.is_line or b_f == 0.0:
        return GeneratedCircle(
            circle=circle,
            generation=generation,
            word=word,
            seed_index=seed_index,
            curvature_f=0.0,
        )
    return GeneratedCircle(
        circle=circle,
        generation=generation,
        word=word,
        seed_index=seed_index,
        curvature_f=b_f,
        x_f=vec[2] / b_f,
        y_f=vec[3] / b_f,
        r_f=1.0 / abs(b_f),
    )


def replay_word(seed: Quartet, word: str) -> Tuple[Quartet, FloatQuartet]:
    """Reconstruct the walk-tree node state for a reduced word.

    Words are the circles' identities (schema v2), so any cached circle's
    local neighborhood can be re-derived in O(len(word)) reflections — this
    is what viewport-driven deepening resumes from.

    Raises:
        ValueError: for non-reduced words or invalid generator letters.
    """
    quartet = seed
    floats: FloatQuartet = (
        _float_vec(seed[0]),
        _float_vec(seed[1]),
        _float_vec(seed[2]),
        _float_vec(seed[3]),
    )
    last = -1
    for letter in word:
        if letter not in "0123":
            raise ValueError(f"Invalid generator letter {letter!r} in word {word!r}")
        j = int(letter)
        if j == last:
            raise ValueError(f"Word {word!r} is not reduced (repeats generator {j})")
        new_circle = reflect(quartet, j)
        new_vec = _reflect_float(floats, j)
        members = list(quartet)
        members[j] = new_circle
        quartet = (members[0], members[1], members[2], members[3])
        new_floats = list(floats)
        new_floats[j] = new_vec
        floats = (new_floats[0], new_floats[1], new_floats[2], new_floats[3])
        last = j
    return quartet, floats


def walk(
    seed: Quartet,
    budget: WalkBudget = WalkBudget(max_depth=5),
    start_word: str = "",
) -> Iterator[GeneratedCircle]:
    """Breadth-first spanning-tree walk of the packing.

    Yields every circle of the packing reachable within the budget exactly
    once, starting with the four seed circles, in generation order.

    Args:
        seed: root quartet of mutually tangent circles (see core.engine.seeds).
        budget: walk limits; the default stops at generation 5. ``max_depth``
            is an ABSOLUTE generation bound (word length), also with a
            non-empty start_word.
        start_word: resume the walk at this tree node instead of the root:
            only circles whose words extend start_word are yielded (the
            node's subtree — the packing detail local to that circle). The
            four seed circles and the node circle itself are NOT re-yielded.

    Yields:
        GeneratedCircle records in BFS (generation) order.
    """
    if start_word:
        quartet0, floats0 = replay_word(seed, start_word)
        count = 0
        if budget.max_depth is not None and len(start_word) >= budget.max_depth:
            return
        queue: deque[Tuple[Quartet, FloatQuartet, int, int, str]] = deque()
        queue.append(
            (quartet0, floats0, int(start_word[-1]), len(start_word), start_word)
        )
    else:
        float_seed: FloatQuartet = (
            _float_vec(seed[0]),
            _float_vec(seed[1]),
            _float_vec(seed[2]),
            _float_vec(seed[3]),
        )

        count = 0
        for index, circle in enumerate(seed):
            if budget.max_circles is not None and count >= budget.max_circles:
                return
            yield _record(circle, float_seed[index], 0, "", index)
            count += 1

        if budget.max_depth is not None and budget.max_depth <= 0:
            return

        # Queue entries: (exact quartet, float quartet, last generator, depth, word).
        queue = deque()
        queue.append((seed, float_seed, -1, 0, ""))

    while queue:
        quartet, floats, last, depth, word = queue.popleft()
        for j in range(4):
            if j == last:
                continue  # reduced words only: never undo the last reflection
            new_vec = _reflect_float(floats, j)
            b_f = new_vec[1]

            # Resolution / curvature pruning on the float mirror (cuts the
            # whole subtree; sound because bends are non-decreasing along
            # reduced words once positive).
            if budget.max_curvature is not None and b_f > budget.max_curvature:
                continue
            if budget.min_radius is not None and b_f != 0.0:
                if 1.0 / abs(b_f) < budget.min_radius:
                    continue

            if budget.max_circles is not None and count >= budget.max_circles:
                return

            new_circle = reflect(quartet, j)
            new_word = word + str(j)
            yield _record(new_circle, new_vec, depth + 1, new_word, j)
            count += 1

            if budget.max_depth is None or depth + 1 < budget.max_depth:
                members = list(quartet)
                members[j] = new_circle
                new_floats = list(floats)
                new_floats[j] = new_vec
                queue.append(
                    (
                        (members[0], members[1], members[2], members[3]),
                        (new_floats[0], new_floats[1], new_floats[2], new_floats[3]),
                        j,
                        depth + 1,
                        new_word,
                    )
                )
