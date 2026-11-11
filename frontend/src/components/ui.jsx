/** Shared building blocks, so every page looks and behaves the same way. */
import React, { createContext, useCallback, useContext, useEffect, useState } from 'react';
import { Link as RouterLink } from 'react-router-dom';
import {
  Alert, Box, Button, Card, CardContent, Chip, CircularProgress, Dialog, DialogActions, DialogContent,
  DialogContentText, DialogTitle, InputAdornment, Link, MenuItem, Paper, Skeleton, Snackbar, Stack, Table,
  TableBody, TableCell, TableContainer, TableHead, TablePagination, TableRow, TextField, Typography,
} from '@mui/material';
import { Search } from '@mui/icons-material';
import { errorMessage } from '../services/api';
import { tokens } from '../theme';

// ------------------------------------------------------------------ formatting

/** Parses a date-only string as local time, so it never shifts a day. */
const asDate = (value) => new Date(value.length === 10 ? `${value}T00:00:00` : value);

export const formatDate = (value) => (value
  ? asDate(value).toLocaleDateString('en-IN', { day: 'numeric', month: 'short', year: 'numeric' })
  : '—');

export const formatDay = (value) => asDate(value).toLocaleDateString('en-IN', { weekday: 'short', day: 'numeric', month: 'short' });

export const formatDateTime = (value) => {
  if (!value) return '—';
  // Timestamps from the API are UTC without a marker
  const d = new Date(/[zZ+]/.test(value) ? value : `${value}Z`);
  return d.toLocaleString('en-IN', { day: 'numeric', month: 'short', year: 'numeric', hour: 'numeric', minute: '2-digit' });
};

export const formatTime = (value) => {
  if (!value) return '';
  const [h, m] = value.split(':').map(Number);
  return new Date(2000, 0, 1, h, m).toLocaleTimeString('en-IN', { hour: 'numeric', minute: '2-digit' });
};

export const formatSize = (bytes) => {
  if (bytes == null) return '—';
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${Math.round(bytes / 1024)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
};

export const isoDate = (date = new Date()) => {
  const offset = date.getTimezoneOffset() * 60000;
  return new Date(date.getTime() - offset).toISOString().slice(0, 10);
};

export const daysFrom = (value) => Math.round((asDate(value) - asDate(isoDate())) / 86400000);

export const fullName = (row) => `${row.fname} ${row.lname}`.trim();

// ------------------------------------------------------------------ toast

const ToastContext = createContext(() => {});
export const useToast = () => useContext(ToastContext);

export function ToastProvider({ children }) {
  const [toast, setToast] = useState(null);
  const show = useCallback((message, severity = 'success') => setToast({ message, severity }), []);
  return (
    <ToastContext.Provider value={show}>
      {children}
      <Snackbar
        open={Boolean(toast)}
        autoHideDuration={toast?.severity === 'error' ? 7000 : 3500}
        onClose={(_, reason) => reason !== 'clickaway' && setToast(null)}
        anchorOrigin={{ vertical: 'bottom', horizontal: 'center' }}
      >
        {toast ? <Alert severity={toast.severity} variant="filled" onClose={() => setToast(null)}>{toast.message}</Alert> : undefined}
      </Snackbar>
    </ToastContext.Provider>
  );
}

// ------------------------------------------------------------------ page structure

export function PageHeader({ title, subtitle, eyebrow, actions }) {
  return (
    <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 2, alignItems: 'flex-end', justifyContent: 'space-between', mb: 3 }}>
      <Box sx={{ minWidth: 0 }}>
        {eyebrow && <Typography variant="overline" color="text.secondary" component="div">{eyebrow}</Typography>}
        <Typography variant="h4" component="h1">{title}</Typography>
        {subtitle && <Typography color="text.secondary" sx={{ mt: 0.5 }}>{subtitle}</Typography>}
      </Box>
      {actions && <Stack direction="row" spacing={1} sx={{ flexWrap: 'wrap', gap: 1 }} useFlexGap>{actions}</Stack>}
    </Box>
  );
}

export function Panel({ title, action, children, sx, noPadding }) {
  return (
    <Card sx={{ height: '100%', ...sx }}>
      <CardContent sx={noPadding ? { p: 0, '&:last-child': { pb: 0 } } : undefined}>
        {(title || action) && (
          <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 1, mb: 1.5, ...(noPadding ? { p: 2, pb: 0 } : {}) }}>
            <Typography variant="h6" component="h2">{title}</Typography>
            {action}
          </Box>
        )}
        {children}
      </CardContent>
    </Card>
  );
}

