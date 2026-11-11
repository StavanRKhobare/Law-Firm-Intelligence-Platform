import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Alert, Box, Button, TextField, Typography } from '@mui/material';
import { authAPI, errorMessage } from '../services/api';
import { useAuth } from '../context/AuthContext';

/** Change password form. Used on its own for a forced change, and inside the profile page. */
export function PasswordForm({ onDone }) {
  const [form, setForm] = useState({ old_password: '', new_password: '', confirm: '' });
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);
  const set = (name) => (e) => setForm((f) => ({ ...f, [name]: e.target.value }));

  const submit = async (e) => {
    e.preventDefault();
    setError('');
    if (form.new_password !== form.confirm) {
      setError('The two new passwords do not match.');
      return;
    }
    setBusy(true);
    try {
      await authAPI.changePassword({ old_password: form.old_password, new_password: form.new_password });
      setForm({ old_password: '', new_password: '', confirm: '' });
      await onDone();
    } catch (err) {
      setError(errorMessage(err));
    } finally {
      setBusy(false);
    }
  };

  return (
    <Box component="form" onSubmit={submit} sx={{ display: 'grid', gap: 2 }}>
      {error && <Alert severity="error" role="alert">{error}</Alert>}
      <TextField label="Current password" type="password" required value={form.old_password} onChange={set('old_password')} autoComplete="current-password" />
      <TextField label="New password" type="password" required value={form.new_password} onChange={set('new_password')} autoComplete="new-password" helperText="At least 8 characters" />
      <TextField label="Confirm new password" type="password" required value={form.confirm} onChange={set('confirm')} autoComplete="new-password" />
      <Button type="submit" variant="contained" disabled={busy}>{busy ? 'Saving…' : 'Change password'}</Button>
    </Box>
  );
}

export default function ChangePassword() {
  const { refreshUser, user, logout } = useAuth();
  const navigate = useNavigate();
  return (
    <Box component="main" sx={{ minHeight: '100vh', display: 'flex', justifyContent: 'center', alignItems: 'center', p: 3 }}>
      <Box sx={{ width: '100%', maxWidth: 400 }}>
        <Typography component="h1" variant="h4" sx={{ mb: 0.5 }}>Choose a new password</Typography>
        <Typography variant="body2" color="text.secondary" sx={{ mb: 3 }}>
          {user?.must_change_password ? 'You were given a temporary password. Choose your own to continue.' : 'Enter your current password and a new one.'}
        </Typography>
        <PasswordForm onDone={async () => { await refreshUser(); navigate('/'); }} />
        <Button sx={{ mt: 2 }} fullWidth onClick={() => { logout(); navigate('/login'); }}>Log out</Button>
      </Box>
    </Box>
  );
}
