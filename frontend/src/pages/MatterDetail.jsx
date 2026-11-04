import React, { useState } from 'react';
import { useNavigate, useParams, useSearchParams } from 'react-router-dom';
import {
  Alert, Box, Button, Chip, Divider, Grid, IconButton, List, ListItem, ListItemText, Paper, Stack, Tab, Tabs, TextField, Tooltip, Typography,
} from '@mui/material';
import {
  Add, ArticleOutlined, BalanceOutlined, ChecklistOutlined, DeleteOutline, DescriptionOutlined, EditOutlined, EventOutlined,
  FlagOutlined, GroupOutlined, PersonRemoveOutlined, StickyNote2Outlined, SwapHorizOutlined,
} from '@mui/icons-material';
import { casesAPI, evidenceAPI, errorMessage, hearingsAPI, tasksAPI } from '../services/api';
import { useFetch } from '../hooks/useFetch';
import { tokens } from '../theme';
import {
  CenteredSpinner, ConfirmDialog, DueLabel, formatDate, formatDateTime, FormDialog, isoDate, LoadError, PageHeader, Panel,
  StatusChip, TextLink, useToast,
} from '../components/ui';
import { DocumentDialog, DocumentsTable, HearingDialog, HearingsTable, TaskDialog, TasksTable, useLawyerOptions } from '../components/work';
import MatterForm from '../components/MatterForm';

const OUTCOMES = ['Won', 'Lost', 'Settled', 'Withdrawn', 'Dismissed', 'Other'];

const EVENT_ICONS = {
  filed: <FlagOutlined fontSize="small" />,
  hearing: <EventOutlined fontSize="small" />,
  note: <StickyNote2Outlined fontSize="small" />,
  status: <SwapHorizOutlined fontSize="small" />,
  document: <DescriptionOutlined fontSize="small" />,
  counsel: <GroupOutlined fontSize="small" />,
  task: <ChecklistOutlined fontSize="small" />,
  disposed: <BalanceOutlined fontSize="small" />,
};

function Fact({ label, children }) {
  return (
    <Box>
      <Typography variant="caption" color="text.secondary" component="div">{label}</Typography>
      <Typography variant="body2" component="div">{children || '—'}</Typography>
    </Box>
  );
}

function Timeline({ caseId, canWork, version }) {
  const toast = useToast();
  const [note, setNote] = useState('');
  const [saving, setSaving] = useState(false);
  const { data, loading, error, reload } = useFetch(() => casesAPI.timeline(caseId), [caseId, version]);

  const addNote = async (e) => {
    e.preventDefault();
    if (!note.trim()) return;
    setSaving(true);
    try {
      await casesAPI.addNote(caseId, note.trim());
      setNote('');
      reload();
    } catch (err) {
      toast(errorMessage(err), 'error');
    } finally {
      setSaving(false);
    }
  };

  return (
    <Panel title="Case history">
      {canWork && (
        <Box component="form" onSubmit={addNote} sx={{ display: 'flex', gap: 1, mb: 2, alignItems: 'flex-start' }}>
          <TextField
            fullWidth
            multiline
            minRows={1}
            label="Add a remark"
            value={note}
            onChange={(e) => setNote(e.target.value)}
          />
          <Button type="submit" variant="contained" disabled={saving || !note.trim()}>Add</Button>
        </Box>
      )}
      {error && <LoadError message={error} onRetry={reload} />}
      {loading && !data && <CenteredSpinner />}
      <Box component="ol" sx={{ listStyle: 'none', m: 0, p: 0 }}>
        {(data || []).map((event, i) => (
          <Box component="li" key={i} sx={{ display: 'flex', gap: 1.5, pb: 2, position: 'relative' }}>
            <Box
              aria-hidden
              sx={{
                flex: '0 0 34px', height: 34, borderRadius: '50%', display: 'grid', placeItems: 'center', zIndex: 1,
                bgcolor: event.upcoming ? tokens.primary : tokens.muted, color: event.upcoming ? '#fff' : tokens.primary,
              }}
            >
              {EVENT_ICONS[event.kind]}
            </Box>
            {i < data.length - 1 && <Box aria-hidden sx={{ position: 'absolute', left: 16, top: 34, bottom: 0, width: 2, bgcolor: tokens.muted }} />}
            <Box sx={{ minWidth: 0 }}>
              <Typography variant="body2" sx={{ fontWeight: 700 }}>
                {event.title}
                {event.upcoming && <Chip size="small" label="Upcoming" sx={{ ml: 1, bgcolor: '#E0E7FF', color: '#1E3A8A' }} />}
              </Typography>
              {event.detail && <Typography variant="body2" sx={{ whiteSpace: 'pre-wrap' }}>{event.detail}</Typography>}
              <Typography variant="caption" color="text.secondary">
                {['note', 'status', 'task'].includes(event.kind) ? formatDateTime(event.at) : formatDate(event.at.slice(0, 10))}
                {event.actor ? ` · ${event.actor}` : ''}
              </Typography>
            </Box>
          </Box>
        ))}
      </Box>
    </Panel>
  );
}

