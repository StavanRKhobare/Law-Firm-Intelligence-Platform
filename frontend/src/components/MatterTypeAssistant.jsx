import React, { useState } from 'react';
import { Box, Button, Card, CardContent, LinearProgress, TextField, Typography, Alert, Stack } from '@mui/material';
import { AutoAwesomeOutlined } from '@mui/icons-material';
import { aiAPI } from '../services/api';

const MIN_LENGTH = 20;

const EXAMPLES = [
  'Wife seeks divorce under the Hindu Marriage Act and maintenance for the minor child.',
  'Operational creditor filed an insolvency petition against the corporate debtor before the NCLT.',
  'Accused arrested under the FIR for cheating; bail application pending before the Sessions Court.',
];

/**
 * Suggests a matter type (Criminal, Civil, Family, Corporate, Constitutional)
 * from a short description, using POST /ai/classify/matter-type.
 */
export default function MatterTypeAssistant() {
  const [text, setText] = useState('');
  const [result, setResult] = useState(null);
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  const tooShort = text.trim().length < MIN_LENGTH;

  const classify = async (e) => {
    e.preventDefault();
    if (tooShort) return;
    setLoading(true);
    setError('');
    try {
      const { data } = await aiAPI.classifyMatter(text.trim());
      setResult(data);
    } catch (err) {
      setResult(null);
      setError(err.response?.data?.detail || 'Could not reach the classifier. Is the backend running?');
    } finally {
      setLoading(false);
    }
  };

  return (
    <Card sx={{ height: '100%' }}>
      <CardContent component="form" onSubmit={classify} sx={{ display: 'flex', flexDirection: 'column', gap: 1.5 }}>
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
          <AutoAwesomeOutlined sx={{ color: 'secondary.main' }} aria-hidden />
          <Typography variant="h6" component="h2">Matter type assistant</Typography>
        </Box>
        <Typography variant="body2" color="text.secondary">
          Describe the facts of a new matter and the model suggests its type.
        </Typography>
        <TextField
          label="Matter description"
          multiline
          minRows={3}
          value={text}
          onChange={(e) => setText(e.target.value)}
          helperText={tooShort && text ? `At least ${MIN_LENGTH} characters` : ' '}
          error={Boolean(tooShort && text)}
          fullWidth
        />
        <Stack direction="row" spacing={1} sx={{ flexWrap: 'wrap', gap: 1 }}>
          {EXAMPLES.map((ex, i) => (
            <Button key={i} size="small" variant="text" onClick={() => setText(ex)} sx={{ minHeight: 32 }}>
              Example {i + 1}
            </Button>
          ))}
          <Box sx={{ flex: 1 }} />
          <Button type="submit" variant="contained" disabled={tooShort || loading}>
            {loading ? 'Classifying…' : 'Suggest type'}
          </Button>
        </Stack>

        {error && <Alert severity="error">{error}</Alert>}

        {result && (
          <Box aria-live="polite" sx={{ borderTop: 1, borderColor: 'divider', pt: 1.5 }}>
            <Typography variant="overline" color="text.secondary">Suggested type</Typography>
            <Typography variant="h5" component="p" sx={{ mb: 1 }}>
              {result.prediction}
              {!result.is_confident && (
                <Typography component="span" variant="body2" color="text.secondary" sx={{ ml: 1 }}>
                  (low confidence, review manually)
                </Typography>
              )}
            </Typography>
            {result.top_3_predictions.map((p) => (
              <Box key={p.matter_type} sx={{ display: 'grid', gridTemplateColumns: '120px 1fr 48px', alignItems: 'center', gap: 1, mb: 0.75 }}>
                <Typography variant="body2">{p.matter_type}</Typography>
                <LinearProgress
                  variant="determinate"
                  value={p.probability * 100}
                  aria-label={`${p.matter_type} probability`}
                  sx={{ height: 8, borderRadius: 4, bgcolor: 'action.hover' }}
                />
                <Typography variant="body2" sx={{ textAlign: 'right', fontVariantNumeric: 'tabular-nums' }}>
                  {Math.round(p.probability * 100)}%
                </Typography>
              </Box>
            ))}
          </Box>
        )}
      </CardContent>
    </Card>
  );
}
