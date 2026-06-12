/**
 * AnalyticsPanel - research statistics for the current gasket.
 *
 * Reference: REVAMP_BLUEPRINT.md Phase 2.4 / Milestone 4.
 *
 * Renders the backend's /api/gaskets/{id}/analytics payload:
 * - bend (curvature) histogram,
 * - counting function N(T) on log-log axes,
 * - the fitted growth exponent vs the Hausdorff dimension δ ≈ 1.305688
 *   (Kontorovich–Oh / McMullen). The estimate converges from below as the
 *   cached packing deepens.
 */

import { useEffect, useState } from 'react';
import { Alert, Box, Skeleton, Stack, Typography } from '@mui/material';
import { BarChart } from '@mui/x-charts/BarChart';
import { LineChart } from '@mui/x-charts/LineChart';

export interface AnalyticsData {
  gasket_id: number;
  total_circles: number;
  histogram: { bin_edges: number[]; counts: number[] };
  counting_function: { T: number; N: number }[];
  dimension_estimate: number | null;
  dimension_reference: number;
}

export interface AnalyticsPanelProps {
  gasketId: number | null;
  /** Bump to re-fetch (e.g. after deepening). */
  refreshKey?: number;
}

export function AnalyticsPanel({ gasketId, refreshKey = 0 }: AnalyticsPanelProps) {
  const [data, setData] = useState<AnalyticsData | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (gasketId === null) {
      setData(null);
      return;
    }
    let cancelled = false;
    setLoading(true);
    setError(null);
    fetch(`/api/gaskets/${gasketId}/analytics`)
      .then((res) => {
        if (!res.ok) throw new Error(`analytics failed: ${res.status}`);
        return res.json();
      })
      .then((payload) => {
        if (!cancelled) setData(payload);
      })
      .catch((err) => {
        if (!cancelled) setError(err instanceof Error ? err.message : String(err));
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [gasketId, refreshKey]);

  if (gasketId === null) {
    return (
      <Typography color="text.secondary" variant="body2">
        Generate a gasket to see curvature statistics.
      </Typography>
    );
  }
  if (loading && !data) {
    return <Skeleton variant="rectangular" height={220} data-testid="analytics-loading" />;
  }
  if (error) {
    return <Alert severity="error">{error}</Alert>;
  }
  if (!data) {
    return null;
  }

  const histogramLabels = data.histogram.counts.map((_, i) => {
    const lo = data.histogram.bin_edges[i];
    return lo >= 1000 ? lo.toExponential(1) : lo.toFixed(0);
  });
  const counting = data.counting_function.filter((p) => p.T > 0 && p.N > 0);

  return (
    <Stack direction={{ xs: 'column', md: 'row' }} spacing={2}>
      <Box sx={{ flex: 1, minWidth: 0 }}>
        <Typography variant="subtitle2">Bend histogram</Typography>
        <BarChart
          height={220}
          xAxis={[{ data: histogramLabels, scaleType: 'band', label: 'bend (bin start)' }]}
          series={[{ data: data.histogram.counts, color: '#1976d2' }]}
          hideLegend
        />
      </Box>
      <Box sx={{ flex: 1, minWidth: 0 }}>
        <Typography variant="subtitle2">
          N(T) — circles with bend ≤ T (log–log)
        </Typography>
        <LineChart
          height={220}
          xAxis={[{ data: counting.map((p) => p.T), scaleType: 'log', label: 'T' }]}
          yAxis={[{ scaleType: 'log' }]}
          series={[
            {
              data: counting.map((p) => p.N),
              color: '#f57c00',
              showMark: false,
            },
          ]}
          hideLegend
        />
        <Typography variant="body2" color="text.secondary">
          Growth exponent fit:{' '}
          <strong data-testid="dimension-estimate">
            {data.dimension_estimate !== null ? data.dimension_estimate.toFixed(4) : 'n/a'}
          </strong>{' '}
          (Hausdorff dimension δ ≈ {data.dimension_reference.toFixed(6)}; the
          fit approaches δ from below as the packing deepens). Circles counted:{' '}
          {data.total_circles}.
        </Typography>
      </Box>
    </Stack>
  );
}

export default AnalyticsPanel;
