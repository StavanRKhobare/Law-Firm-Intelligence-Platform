import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Box,
  Grid,
  Typography,
  Card,
  CardContent,
  Skeleton,
  Alert,
  Button,
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableRow,
  LinearProgress,
} from '@mui/material';
import {
  GavelOutlined,
  EventOutlined,
  TaskAltOutlined,
  DescriptionOutlined,
  ArrowForward,
} from '@mui/icons-material';
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, LabelList } from 'recharts';
import { analyticsAPI, casesAPI } from '../services/api';
import { tokens } from '../theme';
import StatusChip from '../components/StatusChip';
import MatterTypeAssistant from '../components/MatterTypeAssistant';

const MONTHS = ['January', 'February', 'March', 'April', 'May', 'June', 'July', 'August', 'September', 'October', 'November', 'December'];

const axisProps = { tick: { fill: tokens.mutedForeground, fontSize: 12 }, axisLine: false, tickLine: false };

function StatTile({ label, value, hint, icon }) {
  return (
    <Card sx={{ height: '100%' }}>
      <CardContent sx={{ display: 'flex', gap: 2, alignItems: 'flex-start' }}>
        <Box sx={{ p: 1.25, borderRadius: 2, bgcolor: tokens.muted, color: tokens.primary, display: 'flex' }} aria-hidden>
          {icon}
        </Box>
        <Box>
          <Typography variant="body2" color="text.secondary">{label}</Typography>
          <Typography sx={{ fontSize: '1.9rem', fontWeight: 700, lineHeight: 1.2, fontVariantNumeric: 'tabular-nums' }}>
            {value}
          </Typography>
          {hint && <Typography variant="caption" color="text.secondary">{hint}</Typography>}
        </Box>
      </CardContent>
    </Card>
  );
}

function Panel({ title, action, children }) {
  return (
    <Card sx={{ height: '100%' }}>
      <CardContent>
        <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', mb: 1.5 }}>
          <Typography variant="h6" component="h2">{title}</Typography>
          {action}
        </Box>
        {children}
      </CardContent>
    </Card>
  );
}

function ChartTooltip({ active, payload, label, unit = 'matters' }) {
  if (!active || !payload?.length) return null;
  return (
    <Box sx={{ bgcolor: 'background.paper', border: 1, borderColor: 'divider', borderRadius: 1, px: 1.5, py: 1, boxShadow: 2 }}>
      <Typography variant="caption" color="text.secondary">{label}</Typography>
      <Typography variant="body2" sx={{ fontWeight: 700 }}>{payload[0].value} {unit}</Typography>
    </Box>
  );
}

