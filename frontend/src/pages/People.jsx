/** Clients and opposing parties work the same way, so both pages are built from one component. */
import React, { useState } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import { Box, Button, Chip, Grid, Tooltip, Typography } from '@mui/material';
import { Add, DeleteOutline, EditOutlined, LockOutlined } from '@mui/icons-material';
import { clientsAPI, opposingPartiesAPI, workspaceAPI } from '../services/api';
import { useAuth } from '../context/AuthContext';
import { useDebounced, useFetch } from '../hooks/useFetch';
import {
  CenteredSpinner, ConfirmDialog, DataTable, FilterBar, FormDialog, fullName, LoadError, PageHeader, Panel, SearchField, StatTile,
  StatusChip, TextLink, useToast,
} from '../components/ui';
import { PERSON_FIELDS, personBody } from '../components/MatterForm';

const CLIENT = {
  api: clientsAPI, idKey: 'client_id', basePath: '/clients', title: 'Clients', one: 'client', conflictKey: 'clients',
  extraFields: [{ name: 'notes', label: 'Notes', type: 'multiline' }],
};
const PARTY = {
  api: opposingPartiesAPI, idKey: 'party_id', basePath: '/opposing-parties', title: 'Opposing parties', one: 'opposing party', conflictKey: 'parties',
  extraFields: [],
};

function PeopleList({ config }) {
  const toast = useToast();
  const [search, setSearch] = useState('');
  const [page, setPage] = useState(0);
  const [size, setSize] = useState(25);
  const [adding, setAdding] = useState(false);
  const query = useDebounced(search);
  const { data, loading, error, reload } = useFetch(
    () => config.api.getAll({ page: page + 1, size, ...(query && { search: query }) }),
    [page, size, query],
  );

  const columns = [
    {
      key: 'name', label: 'Name',
      render: (p) => (p.can_open ? <TextLink to={`${config.basePath}/${p[config.idKey]}`}>{fullName(p)}</TextLink> : (
        <Tooltip title="Not on any of your matters. Only the name is shown, for conflict checks.">
          <Box sx={{ display: 'inline-flex', alignItems: 'center', gap: 0.5, color: 'text.secondary' }}>
            <LockOutlined sx={{ fontSize: 14 }} aria-label="Restricted" />{fullName(p)}
          </Box>
        </Tooltip>
      )),
    },
    { key: 'email', label: 'Email', render: (p) => p.email || '—' },
    { key: 'total_cases', label: 'Matters', align: 'right', render: (p) => p.total_cases },
    ...(config === PARTY ? [{ key: 'repeat', label: '', render: (p) => (p.repeat_party ? <Chip size="small" label="Repeat party" /> : null) }] : []),
  ];

  return (
    <Box>
      <PageHeader
        title={config.title}
        actions={<Button variant="contained" startIcon={<Add />} onClick={() => setAdding(true)}>Add {config.one}</Button>}
      />
      <FilterBar>
        <SearchField value={search} onChange={(v) => { setSearch(v); setPage(0); }} placeholder="Search by name or email" />
      </FilterBar>
      <DataTable
        columns={columns}
        rows={data?.items}
        rowKey={(p) => p[config.idKey]}
        loading={loading}
        error={error}
        onRetry={reload}
        empty={`No ${config.title.toLowerCase()} found.`}
        pagination={{ total: data?.total, page, size, onPage: setPage, onSize: (s) => { setSize(s); setPage(0); } }}
      />
      <FormDialog
        open={adding}
        title={`Add ${config.one}`}
        fields={[...PERSON_FIELDS, ...config.extraFields]}
        submitLabel={`Add ${config.one}`}
        onClose={() => setAdding(false)}
        onSubmit={async (v) => {
          const { data: created } = await config.api.create(personBody(v));
          // A conflict doesn't block adding someone, but it should be seen straight away
          const check = await workspaceAPI.checkConflicts({ [config.conflictKey]: [{ name: fullName(created), email: created.email, phone: v.phone }] });
          if (check.data.conflicts.length) toast(`Possible conflict: ${check.data.conflicts[0].message}`, 'warning');
          else toast(`${fullName(created)} added`);
          reload();
        }}
      />
    </Box>
  );
}

