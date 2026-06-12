/**
 * TransformPanel - Möbius group actions on the packing.
 *
 * Reference: REVAMP_BLUEPRINT.md M5. Inversion in a selected circle is an
 * exact Lorentz reflection on inversive coordinates (computed server-side);
 * the transformed packing is a DIFFERENT packing, shown transiently —
 * viewport deepening is disabled until the original view is restored.
 */

import { useState } from 'react';
import { Button, Stack, Tooltip, Typography } from '@mui/material';
import FlipCameraAndroidIcon from '@mui/icons-material/FlipCameraAndroid';
import RestoreIcon from '@mui/icons-material/Restore';
import rendererClient from '../../renderer/rendererClient';
import { useGasketStore } from '../../stores/gasketStore';

export interface TransformPanelProps {
  gasketId: number | null;
}

export function TransformPanel({ gasketId }: TransformPanelProps) {
  const selectedCircle = useGasketStore((state) => state.selectedCircle);
  const transformedView = useGasketStore((state) => state.transformedView);
  const setTransformedView = useGasketStore((state) => state.setTransformedView);
  const setSelectedCircle = useGasketStore((state) => state.setSelectedCircle);
  const [busy, setBusy] = useState(false);
  const [info, setInfo] = useState<string | null>(null);

  const invertInSelected = async () => {
    if (gasketId === null || !selectedCircle) return;
    setBusy(true);
    try {
      const res = await fetch(`/api/gaskets/${gasketId}/transform`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ mirror_word: selectedCircle.word, limit: 50000 }),
      });
      if (!res.ok) throw new Error(`transform failed: ${res.status}`);
      const data = await res.json();
      rendererClient.clear();
      rendererClient.addCircles(data.circles);
      setSelectedCircle(null);
      rendererClient.setSelected(null);
      setTransformedView(true);
      setInfo(
        `Inverted in ${data.mirror_word} — ${data.count} images` +
          (data.lines > 0 ? ` (${data.lines} became lines)` : '')
      );
    } catch (err) {
      setInfo(err instanceof Error ? err.message : String(err));
    } finally {
      setBusy(false);
    }
  };

  const restore = async () => {
    if (gasketId === null) return;
    setBusy(true);
    try {
      const res = await fetch(`/api/gaskets/${gasketId}/circles?limit=50000`);
      if (!res.ok) throw new Error(`restore failed: ${res.status}`);
      const data = await res.json();
      rendererClient.clear();
      rendererClient.addCircles(data.circles);
      setTransformedView(false);
      setInfo(null);
    } catch (err) {
      setInfo(err instanceof Error ? err.message : String(err));
    } finally {
      setBusy(false);
    }
  };

  return (
    <Stack spacing={1}>
      <Stack direction="row" spacing={1}>
        <Tooltip title="Invert the whole packing in the selected circle (exact Möbius action)">
          <span style={{ flex: 1 }}>
            <Button
              size="small"
              variant="outlined"
              fullWidth
              startIcon={<FlipCameraAndroidIcon />}
              disabled={busy || gasketId === null || !selectedCircle || transformedView}
              onClick={invertInSelected}
            >
              Invert in selected
            </Button>
          </span>
        </Tooltip>
        <Button
          size="small"
          variant="outlined"
          startIcon={<RestoreIcon />}
          disabled={busy || gasketId === null || !transformedView}
          onClick={restore}
        >
          Restore
        </Button>
      </Stack>
      {info && (
        <Typography variant="caption" color="text.secondary">
          {info}
        </Typography>
      )}
    </Stack>
  );
}

export default TransformPanel;