export default function Dashboard() {
  const navigate = useNavigate();
  const [data, setData] = useState(null);
  const [error, setError] = useState('');

  useEffect(() => {
    Promise.all([
      analyticsAPI.getDashboard(),
      analyticsAPI.getCasesByStatus(),
      analyticsAPI.getCasesByMonth(),
      analyticsAPI.getMatterTypes(),
      analyticsAPI.getLawyerPerformance(),
      casesAPI.getAll({ size: 100 }),
    ])
      .then(([dash, status, month, types, lawyers, cases]) => {
        const order = ['Filed', 'Hearing', 'Pending', 'Disposed'];
        const items = cases.data.items || cases.data;
        setData({
          stats: dash.data,
          status: order.map((s) => status.data.find((x) => x.status === s) || { status: s, count: 0, percentage: 0 }),
          months: month.data.map((m) => ({
            label: `${m.month.slice(0, 3)} ${String(m.year).slice(2)}`,
            count: m.total_cases,
            sort: m.year * 12 + MONTHS.indexOf(m.month),
          })).sort((a, b) => a.sort - b.sort),
          types: [...types.data].sort((a, b) => b.count - a.count),
          lawyers: [...lawyers.data].sort((a, b) => b.active_cases - a.active_cases).slice(0, 5),
          recent: [...items].sort((a, b) => (b.date_cause || '').localeCompare(a.date_cause || '')).slice(0, 5),
        });
      })
      .catch(() => setError('Could not load dashboard data. Check that the backend is running on port 8000.'));
  }, []);

  if (error) return <Alert severity="error">{error}</Alert>;

  const s = data?.stats;
  const active = s ? s.filed_cases + s.hearing_cases + s.pending_cases : 0;
  const maxLoad = Math.max(1, ...(data?.lawyers || []).map((l) => l.active_cases));
  const today = new Date().toLocaleDateString('en-IN', { weekday: 'long', day: 'numeric', month: 'long', year: 'numeric' });

  const tile = (props) =>
    data ? <StatTile {...props} /> : <Skeleton variant="rounded" height={104} />;

  return (
    <Box>
      <Box sx={{ mb: 3 }}>
        <Typography variant="overline" color="text.secondary">{today}</Typography>
        <Typography variant="h4" component="h1">Firm overview</Typography>
      </Box>

      <Grid container spacing={2}>
        <Grid item xs={12} sm={6} lg={3}>
          {tile({ label: 'Active matters', value: active, hint: `of ${s?.total_cases ?? 0} total`, icon: <GavelOutlined /> })}
        </Grid>
        <Grid item xs={12} sm={6} lg={3}>
          {tile({ label: 'In hearing', value: s?.hearing_cases, hint: 'listed before a court', icon: <EventOutlined /> })}
        </Grid>
        <Grid item xs={12} sm={6} lg={3}>
          {tile({ label: 'Disposal rate', value: `${(s?.disposal_rate ?? 0).toFixed(0)}%`, hint: `${s?.disposed_cases ?? 0} matters disposed`, icon: <TaskAltOutlined /> })}
        </Grid>
        <Grid item xs={12} sm={6} lg={3}>
          {tile({ label: 'Evidence items', value: s?.total_evidence, hint: `${s?.total_lawyers ?? 0} lawyers · ${s?.total_clients ?? 0} clients`, icon: <DescriptionOutlined /> })}
        </Grid>

        {/* Pipeline by status */}
        <Grid item xs={12} lg={5}>
          <Panel title="Matter pipeline">
            {!data ? <Skeleton variant="rounded" height={180} /> : (
              <Box sx={{ display: 'flex', flexDirection: 'column', gap: 1.75 }}>
                {data.status.map((row) => (
                  <Box key={row.status}>
                    <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 0.5 }}>
                      <StatusChip status={row.status} />
                      <Typography variant="body2" sx={{ fontVariantNumeric: 'tabular-nums' }}>
                        <b>{row.count}</b> <Typography component="span" variant="body2" color="text.secondary">({row.percentage.toFixed(0)}%)</Typography>
                      </Typography>
                    </Box>
                    <LinearProgress
                      variant="determinate"
                      value={row.percentage}
                      aria-label={`${row.status}: ${row.count} matters`}
                      sx={{ height: 8, borderRadius: 4, bgcolor: tokens.muted, '& .MuiLinearProgress-bar': { bgcolor: tokens.primary, borderRadius: 4 } }}
                    />
                  </Box>
                ))}
              </Box>
            )}
          </Panel>
        </Grid>

        {/* Filings per month */}
        <Grid item xs={12} lg={7}>
          <Panel title="New matters by month">
            {!data ? <Skeleton variant="rounded" height={220} /> : (
              <Box sx={{ height: 220 }} role="img" aria-label={`Bar chart of new matters per month, ${data.months.length} months`}>
                <ResponsiveContainer>
                  <BarChart data={data.months} margin={{ top: 8, right: 8, left: -20, bottom: 0 }}>
                    <CartesianGrid vertical={false} stroke={tokens.muted} />
                    <XAxis dataKey="label" {...axisProps} interval="preserveStartEnd" />
                    <YAxis allowDecimals={false} {...axisProps} />
                    <Tooltip content={<ChartTooltip />} cursor={{ fill: tokens.muted }} />
                    <Bar dataKey="count" fill={tokens.primary} radius={[4, 4, 0, 0]} maxBarSize={28} />
                  </BarChart>
                </ResponsiveContainer>
              </Box>
            )}
          </Panel>
        </Grid>

        {/* Matter types */}
        <Grid item xs={12} md={6} lg={4}>
          <Panel title="Matters by type">
            {!data ? <Skeleton variant="rounded" height={200} /> : (
              <Box sx={{ height: 200 }} role="img" aria-label={data.types.map((t) => `${t.matter_type} ${t.count}`).join(', ')}>
                <ResponsiveContainer>
                  <BarChart data={data.types} layout="vertical" margin={{ top: 0, right: 32, left: 8, bottom: 0 }}>
                    <XAxis type="number" hide allowDecimals={false} />
                    <YAxis type="category" dataKey="matter_type" width={80} {...axisProps} />
                    <Tooltip content={<ChartTooltip />} cursor={{ fill: tokens.muted }} />
                    <Bar dataKey="count" fill={tokens.primary} radius={[0, 4, 4, 0]} barSize={18}>
                      <LabelList dataKey="count" position="right" fill={tokens.foreground} fontSize={12} />
                    </Bar>
                  </BarChart>
                </ResponsiveContainer>
              </Box>
            )}
          </Panel>
        </Grid>

        {/* Lawyer workload */}
        <Grid item xs={12} md={6} lg={4}>
          <Panel
            title="Lawyer workload"
            action={<Button size="small" endIcon={<ArrowForward />} onClick={() => navigate('/lawyers')}>All lawyers</Button>}
          >
            {!data ? <Skeleton variant="rounded" height={200} /> : (
              <Box sx={{ display: 'flex', flexDirection: 'column', gap: 1.5 }}>
                {data.lawyers.map((l) => (
                  <Box key={l.lawyer_id}>
                    <Box sx={{ display: 'flex', justifyContent: 'space-between' }}>
                      <Typography variant="body2" sx={{ fontWeight: 700 }}>{l.lawyer_name}</Typography>
                      <Typography variant="body2" sx={{ fontVariantNumeric: 'tabular-nums' }}>{l.active_cases} active</Typography>
                    </Box>
                    <Typography variant="caption" color="text.secondary">{l.designation} · {l.practice_group}</Typography>
                    <LinearProgress
                      variant="determinate"
                      value={(l.active_cases / maxLoad) * 100}
                      aria-hidden
                      sx={{ mt: 0.5, height: 6, borderRadius: 3, bgcolor: tokens.muted, '& .MuiLinearProgress-bar': { bgcolor: tokens.secondary } }}
                    />
                  </Box>
                ))}
              </Box>
            )}
          </Panel>
        </Grid>

        <Grid item xs={12} lg={4}>
          <MatterTypeAssistant />
        </Grid>

        {/* Recent matters */}
        <Grid item xs={12}>
          <Panel
            title="Recent matters"
            action={<Button size="small" endIcon={<ArrowForward />} onClick={() => navigate('/cases')}>All matters</Button>}
          >
            {!data ? <Skeleton variant="rounded" height={200} /> : (
              <Box sx={{ overflowX: 'auto' }}>
                <Table size="small">
                  <TableHead>
                    <TableRow>
                      <TableCell>Case no.</TableCell>
                      <TableCell>Matter</TableCell>
                      <TableCell>Court</TableCell>
                      <TableCell>Lead counsel</TableCell>
                      <TableCell>Status</TableCell>
                    </TableRow>
                  </TableHead>
                  <TableBody>
                    {data.recent.map((c) => (
                      <TableRow key={c.case_id} hover>
                        <TableCell sx={{ whiteSpace: 'nowrap', fontWeight: 700 }}>{c.case_number}</TableCell>
                        <TableCell>{c.matter_title}</TableCell>
                        <TableCell sx={{ color: 'text.secondary' }}>{c.court_name}</TableCell>
                        <TableCell>{c.lead_counsel || '—'}</TableCell>
                        <TableCell><StatusChip status={c.status} /></TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </Box>
            )}
          </Panel>
        </Grid>
      </Grid>
    </Box>
  );
}
