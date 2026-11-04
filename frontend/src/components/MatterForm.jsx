/** Open or edit a matter, with a conflict check as parties are chosen. */
import React, { useEffect, useState } from 'react';
import {
  Alert, AlertTitle, Autocomplete, Box, Button, Chip, Dialog, DialogActions, DialogContent, DialogTitle, MenuItem,
  TextField, Typography,
} from '@mui/material';
import { AutoAwesomeOutlined } from '@mui/icons-material';
import { aiAPI, casesAPI, clientsAPI, errorMessage, lawyersAPI, opposingPartiesAPI, referenceAPI, workspaceAPI } from '../services/api';
import { useAuth } from '../context/AuthContext';
import { useFetch } from '../hooks/useFetch';
import { compact, FormDialog, fullName, isoDate, useToast } from './ui';

const MATTER_TYPES = ['Civil', 'Criminal', 'Family', 'Corporate', 'Constitutional'];
const SEX_OPTIONS = [{ value: 'F', label: 'Female' }, { value: 'M', label: 'Male' }, { value: 'O', label: 'Other' }];

export const PERSON_FIELDS = [
  { name: 'fname', label: 'First name', required: true, helper: 'For an organisation: its name' },
  { name: 'lname', label: 'Last name', required: true, helper: 'For an organisation: Pvt Ltd, LLP and so on' },
  { name: 'email', label: 'Email', type: 'email' },
  { name: 'phone', label: 'Phone' },
  { name: 'sex', label: 'Gender', type: 'select', options: SEX_OPTIONS },
  { name: 'address', label: 'Address', type: 'multiline' },
];

const PINCODE_FIELDS = [
  { name: 'pincode', label: 'Pincode' },
  { name: 'city', label: 'City', helper: 'Needed if the pincode is new' },
  { name: 'district', label: 'District', helper: 'Needed if the pincode is new' },
  { name: 'state', label: 'State', helper: 'Needed if the pincode is new' },
];

function personBody(values) {
  const { phone, ...rest } = values;
  return compact({ ...rest, phone_numbers: phone ? [phone] : [] });
}

const blank = {
  matter_title: '', case_number: '', matter_description: '', date_cause: '', date_filed: isoDate(), court_id: '', location_id: '',
  matter_types: [], statute_sections: [], clients: [], parties: [], lead: '',
};

