/**
 * Exact rational arithmetic over BigInt, for the deep-zoom camera.
 *
 * Reference: REVAMP_BLUEPRINT.md Milestone 3 (exact camera + origin rebasing).
 *
 * float64 has ~16 significant digits of *relative* precision, so positioning
 * circles at zoom 10^12 with absolute world coordinates is impossible. The
 * camera therefore keeps its anchor (origin) as an exact rational; circle
 * positions are computed as exact differences against that anchor and only
 * the small residual is converted to float (pixel-exact at any zoom).
 *
 * Invariants: denominator > 0, fraction fully reduced.
 */

export interface BigRational {
  /** Numerator (sign carrier). */
  n: bigint;
  /** Denominator, always > 0. */
  d: bigint;
}

export const ZERO: BigRational = { n: 0n, d: 1n };

function gcd(a: bigint, b: bigint): bigint {
  let x = a < 0n ? -a : a;
  let y = b < 0n ? -b : b;
  while (y) {
    const t = x % y;
    x = y;
    y = t;
  }
  return x;
}

/** Normalize: reduce and keep the denominator positive. */
export function normalize(n: bigint, d: bigint): BigRational {
  if (d === 0n) {
    throw new Error('BigRational: zero denominator');
  }
  if (d < 0n) {
    n = -n;
    d = -d;
  }
  if (n === 0n) {
    return { n: 0n, d: 1n };
  }
  const g = gcd(n, d);
  return { n: n / g, d: d / g };
}

/** Parse "p/q" or "p" (the backend's exact wire format). */
export function fromString(value: string): BigRational {
  const slash = value.indexOf('/');
  if (slash === -1) {
    return normalize(BigInt(value.trim()), 1n);
  }
  const num = BigInt(value.slice(0, slash).trim());
  const den = BigInt(value.slice(slash + 1).trim());
  return normalize(num, den);
}

/**
 * Exact conversion of a float64 (every finite double is a dyadic rational).
 */
export function fromNumber(value: number): BigRational {
  if (!Number.isFinite(value)) {
    throw new Error(`BigRational.fromNumber: non-finite value ${value}`);
  }
  let x = value;
  let exp = 0n;
  // Scale by 2 until integral (≤ ~1075 iterations for subnormals).
  while (!Number.isInteger(x)) {
    x *= 2;
    exp += 1n;
  }
  return normalize(BigInt(x), 2n ** exp);
}

export function add(a: BigRational, b: BigRational): BigRational {
  return normalize(a.n * b.d + b.n * a.d, a.d * b.d);
}

export function sub(a: BigRational, b: BigRational): BigRational {
  return normalize(a.n * b.d - b.n * a.d, a.d * b.d);
}

export function mul(a: BigRational, b: BigRational): BigRational {
  return normalize(a.n * b.n, a.d * b.d);
}

export function neg(a: BigRational): BigRational {
  return { n: -a.n, d: a.d };
}

/** -1, 0, or 1 as a < b, a == b, a > b. */
export function cmp(a: BigRational, b: BigRational): number {
  const left = a.n * b.d;
  const right = b.n * a.d;
  if (left < right) return -1;
  if (left > right) return 1;
  return 0;
}

function bitLength(x: bigint): number {
  return x.toString(2).length;
}

/**
 * Nearest-float conversion for any magnitude (10^-300 .. 10^300), exact for
 * dyadic rationals: scale the quotient to ~63 significant bits, convert that
 * integer (JS rounds it correctly to double), then undo the scale with an
 * exact power of two.
 */
export function toNumber(a: BigRational): number {
  if (a.n === 0n) {
    return 0;
  }
  const negative = a.n < 0n;
  const n = negative ? -a.n : a.n;
  const exponent = bitLength(n) - bitLength(a.d);
  const shift = 63 - exponent;
  const q =
    shift >= 0 ? (n << BigInt(shift)) / a.d : n / (a.d << BigInt(-shift));
  let value = Number(q);
  if (shift > 0) {
    // Two exact power-of-two steps: a single 2**-shift underflows to 0 for
    // shift > ~1074 even when the final value is representable.
    const half = shift >> 1;
    value = value * 2 ** -half * 2 ** -(shift - half);
  } else {
    value = value * 2 ** -shift;
  }
  return negative ? -value : value;
}

/** Serialize for postMessage / debugging ("n/d"). */
export function toFractionString(a: BigRational): string {
  return `${a.n}/${a.d}`;
}
