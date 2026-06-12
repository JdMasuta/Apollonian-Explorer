/**
 * ColorMetricPicker - choose the per-circle coloring metric.
 *
 * Reference: REVAMP_BLUEPRINT.md Phase 2.3 / Milestone 4. The metric is
 * evaluated in the projection worker (src/workers/projection.ts).
 */

import { useState } from 'react';
import { MenuItem, Stack, TextField } from '@mui/material';
import rendererClient from '../../renderer/rendererClient';
import type { ColorMetric } from '../../workers/projection';

const METRICS: { value: ColorMetric['kind']; label: string }[] = [
  { value: 'generation', label: 'Generation depth' },
  { value: 'logCurvature', label: 'log |curvature|' },
  { value: 'residue', label: 'Bend residue mod m' },
  { value: 'parity', label: 'Bend parity' },
  { value: 'prime', label: 'Prime bends' },
  { value: 'limb', label: 'Group generator limb' },
];

export function ColorMetricPicker() {
  const [kind, setKind] = useState<ColorMetric['kind']>('generation');
  const [modulus, setModulus] = useState(24);

  const apply = (nextKind: ColorMetric['kind'], nextModulus: number) => {
    const metric: ColorMetric =
      nextKind === 'residue'
        ? { kind: 'residue', modulus: Math.max(2, nextModulus) }
        : ({ kind: nextKind } as ColorMetric);
    rendererClient.setMetric(metric);
  };

  return (
    <Stack direction="row" spacing={1}>
      <TextField
        select
        size="small"
        fullWidth
        label="Color by"
        value={kind}
        onChange={(e) => {
          const next = e.target.value as ColorMetric['kind'];
          setKind(next);
          apply(next, modulus);
        }}
      >
        {METRICS.map((m) => (
          <MenuItem key={m.value} value={m.value}>
            {m.label}
          </MenuItem>
        ))}
      </TextField>
      {kind === 'residue' && (
        <TextField
          size="small"
          type="number"
          label="m"
          sx={{ width: 90 }}
          value={modulus}
          inputProps={{ min: 2, max: 1000 }}
          onChange={(e) => {
            const next = Math.max(2, parseInt(e.target.value) || 24);
            setModulus(next);
            apply('residue', next);
          }}
        />
      )}
    </Stack>
  );
}

export default ColorMetricPicker;
