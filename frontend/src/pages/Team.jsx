import React, { useState } from 'react';
import { useSearchParams } from 'react-router-dom';
import {
  Alert, Badge, Box, Button, Dialog, DialogActions, DialogContent, DialogContentText, DialogTitle, Menu, MenuItem, Stack, Tab, Tabs, Typography,
} from '@mui/material';
import { MoreVert, PersonAddAlt1Outlined } from '@mui/icons-material';
import { errorMessage, lawyersAPI, referenceAPI, teamAPI } from '../services/api';
import { useAuth } from '../context/AuthContext';
import { useFetch } from '../hooks/useFetch';
import {
  compact, ConfirmDialog, DataTable, formatDate, formatDateTime, FormDialog, fullName, PageHeader, StatusChip, TextLink, useToast,
} from '../components/ui';

function TemporaryPassword({ info, onClose }) {
  const toast = useToast();
  return (
    <Dialog open={Boolean(info)} onClose={onClose} maxWidth="xs" fullWidth>
      <DialogTitle>Temporary password</DialogTitle>
      <DialogContent>
        <DialogContentText sx={{ mb: 2 }}>
          Give this to {info?.name} privately. It is shown only once. They’ll choose their own password when they first sign in.
        </DialogContentText>
        <Typography variant="body2" color="text.secondary">Username</Typography>
        <Typography sx={{ fontFamily: 'monospace', mb: 1 }}>{info?.username}</Typography>
        <Typography variant="body2" color="text.secondary">Temporary password</Typography>
        <Typography sx={{ fontFamily: 'monospace', fontWeight: 700 }}>{info?.password}</Typography>
      </DialogContent>
      <DialogActions>
        <Button onClick={() => navigator.clipboard?.writeText(info.password).then(() => toast('Copied'))}>Copy password</Button>
        <Button variant="contained" onClick={onClose}>Done</Button>
      </DialogActions>
    </Dialog>
  );
}

function MemberMenu({ member, onChanged, onPassword }) {
  const toast = useToast();
  const { user } = useAuth();
  const [anchor, setAnchor] = useState(null);
  const [confirm, setConfirm] = useState(null);

  const run = async (fn, message) => {
    setAnchor(null);
    try {
      await fn();
      toast(message);
      onChanged();
    } catch (e) {
      toast(errorMessage(e), 'error');
    }
  };

  const self = member.user_id === user.user_id;
  return (
    <>
      <Button size="small" aria-label={`Actions for ${member.full_name || member.username}`} onClick={(e) => setAnchor(e.currentTarget)} sx={{ minWidth: 40 }}><MoreVert fontSize="small" /></Button>
      <Menu anchorEl={anchor} open={Boolean(anchor)} onClose={() => setAnchor(null)}>
        <MenuItem onClick={() => { setAnchor(null); setConfirm('reset'); }}>Reset password</MenuItem>
        {['admin', 'lawyer', 'staff'].filter((r) => r !== member.role).map((role) => (
          <MenuItem key={role} disabled={self} onClick={() => run(() => teamAPI.changeRole(member.user_id, role), `Now ${role}`)}>Make {role}</MenuItem>
        ))}
        {member.is_active ? (
          <MenuItem disabled={self} onClick={() => { setAnchor(null); setConfirm('deactivate'); }}>Deactivate</MenuItem>
        ) : (
          <MenuItem onClick={() => run(() => teamAPI.activate(member.user_id), 'Reactivated')}>Reactivate</MenuItem>
        )}
      </Menu>
      <ConfirmDialog
        open={confirm === 'deactivate'}
        danger
        title="Deactivate this person?"
        message={`${member.full_name || member.username} loses access immediately. Their history stays. Any matters they lead keep them as lead until you reassign them.`}
        confirmLabel="Deactivate"
        onClose={() => setConfirm(null)}
        onConfirm={async () => {
          await teamAPI.deactivate(member.user_id);
          toast('Deactivated');
          onChanged();
        }}
      />
      <ConfirmDialog
        open={confirm === 'reset'}
        title="Reset this password?"
        message={`${member.full_name || member.username}'s current password stops working, and you'll get a temporary one to pass on.`}
        confirmLabel="Reset password"
        onClose={() => setConfirm(null)}
        onConfirm={async () => {
          const { data } = await teamAPI.resetPassword(member.user_id);
          onPassword({ name: member.full_name || member.username, username: member.username, password: data.temporary_password });
        }}
      />
    </>
  );
}

