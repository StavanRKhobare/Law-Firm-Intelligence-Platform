import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Box, TextField, Button, Typography, Alert, InputAdornment, IconButton } from '@mui/material';
import { AccountBalance, Visibility, VisibilityOff } from '@mui/icons-material';
import { tokens } from '../theme';
import { useAuth } from '../context/AuthContext';

export default function Login() {
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const { login } = useAuth();
  const navigate = useNavigate();

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');
    setLoading(true);

    const result = await login({ username, password });

    if (result.success) {
      navigate('/');
    } else {
      setError(result.error);
    }
    setLoading(false);
  };

  return (
    <Box component="main" sx={{ minHeight: '100vh', display: 'grid', gridTemplateColumns: { xs: '1fr', md: '1fr 1fr' } }}>
      <Box
        sx={{
          display: { xs: 'none', md: 'flex' },
          flexDirection: 'column',
          justifyContent: 'space-between',
          p: 6,
          color: '#E2E8F0',
          bgcolor: tokens.sidebar,
          backgroundImage: 'radial-gradient(circle at 20% 20%, rgba(30,58,138,0.9), transparent 60%)',
        }}
      >
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1.5 }}>
          <AccountBalance sx={{ color: '#FBBF24' }} aria-hidden />
          <Typography sx={{ fontFamily: '"EB Garamond", serif', fontSize: '1.5rem', fontWeight: 600, color: '#fff' }}>
            Chambers
          </Typography>
        </Box>
        <Box sx={{ maxWidth: 440 }}>
          <Typography sx={{ fontFamily: '"EB Garamond", serif', fontSize: '2.6rem', lineHeight: 1.15, color: '#fff', mb: 2 }}>
            Every matter, counsel and filing in one place.
          </Typography>
          <Typography sx={{ color: '#94A3B8' }}>
            Track matters from filing to disposal, manage evidence, and see how the firm’s caseload is moving.
          </Typography>
        </Box>
        <Typography variant="caption" sx={{ color: '#64748B' }}>Litigation case management</Typography>
      </Box>

      <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'center', p: 3, bgcolor: 'background.default' }}>
        <Box sx={{ width: '100%', maxWidth: 380 }}>
          <Typography component="h1" variant="h4" sx={{ mb: 0.5 }}>
            Sign in
          </Typography>
          <Typography variant="body2" color="text.secondary" sx={{ mb: 3 }}>
            Use your firm account to continue.
          </Typography>

          {error && (
            <Alert severity="error" sx={{ mb: 2 }} role="alert">
              {error}
            </Alert>
          )}

          <Box component="form" onSubmit={handleSubmit} noValidate={false}>
            <TextField
              margin="normal"
              required
              fullWidth
              size="medium"
              label="Username"
              autoComplete="username"
              autoFocus
              value={username}
              onChange={(e) => setUsername(e.target.value)}
            />
            <TextField
              margin="normal"
              required
              fullWidth
              size="medium"
              label="Password"
              type={showPassword ? 'text' : 'password'}
              autoComplete="current-password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              InputProps={{
                endAdornment: (
                  <InputAdornment position="end">
                    <IconButton
                      aria-label={showPassword ? 'Hide password' : 'Show password'}
                      onClick={() => setShowPassword(!showPassword)}
                      edge="end"
                    >
                      {showPassword ? <VisibilityOff /> : <Visibility />}
                    </IconButton>
                  </InputAdornment>
                ),
              }}
            />
            <Button type="submit" fullWidth variant="contained" size="large" sx={{ mt: 2, py: 1.25 }} disabled={loading}>
              {loading ? 'Signing in…' : 'Sign in'}
            </Button>
          </Box>

          <Box sx={{ mt: 4, p: 2, border: 1, borderColor: 'divider', borderRadius: 2, bgcolor: 'background.paper' }}>
            <Typography variant="caption" color="text.secondary" sx={{ fontWeight: 700 }} display="block">
              Demo accounts
            </Typography>
            <Typography variant="caption" display="block">admin / admin123 · lawyer1 / lawyer123</Typography>
          </Box>
        </Box>
      </Box>
    </Box>
  );
}
