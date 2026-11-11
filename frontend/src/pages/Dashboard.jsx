/** Everyone starts here. Admins and staff see the firm; a lawyer sees their own day. */
import React from 'react';
import { Link as RouterLink, useNavigate } from 'react-router-dom';
import { Alert, Box, Button, Grid, List, ListItem, ListItemText, Stack, Typography } from '@mui/material';
import {
  ArrowForward, EventBusyOutlined, EventOutlined, GavelOutlined, GroupAddOutlined, TodayOutlined, WarningAmberOutlined,
  PendingActionsOutlined,
} from '@mui/icons-material';
import { workspaceAPI } from '../services/api';
import { useAuth } from '../context/AuthContext';
import { useFetch } from '../hooks/useFetch';
import {
  DueLabel, EmptyState, formatDateTime, formatDay, formatTime, LoadError, Loading, PageHeader, Panel, StatTile, StatusChip, TextLink,
} from '../components/ui';
import { HearingsTable, TasksTable } from '../components/work';

function ViewAll({ to, children = 'View all' }) {
  return <Button component={RouterLink} to={to} size="small" endIcon={<ArrowForward />}>{children}</Button>;
}

function UpcomingHearings({ rows }) {
  if (!rows.length) return <EmptyState>Nothing listed in the next 7 days.</EmptyState>;
  return (
    <List dense disablePadding>
      {rows.map((h) => (
        <ListItem key={h.hearing_id} disableGutters divider sx={{ alignItems: 'flex-start', gap: 2 }}>
          <Box sx={{ flex: '0 0 92px' }}>
            <Typography variant="body2" sx={{ fontWeight: 700 }}>{formatDay(h.hearing_date)}</Typography>
            <Typography variant="caption" color="text.secondary">{formatTime(h.hearing_time)}</Typography>
          </Box>
          <ListItemText
            primary={<TextLink to={`/cases/${h.case_id}?tab=hearings`}>{h.case_number}</TextLink>}
            secondary={[h.purpose, h.court_name, h.courtroom].filter(Boolean).join(' · ') || h.matter_title}
          />
          {h.lead_counsel && <Typography variant="caption" color="text.secondary" sx={{ flexShrink: 0, pt: 0.5 }}>{h.lead_counsel}</Typography>}
        </ListItem>
      ))}
    </List>
  );
}