function JoinRequests({ groups, onChanged }) {
  const toast = useToast();
  const [show, setShow] = useState('Pending');
  const [approving, setApproving] = useState(null);
  const [rejecting, setRejecting] = useState(null);
  const { data, loading, error, reload } = useFetch(() => teamAPI.joinRequests(show), [show]);
  const refresh = () => { reload(); onChanged(); };

  const columns = [
    {
      key: 'person', label: 'Person',
      render: (r) => (
        <Box>
          <Typography variant="body2" sx={{ fontWeight: 700 }}>{r.fname} {r.lname}</Typography>
          <Typography variant="caption" color="text.secondary">{r.email}{r.phoneno ? ` · ${r.phoneno}` : ''}</Typography>
        </Box>
      ),
    },
    { key: 'requested_role', label: 'Joining as', render: (r) => <span style={{ textTransform: 'capitalize' }}>{r.requested_role}</span> },
    {
      key: 'details', label: 'Details',
      render: (r) => (
        <Box>
          <Typography variant="body2">{[r.designation, r.group_name].filter(Boolean).join(' · ') || '—'}</Typography>
          {r.bar_id && <Typography variant="caption" color="text.secondary" component="div">Bar no. {r.bar_id}</Typography>}
          {r.message && <Typography variant="caption" color="text.secondary" component="div">“{r.message}”</Typography>}
        </Box>
      ),
    },
    { key: 'created_at', label: 'Requested', nowrap: true, render: (r) => formatDateTime(r.created_at) },
    show === 'Pending' ? {
      key: 'actions', label: <span className="sr-only">Actions</span>, align: 'right', nowrap: true,
      render: (r) => (
        <Stack direction="row" spacing={1} justifyContent="flex-end">
          <Button size="small" color="error" onClick={() => setRejecting(r)}>Reject</Button>
          <Button size="small" variant="contained" onClick={() => setApproving(r)}>Review and approve</Button>
        </Stack>
      ),
    } : { key: 'status', label: 'Status', render: (r) => <StatusChip status={r.status} /> },
  ];

  return (
    <Box>
      <Stack direction="row" spacing={1} sx={{ mb: 2 }}>
        {['Pending', 'Approved', 'Rejected'].map((s) => (
          <Button key={s} size="small" variant={show === s ? 'contained' : 'outlined'} onClick={() => setShow(s)}>{s}</Button>
        ))}
      </Stack>
      <DataTable columns={columns} rows={data} rowKey={(r) => r.request_id} loading={loading} error={error} onRetry={reload} empty={show === 'Pending' ? 'Nobody is waiting to join.' : `No ${show.toLowerCase()} requests.`} />
      <FormDialog
        open={Boolean(approving)}
        title={`Approve ${approving?.fname} ${approving?.lname}`}
        intro="Check these details, which the applicant entered themselves. Approving gives them access straight away."
        submitLabel="Approve"
        initial={approving && { role: approving.requested_role, bar_id: approving.bar_id, designation: approving.designation, group_id: approving.group_id }}
        fields={[
          { name: 'role', label: 'Role', type: 'select', required: true, options: ['lawyer', 'staff', 'admin'] },
          { name: 'designation', label: 'Designation' },
          { name: 'bar_id', label: 'Bar enrolment number' },
          { name: 'group_id', label: 'Practice group', type: 'select', options: groups },
        ]}
        onClose={() => setApproving(null)}
        onSubmit={async (v) => {
          await teamAPI.approve(approving.request_id, compact(v));
          toast(`${approving.fname} has joined the firm`);
          refresh();
        }}
      />
      <FormDialog
        open={Boolean(rejecting)}
        title={`Reject ${rejecting?.fname} ${rejecting?.lname}'s request?`}
        submitLabel="Reject"
        fields={[{ name: 'note', label: 'Reason (kept for your records)', type: 'multiline' }]}
        onClose={() => setRejecting(null)}
        onSubmit={async (v) => {
          await teamAPI.reject(rejecting.request_id, compact(v));
          toast('Request rejected');
          refresh();
        }}
      />
    </Box>
  );
}

