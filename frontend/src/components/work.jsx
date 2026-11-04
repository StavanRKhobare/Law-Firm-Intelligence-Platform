/** Hearing, task and document pieces used on the dashboard, calendar, matter and list pages. */
import React, { useState } from 'react';
import { Box, Button, Checkbox, IconButton, Stack, Tooltip, Typography } from '@mui/material';
import { DeleteOutline, DownloadOutlined, EditOutlined, UploadFileOutlined } from '@mui/icons-material';
import { casesAPI, evidenceAPI, hearingsAPI, lawyersAPI, tasksAPI, teamAPI } from '../services/api';
import { useFetch } from '../hooks/useFetch';
import {
  compact, ConfirmDialog, DataTable, DueLabel, formatDate, formatSize, formatTime, FormDialog, fullName, isoDate,
  StatusChip, TextLink, useToast,
} from './ui';

export const DOCUMENT_CATEGORIES = ['Evidence', 'Pleading', 'Order', 'Correspondence', 'Draft', 'Other'];
export const DOCUMENT_STATUSES = ['Received', 'Under Review', 'Filed', 'Produced'];
export const TASK_KINDS = [
  { value: 'Task', label: 'Task' },
  { value: 'Limitation', label: 'Limitation deadline' },
  { value: 'Filing', label: 'Filing deadline' },
  { value: 'Reply', label: 'Reply deadline' },
  { value: 'Compliance', label: 'Compliance deadline' },
];

export function useLawyerOptions() {
  const { data } = useFetch(() => lawyersAPI.getAll({ size: 100, active_only: true }));
  return (data?.items || []).map((l) => ({ value: l.lawyer_id, label: fullName(l) }));
}

/** Matters the user can work on, for pickers on list pages. */
export function useMatterOptions() {
  const { data } = useFetch(() => casesAPI.getAll({ size: 100, scope: 'mine' }));
  return (data?.items || []).map((c) => ({ value: c.case_id, label: `${c.case_number} · ${c.matter_title}` }));
}

// ------------------------------------------------------------------ hearings

export function HearingDialog({ open, onClose, onSaved, caseId, hearing, matterOptions }) {
  const toast = useToast();
  const fields = [
    ...(caseId || hearing ? [] : [{ name: 'case_id', label: 'Matter', type: 'select', required: true, options: matterOptions || [], full: true }]),
    { name: 'hearing_date', label: 'Date', type: 'date', required: true },
    { name: 'hearing_time', label: 'Time', type: 'time' },
    { name: 'purpose', label: 'Purpose', full: true, helper: 'For example: arguments, evidence, framing of issues' },
    { name: 'judge', label: 'Judge or bench' },
    { name: 'courtroom', label: 'Courtroom' },
  ];
  return (
    <FormDialog
      open={open}
      onClose={onClose}
      title={hearing ? 'Edit hearing' : 'List a hearing'}
      fields={fields}
      initial={hearing ? { ...hearing, hearing_time: hearing.hearing_time?.slice(0, 5) } : { hearing_date: isoDate() }}
      onSubmit={async (v) => {
        const body = {
          hearing_date: v.hearing_date,
          hearing_time: v.hearing_time || null,
          purpose: v.purpose || null,
          judge: v.judge || null,
          courtroom: v.courtroom || null,
        };
        if (hearing) await hearingsAPI.update(hearing.hearing_id, body);
        else await hearingsAPI.create({ ...body, case_id: caseId || v.case_id });
        toast(hearing ? 'Hearing updated' : 'Hearing listed');
        onSaved();
      }}
    />
  );
}

export function HearingResultDialog({ open, onClose, onSaved, hearing }) {
  const toast = useToast();
  const lawyers = useLawyerOptions();
  if (!hearing) return null;
  return (
    <FormDialog
      open={open}
      onClose={onClose}
      title="Record what happened"
      intro={`${hearing.case_number}, ${formatDate(hearing.hearing_date)}${hearing.purpose ? `: ${hearing.purpose}` : ''}`}
      submitLabel="Save result"
      initial={{ status: 'Held', outcome: hearing.outcome, remarks: hearing.remarks, attended_by: hearing.attended_by }}
      fields={[
        { name: 'status', label: 'What happened', type: 'select', required: true, options: ['Held', 'Adjourned', 'Cancelled'] },
        { name: 'attended_by', label: 'Attended by', type: 'select', options: lawyers },
        { name: 'outcome', label: 'Order or outcome', full: true, helper: 'What the court did' },
        { name: 'remarks', label: 'Remarks', type: 'multiline', helper: 'Notes for the file' },
        { name: 'next_date', label: 'Next date', type: 'date', showIf: (v) => v.status !== 'Cancelled' },
        { name: 'next_purpose', label: 'Purpose of next date', showIf: (v) => v.status !== 'Cancelled' },
      ]}
      onSubmit={async (v) => {
        await hearingsAPI.recordResult(hearing.hearing_id, compact({ ...v, next_date: v.status === 'Cancelled' ? '' : v.next_date }));
        toast(v.next_date ? 'Result saved and next hearing listed' : 'Result saved');
        onSaved();
      }}
    />
  );
}