export function StatTile({ label, value, hint, icon, to, tone }) {
  const toneColor = tone === 'alert' ? '#B91C1C' : tone === 'warn' ? '#92400E' : tokens.primary;
  const toneBg = tone === 'alert' ? '#FEE2E2' : tone === 'warn' ? '#FEF3C7' : tokens.muted;
  const body = (
    <CardContent sx={{ display: 'flex', gap: 2, alignItems: 'flex-start' }}>
      {icon && <Box sx={{ p: 1.25, borderRadius: 2, bgcolor: toneBg, color: toneColor, display: 'flex' }} aria-hidden>{icon}</Box>}
      <Box>
        <Typography variant="body2" color="text.secondary">{label}</Typography>
        <Typography sx={{ fontSize: '1.9rem', fontWeight: 700, lineHeight: 1.2, fontVariantNumeric: 'tabular-nums' }}>{value ?? '—'}</Typography>
        {hint && <Typography variant="caption" color="text.secondary">{hint}</Typography>}
      </Box>
    </CardContent>
  );
  if (!to) return <Card sx={{ height: '100%' }}>{body}</Card>;
  return (
    <Card
      component={RouterLink}
      to={to}
      sx={{ height: '100%', display: 'block', textDecoration: 'none', color: 'inherit', transition: 'border-color 150ms', '&:hover': { borderColor: tokens.primary } }}
    >
      {body}
    </Card>
  );
}

export function EmptyState({ children, action }) {
  return (
    <Box sx={{ py: 4, px: 2, textAlign: 'center' }}>
      <Typography color="text.secondary">{children}</Typography>
      {action && <Box sx={{ mt: 1.5 }}>{action}</Box>}
    </Box>
  );
}

export function Loading({ height = 200 }) {
  return <Skeleton variant="rounded" height={height} aria-label="Loading" />;
}

export function CenteredSpinner() {
  return <Box sx={{ display: 'grid', placeItems: 'center', minHeight: '40vh' }}><CircularProgress aria-label="Loading" /></Box>;
}

/** Shown when a page's data can't load. */
export function LoadError({ message, onRetry }) {
  return (
    <Alert severity="error" action={onRetry ? <Button color="inherit" size="small" onClick={onRetry}>Retry</Button> : undefined}>
      {message}
    </Alert>
  );
}

export function TextLink({ to, children, ...props }) {
  return <Link component={RouterLink} to={to} underline="hover" sx={{ fontWeight: 700 }} {...props}>{children}</Link>;
}

// ------------------------------------------------------------------ chips

const CHIP_STYLES = {
  // matter
  Filed: { bg: '#E0E7FF', fg: '#1E3A8A' },
  Hearing: { bg: '#FEF3C7', fg: '#92400E' },
  Pending: { bg: '#F1F5F9', fg: '#334155' },
  Disposed: { bg: '#DCFCE7', fg: '#166534' },
  // hearing
  Scheduled: { bg: '#E0E7FF', fg: '#1E3A8A' },
  Held: { bg: '#DCFCE7', fg: '#166534' },
  Adjourned: { bg: '#FEF3C7', fg: '#92400E' },
  Cancelled: { bg: '#F1F5F9', fg: '#475569' },
  // document
  Received: { bg: '#E0E7FF', fg: '#1E3A8A' },
  'Under Review': { bg: '#FEF3C7', fg: '#92400E' },
  Produced: { bg: '#DCFCE7', fg: '#166534' },
  // task
  Open: { bg: '#E0E7FF', fg: '#1E3A8A' },
  'In Progress': { bg: '#FEF3C7', fg: '#92400E' },
  Done: { bg: '#DCFCE7', fg: '#166534' },
  High: { bg: '#FEE2E2', fg: '#991B1B' },
  // people
  Active: { bg: '#DCFCE7', fg: '#166534' },
  Inactive: { bg: '#F1F5F9', fg: '#475569' },
  Approved: { bg: '#DCFCE7', fg: '#166534' },
  Rejected: { bg: '#FEE2E2', fg: '#991B1B' },
};

/** The label always carries the meaning, the colour only supports it. */
export function StatusChip({ status }) {
  const style = CHIP_STYLES[status] || { bg: '#F1F5F9', fg: '#334155' };
  return <Chip size="small" label={status} sx={{ bgcolor: style.bg, color: style.fg }} />;
}

