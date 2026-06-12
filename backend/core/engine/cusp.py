"""
Parabolic (cusp) chain acceleration.

Reference: REVAMP_BLUEPRINT.md M5; ISSUES.md #6.

The circles converging to the tangency point of two circles A, B form a
chain where consecutive members satisfy the swap relation in the quartet
(A, B, C_{n-1}, C_n):

    C_{n+1} = 2(A + B + C_n) − C_{n−1}

a linear three-term recurrence with doubled characteristic root 1 — the
algebraic shadow of the parabolic Möbius transformation fixing the cusp.
Its exact closed form is

    C_n = C_0 + n·V + n²·(A+B),   V = C_1 − C_0 − (A+B)

so chain element n costs O(1) exact operations instead of O(n) tree steps
(bends grow quadratically along cusp chains: reaching viewport size ε at a
cusp needs word length ~ 1/√ε·…, which is why the word-replay deepener
cannot serve cusp zooms — this module can).

Tree words: when (A, B, C_{-1}, C_0) is the quartet at tree node w, chain
element words are w followed by the slot letters of C_{-1} and C_0
alternating: C_k (k ≥ 1) appends k letters starting with C_{-1}'s slot;
C_{-(k+1)} (k ≥ 1) appends k letters starting with C_0's slot. The first
word of each direction is verified by exact replay, so persisted identities
remain sound tree addresses (deduplicating against ordinary walks).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterator, List, Optional

from core.engine.group import Quartet
from core.engine.inversive import InversiveCircle
from core.engine.walk import GeneratedCircle, replay_word


@dataclass(frozen=True)
class CuspChainResult:
    """Chain circles (both directions) with provenance and a status flag."""

    records: List[GeneratedCircle]
    #: False when word construction hit a non-reduced step or failed replay
    #: verification (that direction is then omitted).
    verified_words: bool


def _combine(c0: InversiveCircle, v: InversiveCircle, w: InversiveCircle, n: int) -> InversiveCircle:
    """C_n = c0 + n·v + n²·w, componentwise exact."""
    n2 = n * n
    return InversiveCircle(
        c0.cocurvature + n * v.cocurvature + n2 * w.cocurvature,
        c0.curvature + n * v.curvature + n2 * w.curvature,
        c0.kx + n * v.kx + n2 * w.kx,
        c0.ky + n * v.ky + n2 * w.ky,
    )


def _record_for(circle: InversiveCircle, word: str) -> GeneratedCircle:
    b_f = float(circle.curvature)
    return GeneratedCircle(
        circle=circle,
        generation=len(word),
        word=word,
        seed_index=int(word[-1]),
        curvature_f=b_f,
        x_f=float(circle.kx) / b_f,
        y_f=float(circle.ky) / b_f,
        r_f=1.0 / abs(b_f),
    )


def _digits(word: str) -> str:
    """Tree-walkable part of a word ('' for seed words S0-S3)."""
    return "" if word.startswith("S") else word


def cusp_chain(
    seed: Quartet,
    word_a: str,
    word_b: str,
    min_radius: float,
    max_elements: int = 512,
) -> CuspChainResult:
    """Generate the cusp chain converging to the tangency point of A and B.

    A and B are addressed by their tree words ('S0'-'S3' for seed circles).
    The deeper word's node quartet contains both circles for any exactly
    tangent pair (the deeper circle's parents are the only earlier circles
    tangent to it). Both chain directions are generated until the radius
    drops below ``min_radius`` or ``max_elements`` is reached. C_{-1} and
    C_0 themselves (existing quartet members) are not re-emitted.

    Raises:
        ValueError: for invalid words, non-tangent circles, or a quartet
            that does not contain both circles.
    """

    def resolve(word: str) -> InversiveCircle:
        if word.startswith("S"):
            return seed[int(word[1])]
        quartet, _ = replay_word(seed, word)
        return quartet[int(word[-1])]

    circle_a = resolve(word_a)
    circle_b = resolve(word_b)
    if circle_a.inner(circle_b) != 1:
        raise ValueError(f"Circles {word_a!r} and {word_b!r} are not tangent (B != 1)")

    deeper = word_a if len(_digits(word_a)) >= len(_digits(word_b)) else word_b
    node_word = _digits(deeper)
    quartet = replay_word(seed, node_word)[0] if node_word else seed

    slot_a = next((m for m in range(4) if quartet[m] == circle_a), None)
    slot_b = next((m for m in range(4) if quartet[m] == circle_b), None)
    if slot_a is None or slot_b is None:
        raise ValueError(
            f"Quartet at node {node_word!r} does not contain both circles "
            f"({word_a!r}, {word_b!r})"
        )
    slot_cm1, slot_c0 = (m for m in range(4) if m not in (slot_a, slot_b))
    c_minus1 = quartet[slot_cm1]
    c_0 = quartet[slot_c0]

    # Closed form coefficients.
    ab = InversiveCircle(
        circle_a.cocurvature + circle_b.cocurvature,
        circle_a.curvature + circle_b.curvature,
        circle_a.kx + circle_b.kx,
        circle_a.ky + circle_b.ky,
    )
    c_1 = InversiveCircle(  # 2(A+B) + 2C_0 − C_{-1}
        2 * ab.cocurvature + 2 * c_0.cocurvature - c_minus1.cocurvature,
        2 * ab.curvature + 2 * c_0.curvature - c_minus1.curvature,
        2 * ab.kx + 2 * c_0.kx - c_minus1.kx,
        2 * ab.ky + 2 * c_0.ky - c_minus1.ky,
    )
    v = InversiveCircle(  # C_1 − C_0 − (A+B)
        c_1.cocurvature - c_0.cocurvature - ab.cocurvature,
        c_1.curvature - c_0.curvature - ab.curvature,
        c_1.kx - c_0.kx - ab.kx,
        c_1.ky - c_0.ky - ab.ky,
    )

    def alternating_words(first_slot: int, second_slot: int) -> Iterator[Optional[str]]:
        letters = (str(first_slot), str(second_slot))
        word = node_word
        k = 0
        while True:
            nxt = letters[k % 2]
            if word and word[-1] == nxt:
                yield None  # non-reduced step: chain overlaps ancestry
                return
            word = word + nxt
            k += 1
            yield word

    def verify(word: Optional[str], expected: InversiveCircle) -> bool:
        if word is None:
            return False
        try:
            return replay_word(seed, word)[0][int(word[-1])] == expected
        except ValueError:
            return False

    records: List[GeneratedCircle] = []
    verified = True
    # direction +1: C_1, C_2, ... ; direction −1: C_{-2}, C_{-3}, ...
    directions: List[tuple[bool, int, int]] = [
        (True, slot_cm1, slot_c0),
        (False, slot_c0, slot_cm1),
    ]
    for positive, first_slot, second_slot in directions:
        gen = alternating_words(first_slot, second_slot)
        for k in range(1, max_elements + 1):
            circle = _combine(c_0, v, ab, k if positive else -(k + 1))
            word = next(gen, None)
            if k == 1 and not verify(word, circle):
                verified = False
                break
            if word is None:
                verified = False
                break
            if circle.is_line:
                break
            b_f = float(circle.curvature)
            if b_f == 0.0 or 1.0 / abs(b_f) < min_radius:
                break
            records.append(_record_for(circle, word))
            if len(records) >= max_elements:
                break

    return CuspChainResult(records=records, verified_words=verified)