/** Hearings as a table. showMatter adds the matter column; hides it inside a matter. */
export function HearingsTable({ hearings, loading, error, onRetry, showMatter = true, onChanged, canWork = true, canDelete = false, flat, empty }) {
  const toast = useToast();
  const [resultFor, setResultFor] = useState(null);
  const [editing, setEditing] = useState(null);
  const [deleting, setDeleting] = useState(null);
  const today = isoDate();
  const columns = [
    {
      key: 'date', label: 'Date', nowrap: true,
      render: (h) => (
        <Box>
          <Typography variant="body2" sx={{ fontWeight: 700 }}>{formatDate(h.hearing_date)}</Typography>
          <Typography variant="caption" color="text.secondary">{formatTime(h.hearing_time)}</Typography>
        </Box>
      ),
    },
    ...(showMatter ? [{
      key: 'matter', label: 'Matter',
      render: (h) => (
        <Box>
          <TextLink to={`/cases/${h.case_id}`}>{h.case_number}</TextLink>
          <Typography variant="body2" color="text.secondary">{h.matter_title}</Typography>
        </Box>
      ),
    }] : []),
    {
      key: 'purpose', label: 'Purpose',
      render: (h) => (
        <Box>
          <Typography variant="body2">{h.purpose || '—'}</Typography>
          {(h.outcome || h.remarks) && (
            <Typography variant="caption" color="text.secondary" component="div">{[h.outcome, h.remarks].filter(Boolean).join(' · ')}</Typography>
          )}
        </Box>
      ),
    },
    {
      key: 'court', label: 'Court',
      render: (h) => (
        <Box>
          <Typography variant="body2">{h.court_name || '—'}</Typography>
          <Typography variant="caption" color="text.secondary">{[h.courtroom, h.judge].filter(Boolean).join(' · ')}</Typography>
        </Box>
      ),
    },
    ...(showMatter ? [{ key: 'lead_counsel', label: 'Lead counsel', render: (h) => h.lead_counsel || '—' }] : []),
    { key: 'status', label: 'Status', render: (h) => <StatusChip status={h.status} /> },
    ...(canWork ? [{
      key: 'actions', label: <span className="sr-only">Actions</span>, align: 'right', nowrap: true,
      render: (h) => (
        <Stack direction="row" spacing={0.5} justifyContent="flex-end" alignItems="center">
          {h.status === 'Scheduled' && (
            <Button size="small" variant={h.hearing_date <= today ? 'contained' : 'text'} onClick={() => setResultFor(h)}>Record result</Button>
          )}
          <Tooltip title="Edit"><IconButton size="small" aria-label="Edit hearing" onClick={() => setEditing(h)}><EditOutlined fontSize="small" /></IconButton></Tooltip>
          {canDelete && (
            <Tooltip title="Delete"><IconButton size="small" aria-label="Delete hearing" onClick={() => setDeleting(h)}><DeleteOutline fontSize="small" /></IconButton></Tooltip>
          )}
        </Stack>
      ),
    }] : []),
  ];
  return (
    <>
      <DataTable
        columns={columns}
        rows={hearings}
        rowKey={(h) => h.hearing_id}
        loading={loading}
        error={error}
        onRetry={onRetry}
        flat={flat}
        empty={empty || 'No hearings to show.'}
      />
      <HearingResultDialog open={Boolean(resultFor)} hearing={resultFor} onClose={() => setResultFor(null)} onSaved={onChanged} />
      <HearingDialog open={Boolean(editing)} hearing={editing} onClose={() => setEditing(null)} onSaved={onChanged} />
      <ConfirmDialog
        open={Boolean(deleting)}
        danger
        title="Delete this hearing?"
        message="Use this only for an entry made by mistake. If the hearing didn't take place, record it as cancelled so the history stays complete."
        confirmLabel="Delete"
        onClose={() => setDeleting(null)}
        onConfirm={async () => {
          await hearingsAPI.delete(deleting.hearing_id);
          toast('Hearing deleted');
          onChanged();
        }}
      />
    </>
  );
}

// ------------------------------------------------------------------ tasks