/** "in 3 days", "today", "2 days overdue". */
export function DueLabel({ date, done }) {
  if (!date) return <Typography variant="body2" color="text.secondary">No date</Typography>;
  const days = daysFrom(date);
  const late = days < 0 && !done;
  const label = days === 0 ? 'Today' : days === 1 ? 'Tomorrow' : days < 0 ? `${-days} day${days === -1 ? '' : 's'} ${done ? 'ago' : 'overdue'}` : `In ${days} days`;
  return (
    <Box>
      <Typography variant="body2" sx={{ fontWeight: late || days === 0 ? 700 : 400, color: late ? '#B91C1C' : 'text.primary' }}>{label}</Typography>
      <Typography variant="caption" color="text.secondary">{formatDate(date)}</Typography>
    </Box>
  );
}

// ------------------------------------------------------------------ lists

export function SearchField({ value, onChange, placeholder = 'Search', sx }) {
  return (
    <TextField
      placeholder={placeholder}
      value={value}
      onChange={(e) => onChange(e.target.value)}
      inputProps={{ 'aria-label': placeholder }}
      sx={{ minWidth: 240, flex: 1, ...sx }}
      InputProps={{ startAdornment: <InputAdornment position="start"><Search fontSize="small" /></InputAdornment> }}
    />
  );
}

export function FilterSelect({ label, value, onChange, options, minWidth = 170 }) {
  return (
    <TextField select label={label} value={value} onChange={(e) => onChange(e.target.value)} sx={{ minWidth }}>
      {options.map((o) => {
        const opt = typeof o === 'string' ? { value: o, label: o } : o;
        return <MenuItem key={opt.value} value={opt.value}>{opt.label}</MenuItem>;
      })}
    </TextField>
  );
}

export function FilterBar({ children }) {
  return (
    <Paper variant="outlined" sx={{ p: 2, mb: 2, display: 'flex', gap: 1.5, flexWrap: 'wrap', alignItems: 'center' }}>
      {children}
    </Paper>
  );
}

/**
 * columns: [{ key, label, render(row), align, nowrap }]
 * Pass `pagination` ({ total, page, size, onPage, onSize }) for server-side paging.
 */
