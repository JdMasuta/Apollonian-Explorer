/** Tests for exact BigInt rational arithmetic (deep-zoom camera support). */

import { describe, it, expect } from 'vitest';
import {
  add,
  cmp,
  fromNumber,
  fromString,
  mul,
  neg,
  normalize,
  sub,
  toFractionString,
  toNumber,
} from './rational';

describe('rational', () => {
  describe('fromString', () => {
    it('parses integers and fractions', () => {
      expect(fromString('6')).toEqual({ n: 6n, d: 1n });
      expect(fromString('-3/2')).toEqual({ n: -3n, d: 2n });
      expect(fromString('2/3')).toEqual({ n: 2n, d: 3n });
    });

    it('normalizes sign and reduces', () => {
      expect(fromString('4/-6')).toEqual({ n: -2n, d: 3n });
      expect(fromString('0/5')).toEqual({ n: 0n, d: 1n });
    });

    it('handles huge wire values exactly', () => {
      const r = fromString('123456789012345678901234567890/987654321098765432109876543210');
      expect(toFractionString(mul(r, fromString('987654321098765432109876543210')))).toBe(
        '123456789012345678901234567890/1'
      );
    });
  });

  describe('fromNumber', () => {
    it('is exact for dyadic floats', () => {
      expect(fromNumber(0.5)).toEqual({ n: 1n, d: 2n });
      expect(fromNumber(-0.75)).toEqual({ n: -3n, d: 4n });
      expect(fromNumber(3)).toEqual({ n: 3n, d: 1n });
    });

    it('round-trips arbitrary floats exactly', () => {
      for (const x of [0.1, 1e-15, 123456.789, -2.2250738585072014e-308]) {
        expect(toNumber(fromNumber(x))).toBe(x);
      }
    });

    it('rejects non-finite values', () => {
      expect(() => fromNumber(Infinity)).toThrow();
      expect(() => fromNumber(NaN)).toThrow();
    });
  });

  describe('arithmetic', () => {
    it('adds and subtracts exactly', () => {
      const a = fromString('1/3');
      const b = fromString('1/6');
      expect(add(a, b)).toEqual({ n: 1n, d: 2n });
      expect(sub(a, b)).toEqual({ n: 1n, d: 6n });
    });

    it('exact subtraction of nearby giants preserves the tiny difference', () => {
      // The whole point of the exact camera: (x − origin) survives when both
      // are ~1 and their difference is ~1e-30.
      const origin = fromString('1/1');
      const x = add(origin, fromString('1/1000000000000000000000000000000'));
      const diff = sub(x, origin);
      expect(toFractionString(diff)).toBe('1/1000000000000000000000000000000');
      expect(toNumber(diff)).toBeCloseTo(1e-30, 35);
    });

    it('mul and neg', () => {
      expect(mul(fromString('2/3'), fromString('3/4'))).toEqual({ n: 1n, d: 2n });
      expect(neg(fromString('2/3'))).toEqual({ n: -2n, d: 3n });
    });

    it('cmp orders correctly', () => {
      expect(cmp(fromString('1/3'), fromString('1/2'))).toBe(-1);
      expect(cmp(fromString('2/4'), fromString('1/2'))).toBe(0);
      expect(cmp(fromString('-1/3'), fromString('-1/2'))).toBe(1);
    });
  });

  describe('toNumber', () => {
    it('is accurate for values with huge numerator/denominator', () => {
      const r = normalize(10n ** 40n + 5n * 10n ** 39n, 10n ** 40n); // 1.5
      expect(toNumber(r)).toBe(1.5);
    });

    it('handles negative values', () => {
      expect(toNumber(fromString('-7/2'))).toBe(-3.5);
    });
  });

  describe('normalize', () => {
    it('rejects zero denominators', () => {
      expect(() => normalize(1n, 0n)).toThrow();
    });
  });
});
