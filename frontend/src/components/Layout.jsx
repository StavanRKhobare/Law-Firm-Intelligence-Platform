import React, { useEffect, useRef, useState } from 'react';
import { Outlet, useLocation, useNavigate } from 'react-router-dom';
import {
  AppBar, Avatar, Badge, Box, ButtonBase, ClickAwayListener, Divider, Drawer, IconButton, InputAdornment, List,
  ListItem, ListItemButton, ListItemIcon, ListItemText, Menu, MenuItem, Paper, Popper, TextField, Toolbar, Typography,
} from '@mui/material';
import {
  AccountBalance as BrandIcon,
  CalendarMonthOutlined,
  ChecklistOutlined,
  DashboardOutlined,
  DescriptionOutlined,
  ExpandMore,
  GavelOutlined,
  GroupsOutlined,
  HistoryOutlined,
  InsightsOutlined,
  Logout,
  Menu as MenuIcon,
  BadgeOutlined,
  PeopleOutline,
  PersonOutline,
  PersonSearchOutlined,
  Search,
} from '@mui/icons-material';
import { useAuth } from '../context/AuthContext';
import { tokens } from '../theme';
import { workspaceAPI } from '../services/api';
import { useDebounced } from '../hooks/useFetch';

const drawerWidth = 248;

function navFor(role) {
  const admin = role === 'admin';
  return [
    {
      label: 'Today',
      items: [
        { text: role === 'lawyer' ? 'My day' : 'Dashboard', icon: <DashboardOutlined />, path: '/' },
        { text: 'Calendar', icon: <CalendarMonthOutlined />, path: '/calendar' },
        { text: role === 'lawyer' ? 'My tasks' : 'Tasks', icon: <ChecklistOutlined />, path: '/tasks' },
      ],
    },
    {
      label: 'Practice',
      items: [
        { text: 'Matters', icon: <GavelOutlined />, path: '/cases' },
        { text: 'Documents', icon: <DescriptionOutlined />, path: '/documents' },
      ],
    },
    {
      label: 'People',
      items: [
        { text: 'Lawyers', icon: <BadgeOutlined />, path: '/lawyers' },
        { text: 'Clients', icon: <PeopleOutline />, path: '/clients' },
        { text: 'Opposing parties', icon: <PersonSearchOutlined />, path: '/opposing-parties' },
      ],
    },
    ...(admin ? [{
      label: 'Firm',
      items: [
        { text: 'Analytics', icon: <InsightsOutlined />, path: '/analytics' },
        { text: 'Team & access', icon: <GroupsOutlined />, path: '/team' },
        { text: 'Audit log', icon: <HistoryOutlined />, path: '/audit' },
      ],
    }] : []),
  ];
}

const SEARCH_GROUPS = [
  ['matters', 'Matters', (r) => `/cases/${r.id}`],
  ['clients', 'Clients', (r) => `/clients/${r.id}`],
  ['parties', 'Opposing parties', (r) => `/opposing-parties/${r.id}`],
  ['lawyers', 'Lawyers', (r) => `/lawyers/${r.id}`],
  ['documents', 'Documents', (r) => `/cases/${r.case_id}?tab=documents`],
];

