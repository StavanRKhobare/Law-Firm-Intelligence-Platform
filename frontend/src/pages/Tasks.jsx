import React, { useState } from 'react';
import { Box, Button } from '@mui/material';
import { Add } from '@mui/icons-material';
import { tasksAPI } from '../services/api';
import { useAuth } from '../context/AuthContext';
import { useFetch } from '../hooks/useFetch';
import { FilterBar, FilterSelect, PageHeader } from '../components/ui';
import { TaskDialog, TasksTable, useMatterOptions } from '../components/work';

export default function Tasks() {
  const { isLawyer } = useAuth();
  const [who, setWho] = useState(isLawyer ? 'mine' : 'all');
  const [show, setShow] = useState('open');
  const [kind, setKind] = useState('');
  const [page, setPage] = useState(0);
  const [size, setSize] = useState(25);
  const [adding, setAdding] = useState(false);
  const matters = useMatterOptions();

  const { data, loading, error, reload } = useFetch(
    () => tasksAPI.getAll({
      page: page + 1, size,
      mine: who === 'mine',
      open_only: show !== 'all',
      overdue: show === 'overdue',
      deadlines_only: kind === 'deadlines',
    }),
    [page, size, who, show, kind],
  );

  const resetPage = (fn) => (v) => { fn(v); setPage(0); };

  return (
    <Box>
      <PageHeader
        title="Tasks and deadlines"
        subtitle="Limitation, filing and compliance dates, and day-to-day work"
        actions={<Button variant="contained" startIcon={<Add />} onClick={() => setAdding(true)}>Add</Button>}
      />
      <FilterBar>
        <FilterSelect label="Assigned to" value={who} onChange={resetPage(setWho)} options={[{ value: 'mine', label: 'Me' }, { value: 'all', label: isLawyer ? 'Everyone on my matters' : 'Everyone' }]} />
        <FilterSelect label="Show" value={show} onChange={resetPage(setShow)} options={[{ value: 'open', label: 'Open' }, { value: 'overdue', label: 'Overdue' }, { value: 'all', label: 'Including done' }]} />
        <FilterSelect label="Type" value={kind} onChange={resetPage(setKind)} options={[{ value: '', label: 'All' }, { value: 'deadlines', label: 'Legal deadlines only' }]} />
      </FilterBar>
      <TasksTable
        tasks={data?.items}
        loading={loading}
        error={error}
        onRetry={reload}
        onChanged={reload}
        pagination={{ total: data?.total, page, size, onPage: setPage, onSize: (s) => { setSize(s); setPage(0); } }}
        empty={show === 'overdue' ? 'Nothing is overdue.' : 'Nothing to do here.'}
      />
      <TaskDialog open={adding} matterOptions={matters} onClose={() => setAdding(false)} onSaved={reload} />
    </Box>
  );
}
