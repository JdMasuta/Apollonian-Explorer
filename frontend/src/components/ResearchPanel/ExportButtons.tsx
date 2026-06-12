/**
 * ExportButtons - download the circle table for external analysis.
 *
 * Reference: REVAMP_BLUEPRINT.md Phase 2.4 / Milestone 4. Streams from
 * GET /api/gaskets/{id}/export (CSV / JSON with exact strings, float
 * mirrors, residues mod 24, prime-bend tags, reproducibility metadata).
 */

import { Button, Stack } from '@mui/material';
import DownloadIcon from '@mui/icons-material/Download';

export interface ExportButtonsProps {
  gasketId: number | null;
}

export function ExportButtons({ gasketId }: ExportButtonsProps) {
  const open = (format: 'csv' | 'json') => {
    if (gasketId === null) return;
    window.open(`/api/gaskets/${gasketId}/export?format=${format}`, '_blank');
  };

  return (
    <Stack direction="row" spacing={1}>
      <Button
        size="small"
        variant="outlined"
        startIcon={<DownloadIcon />}
        disabled={gasketId === null}
        onClick={() => open('csv')}
      >
        CSV
      </Button>
      <Button
        size="small"
        variant="outlined"
        startIcon={<DownloadIcon />}
        disabled={gasketId === null}
        onClick={() => open('json')}
      >
        JSON
      </Button>
    </Stack>
  );
}

export default ExportButtons;
