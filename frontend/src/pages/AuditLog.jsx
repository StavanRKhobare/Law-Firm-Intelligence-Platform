import React, { useState } from 'react';
import { Box, TextField, Typography } from '@mui/material';
import { auditAPI } from '../services/api';
import { useDebounced, useFetch } from '../hooks/useFetch';
import { DataTable, FilterBar, formatDateTime, PageHeader, SearchField, TextLink } from '../components/ui';

const readableAction = (action) => action.replace(/_/g, ' ').replace(/^./, (c) => c.toUpperCase());

function detailText(detail) {
  if (!detail) return '';
  try {
    const parsed = JSON.parse(detail);
    if (parsed && typeof parsed === 'object') {
      return Object.entries(parsed)
        .filter(([key, value]) => value !== null && key !== 'sha256')
        .map(([key, value]) => `${key.replace(/_/g, ' ')}: ${Array.isArray(value) ? value.join(', ') : value}`)
        .join(' · ');
    }
  } catch { /* plain text */ }
  return detail;
}

export default function AuditLog() {
  const [username, setUsername] = useState('');
  const [from, setFrom] = useState('');
  const [to, setTo] = useState('');
  const [page, setPage] = useState(0);
  const [size, setSize] = useState(25);
  const who = useDebounced(username);
  const { data, loading, error, reload } = useFetch(
    () => auditAPI.getAll({
      page: page + 1, size,
      ...(who && { username: who }),
      ...(from && { date_from: from }),
      ...(to && { date_to: to }),
    }),
    [page, size, who, from, to],
  );

  const columns = [
    { key: 'created_at', label: 'When', nowrap: true, render: (r) => formatDateTime(r.created_at) },
    { key: 'username', label: 'Who', render: (r) => r.username || 'Public' },
    { key: 'action', label: 'Action', render: (r) => readableAction(r.action) },
    { key: 'case', label: 'Matter', render: (r) => (r.case_id ? <TextLink to={`/cases/${r.case_id}?tab=history`}>#{r.case_id}</TextLink> : '—') },
    { key: 'detail', label: 'Detail', render: (r) => <Typography variant="body2" color="text.secondary">{detailText(r.detail)}</Typography> },
  ];

  return (
    <Box>
      <PageHeader title="Audit log" subtitle="Every significant action, including who opened files. Entries can’t be changed or deleted." />
      <FilterBar>
        <SearchField value={username} onChange={(v) => { setUsername(v); setPage(0); }} placeholder="Filter by username" />
        <TextField label="From" type="date" InputLabelProps={{ shrink: true }} value={from} onChange={(e) => { setFrom(e.target.value); setPage(0); }} />
        <TextField label="To" type="date" InputLabelProps={{ shrink: true }} value={to} onChange={(e) => { setTo(e.target.value); setPage(0); }} />
      </FilterBar>
      <DataTable
        dense
        columns={columns}
        rows={data?.items}
        rowKey={(r) => r.log_id}
        loading={loading}
        error={error}
        onRetry={reload}
        empty="No entries."
        pagination={{ total: data?.total, page, size, onPage: setPage, onSize: (s) => { setSize(s); setPage(0); } }}
      />
    </Box>
  );
}
