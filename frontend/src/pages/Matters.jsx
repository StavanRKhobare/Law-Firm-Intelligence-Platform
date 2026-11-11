import React, { useState } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { Box, Button, Chip, Tooltip, Typography } from '@mui/material';
import { Add, LockOutlined } from '@mui/icons-material';
import { casesAPI } from '../services/api';
import { useAuth } from '../context/AuthContext';
import { useDebounced, useFetch } from '../hooks/useFetch';
import { DataTable, DueLabel, FilterBar, FilterSelect, formatDate, PageHeader, SearchField, StatusChip, TextLink } from '../components/ui';
import MatterForm from '../components/MatterForm';

export default function Matters() {
  const { isLawyer, isAdmin } = useAuth();
  const navigate = useNavigate();
  const [params] = useSearchParams();
  const [search, setSearch] = useState('');
  const [status, setStatus] = useState('');
  const [scope, setScope] = useState(isLawyer ? 'mine' : 'all');
  const [unassigned, setUnassigned] = useState(params.get('unassigned') === 'true');
  const [page, setPage] = useState(0);
  const [size, setSize] = useState(25);
  const [creating, setCreating] = useState(false);
  const query = useDebounced(search);

  const { data, loading, error, reload } = useFetch(
    () => casesAPI.getAll({
      page: page + 1, size, scope,
      ...(query && { search: query }),
      ...(status && { status }),
      ...(unassigned && { unassigned: true }),
    }),
    [page, size, query, status, scope, unassigned],
  );

  const resetPage = (fn) => (value) => { fn(value); setPage(0); };

  const columns = [
    {
      key: 'matter', label: 'Matter',
      render: (c) => (c.can_open ? (
        <Box>
          <TextLink to={`/cases/${c.case_id}`}>{c.case_number}</TextLink>
          <Typography variant="body2">{c.matter_title}</Typography>
          {c.matter_types.length > 0 && <Typography variant="caption" color="text.secondary">{c.matter_types.join(', ')}</Typography>}
        </Box>
      ) : (
        <Tooltip title="You are not on this matter. Only its title and number are shown, for conflict checks.">
          <Box sx={{ color: 'text.secondary' }}>
            <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5 }}>
              <LockOutlined sx={{ fontSize: 14 }} aria-label="Restricted" />
              <Typography variant="body2" sx={{ fontWeight: 700 }}>{c.case_number}</Typography>
            </Box>
            <Typography variant="body2">{c.matter_title}</Typography>
          </Box>
        </Tooltip>
      )),
    },
    { key: 'status', label: 'Status', render: (c) => <StatusChip status={c.status} /> },
    {
      key: 'lead_counsel', label: 'Lead counsel',
      render: (c) => c.lead_counsel || (c.status === 'Disposed' ? '—' : <Chip size="small" label="Unassigned" sx={{ bgcolor: '#FEE2E2', color: '#991B1B' }} />),
    },
    { key: 'court_name', label: 'Court', render: (c) => c.court_name || '—' },
    { key: 'date_filed', label: 'Filed', nowrap: true, render: (c) => formatDate(c.date_filed) },
    {
      key: 'next_hearing', label: 'Next hearing', nowrap: true,
      render: (c) => {
        if (c.next_hearing) return <DueLabel date={c.next_hearing} />;
        if (!c.can_open || c.status === 'Disposed') return '—';
        return <Typography variant="body2" sx={{ color: '#92400E', fontWeight: 700 }}>No date set</Typography>;
      },
    },
  ];

  return (
    <Box>
      <PageHeader
        title="Matters"
        subtitle={scope === 'mine' ? 'Matters you are working on' : 'All matters at the firm'}
        actions={<Button variant="contained" startIcon={<Add />} onClick={() => setCreating(true)}>New matter</Button>}
      />
      <FilterBar>
        <SearchField value={search} onChange={resetPage(setSearch)} placeholder="Search by title or case number" />
        {isLawyer && (
          <FilterSelect
            label="Show"
            value={scope}
            onChange={resetPage(setScope)}
            options={[{ value: 'mine', label: 'My matters' }, { value: 'all', label: 'All matters (titles only)' }]}
            minWidth={220}
          />
        )}
        <FilterSelect
          label="Status"
          value={status}
          onChange={resetPage(setStatus)}
          options={[{ value: '', label: 'Any status' }, 'Filed', 'Hearing', 'Pending', 'Disposed']}
        />
        {isAdmin && (
          <Button variant={unassigned ? 'contained' : 'outlined'} onClick={() => { setUnassigned(!unassigned); setPage(0); }}>
            Unassigned only
          </Button>
        )}
      </FilterBar>
      <DataTable
        columns={columns}
        rows={data?.items}
        rowKey={(c) => c.case_id}
        loading={loading}
        error={error}
        onRetry={reload}
        empty={query || status || unassigned ? 'No matters match these filters.' : 'No matters yet. Open your first one.'}
        pagination={{ total: data?.total, page, size, onPage: setPage, onSize: (s) => { setSize(s); setPage(0); } }}
      />
      <MatterForm open={creating} onClose={() => setCreating(false)} onSaved={(m) => navigate(`/cases/${m.case_id}`)} />
    </Box>
  );
}