export function TaskDialog({ open, onClose, onSaved, caseId, task, matterOptions }) {
  const toast = useToast();
  const { data: people } = useFetch(() => teamAPI.directory());
  const assignees = (people || []).map((p) => ({ value: p.user_id, label: p.name }));
  const fields = [
    { name: 'title', label: 'What needs doing', required: true, full: true },
    { name: 'kind', label: 'Type', type: 'select', required: true, options: TASK_KINDS },
    { name: 'priority', label: 'Priority', type: 'select', required: true, options: ['Low', 'Normal', 'High'] },
    { name: 'due_date', label: 'Due date', type: 'date', helper: 'Required for a deadline' },
    { name: 'assignee_id', label: 'Assigned to', type: 'select', options: assignees, helper: 'You, if left empty' },
    ...(caseId || task ? [] : [{ name: 'case_id', label: 'Matter', type: 'select', options: matterOptions || [], full: true }]),
    { name: 'description', label: 'Details', type: 'multiline' },
  ];
  return (
    <FormDialog
      open={open}
      onClose={onClose}
      title={task ? 'Edit task' : 'Add a task or deadline'}
      fields={fields}
      initial={task || { kind: 'Task', priority: 'Normal' }}
      onSubmit={async (v) => {
        const body = {
          title: v.title, kind: v.kind, priority: v.priority, description: v.description || null,
          due_date: v.due_date || null, assignee_id: v.assignee_id || null,
        };
        if (task) await tasksAPI.update(task.task_id, body);
        else await tasksAPI.create({ ...body, case_id: caseId || v.case_id || null });
        toast(task ? 'Task updated' : 'Task added');
        onSaved();
      }}
    />
  );
}

export function TasksTable({ tasks, loading, error, onRetry, onChanged, showMatter = true, flat, empty, pagination }) {
  const toast = useToast();
  const [editing, setEditing] = useState(null);
  const toggle = async (task) => {
    try {
      await tasksAPI.update(task.task_id, { status: task.status === 'Done' ? 'Open' : 'Done' });
      onChanged();
    } catch {
      toast('Could not update that task', 'error');
    }
  };
  const columns = [
    {
      key: 'done', label: <span className="sr-only">Done</span>,
      render: (t) => <Checkbox checked={t.status === 'Done'} onChange={() => toggle(t)} inputProps={{ 'aria-label': `Mark "${t.title}" done` }} />,
    },
    {
      key: 'title', label: 'Task',
      render: (t) => (
        <Box>
          <Typography variant="body2" sx={{ fontWeight: 700, textDecoration: t.status === 'Done' ? 'line-through' : 'none' }}>{t.title}</Typography>
          <Typography variant="caption" color="text.secondary">
            {t.kind === 'Task' ? 'Task' : `${t.kind} deadline`}{t.priority === 'High' ? ' · High priority' : ''}
          </Typography>
        </Box>
      ),
    },
    ...(showMatter ? [{ key: 'matter', label: 'Matter', nowrap: true, render: (t) => (t.case_id ? <TextLink to={`/cases/${t.case_id}`}>{t.case_number}</TextLink> : '—') }] : []),
    { key: 'due', label: 'Due', nowrap: true, render: (t) => <DueLabel date={t.due_date} done={t.status === 'Done'} /> },
    { key: 'assignee_name', label: 'Assigned to' },
    {
      key: 'edit', label: <span className="sr-only">Edit</span>, align: 'right',
      render: (t) => <IconButton size="small" aria-label={`Edit "${t.title}"`} onClick={() => setEditing(t)}><EditOutlined fontSize="small" /></IconButton>,
    },
  ];
  return (
    <>
      <DataTable
        columns={columns}
        rows={tasks}
        rowKey={(t) => t.task_id}
        loading={loading}
        error={error}
        onRetry={onRetry}
        flat={flat}
        pagination={pagination}
        empty={empty || 'Nothing to do here.'}
      />
      <TaskDialog open={Boolean(editing)} task={editing} onClose={() => setEditing(null)} onSaved={onChanged} />
    </>
  );
}

// ------------------------------------------------------------------ documents

async function saveDownload(doc) {
  const response = await evidenceAPI.downloadFile(doc.evidence_id);
  const url = window.URL.createObjectURL(new Blob([response.data], { type: doc.content_type }));
  const link = document.createElement('a');
  link.href = url;
  link.download = doc.file_name || `document-${doc.evidence_id}`;
  document.body.appendChild(link);
  link.click();
  link.remove();
  window.URL.revokeObjectURL(url);
}