export default function Team() {
  const toast = useToast();
  const [params, setParams] = useSearchParams();
  const tab = params.get('tab') || 'members';
  const [adding, setAdding] = useState(false);
  const [newPassword, setNewPassword] = useState(null);
  const members = useFetch(() => teamAPI.members());
  const pending = useFetch(() => teamAPI.joinRequests('Pending'));
  const { data: groupRows } = useFetch(() => referenceAPI.practiceGroups());
  const { data: lawyerRows, reload: reloadLawyers } = useFetch(() => lawyersAPI.getAll({ size: 100 }));
  const groups = (groupRows || []).map((g) => ({ value: g.group_id, label: g.group_name }));
  const withoutLogin = (lawyerRows?.items || []).filter((l) => !l.has_login && l.is_active);
  const [prefill, setPrefill] = useState(null);

  const openAdd = (lawyer) => {
    setPrefill(lawyer ? {
      lawyer_id: lawyer.lawyer_id, fname: lawyer.fname, lname: lawyer.lname, role: 'lawyer',
    } : { role: 'lawyer' });
    setAdding(true);
  };

  const columns = [
    {
      key: 'name', label: 'Name',
      render: (m) => (
        <Box>
          {m.lawyer_id ? <TextLink to={`/lawyers/${m.lawyer_id}`}>{m.full_name || m.username}</TextLink> : <Typography variant="body2" sx={{ fontWeight: 700 }}>{m.full_name || m.username}</Typography>}
          <Typography variant="caption" color="text.secondary" component="div">{m.username} · {m.email}</Typography>
        </Box>
      ),
    },
    { key: 'role', label: 'Role', render: (m) => <span style={{ textTransform: 'capitalize' }}>{m.role}</span> },
    { key: 'status', label: 'Status', render: (m) => <StatusChip status={m.is_active ? 'Active' : 'Inactive'} /> },
    { key: 'last_login_at', label: 'Last sign-in', nowrap: true, render: (m) => (m.must_change_password ? 'Hasn’t set a password yet' : formatDateTime(m.last_login_at)) },
    { key: 'created_at', label: 'Added', nowrap: true, render: (m) => formatDate(m.created_at.slice(0, 10)) },
    {
      key: 'actions', label: <span className="sr-only">Actions</span>, align: 'right',
      render: (m) => <MemberMenu member={m} onChanged={members.reload} onPassword={setNewPassword} />,
    },
  ];

  return (
    <Box>
      <PageHeader
        title="Team and access"
        subtitle="Who can sign in, and what they can do"
        actions={<Button variant="contained" startIcon={<PersonAddAlt1Outlined />} onClick={() => openAdd(null)}>Add a person</Button>}
      />
      <Tabs value={tab} onChange={(_, v) => setParams(v === 'members' ? {} : { tab: v }, { replace: true })} sx={{ mb: 2, borderBottom: 1, borderColor: 'divider' }}>
        <Tab value="members" label="Members" />
        <Tab
          value="requests"
          label={<Badge color="secondary" badgeContent={pending.data?.length || 0} sx={{ '& .MuiBadge-badge': { right: -14 } }}>Join requests</Badge>}
        />
      </Tabs>
      {tab === 'members' && (
        <>
          {withoutLogin.length > 0 && (
            <Alert severity="info" sx={{ mb: 2 }}>
              <Typography variant="body2" sx={{ mb: 1 }}>{withoutLogin.length} {withoutLogin.length === 1 ? 'lawyer has' : 'lawyers have'} no login yet:</Typography>
              <Stack direction="row" spacing={1} useFlexGap sx={{ flexWrap: 'wrap' }}>
                {withoutLogin.map((l) => <Button key={l.lawyer_id} size="small" variant="outlined" onClick={() => openAdd(l)}>Create login for {fullName(l)}</Button>)}
              </Stack>
            </Alert>
          )}
          <DataTable columns={columns} rows={members.data} rowKey={(m) => m.user_id} loading={members.loading} error={members.error} onRetry={members.reload} empty="No members yet." />
        </>
      )}
      {tab === 'requests' && <JoinRequests groups={groups} onChanged={() => { pending.reload(); members.reload(); reloadLawyers(); }} />}

      <FormDialog
        open={adding}
        title={prefill?.lawyer_id ? `Create a login for ${prefill.fname} ${prefill.lname}` : 'Add a person'}
        intro="They get a temporary password, and must choose their own when they first sign in."
        submitLabel="Create account"
        initial={prefill}
        fields={[
          { name: 'fname', label: 'First name', required: true },
          { name: 'lname', label: 'Last name', required: true },
          { name: 'username', label: 'Username', required: true },
          { name: 'email', label: 'Email', type: 'email', required: true },
          { name: 'role', label: 'Role', type: 'select', required: true, options: ['lawyer', 'staff', 'admin'] },
          { name: 'phoneno', label: 'Phone', showIf: (v) => v.role === 'lawyer' && !v.lawyer_id },
          { name: 'designation', label: 'Designation', showIf: (v) => v.role === 'lawyer' && !v.lawyer_id },
          { name: 'bar_id', label: 'Bar enrolment number', showIf: (v) => v.role === 'lawyer' && !v.lawyer_id },
          { name: 'group_id', label: 'Practice group', type: 'select', options: groups, showIf: (v) => v.role === 'lawyer' && !v.lawyer_id, full: true },
        ]}
        onClose={() => setAdding(false)}
        onSubmit={async (v) => {
          const { data } = await teamAPI.addMember(compact(v));
          setNewPassword({ name: data.member.full_name, username: data.member.username, password: data.temporary_password });
          members.reload();
          reloadLawyers();
          toast('Account created');
        }}
      />
      <TemporaryPassword info={newPassword} onClose={() => setNewPassword(null)} />
    </Box>
  );
}