export default function MatterForm({ open, onClose, onSaved, matter }) {
  const toast = useToast();
  const { isAdmin, user } = useAuth();
  const [form, setForm] = useState(blank);
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);
  const [touched, setTouched] = useState(false);
  const [conflicts, setConflicts] = useState([]);
  const [suggestion, setSuggestion] = useState(null);
  const [adding, setAdding] = useState(null);

  const clientsList = useFetch(() => (open ? clientsAPI.getAll({ size: 100 }) : Promise.resolve({ data: null })), [open]);
  const partiesList = useFetch(() => (open ? opposingPartiesAPI.getAll({ size: 100 }) : Promise.resolve({ data: null })), [open]);
  const courts = useFetch(() => (open ? referenceAPI.courts() : Promise.resolve({ data: null })), [open]);
  const locations = useFetch(() => (open ? referenceAPI.locations() : Promise.resolve({ data: null })), [open]);
  const lawyers = useFetch(() => (open && isAdmin && !matter ? lawyersAPI.getAll({ size: 100, active_only: true }) : Promise.resolve({ data: null })), [open]);

  useEffect(() => {
    if (!open) return;
    setError('');
    setTouched(false);
    setConflicts([]);
    setSuggestion(null);
    if (matter) {
      setForm({
        ...blank,
        matter_title: matter.matter_title,
        case_number: matter.case_number,
        matter_description: matter.matter_description || '',
        date_cause: matter.date_cause,
        date_filed: matter.date_filed,
        court_id: matter.court?.court_id || '',
        location_id: matter.location?.location_id || '',
        matter_types: matter.matter_types.map((m) => m.matter_type),
        statute_sections: matter.statute_sections.map((s) => s.statute_section),
        clients: matter.clients,
        parties: matter.opposing_parties,
      });
    } else {
      setForm(blank);
    }
  }, [open, matter]);

  const set = (name, value) => setForm((f) => ({ ...f, [name]: value }));

  // Check for conflicts whenever the parties change
  const clientIds = form.clients.map((c) => c.client_id).join(',');
  const partyIds = form.parties.map((p) => p.party_id).join(',');
  useEffect(() => {
    if (!open || (!clientIds && !partyIds)) {
      setConflicts([]);
      return undefined;
    }
    let current = true;
    workspaceAPI.checkConflicts({
      client_ids: form.clients.map((c) => c.client_id),
      party_ids: form.parties.map((p) => p.party_id),
      exclude_case_id: matter?.case_id,
    }).then(({ data }) => { if (current) setConflicts(data.conflicts); }).catch(() => {});
    return () => { current = false; };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [open, clientIds, partyIds]);

  const suggestType = async () => {
    try {
      const { data } = await aiAPI.classifyMatter(form.matter_description);
      setSuggestion(data);
    } catch (e) {
      toast(errorMessage(e, 'The suggestion is not available right now'), 'error');
    }
  };

  const submit = async (e) => {
    e.preventDefault();
    setTouched(true);
    if (!form.matter_title || !form.case_number || !form.date_cause || !form.date_filed) return;
    setBusy(true);
    setError('');
    const common = {
      matter_title: form.matter_title,
      case_number: form.case_number,
      matter_description: form.matter_description || null,
      date_cause: form.date_cause,
      date_filed: form.date_filed,
      court_id: form.court_id || null,
      location_id: form.location_id || null,
      matter_types: form.matter_types,
      statute_sections: form.statute_sections,
      client_ids: form.clients.map((c) => c.client_id),
      party_ids: form.parties.map((p) => p.party_id),
    };
    try {
      const { data } = matter
        ? await casesAPI.update(matter.case_id, common)
        : await casesAPI.create({
          ...common,
          assignments: form.lead ? [{ lawyer_id: form.lead, role: 'Lead Counsel', assigned_date: isoDate() }] : [],
        });
      toast(matter ? 'Matter updated' : 'Matter opened');
      onSaved(data);
      onClose();
    } catch (err) {
      setError(errorMessage(err));
    } finally {
      setBusy(false);
    }
  };

  const required = (value) => touched && !value;

  return (
    <>
      <Dialog open={open} onClose={onClose} maxWidth="md" fullWidth>
        <Box component="form" onSubmit={submit} noValidate>
          <DialogTitle>{matter ? 'Edit matter' : 'Open a new matter'}</DialogTitle>
          <DialogContent dividers>
            {error && <Alert severity="error" sx={{ mb: 2 }} role="alert">{error}</Alert>}
            <Box sx={{ display: 'grid', gridTemplateColumns: { xs: '1fr', sm: '2fr 1fr' }, gap: 2, mb: 2 }}>
              <TextField label="Matter title" required value={form.matter_title} onChange={(e) => set('matter_title', e.target.value)} error={required(form.matter_title)} helperText={required(form.matter_title) ? 'This is required' : ' '} />
              <TextField label="Case number" required value={form.case_number} onChange={(e) => set('case_number', e.target.value)} error={required(form.case_number)} helperText={required(form.case_number) ? 'This is required' : 'For example: OS 112/2026'} />
            </Box>
            <TextField
              label="Description of the matter"
              multiline
              minRows={3}
              fullWidth
              value={form.matter_description}
              onChange={(e) => set('matter_description', e.target.value)}
              sx={{ mb: 1 }}
            />
            <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, flexWrap: 'wrap', mb: 2 }}>
              <Button size="small" startIcon={<AutoAwesomeOutlined />} disabled={form.matter_description.trim().length < 20} onClick={suggestType}>
                Suggest matter type
              </Button>
              {suggestion && (
                <>
                  <Chip
                    label={`${suggestion.prediction} (${Math.round(suggestion.confidence * 100)}%)`}
                    onClick={() => set('matter_types', [...new Set([...form.matter_types, suggestion.prediction])])}
                  />
                  <Typography variant="caption" color="text.secondary">
                    {suggestion.is_confident ? 'Click to use it.' : 'Low confidence. Review before using.'} This is a suggestion, please check it.
                  </Typography>
                </>
              )}
            </Box>
            <Box sx={{ display: 'grid', gridTemplateColumns: { xs: '1fr', sm: '1fr 1fr' }, gap: 2 }}>
              <Autocomplete
                multiple
                freeSolo
                options={MATTER_TYPES}
                value={form.matter_types}
                onChange={(_, v) => set('matter_types', v)}
                renderInput={(p) => <TextField {...p} label="Matter types" helperText="Choose, or type your own and press Enter" />}
              />
              <Autocomplete
                multiple
                freeSolo
                options={[]}
                value={form.statute_sections}
                onChange={(_, v) => set('statute_sections', v)}
                renderInput={(p) => <TextField {...p} label="Statutes and sections" helperText="Type one, such as NI Act 138, and press Enter" />}
              />
              <TextField label="Date of cause of action" type="date" required InputLabelProps={{ shrink: true }} value={form.date_cause} onChange={(e) => set('date_cause', e.target.value)} error={required(form.date_cause)} helperText={required(form.date_cause) ? 'This is required' : ' '} />
              <TextField label="Date filed" type="date" required InputLabelProps={{ shrink: true }} value={form.date_filed} onChange={(e) => set('date_filed', e.target.value)} error={required(form.date_filed)} helperText={required(form.date_filed) ? 'This is required' : ' '} />
              <Box>
                <TextField select fullWidth label="Court" value={form.court_id} onChange={(e) => set('court_id', e.target.value)}>
                  <MenuItem value=""><em>None</em></MenuItem>
                  {(courts.data || []).map((c) => <MenuItem key={c.court_id} value={c.court_id}>{c.court_name}</MenuItem>)}
                </TextField>
                <Button size="small" onClick={() => setAdding('court')}>Add a court</Button>
              </Box>
              <Box>
                <TextField select fullWidth label="Place of dispute" value={form.location_id} onChange={(e) => set('location_id', e.target.value)}>
                  <MenuItem value=""><em>None</em></MenuItem>
                  {(locations.data || []).map((l) => <MenuItem key={l.location_id} value={l.location_id}>{[l.landmark, l.city].filter(Boolean).join(', ')}</MenuItem>)}
                </TextField>
                <Button size="small" onClick={() => setAdding('location')}>Add a place</Button>
              </Box>
              <Box>
                <Autocomplete
                  multiple
                  options={clientsList.data?.items || []}
                  value={form.clients}
                  getOptionLabel={fullName}
                  isOptionEqualToValue={(a, b) => a.client_id === b.client_id}
                  onChange={(_, v) => set('clients', v)}
                  renderInput={(p) => <TextField {...p} label="Clients" />}
                />
                <Button size="small" onClick={() => setAdding('client')}>Add a new client</Button>
              </Box>
              <Box>
                <Autocomplete
                  multiple
                  options={partiesList.data?.items || []}
                  value={form.parties}
                  getOptionLabel={fullName}
                  isOptionEqualToValue={(a, b) => a.party_id === b.party_id}
                  onChange={(_, v) => set('parties', v)}
                  renderInput={(p) => <TextField {...p} label="Opposing parties" />}
                />
                <Button size="small" onClick={() => setAdding('party')}>Add a new opposing party</Button>
              </Box>
              {isAdmin && !matter && (
                <TextField select label="Lead counsel" value={form.lead} onChange={(e) => set('lead', e.target.value)} helperText="Leave empty to assign later" sx={{ gridColumn: '1 / -1' }}>
                  <MenuItem value=""><em>Assign later</em></MenuItem>
                  {(lawyers.data?.items || []).map((l) => <MenuItem key={l.lawyer_id} value={l.lawyer_id}>{fullName(l)}</MenuItem>)}
                </TextField>
              )}
              {!isAdmin && !matter && user?.lawyer_id && (
                <Typography variant="body2" color="text.secondary" sx={{ gridColumn: '1 / -1' }}>You will be the lead counsel on this matter.</Typography>
              )}
            </Box>
            {conflicts.length > 0 && (
              <Alert severity="warning" sx={{ mt: 2 }} role="alert">
                <AlertTitle>Possible conflict of interest</AlertTitle>
                {conflicts.map((c, i) => (
                  <Typography key={i} variant="body2" sx={{ mb: 0.5 }}>
                    {c.message} {c.matters.map((m) => m.case_number).join(', ')}
                  </Typography>
                ))}
                <Typography variant="caption">Please check this before going ahead. You can still save the matter.</Typography>
              </Alert>
            )}
          </DialogContent>
          <DialogActions>
            <Button onClick={onClose}>Cancel</Button>
            <Button type="submit" variant="contained" disabled={busy}>{busy ? 'Saving…' : matter ? 'Save changes' : 'Open matter'}</Button>
          </DialogActions>
        </Box>
      </Dialog>

      <FormDialog
        open={adding === 'client'}
        title="Add a new client"
        fields={PERSON_FIELDS}
        submitLabel="Add client"
        onClose={() => setAdding(null)}
        onSubmit={async (v) => {
          const { data } = await clientsAPI.create(personBody(v));
          await clientsList.reload();
          set('clients', [...form.clients, data]);
        }}
      />
      <FormDialog
        open={adding === 'party'}
        title="Add a new opposing party"
        fields={PERSON_FIELDS}
        submitLabel="Add opposing party"
        onClose={() => setAdding(null)}
        onSubmit={async (v) => {
          const { data } = await opposingPartiesAPI.create(personBody(v));
          await partiesList.reload();
          set('parties', [...form.parties, data]);
        }}
      />
      <FormDialog
        open={adding === 'court'}
        title="Add a court"
        fields={[
          { name: 'court_name', label: 'Court name', required: true, full: true },
          { name: 'court_type', label: 'Type', required: true, helper: 'For example: High Court, Tribunal' },
          ...PINCODE_FIELDS,
        ]}
        submitLabel="Add court"
        onClose={() => setAdding(null)}
        onSubmit={async (v) => {
          const { data } = await referenceAPI.addCourt(compact(v));
          await courts.reload();
          set('court_id', data.court_id);
        }}
      />
      <FormDialog
        open={adding === 'location'}
        title="Add a place of dispute"
        fields={[
          { name: 'landmark', label: 'Place or landmark', required: true, full: true },
          { name: 'streetno', label: 'Street' },
          ...PINCODE_FIELDS,
        ]}
        submitLabel="Add place"
        onClose={() => setAdding(null)}
        onSubmit={async (v) => {
          const { data } = await referenceAPI.addLocation(compact(v));
          await locations.reload();
          set('location_id', data.location_id);
        }}
      />
    </>
  );
}

export { personBody };
