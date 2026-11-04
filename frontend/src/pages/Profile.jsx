import React from 'react';
import { Box, Button, Grid, Typography } from '@mui/material';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { formatDateTime, PageHeader, Panel, useToast } from '../components/ui';
import { PasswordForm } from './ChangePassword';

export default function Profile() {
  const { user } = useAuth();
  const toast = useToast();
  const navigate = useNavigate();
  const facts = [
    ['Name', user.full_name], ['Username', user.username], ['Email', user.email],
    ['Role', user.role], ['Last sign-in', formatDateTime(user.last_login_at)],
  ];
  return (
    <Box>
      <PageHeader title="My profile" />
      <Grid container spacing={2}>
        <Grid item xs={12} md={6}>
          <Panel title="Account">
            {facts.map(([label, value]) => (
              <Box key={label} sx={{ mb: 1.25 }}>
                <Typography variant="caption" color="text.secondary" component="div">{label}</Typography>
                <Typography variant="body2" sx={{ textTransform: label === 'Role' ? 'capitalize' : 'none' }}>{value || '—'}</Typography>
              </Box>
            ))}
            {user.lawyer_id && <Button onClick={() => navigate(`/lawyers/${user.lawyer_id}`)}>View my lawyer profile</Button>}
          </Panel>
        </Grid>
        <Grid item xs={12} md={6}>
          <Panel title="Change password">
            <PasswordForm onDone={() => toast('Password changed')} />
          </Panel>
        </Grid>
      </Grid>
    </Box>
  );
}