function Counsel({ matter, reload }) {
  const toast = useToast();
  const lawyers = useLawyerOptions();
  const [assigning, setAssigning] = useState(false);
  const [removing, setRemoving] = useState(null);
  const canAssign = matter.permissions.assign;
  const current = matter.assignments.filter((a) => !a.end_date);
  const past = matter.assignments.filter((a) => a.end_date);
  const hasLead = current.some((a) => a.role === 'Lead Counsel');

  return (
    <Panel
      title="Counsel"
      action={canAssign && <Button size="small" startIcon={<Add />} onClick={() => setAssigning(true)}>Assign</Button>}
    >
      {!hasLead && matter.status !== 'Disposed' && (
        <Alert severity="warning" sx={{ mb: 1.5 }} action={canAssign && <Button color="inherit" size="small" onClick={() => setAssigning(true)}>Assign now</Button>}>
          This matter has no lead counsel.
        </Alert>
      )}
      <List dense disablePadding>
        {current.map((a) => (
          <ListItem
            key={a.lawyer_id}
            disableGutters
            secondaryAction={canAssign && (
              <Tooltip title="Take off this matter">
                <IconButton size="small" aria-label={`Take ${a.lawyer_name} off this matter`} onClick={() => setRemoving(a)}>
                  <PersonRemoveOutlined fontSize="small" />
                </IconButton>
              </Tooltip>
            )}
          >
            <ListItemText primary={<TextLink to={`/lawyers/${a.lawyer_id}`}>{a.lawyer_name}</TextLink>} secondary={`${a.role} · since ${formatDate(a.assigned_date)}`} />
          </ListItem>
        ))}
      </List>
      {past.length > 0 && (
        <>
          <Divider sx={{ my: 1 }} />
          <Typography variant="caption" color="text.secondary">Previously</Typography>
          {past.map((a) => (
            <Typography key={a.lawyer_id} variant="body2" color="text.secondary">
              {a.lawyer_name}, {a.role}, until {formatDate(a.end_date)}
            </Typography>
          ))}
        </>
      )}
      <FormDialog
        open={assigning}
        title="Assign counsel"
        intro={hasLead ? 'A new lead counsel replaces the current one. The current lead stays in the history.' : undefined}
        submitLabel="Assign"
        initial={{ role: hasLead ? 'Associate' : 'Lead Counsel', assigned_date: isoDate() }}
        fields={[
          { name: 'lawyer_id', label: 'Lawyer', type: 'select', required: true, options: lawyers, full: true },
          { name: 'role', label: 'Role', type: 'select', required: true, options: ['Lead Counsel', 'Associate', 'Research'] },
          { name: 'assigned_date', label: 'From', type: 'date', required: true },
        ]}
        onClose={() => setAssigning(false)}
        onSubmit={async (v) => {
          await casesAPI.assign(matter.case_id, v);
          toast('Counsel assigned');
          reload();
        }}
      />
      <ConfirmDialog
        open={Boolean(removing)}
        title="Take this lawyer off the matter?"
        message={`${removing?.lawyer_name} will lose access to this matter. Their past work stays in the history.`}
        confirmLabel="Take off matter"
        onClose={() => setRemoving(null)}
        onConfirm={async () => {
          await casesAPI.endAssignment(matter.case_id, removing.lawyer_id);
          toast('Counsel updated');
          reload();
        }}
      />
    </Panel>
  );
}

function PeopleList({ title, rows, idKey, basePath }) {
  return (
    <Panel title={title}>
      {rows.length === 0 ? <Typography variant="body2" color="text.secondary">None recorded.</Typography> : rows.map((p) => (
        <Typography key={p[idKey]} variant="body2" sx={{ mb: 0.5 }}>
          <TextLink to={`${basePath}/${p[idKey]}`}>{p.fname} {p.lname}</TextLink>
          {p.repeat_party && <Chip size="small" label="Repeat party" sx={{ ml: 1 }} />}
        </Typography>
      ))}
    </Panel>
  );
}