export default function Dashboard() {
  const { user, isAdmin, isLawyer } = useAuth();
  const navigate = useNavigate();
  const { data, loading, error, reload } = useFetch(() => workspaceAPI.summary());

  const today = new Date().toLocaleDateString('en-IN', { weekday: 'long', day: 'numeric', month: 'long', year: 'numeric' });
  const firstName = (user?.full_name || user?.username || '').split(' ')[0];
  const header = (
    <PageHeader
      eyebrow={today}
      title={isLawyer ? `Good to see you, ${firstName}` : 'Firm today'}
      subtitle={isLawyer ? 'Your hearings, deadlines and matters' : 'What needs attention across the firm'}
      actions={<Button variant="contained" onClick={() => navigate('/cases')}>Go to matters</Button>}
    />
  );

  if (error) return <Box>{header}<LoadError message={error} onRetry={reload} /></Box>;
  if (loading && !data) return <Box>{header}<Loading height={400} /></Box>;

  const c = data.counts;
  const notLinked = isLawyer && !data.linked_to_lawyer;

  return (
    <Box>
      {header}
      {notLinked && (
        <Alert severity="warning" sx={{ mb: 2 }}>
          Your account isn’t linked to a lawyer record yet, so no matters appear here. Ask an admin to link it under Team and access.
        </Alert>
      )}
      {isAdmin && (data.pending_join_requests > 0 || data.unassigned_matters > 0) && (
        <Stack spacing={1} sx={{ mb: 2 }}>
          {data.pending_join_requests > 0 && (
            <Alert severity="info" icon={<GroupAddOutlined />} action={<Button color="inherit" size="small" onClick={() => navigate('/team')}>Review</Button>}>
              {data.pending_join_requests} {data.pending_join_requests === 1 ? 'person is' : 'people are'} waiting to join the firm.
            </Alert>
          )}
          {data.unassigned_matters > 0 && (
            <Alert severity="warning" action={<Button color="inherit" size="small" onClick={() => navigate('/cases?unassigned=true')}>Assign</Button>}>
              {data.unassigned_matters} open {data.unassigned_matters === 1 ? 'matter has' : 'matters have'} no lead counsel.
            </Alert>
          )}
        </Stack>
      )}

      <Grid container spacing={2}>
        <Grid item xs={6} md={4} lg={2}><StatTile label={isLawyer ? 'My open matters' : 'Open matters'} value={c.open_matters} icon={<GavelOutlined />} to="/cases" /></Grid>
        <Grid item xs={6} md={4} lg={2}><StatTile label="Hearings today" value={c.hearings_today} icon={<TodayOutlined />} to="/calendar" /></Grid>
        <Grid item xs={6} md={4} lg={2}><StatTile label="Next 7 days" value={c.hearings_this_week} icon={<EventOutlined />} to="/calendar" /></Grid>
        <Grid item xs={6} md={4} lg={2}><StatTile label="Overdue work" value={c.overdue_tasks} hint={`${c.overdue_deadlines} legal ${c.overdue_deadlines === 1 ? 'deadline' : 'deadlines'}`} icon={<WarningAmberOutlined />} to="/tasks" tone={c.overdue_tasks ? 'alert' : undefined} /></Grid>
        <Grid item xs={6} md={4} lg={2}><StatTile label="Results to record" value={c.awaiting_result} icon={<PendingActionsOutlined />} tone={c.awaiting_result ? 'warn' : undefined} /></Grid>
        <Grid item xs={6} md={4} lg={2}><StatTile label="No next date" value={c.without_next_date} icon={<EventBusyOutlined />} tone={c.without_next_date ? 'warn' : undefined} /></Grid>

        {data.awaiting_result.length > 0 && (
          <Grid item xs={12}>
            <Panel noPadding title="Hearings that have passed, with no result recorded">
              <HearingsTable flat hearings={data.awaiting_result} onChanged={reload} />
            </Panel>
          </Grid>
        )}

        <Grid item xs={12} lg={7}>
          <Panel title="Next 7 days" action={<ViewAll to="/calendar">Calendar</ViewAll>}>
            <UpcomingHearings rows={data.hearings} />
          </Panel>
        </Grid>
        <Grid item xs={12} lg={5}>
          <Panel title="Deadlines, next 30 days" action={<ViewAll to="/tasks" />}>
            {data.deadlines.length === 0 ? <EmptyState>No legal deadlines coming up.</EmptyState> : (
              <List dense disablePadding>
                {data.deadlines.map((t) => (
                  <ListItem key={t.task_id} disableGutters divider sx={{ alignItems: 'flex-start', gap: 2 }}>
                    <ListItemText
                      primary={t.title}
                      secondary={[t.kind, t.case_number, t.assignee_name].filter(Boolean).join(' · ')}
                    />
                    <Box sx={{ flexShrink: 0, textAlign: 'right' }}><DueLabel date={t.due_date} /></Box>
                  </ListItem>
                ))}
              </List>
            )}
          </Panel>
        </Grid>

        <Grid item xs={12}>
          <Panel noPadding title="My tasks" action={<ViewAll to="/tasks" />}>
            <TasksTable flat tasks={data.my_tasks} onChanged={reload} empty="Nothing is assigned to you." />
          </Panel>
        </Grid>

        <Grid item xs={12} lg={6}>
          <Panel title="Open matters with no next date">
            {data.without_next_date.length === 0 ? <EmptyState>Every open matter has a next date.</EmptyState> : (
              <>
                <List dense disablePadding>
                  {data.without_next_date.map((m) => (
                    <ListItem key={m.case_id} disableGutters divider secondaryAction={<StatusChip status={m.status} />}>
                      <ListItemText primary={<TextLink to={`/cases/${m.case_id}?tab=hearings`}>{m.case_number}</TextLink>} secondary={m.matter_title} />
                    </ListItem>
                  ))}
                </List>
                {c.without_next_date > data.without_next_date.length && (
                  <Typography variant="caption" color="text.secondary">And {c.without_next_date - data.without_next_date.length} more.</Typography>
                )}
              </>
            )}
          </Panel>
        </Grid>
        <Grid item xs={12} lg={6}>
          <Panel title="Latest remarks">
            {data.recent_notes.length === 0 ? <EmptyState>No remarks yet.</EmptyState> : (
              <List dense disablePadding>
                {data.recent_notes.map((n) => (
                  <ListItem key={n.note_id} disableGutters divider>
                    <ListItemText
                      primary={n.body}
                      primaryTypographyProps={{ sx: { display: '-webkit-box', WebkitLineClamp: 2, WebkitBoxOrient: 'vertical', overflow: 'hidden' } }}
                      secondary={<><TextLink to={`/cases/${n.case_id}?tab=history`}>{n.case_number}</TextLink> · {n.author_name} · {formatDateTime(n.created_at)}</>}
                    />
                  </ListItem>
                ))}
              </List>
            )}
          </Panel>
        </Grid>
      </Grid>
    </Box>
  );
}
