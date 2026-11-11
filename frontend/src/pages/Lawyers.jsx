import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Box, Button, Typography } from '@mui/material';
import { PersonAddAlt1Outlined } from '@mui/icons-material';
import { lawyersAPI } from '../services/api';
import { useAuth } from '../context/AuthContext';
import { useDebounced, useFetch } from '../hooks/useFetch';
import { DataTable, FilterBar, fullName, PageHeader, SearchField, StatusChip, TextLink } from '../components/ui';

export default function Lawyers() {
  const { isAdmin, isStaff } = useAuth();
  const navigate = useNavigate();
  const [search, setSearch] = useState('');
  const [page, setPage] = useState(0);
  const [size, setSize] = useState(25);
  const query = useDebounced(search);
  const { data, loading, error, reload } = useFetch(
    () => lawyersAPI.getAll({ page: page + 1, size, ...(query && { search: query }) }),
    [page, size, query],
  );

  const columns = [
    {
      key: 'name', label: 'Name',
      render: (l) => (
        <Box>
          <TextLink to={`/lawyers/${l.lawyer_id}`}>{fullName(l)}</TextLink>
          {l.designation && <Typography variant="body2" color="text.secondary">{l.designation}</Typography>}
        </Box>
      ),
    },
    { key: 'group_name', label: 'Practice group', render: (l) => l.group_name || '—' },
    ...(isAdmin || isStaff ? [{ key: 'total_cases', label: 'Matters', align: 'right', render: (l) => l.total_cases }] : []),
    { key: 'active', label: 'Status', render: (l) => <StatusChip status={l.is_active ? 'Active' : 'Inactive'} /> },
    ...(isAdmin ? [{ key: 'login', label: 'Login', render: (l) => (l.has_login ? 'Has a login' : <Typography variant="body2" sx={{ color: '#92400E' }}>No login yet</Typography>) }] : []),
  ];

  return (
    <Box>
      <PageHeader
        title="Lawyers"
        actions={isAdmin && <Button variant="contained" startIcon={<PersonAddAlt1Outlined />} onClick={() => navigate('/team')}>Add a lawyer</Button>}
      />
      <FilterBar>
        <SearchField value={search} onChange={(v) => { setSearch(v); setPage(0); }} placeholder="Search by name" />
      </FilterBar>
      <DataTable
        columns={columns}
        rows={data?.items}
        rowKey={(l) => l.lawyer_id}
        loading={loading}
        error={error}
        onRetry={reload}
        empty="No lawyers found."
        pagination={{ total: data?.total, page, size, onPage: setPage, onSize: (s) => { setSize(s); setPage(0); } }}
      />
    </Box>
  );
}