export function DocumentDialog({ open, onClose, onSaved, caseId, matterOptions }) {
  const toast = useToast();
  return (
    <FormDialog
      open={open}
      onClose={onClose}
      title="Add a document"
      submitLabel="Upload"
      initial={{ filed_date: isoDate(), category: 'Evidence', status: 'Received' }}
      fields={[
        ...(caseId ? [] : [{ name: 'case_id', label: 'Matter', type: 'select', required: true, options: matterOptions || [], full: true }]),
        { name: 'file', label: 'Choose a file', type: 'file', helper: 'PDF, Word, Excel, images, audio or video, up to 50 MB. Leave empty to record a physical document.' },
        { name: 'description', label: 'Description', type: 'multiline' },
        { name: 'category', label: 'Category', type: 'select', required: true, options: DOCUMENT_CATEGORIES },
        { name: 'status', label: 'Status', type: 'select', required: true, options: DOCUMENT_STATUSES },
        { name: 'filed_date', label: 'Document date', type: 'date', required: true },
      ]}
      onSubmit={async (v) => {
        const form = new FormData();
        form.append('case_id', caseId || v.case_id);
        form.append('filed_date', v.filed_date);
        form.append('category', v.category);
        form.append('status', v.status);
        if (v.description) form.append('description', v.description);
        if (v.file) form.append('file', v.file);
        await evidenceAPI.create(form);
        toast('Document added');
        onSaved();
      }}
    />
  );
}

export function DocumentsTable({ documents, loading, error, onRetry, onChanged, showMatter = true, canDelete = () => false, flat, empty, pagination }) {
  const toast = useToast();
  const [deleting, setDeleting] = useState(null);

  const download = async (doc) => {
    try {
      await saveDownload(doc);
    } catch {
      toast('Could not download that file. File storage may be unavailable.', 'error');
    }
  };
  const attach = async (doc, file) => {
    if (!file) return;
    const form = new FormData();
    form.append('file', file);
    try {
      await evidenceAPI.uploadFile(doc.evidence_id, form);
      toast('File attached');
      onChanged();
    } catch (e) {
      toast(e.response?.data?.detail || 'Could not upload that file', 'error');
    }
  };

  const columns = [
    {
      key: 'doc', label: 'Document',
      render: (d) => (
        <Box>
          <Typography variant="body2" sx={{ fontWeight: 700 }}>{d.file_name || d.description || `Document ${d.evidence_id}`}</Typography>
          <Typography variant="caption" color="text.secondary">
            {d.file_name && d.description ? `${d.description} · ` : ''}{d.has_file ? formatSize(d.file_size) : 'No file attached'}
          </Typography>
        </Box>
      ),
    },
    ...(showMatter ? [{ key: 'matter', label: 'Matter', nowrap: true, render: (d) => <TextLink to={`/cases/${d.case_id}?tab=documents`}>{d.case_number}</TextLink> }] : []),
    { key: 'category', label: 'Category' },
    { key: 'filed_date', label: 'Date', nowrap: true, render: (d) => formatDate(d.filed_date) },
    { key: 'status', label: 'Status', render: (d) => <StatusChip status={d.status} /> },
    {
      key: 'actions', label: <span className="sr-only">Actions</span>, align: 'right', nowrap: true,
      render: (d) => (
        <Stack direction="row" spacing={0.5} justifyContent="flex-end">
          {d.has_file ? (
            <Tooltip title="Download"><IconButton size="small" aria-label={`Download ${d.file_name}`} onClick={() => download(d)}><DownloadOutlined fontSize="small" /></IconButton></Tooltip>
          ) : (
            <Tooltip title="Attach a file">
              <IconButton size="small" component="label" aria-label="Attach a file">
                <UploadFileOutlined fontSize="small" />
                <input hidden type="file" onChange={(e) => attach(d, e.target.files?.[0])} />
              </IconButton>
            </Tooltip>
          )}
          {canDelete(d) && (
            <Tooltip title="Delete"><IconButton size="small" aria-label="Delete document" onClick={() => setDeleting(d)}><DeleteOutline fontSize="small" /></IconButton></Tooltip>
          )}
        </Stack>
      ),
    },
  ];
  return (
    <>
      <DataTable columns={columns} rows={documents} rowKey={(d) => d.evidence_id} loading={loading} error={error} onRetry={onRetry} flat={flat} pagination={pagination} empty={empty || 'No documents yet.'} />
      <ConfirmDialog
        open={Boolean(deleting)}
        danger
        title="Delete this document?"
        message={`This permanently removes "${deleting?.file_name || deleting?.description || 'the document'}" and its file. The audit log keeps a record that it existed.`}
        confirmLabel="Delete"
        onClose={() => setDeleting(null)}
        onConfirm={async () => {
          await evidenceAPI.delete(deleting.evidence_id);
          toast('Document deleted');
          onChanged();
        }}
      />
    </>
  );
}