function GlobalSearch() {
  const navigate = useNavigate();
  const anchor = useRef(null);
  const [text, setText] = useState('');
  const [results, setResults] = useState(null);
  const [open, setOpen] = useState(false);
  const query = useDebounced(text.trim(), 250);

  useEffect(() => {
    if (query.length < 2) {
      setResults(null);
      return undefined;
    }
    let current = true;
    workspaceAPI.search(query)
      .then(({ data }) => { if (current) { setResults(data); setOpen(true); } })
      .catch(() => { if (current) setResults(null); });
    return () => { current = false; };
  }, [query]);

  const groups = results ? SEARCH_GROUPS.filter(([key]) => results[key]?.length) : [];

  const go = (path) => {
    setOpen(false);
    setText('');
    navigate(path);
  };

  return (
    <ClickAwayListener onClickAway={() => setOpen(false)}>
      <Box ref={anchor} sx={{ flex: 1, maxWidth: 520, mx: { xs: 1, sm: 2 } }}>
        <TextField
          fullWidth
          placeholder="Search matters, people, documents"
          value={text}
          onChange={(e) => setText(e.target.value)}
          onFocus={() => results && setOpen(true)}
          onKeyDown={(e) => e.key === 'Escape' && setOpen(false)}
          inputProps={{ 'aria-label': 'Search the firm' }}
          InputProps={{ startAdornment: <InputAdornment position="start"><Search fontSize="small" /></InputAdornment> }}
        />
        <Popper open={open && Boolean(results)} anchorEl={anchor.current} placement="bottom-start" sx={{ zIndex: 1300, width: anchor.current?.offsetWidth }}>
          <Paper variant="outlined" sx={{ mt: 0.5, maxHeight: '70vh', overflowY: 'auto', boxShadow: 3 }}>
            {groups.length === 0 && <Typography sx={{ p: 2 }} color="text.secondary">No results for “{query}”.</Typography>}
            {groups.map(([key, label, pathOf]) => (
              <List key={key} dense disablePadding subheader={<Typography variant="overline" color="text.secondary" component="div" sx={{ px: 2, pt: 1 }}>{label}</Typography>}>
                {results[key].map((r) => (
                  <ListItemButton key={`${key}-${r.id}`} disabled={!r.can_open} onClick={() => go(pathOf(r))}>
                    <ListItemText primary={r.title} secondary={r.can_open ? r.subtitle : `${r.subtitle} · not on your matters`} />
                  </ListItemButton>
                ))}
              </List>
            ))}
          </Paper>
        </Popper>
      </Box>
    </ClickAwayListener>
  );
}