function PersonDetail({ config }) {
  const { id } = useParams();
  const { isAdmin } = useAuth();
  const navigate = useNavigate();
  const toast = useToast();
  const [editing, setEditing] = useState(false);
  const [deleting, setDeleting] = useState(false);
  const { data: person, loading, error, reload } = useFetch(() => config.api.getById(id), [id]);

  if (loading && !person) return <CenteredSpinner />;
  if (error && !person) return <LoadError message={error} onRetry={reload} />;

  const columns = [
    {
      key: 'matter', label: 'Matter',
      render: (c) => (
        <Box>
          <TextLink to={`/cases/${c.case_id}`}>{c.case_number}</TextLink>
          <Typography variant="body2">{c.matter_title}</Typography>
        </Box>
      ),
    },
    { key: 'status', label: 'Status', render: (c) => <StatusChip status={c.status} /> },
  ];

  const info = [
    ['Phone', person.phone_numbers.join(', ')],
    ['Email', person.email],
    ['Address', person.address],
    ...(config === CLIENT ? [['Notes', person.notes]] : []),
  ];

  return (
    <Box>
      <PageHeader
        eyebrow={config.title}
        title={fullName(person)}
        actions={(
          <>
            <Button variant="outlined" startIcon={<EditOutlined />} onClick={() => setEditing(true)}>Edit</Button>
            {isAdmin && <Button color="error" startIcon={<DeleteOutline />} onClick={() => setDeleting(true)}>Delete</Button>}
          </>
        )}
      />
      <Grid container spacing={2}>
        <Grid item xs={12} md={4}>
          <Panel title="Contact">
            {info.map(([label, value]) => (
              <Box key={label} sx={{ mb: 1.25 }}>
                <Typography variant="caption" color="text.secondary" component="div">{label}</Typography>
                <Typography variant="body2" sx={{ whiteSpace: 'pre-wrap' }}>{value || '—'}</Typography>
              </Box>
            ))}
            {person.repeat_party && <Chip size="small" label="Repeat party" />}
          </Panel>
        </Grid>
        <Grid item xs={12} md={8}>
          <Grid container spacing={2} sx={{ mb: 2 }}>
            <Grid item xs={6}><StatTile label="Active matters" value={person.active_cases} /></Grid>
            <Grid item xs={6}><StatTile label="Disposed matters" value={person.disposed_cases} /></Grid>
          </Grid>
          <Panel noPadding title="Matters">
            <DataTable flat columns={columns} rows={person.recent_cases} rowKey={(c) => c.case_id} empty="Not on any matter." />
          </Panel>
        </Grid>
      </Grid>
      <FormDialog
        open={editing}
        title={`Edit ${config.one}`}
        fields={[...PERSON_FIELDS.filter((f) => f.name !== 'phone'), ...config.extraFields]}
        initial={person}
        onClose={() => setEditing(false)}
        onSubmit={async (v) => {
          const body = {
            fname: v.fname, lname: v.lname, email: v.email || null, address: v.address || null, sex: v.sex || null,
            ...(config === CLIENT && { notes: v.notes || null }),
          };
          await config.api.update(id, body);
          toast('Saved');
          reload();
        }}
      />
      <ConfirmDialog
        open={deleting}
        danger
        title={`Delete this ${config.one}?`}
        message="Only someone who isn't on a matter can be deleted."
        confirmLabel="Delete"
        onClose={() => setDeleting(false)}
        onConfirm={async () => {
          await config.api.delete(id);
          toast('Deleted');
          navigate(config.basePath);
        }}
      />
    </Box>
  );
}

export const Clients = () => <PeopleList config={CLIENT} />;
export const OpposingParties = () => <PeopleList config={PARTY} />;
export const ClientDetail = () => <PersonDetail config={CLIENT} />;
export const OpposingPartyDetail = () => <PersonDetail config={PARTY} />;
