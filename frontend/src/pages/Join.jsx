import React, { useEffect, useState } from 'react';
import { Alert, Box, Button, MenuItem, TextField, Typography } from '@mui/material';
import { CheckCircleOutline } from '@mui/icons-material';
import { authAPI, errorMessage } from '../services/api';
import { TextLink } from '../components/ui';

const EMPTY = {
  fname: '', lname: '', username: '', email: '', password: '', confirm: '', phoneno: '',
  requested_role: 'lawyer', bar_id: '', designation: '', group_id: '', message: '',
};

export default function Join() {
  const [form, setForm] = useState(EMPTY);
  const [groups, setGroups] = useState([]);
  const [needsAdmin, setNeedsAdmin] = useState(false);
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);
  const [done, setDone] = useState(false);

  useEffect(() => {
    authAPI.setupStatus().then(({ data }) => setNeedsAdmin(data.needs_first_admin)).catch(() => {});
    authAPI.practiceGroups().then(({ data }) => setGroups(data)).catch(() => {});
  }, []);

  const set = (name) => (e) => setForm((f) => ({ ...f, [name]: e.target.value }));

  const submit = async (e) => {
    e.preventDefault();
    setError('');
    if (form.password !== form.confirm) {
      setError('The two passwords do not match.');
      return;
    }
    setBusy(true);
    try {
      if (needsAdmin) {
        await authAPI.createFirstAdmin({
          username: form.username, email: form.email, password: form.password,
          full_name: `${form.fname} ${form.lname}`.trim(), role: 'admin',
        });
      } else {
        const { confirm, ...body } = form;
        Object.keys(body).forEach((k) => { if (body[k] === '') delete body[k]; });
        await authAPI.submitJoinRequest(body);
      }
      setDone(true);
    } catch (err) {
      setError(errorMessage(err));
    } finally {
      setBusy(false);
    }
  };

  const page = (children) => (
    <Box component="main" sx={{ minHeight: '100vh', display: 'flex', justifyContent: 'center', alignItems: 'center', p: 3, bgcolor: 'background.default' }}>
      <Box sx={{ width: '100%', maxWidth: 560 }}>{children}</Box>
    </Box>
  );

  if (done) {
    return page(
      <Box sx={{ textAlign: 'center' }}>
        <CheckCircleOutline sx={{ fontSize: 48, color: '#166534' }} aria-hidden />
        <Typography component="h1" variant="h4" sx={{ mb: 1 }}>{needsAdmin ? 'Admin account created' : 'Request sent'}</Typography>
        <Typography color="text.secondary" sx={{ mb: 3 }}>
          {needsAdmin
            ? 'You can now sign in and set up the firm.'
            : 'An admin at the firm will review your request. You can sign in with this username and password once it is approved.'}
        </Typography>
        <TextLink to="/login">Back to sign in</TextLink>
      </Box>,
    );
  }

  const isLawyer = !needsAdmin && form.requested_role === 'lawyer';
  return page(
    <>
      <Typography component="h1" variant="h4" sx={{ mb: 0.5 }}>{needsAdmin ? 'Set up the first admin' : 'Request to join the firm'}</Typography>
      <Typography variant="body2" color="text.secondary" sx={{ mb: 3 }}>
        {needsAdmin ? 'This account will manage the firm and approve everyone else.' : 'An admin reviews every request before access is given.'}
      </Typography>
      {error && <Alert severity="error" sx={{ mb: 2 }} role="alert">{error}</Alert>}
      <Box component="form" onSubmit={submit} sx={{ display: 'grid', gridTemplateColumns: { xs: '1fr', sm: '1fr 1fr' }, gap: 2 }}>
        <TextField label="First name" required value={form.fname} onChange={set('fname')} autoFocus />
        <TextField label="Last name" required value={form.lname} onChange={set('lname')} />
        <TextField label="Email" type="email" required value={form.email} onChange={set('email')} autoComplete="email" />
        <TextField label="Username" required value={form.username} onChange={set('username')} autoComplete="username" helperText="At least 3 characters" />
        <TextField label="Password" type="password" required value={form.password} onChange={set('password')} autoComplete="new-password" helperText="At least 8 characters" />
        <TextField label="Confirm password" type="password" required value={form.confirm} onChange={set('confirm')} autoComplete="new-password" />
        {!needsAdmin && (
          <>
            <TextField select label="I am joining as" value={form.requested_role} onChange={set('requested_role')}>
              <MenuItem value="lawyer">Lawyer</MenuItem>
              <MenuItem value="staff">Staff</MenuItem>
            </TextField>
            <TextField label="Phone" value={form.phoneno} onChange={set('phoneno')} autoComplete="tel" />
          </>
        )}
        {isLawyer && (
          <>
            <TextField label="Bar enrolment number" value={form.bar_id} onChange={set('bar_id')} />
            <TextField label="Designation" value={form.designation} onChange={set('designation')} helperText="For example: Associate" />
            <TextField select label="Practice group" value={form.group_id} onChange={set('group_id')} sx={{ gridColumn: '1 / -1' }}>
              <MenuItem value=""><em>Not sure yet</em></MenuItem>
              {groups.map((g) => <MenuItem key={g.group_id} value={g.group_id}>{g.group_name}</MenuItem>)}
            </TextField>
          </>
        )}
        {!needsAdmin && <TextField label="Message for the admin" multiline minRows={2} value={form.message} onChange={set('message')} sx={{ gridColumn: '1 / -1' }} />}
        <Button type="submit" variant="contained" size="large" disabled={busy} sx={{ gridColumn: '1 / -1' }}>
          {busy ? 'Sending…' : needsAdmin ? 'Create admin account' : 'Send request'}
        </Button>
      </Box>
      <Typography variant="body2" sx={{ mt: 3 }} align="center">Already have an account? <TextLink to="/login">Sign in</TextLink></Typography>
    </>,
  );
}
