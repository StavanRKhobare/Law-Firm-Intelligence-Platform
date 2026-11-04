import React, { useMemo, useState } from 'react';
import { Box, Button, ButtonGroup, IconButton, Paper, Stack, Typography } from '@mui/material';
import { Add, ChevronLeft, ChevronRight, PrintOutlined } from '@mui/icons-material';
import { hearingsAPI } from '../services/api';
import { useAuth } from '../context/AuthContext';
import { useFetch } from '../hooks/useFetch';
import { EmptyState, FilterSelect, isoDate, LoadError, Loading, PageHeader } from '../components/ui';
import { HearingDialog, HearingsTable, useLawyerOptions, useMatterOptions } from '../components/work';

const addDays = (date, days) => {
  const next = new Date(date);
  next.setDate(next.getDate() + days);
  return next;
};

const startOfWeek = (date) => addDays(date, -((date.getDay() + 6) % 7));

const dayHeading = (iso) => {
  const label = new Date(`${iso}T00:00:00`).toLocaleDateString('en-IN', { weekday: 'long', day: 'numeric', month: 'long' });
  return iso === isoDate() ? `Today, ${label}` : label;
};

export default function Calendar() {
  const { isLawyer } = useAuth();
  const [view, setView] = useState('week');
  const [anchor, setAnchor] = useState(() => new Date());
  const [lawyer, setLawyer] = useState('');
  const [adding, setAdding] = useState(false);
  const lawyers = useLawyerOptions();
  const matters = useMatterOptions();

  const [from, to] = useMemo(() => {
    if (view === 'day') return [anchor, anchor];
    const start = startOfWeek(anchor);
    return [start, addDays(start, 6)];
  }, [view, anchor]);

  const { data, loading, error, reload } = useFetch(
    () => hearingsAPI.getAll({ date_from: isoDate(from), date_to: isoDate(to), ...(lawyer && { lawyer_id: lawyer }) }),
    [isoDate(from), isoDate(to), lawyer],
  );

  const byDay = useMemo(() => {
    const groups = new Map();
    (data || []).filter((h) => h.status !== 'Cancelled').forEach((h) => {
      groups.set(h.hearing_date, [...(groups.get(h.hearing_date) || []), h]);
    });
    return [...groups.entries()];
  }, [data]);

  const step = view === 'day' ? 1 : 7;
  const rangeLabel = view === 'day'
    ? dayHeading(isoDate(anchor))
    : `${from.toLocaleDateString('en-IN', { day: 'numeric', month: 'short' })} to ${to.toLocaleDateString('en-IN', { day: 'numeric', month: 'short', year: 'numeric' })}`;

  return (
    <Box>
      <PageHeader
        title="Calendar"
        subtitle={isLawyer ? 'Hearings on your matters' : 'Hearings across the firm'}
        actions={(
          <>
            <Button variant="outlined" startIcon={<PrintOutlined />} onClick={() => window.print()}>Print cause list</Button>
            <Button variant="contained" startIcon={<Add />} onClick={() => setAdding(true)}>List a hearing</Button>
          </>
        )}
      />
      <Paper variant="outlined" sx={{ p: 2, mb: 2, display: 'flex', gap: 1.5, flexWrap: 'wrap', alignItems: 'center' }}>
        <Stack direction="row" alignItems="center" spacing={0.5}>
          <IconButton aria-label="Earlier" onClick={() => setAnchor(addDays(anchor, -step))}><ChevronLeft /></IconButton>
          <Button onClick={() => setAnchor(new Date())}>Today</Button>
          <IconButton aria-label="Later" onClick={() => setAnchor(addDays(anchor, step))}><ChevronRight /></IconButton>
        </Stack>
        <Typography sx={{ fontWeight: 700, flex: 1, minWidth: 180 }} aria-live="polite">{rangeLabel}</Typography>
        {!isLawyer && (
          <FilterSelect label="Lawyer" value={lawyer} onChange={setLawyer} options={[{ value: '', label: 'Everyone' }, ...lawyers]} />
        )}
        <ButtonGroup aria-label="Range">
          <Button variant={view === 'day' ? 'contained' : 'outlined'} onClick={() => setView('day')}>Day</Button>
          <Button variant={view === 'week' ? 'contained' : 'outlined'} onClick={() => setView('week')}>Week</Button>
        </ButtonGroup>
      </Paper>

      {error && <LoadError message={error} onRetry={reload} />}
      {loading && !data && <Loading height={300} />}
      {data && byDay.length === 0 && <Paper variant="outlined"><EmptyState>No hearings in this period.</EmptyState></Paper>}
      <Stack spacing={2}>
        {byDay.map(([day, rows]) => (
          <Box key={day}>
            <Typography variant="h6" component="h2" sx={{ mb: 1 }}>
              {dayHeading(day)} <Typography component="span" variant="body2" color="text.secondary">· {rows.length} {rows.length === 1 ? 'hearing' : 'hearings'}</Typography>
            </Typography>
            <HearingsTable hearings={rows} onChanged={reload} />
          </Box>
        ))}
      </Stack>
      <HearingDialog open={adding} matterOptions={matters} onClose={() => setAdding(false)} onSaved={reload} />
    </Box>
  );
}
