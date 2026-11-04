import React, { useState } from 'react';
import { Outlet, useNavigate, useLocation } from 'react-router-dom';
import {
  Box,
  Drawer,
  AppBar,
  Toolbar,
  List,
  Typography,
  Divider,
  IconButton,
  ListItem,
  ListItemButton,
  ListItemIcon,
  ListItemText,
  Avatar,
  Menu,
  MenuItem,
  ButtonBase,
} from '@mui/material';
import {
  Menu as MenuIcon,
  DashboardOutlined as DashboardIcon,
  GavelOutlined as GavelIcon,
  BadgeOutlined as BadgeIcon,
  PersonSearchOutlined as PersonSearchIcon,
  PeopleOutline as PeopleIcon,
  DescriptionOutlined as DescriptionIcon,
  InsightsOutlined as AnalyticsIcon,
  AccountBalance as BrandIcon,
  AccountCircle,
  Logout,
  ExpandMore,
} from '@mui/icons-material';
import { useAuth } from '../context/AuthContext';
import { tokens } from '../theme';

const drawerWidth = 248;

const navSections = [
  {
    label: 'Overview',
    items: [
      { text: 'Dashboard', icon: <DashboardIcon />, path: '/' },
      { text: 'Analytics', icon: <AnalyticsIcon />, path: '/analytics' },
    ],
  },
  {
    label: 'Practice',
    items: [
      { text: 'Matters', icon: <GavelIcon />, path: '/cases' },
      { text: 'Evidence', icon: <DescriptionIcon />, path: '/evidence' },
    ],
  },
  {
    label: 'People',
    items: [
      { text: 'Lawyers', icon: <BadgeIcon />, path: '/lawyers' },
      { text: 'Clients', icon: <PeopleIcon />, path: '/clients' },
      { text: 'Opposing parties', icon: <PersonSearchIcon />, path: '/opposing-parties' },
    ],
  },
];

const allItems = navSections.flatMap((s) => s.items);

export default function Layout() {
  const [mobileOpen, setMobileOpen] = useState(false);
  const [anchorEl, setAnchorEl] = useState(null);
  const navigate = useNavigate();
  const location = useLocation();
  const { user, logout } = useAuth();

  const current = allItems.find((i) => i.path === location.pathname);

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
          <Typography sx={{ fontFamily: '"EB Garamond", serif', fontWeight: 600, fontSize: '1.35rem', lineHeight: 1.1, color: '#fff' }}>
            Chambers
          </Typography>
          <Typography variant="caption" sx={{ color: '#94A3B8' }}>
            Case management
          </Typography>
        </Box>
      </Toolbar>
      <Divider sx={{ borderColor: 'rgba(255,255,255,0.08)' }} />
      <Box component="nav" aria-label="Main" sx={{ flex: 1, overflowY: 'auto', py: 1 }}>
        {navSections.map((section) => (
          <List
            key={section.label}
            dense
            subheader={
              <Typography variant="overline" component="div" sx={{ px: 2.5, pt: 1.5, color: '#94A3B8', fontSize: '0.68rem' }}>
                {section.label}
              </Typography>
            }
          >
            {section.items.map((item) => {
              const selected = location.pathname === item.path;
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
                      '&.Mui-selected, &.Mui-selected:hover': {
                        bgcolor: 'rgba(251,191,36,0.14)',
                        color: '#fff',
                        boxShadow: 'inset 3px 0 0 #FBBF24',
                      },
                    }}
                  >
                    <ListItemIcon sx={{ minWidth: 38, color: selected ? '#FBBF24' : '#94A3B8' }}>{item.icon}</ListItemIcon>
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
          <IconButton
            edge="start"
            aria-label="Open navigation"
            onClick={() => setMobileOpen(true)}
            sx={{ mr: 1, display: { md: 'none' } }}
          >
            <MenuIcon />
          </IconButton>
          <Typography variant="subtitle1" component="div" sx={{ flexGrow: 1, fontWeight: 700 }} noWrap>
            {current?.text || 'Chambers'}
          </Typography>
          <ButtonBase
            onClick={(e) => setAnchorEl(e.currentTarget)}
            aria-label="Account menu"
            aria-haspopup="menu"
            sx={{ borderRadius: 2, px: 1, py: 0.5, gap: 1.25, '&:hover': { bgcolor: tokens.muted } }}
          >
            <Avatar sx={{ width: 34, height: 34, bgcolor: tokens.primary, fontSize: '0.95rem' }}>
              {user?.username?.charAt(0).toUpperCase()}
            </Avatar>
            <Box sx={{ textAlign: 'left', display: { xs: 'none', sm: 'block' } }}>
              <Typography variant="body2" sx={{ fontWeight: 700, lineHeight: 1.2 }}>
                {user?.full_name || user?.username}
              </Typography>
              <Typography variant="caption" color="text.secondary" sx={{ textTransform: 'capitalize' }}>
                {user?.role}
              </Typography>
            </Box>
            <ExpandMore fontSize="small" sx={{ color: 'text.secondary' }} />
          </ButtonBase>
        </Toolbar>
      </AppBar>

      <Menu anchorEl={anchorEl} open={Boolean(anchorEl)} onClose={() => setAnchorEl(null)}>
        <MenuItem disabled>
          <ListItemIcon>
            <AccountCircle fontSize="small" />
          </ListItemIcon>
          <ListItemText sx={{ textTransform: 'capitalize' }}>{user?.role}</ListItemText>
        </MenuItem>
        <Divider />
        <MenuItem onClick={handleLogout}>
          <ListItemIcon>
            <Logout fontSize="small" />
          </ListItemIcon>
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
        <Drawer
          variant="permanent"
          open
          sx={{ display: { xs: 'none', md: 'block' }, '& .MuiDrawer-paper': { width: drawerWidth, border: 0 } }}
        >
          {drawer}
        </Drawer>
      </Box>

      <Box
        component="main"
        id="main-content"
        tabIndex={-1}
        sx={{
          flexGrow: 1,
          minWidth: 0,
          p: { xs: 2, sm: 3 },
          width: { md: `calc(100% - ${drawerWidth}px)` },
          minHeight: '100vh',
          bgcolor: 'background.default',
          outline: 'none',
        }}
      >
        <Toolbar />
        <Box sx={{ maxWidth: 1400, mx: 'auto' }}>
          <Outlet />
        </Box>
      </Box>
    </Box>
  );
}
