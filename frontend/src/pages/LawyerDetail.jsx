import React, { useState } from 'react';
import { useParams } from 'react-router-dom';
import { Alert, Box, Button, Grid, Stack, Typography } from '@mui/material';
import { EditOutlined, EventOutlined, GavelOutlined, TaskAltOutlined, WarningAmberOutlined } from '@mui/icons-material';
import { hearingsAPI, lawyersAPI, referenceAPI } from '../services/api';
import { useAuth } from '../context/AuthContext';
import { useFetch } from '../hooks/useFetch';
import {
  CenteredSpinner, compact, DataTable, formatDate, FormDialog, fullName, isoDate, LoadError, PageHeader, Panel, StatTile, StatusChip,
  TextLink, useToast,
} from '../components/ui';
import { HearingsTable } from '../components/work';

function Detail({ label, value }) {
  return (
    <Box sx={{ mb: 1.25 }}>
      <Typography variant="caption" color="text.secondary" component="div">{label}</Typography>
      <Typography variant="body2">{value || '—'}</Typography>
    </Box>
  );
}

export default function LawyerDetail() {
  const { id } = useParams();
  const { isAdmin, user } = useAuth();
  const toast = useToast();
  const [editing, setEditing] = useState(false);
  const { data: lawyer, loading, error, reload } = useFetch(() => lawyersAPI.getById(id), [id]);
  const canSeeMatters = lawyer?.can_view_matters;
  const hearings = useFetch(
    () => (canSeeMatters ? hearingsAPI.getAll({ lawyer_id: id, date_from: isoDate(), status: 'Scheduled' }) : Promise.resolve({ data: [] })),
    [id, canSeeMatters],
  );
  const { data: groups } = useFetch(() => (isAdmin ? referenceAPI.practiceGroups() : Promise.resolve({ data: [] })), [isAdmin]);

  if (loading && !lawyer) return <CenteredSpinner />;
  if (error && !lawyer) return <LoadError message={error} onRetry={reload} />;

  const isSelf = user?.lawyer_id === lawyer.lawyer_id;
  const fields = isAdmin ? [
    { name: 'fname', label: 'First name', required: true },
    { name: 'lname', label: 'Last name', required: true },
    { name: 'designation', label: 'Designation' },
    { name: 'group_id', label: 'Practice group', type: 'select', options: (groups || []).map((g) => ({ value: g.group_id, label: g.group_name })) },
    { name: 'bar_id', label: 'Bar enrolment number' },
    { name: 'joined_date', label: 'Joined', type: 'date' },
    { name: 'phoneno', label: 'Phone' },
    { name: 'email', label: 'Email', type: 'email' },
  ] : [
    { name: 'phoneno', label: 'Phone' },
    { name: 'email', label: 'Email', type: 'email' },
  ];

  const matterColumns = [
    {
      key: 'matter', label: 'Matter',
      render: (m) => (
        <Box>
          <TextLink to={`/cases/${m.case_id}`}>{m.case_number}</TextLink>
          <Typography variant="body2">{m.matter_title}</Typography>
        </Box>
      ),
    },
    { key: 'role', label: 'Role' },
    { key: 'assigned_date', label: 'Since', nowrap: true, render: (m) => formatDate(m.assigned_date) },
    { key: 'status', label: 'Status', render: (m) => <StatusChip status={m.status} /> },
  ];

  return (
    <Box>
      <PageHeader
        eyebrow={lawyer.practice_group?.group_name}
        title={fullName(lawyer)}
        subtitle={lawyer.designation}
        actions={(isAdmin || isSelf) && <Button variant="outlined" startIcon={<EditOutlined />} onClick={() => setEditing(true)}>Edit</Button>}
      />
      {!lawyer.is_active && <Alert severity="info" sx={{ mb: 2 }}>This lawyer is no longer active at the firm.</Alert>}
      {isAdmin && lawyer.is_active && !lawyer.has_login && (
        <Alert severity="warning" sx={{ mb: 2 }}>This lawyer has no login yet. You can create one under Team and access.</Alert>
      )}

      <Grid container spacing={2}>
        <Grid item xs={12} md={4}>
          <Panel title="Details">
            <Detail label="Bar enrolment number" value={lawyer.bar_id} />
            <Detail label="Practice group" value={lawyer.practice_group?.group_name} />
            <Detail label="Phone" value={lawyer.phoneno} />
            <Detail label="Email" value={lawyer.email} />
            <Detail label="Joined" value={lawyer.joined_date && formatDate(lawyer.joined_date)} />
          </Panel>
        </Grid>
        {canSeeMatters ? (
          <Grid item xs={12} md={8}>
            <Grid container spacing={2}>
              <Grid item xs={6} lg={3}><StatTile label="Active matters" value={lawyer.active_cases} icon={<GavelOutlined />} /></Grid>
              <Grid item xs={6} lg={3}><StatTile label="Disposed" value={lawyer.disposed_cases} icon={<TaskAltOutlined />} /></Grid>
              <Grid item xs={6} lg={3}><StatTile label="Hearings, 14 days" value={lawyer.upcoming_hearings} icon={<EventOutlined />} /></Grid>
              <Grid item xs={6} lg={3}><StatTile label="Overdue tasks" value={lawyer.overdue_tasks} icon={<WarningAmberOutlined />} tone={lawyer.overdue_tasks ? 'alert' : undefined} /></Grid>
            </Grid>
          </Grid>
        ) : (
          <Grid item xs={12} md={8}>
            <Panel title="Matters">
              <Typography color="text.secondary">Only {lawyer.fname} and the firm’s admins can see {lawyer.fname}’s matters.</Typography>
            </Panel>
          </Grid>
        )}
      </Grid>

      {canSeeMatters && (
        <Stack spacing={2} sx={{ mt: 2 }}>
          <Panel noPadding title={`Assigned matters (${lawyer.matters.length})`}>
            <DataTable flat columns={matterColumns} rows={lawyer.matters} rowKey={(m) => m.case_id} empty="Not assigned to any matter." />
          </Panel>
          <Panel noPadding title="Upcoming hearings">
            <HearingsTable flat hearings={hearings.data} loading={hearings.loading} onChanged={hearings.reload} empty="No hearings listed." />
          </Panel>
        </Stack>
      )}

      <FormDialog
        open={editing}
        title="Edit details"
        fields={fields}
        initial={lawyer}
        onClose={() => setEditing(false)}
        onSubmit={async (v) => {
          const names = fields.map((f) => f.name);
          const body = Object.fromEntries(names.map((n) => [n, v[n] === '' ? null : v[n]]));
          await lawyersAPI.update(id, compact(body));
          toast('Details saved');
          reload();
        }}
      />
    </Box>
  );
}