export default function Layout() {
  const [mobileOpen, setMobileOpen] = useState(false);
  const [anchorEl, setAnchorEl] = useState(null);
  const [pending, setPending] = useState(0);
  const navigate = useNavigate();
  const location = useLocation();
  const { user, logout, isAdmin } = useAuth();
  const sections = navFor(user?.role);

  useEffect(() => {
    if (!isAdmin) return;
    workspaceAPI.summary().then(({ data }) => setPending(data.pending_join_requests || 0)).catch(() => {});
    // Refreshes when moving between pages, so an approval clears the badge
  }, [isAdmin, location.pathname]);

  const isCurrent = (path) => (path === '/' ? location.pathname === '/' : location.pathname.startsWith(path));

  const go = (path) => {
    navigate(path);
    setMobileOpen(false);
  };

  const handleLogout = () => {
    setAnchorEl(null);
    logout();
    navigate('/login');
  };

  const drawer = (
    <Box sx={{ height: '100%', bgcolor: tokens.sidebar, color: '#E2E8F0', display: 'flex', flexDirection: 'column' }}>
      <Toolbar sx={{ gap: 1.5, px: 2.5 }}>
        <BrandIcon sx={{ color: '#FBBF24' }} aria-hidden />
        <Box>
          <Typography sx={{ fontFamily: '"EB Garamond", serif', fontWeight: 600, fontSize: '1.35rem', lineHeight: 1.1, color: '#fff' }}>Chambers</Typography>
          <Typography variant="caption" sx={{ color: '#94A3B8' }}>Case management</Typography>
        </Box>
      </Toolbar>
      <Divider sx={{ borderColor: 'rgba(255,255,255,0.08)' }} />
      <Box component="nav" aria-label="Main" sx={{ flex: 1, overflowY: 'auto', py: 1 }}>
        {sections.map((section) => (
          <List
            key={section.label}
            dense
            subheader={<Typography variant="overline" component="div" sx={{ px: 2.5, pt: 1.5, color: '#94A3B8', fontSize: '0.68rem' }}>{section.label}</Typography>}
          >
            {section.items.map((item) => {
              const selected = isCurrent(item.path);
              return (
                <ListItem key={item.text} disablePadding sx={{ px: 1.25 }}>
                  <ListItemButton
                    selected={selected}
                    aria-current={selected ? 'page' : undefined}
                    onClick={() => go(item.path)}
                    sx={{
                      borderRadius: 1.5,
                      minHeight: 44,
                      color: '#CBD5E1',
                      transition: 'background-color 150ms',
                      '&:hover': { bgcolor: 'rgba(255,255,255,0.06)' },
                      '&.Mui-selected, &.Mui-selected:hover': { bgcolor: 'rgba(251,191,36,0.14)', color: '#fff', boxShadow: 'inset 3px 0 0 #FBBF24' },
                    }}
                  >
                    <ListItemIcon sx={{ minWidth: 38, color: selected ? '#FBBF24' : '#94A3B8' }}>
                      {item.path === '/team' && pending > 0 ? <Badge badgeContent={pending} color="secondary">{item.icon}</Badge> : item.icon}
                    </ListItemIcon>
                    <ListItemText primary={item.text} primaryTypographyProps={{ fontWeight: selected ? 700 : 400, fontSize: '0.92rem' }} />
                  </ListItemButton>
                </ListItem>
              );
            })}
          </List>
        ))}
      </Box>
    </Box>
  );

  return (
    <Box sx={{ display: 'flex' }}>
      <a className="skip-link" href="#main-content">Skip to content</a>
      <AppBar
        position="fixed"
        color="inherit"
        elevation={0}
        sx={{
          width: { md: `calc(100% - ${drawerWidth}px)` },
          ml: { md: `${drawerWidth}px` },
          bgcolor: 'rgba(255,255,255,0.92)',
          backdropFilter: 'blur(6px)',
          borderBottom: `1px solid ${tokens.border}`,
        }}
      >
        <Toolbar>
          <IconButton edge="start" aria-label="Open navigation" onClick={() => setMobileOpen(true)} sx={{ mr: 1, display: { md: 'none' } }}>
            <MenuIcon />
          </IconButton>
          <GlobalSearch />
          <Box sx={{ flexGrow: 1 }} />
          <ButtonBase
            onClick={(e) => setAnchorEl(e.currentTarget)}
            aria-label="Account menu"
            aria-haspopup="menu"
            sx={{ borderRadius: 2, px: 1, py: 0.5, gap: 1.25, '&:hover': { bgcolor: tokens.muted } }}
          >
            <Avatar sx={{ width: 34, height: 34, bgcolor: tokens.primary, fontSize: '0.95rem' }}>
              {(user?.full_name || user?.username)?.charAt(0).toUpperCase()}
            </Avatar>
            <Box sx={{ textAlign: 'left', display: { xs: 'none', lg: 'block' } }}>
              <Typography variant="body2" sx={{ fontWeight: 700, lineHeight: 1.2 }}>{user?.full_name || user?.username}</Typography>
              <Typography variant="caption" color="text.secondary" sx={{ textTransform: 'capitalize' }}>{user?.role}</Typography>
            </Box>
            <ExpandMore fontSize="small" sx={{ color: 'text.secondary' }} />
          </ButtonBase>
        </Toolbar>
      </AppBar>

      <Menu anchorEl={anchorEl} open={Boolean(anchorEl)} onClose={() => setAnchorEl(null)}>
        <MenuItem onClick={() => { setAnchorEl(null); navigate('/profile'); }}>
          <ListItemIcon><PersonOutline fontSize="small" /></ListItemIcon>
          <ListItemText>My profile</ListItemText>
        </MenuItem>
        <Divider />
        <MenuItem onClick={handleLogout}>
          <ListItemIcon><Logout fontSize="small" /></ListItemIcon>
          <ListItemText>Log out</ListItemText>
        </MenuItem>
      </Menu>

      <Box sx={{ width: { md: drawerWidth }, flexShrink: { md: 0 } }}>
        <Drawer
          variant="temporary"
          open={mobileOpen}
          onClose={() => setMobileOpen(false)}
          ModalProps={{ keepMounted: true }}
          sx={{ display: { xs: 'block', md: 'none' }, '& .MuiDrawer-paper': { width: drawerWidth, border: 0 } }}
        >
          {drawer}
        </Drawer>
        <Drawer variant="permanent" open sx={{ display: { xs: 'none', md: 'block' }, '& .MuiDrawer-paper': { width: drawerWidth, border: 0 } }}>
          {drawer}
        </Drawer>
      </Box>

      <Box
        component="main"
        id="main-content"
        tabIndex={-1}
        sx={{ flexGrow: 1, minWidth: 0, p: { xs: 2, sm: 3 }, width: { md: `calc(100% - ${drawerWidth}px)` }, minHeight: '100vh', bgcolor: 'background.default', outline: 'none' }}
      >
        <Toolbar />
        <Box sx={{ maxWidth: 1400, mx: 'auto' }}>
          <Outlet />
        </Box>
      </Box>
    </Box>
  );
}