export default function MatterDetail() {
  const { id } = useParams();
  const navigate = useNavigate();
  const toast = useToast();
  const [params, setParams] = useSearchParams();
  const tab = params.get('tab') || 'overview';
  const [dialog, setDialog] = useState(null);
  const [version, setVersion] = useState(0);

  const { data: matter, loading, error, reload } = useFetch(() => casesAPI.getById(id), [id]);
  const hearings = useFetch(() => hearingsAPI.getAll({ case_id: id }), [id, version]);
  const tasks = useFetch(() => tasksAPI.getAll({ case_id: id, open_only: false, size: 100 }), [id, version]);
  const documents = useFetch(() => evidenceAPI.getAll({ case_id: id, size: 100 }), [id, version]);

  if (loading && !matter) return <CenteredSpinner />;
  if (error && !matter) {
    return (
      <Box>
        <PageHeader title="Matter" />
        <LoadError message={error} onRetry={reload} />
        <Button sx={{ mt: 2 }} onClick={() => navigate('/cases')}>Back to matters</Button>
      </Box>
    );
  }

  const can = matter.permissions;
  const refresh = () => {
    reload();
    setVersion((v) => v + 1);
  };
  const openTasks = (tasks.data?.items || []).filter((t) => t.status !== 'Done').length;

  return (
    <Box>
      <PageHeader
        eyebrow={matter.case_number}
        title={matter.matter_title}
        actions={(
          <>
            {can.edit && <Button startIcon={<SwapHorizOutlined />} variant="outlined" onClick={() => setDialog('status')}>Change status</Button>}
            {can.edit && <Button startIcon={<EditOutlined />} variant="outlined" onClick={() => setDialog('edit')}>Edit</Button>}
            {can.delete && <Button startIcon={<DeleteOutline />} color="error" onClick={() => setDialog('delete')}>Delete</Button>}
          </>
        )}
      />

      <Paper variant="outlined" sx={{ p: 2, mb: 2 }}>
        <Stack direction="row" spacing={4} useFlexGap sx={{ flexWrap: 'wrap' }}>
          <Fact label="Status"><StatusChip status={matter.status} /></Fact>
          <Fact label="Next hearing">
            {matter.next_hearing ? <DueLabel date={matter.next_hearing} /> : matter.status === 'Disposed' ? '—' : <Typography variant="body2" sx={{ color: '#92400E', fontWeight: 700 }}>No date set</Typography>}
          </Fact>
          <Fact label="Court">{matter.court?.court_name}</Fact>
          <Fact label="Filed">{formatDate(matter.date_filed)}</Fact>
          {matter.status === 'Disposed' && <Fact label="Disposed">{formatDate(matter.disposed_on)}{matter.outcome ? `: ${matter.outcome}` : ''}</Fact>}
        </Stack>
      </Paper>

      <Tabs
        value={tab}
        onChange={(_, v) => setParams(v === 'overview' ? {} : { tab: v }, { replace: true })}
        variant="scrollable"
        allowScrollButtonsMobile
        sx={{ mb: 2, borderBottom: 1, borderColor: 'divider' }}
      >
        <Tab value="overview" label="Overview" icon={<ArticleOutlined fontSize="small" />} iconPosition="start" />
        <Tab value="history" label="History and remarks" icon={<StickyNote2Outlined fontSize="small" />} iconPosition="start" />
        <Tab value="hearings" label={`Hearings (${hearings.data?.length ?? 0})`} icon={<EventOutlined fontSize="small" />} iconPosition="start" />
        <Tab value="tasks" label={`Tasks (${openTasks})`} icon={<ChecklistOutlined fontSize="small" />} iconPosition="start" />
        <Tab value="documents" label={`Documents (${documents.data?.total ?? 0})`} icon={<DescriptionOutlined fontSize="small" />} iconPosition="start" />
      </Tabs>

      {tab === 'overview' && (
        <Grid container spacing={2}>
          <Grid item xs={12} md={7}>
            <Panel title="About this matter">
              <Typography variant="body2" sx={{ whiteSpace: 'pre-wrap', mb: 2 }} color={matter.matter_description ? 'text.primary' : 'text.secondary'}>
                {matter.matter_description || 'No description yet.'}
              </Typography>
              <Box sx={{ display: 'grid', gridTemplateColumns: { xs: '1fr', sm: '1fr 1fr' }, gap: 2 }}>
                <Fact label="Matter types">{matter.matter_types.map((m) => m.matter_type).join(', ')}</Fact>
                <Fact label="Statutes and sections">{matter.statute_sections.map((s) => s.statute_section).join(', ')}</Fact>
                <Fact label="Cause of action">{formatDate(matter.date_cause)}</Fact>
                <Fact label="Place of dispute">{matter.location?.landmark}</Fact>
              </Box>
            </Panel>
          </Grid>
          <Grid item xs={12} md={5}><Counsel matter={matter} reload={refresh} /></Grid>
          <Grid item xs={12} sm={6}><PeopleList title="Clients" rows={matter.clients} idKey="client_id" basePath="/clients" /></Grid>
          <Grid item xs={12} sm={6}><PeopleList title="Opposing parties" rows={matter.opposing_parties} idKey="party_id" basePath="/opposing-parties" /></Grid>
        </Grid>
      )}

      {tab === 'history' && <Timeline caseId={id} canWork={can.work} version={version} />}

      {tab === 'hearings' && (
        <Panel noPadding title="Hearings" action={can.work && matter.status !== 'Disposed' && <Button size="small" startIcon={<Add />} onClick={() => setDialog('hearing')}>List a hearing</Button>}>
          <HearingsTable
            flat
            showMatter={false}
            hearings={hearings.data}
            loading={hearings.loading}
            error={hearings.error}
            onRetry={hearings.reload}
            onChanged={refresh}
            canWork={can.work}
            canDelete={can.edit}
            empty="No hearings recorded yet."
          />
        </Panel>
      )}

      {tab === 'tasks' && (
        <Panel noPadding title="Tasks and deadlines" action={can.work && <Button size="small" startIcon={<Add />} onClick={() => setDialog('task')}>Add</Button>}>
          <TasksTable flat showMatter={false} tasks={tasks.data?.items} loading={tasks.loading} error={tasks.error} onRetry={tasks.reload} onChanged={refresh} empty="No tasks or deadlines on this matter." />
        </Panel>
      )}

      {tab === 'documents' && (
        <Panel noPadding title="Documents" action={can.work && <Button size="small" startIcon={<Add />} onClick={() => setDialog('document')}>Add a document</Button>}>
          <DocumentsTable
            flat
            showMatter={false}
            documents={documents.data?.items}
            loading={documents.loading}
            error={documents.error}
            onRetry={documents.reload}
            onChanged={refresh}
            canDelete={() => can.edit}
          />
        </Panel>
      )}

      <MatterForm open={dialog === 'edit'} matter={matter} onClose={() => setDialog(null)} onSaved={refresh} />
      <HearingDialog open={dialog === 'hearing'} caseId={id} onClose={() => setDialog(null)} onSaved={refresh} />
      <TaskDialog open={dialog === 'task'} caseId={id} onClose={() => setDialog(null)} onSaved={refresh} />
      <DocumentDialog open={dialog === 'document'} caseId={id} onClose={() => setDialog(null)} onSaved={refresh} />
      <FormDialog
        open={dialog === 'status'}
        title="Change status"
        submitLabel="Update status"
        initial={{ new_status: matter.status, outcome: matter.outcome, disposed_on: matter.disposed_on || isoDate() }}
        fields={[
          { name: 'new_status', label: 'Status', type: 'select', required: true, options: ['Filed', 'Hearing', 'Pending', 'Disposed'], full: true },
          { name: 'outcome', label: 'Outcome', type: 'select', required: true, options: OUTCOMES, showIf: (v) => v.new_status === 'Disposed' },
          { name: 'disposed_on', label: 'Disposed on', type: 'date', required: true, showIf: (v) => v.new_status === 'Disposed' },
        ]}
        intro="Disposing a matter cancels any future hearings listed on it."
        onClose={() => setDialog(null)}
        onSubmit={async (v) => {
          const disposed = v.new_status === 'Disposed';
          await casesAPI.updateStatus(id, {
            new_status: v.new_status,
            ...(disposed && { outcome: v.outcome, disposed_on: v.disposed_on }),
          });
          toast('Status updated');
          refresh();
        }}
      />
      <ConfirmDialog
        open={dialog === 'delete'}
        danger
        title="Delete this matter?"
        message={`This permanently deletes ${matter.case_number}, with its hearings, remarks, tasks, documents and files. It cannot be undone. Most closed matters should be marked Disposed instead.`}
        confirmLabel="Delete permanently"
        onClose={() => setDialog(null)}
        onConfirm={async () => {
          await casesAPI.delete(id);
          toast('Matter deleted');
          navigate('/cases');
        }}
      />
    </Box>
  );
}
