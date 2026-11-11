import React, { useState } from 'react';
import { Box, Button } from '@mui/material';
import { Add } from '@mui/icons-material';
import { evidenceAPI } from '../services/api';
import { useAuth } from '../context/AuthContext';
import { useDebounced, useFetch } from '../hooks/useFetch';
import { FilterBar, FilterSelect, PageHeader, SearchField } from '../components/ui';
import { DOCUMENT_CATEGORIES, DOCUMENT_STATUSES, DocumentDialog, DocumentsTable, useMatterOptions } from '../components/work';

export default function Documents() {
  const { isLawyer, isAdmin } = useAuth();
  const [search, setSearch] = useState('');
  const [category, setCategory] = useState('');
  const [status, setStatus] = useState('');
  const [page, setPage] = useState(0);
  const [size, setSize] = useState(25);
  const [adding, setAdding] = useState(false);
  const matters = useMatterOptions();
  const query = useDebounced(search);

  const { data, loading, error, reload } = useFetch(
    () => evidenceAPI.getAll({
      page: page + 1, size,
      ...(query && { search: query }),
      ...(category && { category }),
      ...(status && { status }),
    }),
    [page, size, query, category, status],
  );

  const resetPage = (fn) => (v) => { fn(v); setPage(0); };

  return (
    <Box>
      <PageHeader
        title="Documents"
        subtitle={isLawyer ? 'Documents and evidence on your matters' : 'Documents and evidence across the firm'}
        actions={<Button variant="contained" startIcon={<Add />} onClick={() => setAdding(true)}>Add a document</Button>}
      />
      <FilterBar>
        <SearchField value={search} onChange={resetPage(setSearch)} placeholder="Search by file name or description" />
        <FilterSelect label="Category" value={category} onChange={resetPage(setCategory)} options={[{ value: '', label: 'Any category' }, ...DOCUMENT_CATEGORIES]} />
        <FilterSelect label="Status" value={status} onChange={resetPage(setStatus)} options={[{ value: '', label: 'Any status' }, ...DOCUMENT_STATUSES]} />
      </FilterBar>
      <DocumentsTable
        documents={data?.items}
        loading={loading}
        error={error}
        onRetry={reload}
        onChanged={reload}
        canDelete={() => isAdmin || isLawyer}
        pagination={{ total: data?.total, page, size, onPage: setPage, onSize: (s) => { setSize(s); setPage(0); } }}
      />
      <DocumentDialog open={adding} matterOptions={matters} onClose={() => setAdding(false)} onSaved={reload} />
    </Box>
  );
}
