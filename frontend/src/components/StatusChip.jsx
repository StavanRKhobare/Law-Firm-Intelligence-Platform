import React from 'react';
import { Chip } from '@mui/material';
import { statusColors } from '../theme';

// Matter status badge: colour plus the status text, so it never relies on colour alone.
export default function StatusChip({ status }) {
  const c = statusColors[status] || statusColors.Pending;
  return <Chip size="small" label={status} sx={{ bgcolor: c.bg, color: c.fg }} />;
}
