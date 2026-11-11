/** Firm analytics, for admins. Every chart here is backed by a figure someone could act on. */
import React from 'react';
import { Box, Chip, Grid, Typography } from '@mui/material';
import { EventBusyOutlined, EventOutlined, GavelOutlined, PersonOffOutlined, TaskAltOutlined, WarningAmberOutlined } from '@mui/icons-material';
import { Bar, BarChart, CartesianGrid, LabelList, Legend, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts';
import { analyticsAPI } from '../services/api';
import { useFetch } from '../hooks/useFetch';
import { tokens } from '../theme';
import { DataTable, EmptyState, formatDate, LoadError, Loading, PageHeader, Panel, StatTile, StatusChip, TextLink } from '../components/ui';

// Validated categorical pair (blue, orange), distinguishable with colour-blindness.
const FILED_COLOR = '#2a78d6';
const DISPOSED_COLOR = '#eb6834';
const axis = { tick: { fill: tokens.mutedForeground, fontSize: 12 }, axisLine: false, tickLine: false };

function ChartTip({ active, payload, label }) {
  if (!active || !payload?.length) return null;
  return (
    <Box sx={{ bgcolor: 'background.paper', border: 1, borderColor: 'divider', borderRadius: 1, px: 1.5, py: 1, boxShadow: 2 }}>
      <Typography variant="caption" color="text.secondary">{label}</Typography>
      {payload.map((p) => <Typography key={p.dataKey} variant="body2" sx={{ fontWeight: 700 }}>{p.value} {p.name}</Typography>)}
    </Box>
  );
}

/** A labelled single-series horizontal bar chart. */
function HorizontalBars({ data, labelKey, valueKey, unit, labelWidth = 110 }) {
  if (!data.length) return <EmptyState>No data yet.</EmptyState>;
  return (
    <Box sx={{ height: Math.max(160, data.length * 44) }} role="img" aria-label={data.map((d) => `${d[labelKey]}: ${d[valueKey]} ${unit}`).join(', ')}>
      <ResponsiveContainer>
        <BarChart data={data} layout="vertical" margin={{ top: 0, right: 44, left: 8, bottom: 0 }}>
          <XAxis type="number" hide allowDecimals={false} />
          <YAxis type="category" dataKey={labelKey} width={labelWidth} {...axis} />
          <Tooltip content={<ChartTip />} cursor={{ fill: tokens.muted }} />
          <Bar isAnimationActive={false} dataKey={valueKey} name={unit} fill={tokens.primary} radius={[0, 4, 4, 0]} barSize={18}>
            <LabelList dataKey={valueKey} position="right" fill={tokens.foreground} fontSize={12} />
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </Box>
  );
}

const matterCell = (m) => (
  <Box>
    <TextLink to={`/cases/${m.case_id}`}>{m.case_number}</TextLink>
    <Typography variant="body2" color="text.secondary">{m.matter_title}</Typography>
  </Box>
);

export default function Analytics() {
  const { data, loading, error, reload } = useFetch(() => analyticsAPI.firm());
  const types = useFetch(() => analyticsAPI.byMatterType());

  if (error) return <Box><PageHeader title="Analytics" /><LoadError message={error} onRetry={reload} /></Box>;
  if (loading && !data) return <Box><PageHeader title="Analytics" /><Loading height={500} /></Box>;

  const h = data.headline;

  return (
    <Box>
      <PageHeader title="Analytics" subtitle="Risks, workload, and how matters move through the firm" />
      <Grid container spacing={2}>
        <Grid item xs={6} md={4} lg={2}><StatTile label="Active matters" value={h.active_matters} icon={<GavelOutlined />} to="/cases" /></Grid>
        <Grid item xs={6} md={4} lg={2}><StatTile label="Disposal rate" value={`${Math.round(h.disposal_rate)}%`} hint={`${h.disposed_matters} disposed`} icon={<TaskAltOutlined />} /></Grid>
        <Grid item xs={6} md={4} lg={2}><StatTile label="Hearings, 7 days" value={h.hearings_next_7_days} icon={<EventOutlined />} to="/calendar" /></Grid>
        <Grid item xs={6} md={4} lg={2}><StatTile label="Overdue deadlines" value={h.overdue_deadlines} hint={`${h.overdue_tasks} overdue in all`} icon={<WarningAmberOutlined />} to="/tasks" tone={h.overdue_deadlines ? 'alert' : undefined} /></Grid>
        <Grid item xs={6} md={4} lg={2}><StatTile label="No lead counsel" value={h.unassigned_matters} icon={<PersonOffOutlined />} to="/cases?unassigned=true" tone={h.unassigned_matters ? 'warn' : undefined} /></Grid>
        <Grid item xs={6} md={4} lg={2}><StatTile label="No next date" value={h.matters_without_next_date} icon={<EventBusyOutlined />} tone={h.matters_without_next_date ? 'warn' : undefined} /></Grid>

        <Grid item xs={12} lg={8}>
          <Panel title="Filed and disposed, last 12 months">
            <Box
              sx={{ height: 280 }}
              role="img"
              aria-label={`Filed: ${data.flow.reduce((a, m) => a + m.filed, 0)} matters. Disposed: ${data.flow.reduce((a, m) => a + m.disposed, 0)} matters, over the last 12 months.`}
            >
              <ResponsiveContainer>
                <BarChart data={data.flow} margin={{ top: 8, right: 8, left: -20, bottom: 0 }} barGap={2}>
                  <CartesianGrid vertical={false} stroke={tokens.muted} />
                  <XAxis dataKey="label" {...axis} />
                  <YAxis allowDecimals={false} {...axis} />
                  <Tooltip content={<ChartTip />} cursor={{ fill: tokens.muted }} />
                  <Legend formatter={(v) => <span style={{ color: tokens.foreground }}>{v}</span>} />
                  <Bar isAnimationActive={false} dataKey="filed" name="filed" fill={FILED_COLOR} radius={[4, 4, 0, 0]} maxBarSize={18} />
                  <Bar isAnimationActive={false} dataKey="disposed" name="disposed" fill={DISPOSED_COLOR} radius={[4, 4, 0, 0]} maxBarSize={18} />
                </BarChart>
              </ResponsiveContainer>
            </Box>
          </Panel>
        </Grid>
        <Grid item xs={12} sm={6} lg={4}>
          <Panel title="How long open matters have run">
            <HorizontalBars data={data.age_of_open_matters} labelKey="bucket" valueKey="count" unit="matters" />
          </Panel>
        </Grid>

        <Grid item xs={12} sm={6} lg={4}>
          <Panel title="Matters by type">
            <HorizontalBars data={types.data || []} labelKey="matter_type" valueKey="count" unit="matters" />
          </Panel>
        </Grid>
        <Grid item xs={12} sm={6} lg={4}>
          <Panel title="Average days to disposal">
            <HorizontalBars data={data.time_to_disposal} labelKey="matter_type" valueKey="average_days" unit="days" />
          </Panel>
        </Grid>
        <Grid item xs={12} sm={6} lg={4}>
          <Panel title="How matters ended">
            <HorizontalBars data={data.outcomes} labelKey="outcome" valueKey="count" unit="matters" labelWidth={80} />
          </Panel>
        </Grid>

        <Grid item xs={12}>
          <Panel noPadding title="Lawyer workload">
            <DataTable
              flat
              rowKey={(l) => l.lawyer_id}
              rows={data.lawyers}
              columns={[
                {
                  key: 'name', label: 'Lawyer',
                  render: (l) => (
                    <Box>
                      <TextLink to={`/lawyers/${l.lawyer_id}`}>{l.lawyer_name}</TextLink>
                      <Typography variant="body2" color="text.secondary">{[l.designation, l.practice_group].filter(Boolean).join(' · ')}</Typography>
                    </Box>
                  ),
                },
                { key: 'active_matters', label: 'Active matters', align: 'right' },
                { key: 'leading', label: 'Leading', align: 'right' },
                { key: 'hearings_next_14_days', label: 'Hearings, 14 days', align: 'right' },
                {
                  key: 'overdue_tasks', label: 'Overdue tasks', align: 'right',
                  render: (l) => (l.overdue_tasks ? <Chip size="small" label={l.overdue_tasks} sx={{ bgcolor: '#FEE2E2', color: '#991B1B' }} /> : 0),
                },
              ]}
            />
          </Panel>
        </Grid>

        <Grid item xs={12}>
          <Panel noPadding title="Courts">
            <DataTable
              flat
              rowKey={(c) => c.court_name}
              rows={data.courts}
              empty="No court activity yet."
              columns={[
                { key: 'court_name', label: 'Court' },
                { key: 'active_matters', label: 'Active matters', align: 'right' },
                { key: 'hearings', label: 'Hearings recorded', align: 'right' },
                { key: 'adjourned', label: 'Adjourned', align: 'right' },
                { key: 'rate', label: 'Adjournment rate', align: 'right', render: (c) => (c.adjournment_rate == null ? '—' : `${c.adjournment_rate}%`) },
              ]}
            />
          </Panel>
        </Grid>

        <Grid item xs={12} lg={7}>
          <Panel noPadding title="Open matters with no next date">
            <DataTable
              flat
              rowKey={(m) => m.case_id}
              rows={data.no_next_date}
              empty="Every open matter has a next date."
              columns={[
                { key: 'matter', label: 'Matter', render: matterCell },
                { key: 'lead_counsel', label: 'Lead counsel', render: (m) => m.lead_counsel || '—' },
                { key: 'last_hearing', label: 'Last hearing', nowrap: true, render: (m) => formatDate(m.last_hearing) },
              ]}
            />
          </Panel>
        </Grid>
        <Grid item xs={12} lg={5}>
          <Panel noPadding title="Open matters with no lead counsel">
            <DataTable
              flat
              rowKey={(m) => m.case_id}
              rows={data.unassigned}
              empty="Every open matter has a lead counsel."
              columns={[
                { key: 'matter', label: 'Matter', render: matterCell },
                { key: 'status', label: 'Status', render: (m) => <StatusChip status={m.status} /> },
              ]}
            />
          </Panel>
        </Grid>
      </Grid>
    </Box>
  );
}