export function DataTable({ columns, rows, rowKey, loading, error, onRetry, empty = 'Nothing to show.', pagination, dense, flat, rowSx }) {
  const content = (
    <>
      {error && <Box sx={{ p: 2 }}><LoadError message={error} onRetry={onRetry} /></Box>}
      <TableContainer>
        <Table size={dense ? 'small' : 'medium'}>
          <TableHead>
            <TableRow>
              {columns.map((c) => <TableCell key={c.key} align={c.align}>{c.label}</TableCell>)}
            </TableRow>
          </TableHead>
          <TableBody>
            {loading && !rows?.length ? (
              <TableRow><TableCell colSpan={columns.length} align="center" sx={{ py: 5 }}><CircularProgress size={28} aria-label="Loading" /></TableCell></TableRow>
            ) : !rows?.length ? (
              <TableRow><TableCell colSpan={columns.length} sx={{ border: 0 }}><EmptyState>{empty}</EmptyState></TableCell></TableRow>
            ) : rows.map((row) => (
              <TableRow key={rowKey(row)} hover sx={rowSx?.(row)}>
                {columns.map((c) => (
                  <TableCell key={c.key} align={c.align} sx={c.nowrap ? { whiteSpace: 'nowrap' } : undefined}>
                    {c.render ? c.render(row) : (row[c.key] ?? '—')}
                  </TableCell>
                ))}
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </TableContainer>
      {pagination && (
        <TablePagination
          component="div"
          count={pagination.total || 0}
          page={pagination.page}
          onPageChange={(_, p) => pagination.onPage(p)}
          rowsPerPage={pagination.size}
          onRowsPerPageChange={(e) => pagination.onSize(parseInt(e.target.value, 10))}
          rowsPerPageOptions={[10, 25, 50, 100]}
        />
      )}
    </>
  );
  return flat ? content : <Paper variant="outlined">{content}</Paper>;
}

// ------------------------------------------------------------------ dialogs

export function ConfirmDialog({ open, title, message, confirmLabel = 'Confirm', danger, onConfirm, onClose }) {
  const toast = useToast();
  const [busy, setBusy] = useState(false);
  const confirm = async () => {
    setBusy(true);
    try {
      await onConfirm();
      onClose();
    } catch (e) {
      toast(errorMessage(e), 'error');
    } finally {
      setBusy(false);
    }
  };
  return (
    <Dialog open={open} onClose={onClose} maxWidth="xs" fullWidth>
      <DialogTitle>{title}</DialogTitle>
      <DialogContent><DialogContentText>{message}</DialogContentText></DialogContent>
      <DialogActions>
        <Button onClick={onClose}>Cancel</Button>
        <Button onClick={confirm} disabled={busy} variant="contained" color={danger ? 'error' : 'primary'}>{busy ? 'Working…' : confirmLabel}</Button>
      </DialogActions>
    </Dialog>
  );
}

/**
 * A form dialog built from a list of fields, so every form validates and reports errors the same way.
 * field: { name, label, type: text|multiline|date|time|select|file|email|password,
 *          required, options, helper, full, showIf(values) }
 */
export function FormDialog({ open, title, intro, fields, initial, submitLabel = 'Save', onSubmit, onClose, maxWidth = 'sm' }) {
  const [values, setValues] = useState({});
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);
  const [touched, setTouched] = useState(false);

  useEffect(() => {
    if (open) {
      setValues({ ...(initial || {}) });
      setError('');
      setTouched(false);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [open]);

  const set = (name, value) => setValues((v) => ({ ...v, [name]: value }));
  const visible = fields.filter((f) => !f.showIf || f.showIf(values));
  const missing = (f) => f.required && (values[f.name] === undefined || values[f.name] === null || values[f.name] === '');

  const submit = async (e) => {
    e.preventDefault();
    setTouched(true);
    if (visible.some(missing)) return;
    setBusy(true);
    setError('');
    try {
      await onSubmit(values);
      onClose();
    } catch (err) {
      setError(errorMessage(err));
    } finally {
      setBusy(false);
    }
  };

  return (
    <Dialog open={open} onClose={onClose} maxWidth={maxWidth} fullWidth>
      <Box component="form" onSubmit={submit} noValidate>
        <DialogTitle>{title}</DialogTitle>
        <DialogContent dividers>
          {intro && <DialogContentText sx={{ mb: 2 }}>{intro}</DialogContentText>}
          {error && <Alert severity="error" sx={{ mb: 2 }} role="alert">{error}</Alert>}
          <Box sx={{ display: 'grid', gridTemplateColumns: { xs: '1fr', sm: '1fr 1fr' }, gap: 2 }}>
            {visible.map((f) => {
              const invalid = touched && missing(f);
              const common = {
                key: f.name,
                label: f.label,
                required: f.required,
                error: invalid,
                helperText: invalid ? 'This is required' : f.helper,
                sx: { gridColumn: f.full || f.type === 'multiline' ? '1 / -1' : undefined },
              };
              if (f.type === 'file') {
                return (
                  <Box key={f.name} sx={{ gridColumn: '1 / -1' }}>
                    <Button component="label" variant="outlined">
                      {values[f.name] ? 'Choose a different file' : f.label}
                      <input hidden type="file" onChange={(e) => set(f.name, e.target.files?.[0] || null)} />
                    </Button>
                    <Typography variant="body2" sx={{ mt: 1 }} color="text.secondary">
                      {values[f.name] ? `${values[f.name].name} (${formatSize(values[f.name].size)})` : f.helper}
                    </Typography>
                  </Box>
                );
              }
              if (f.type === 'select') {
                return (
                  <TextField {...common} select value={values[f.name] ?? ''} onChange={(e) => set(f.name, e.target.value)}>
                    {!f.required && <MenuItem value=""><em>None</em></MenuItem>}
                    {(f.options || []).map((o) => {
                      const opt = typeof o === 'string' ? { value: o, label: o } : o;
                      return <MenuItem key={opt.value} value={opt.value}>{opt.label}</MenuItem>;
                    })}
                  </TextField>
                );
              }
              return (
                <TextField
                  {...common}
                  type={f.type === 'multiline' ? 'text' : (f.type || 'text')}
                  multiline={f.type === 'multiline'}
                  minRows={f.type === 'multiline' ? 3 : undefined}
                  value={values[f.name] ?? ''}
                  onChange={(e) => set(f.name, e.target.value)}
                  InputLabelProps={f.type === 'date' || f.type === 'time' ? { shrink: true } : undefined}
                />
              );
            })}
          </Box>
        </DialogContent>
        <DialogActions>
          <Button onClick={onClose}>Cancel</Button>
          <Button type="submit" variant="contained" disabled={busy}>{busy ? 'Saving…' : submitLabel}</Button>
        </DialogActions>
      </Box>
    </Dialog>
  );
}

/** Drop empty strings, so optional fields reach the API as absent rather than "". */
export function compact(values) {
  const out = {};
  Object.entries(values).forEach(([k, v]) => {
    if (v !== '' && v !== undefined) out[k] = v;
  });
  return out;
}
