import { createTheme } from '@mui/material';

// Design tokens from the ui-ux-pro-max design system for this project
// ("Trust & Authority": navy + gold, EB Garamond headings, Lato body).
export const tokens = {
  primary: '#1E3A8A',
  primaryDark: '#172E6E',
  secondary: '#1E40AF',
  accent: '#B45309',
  background: '#F8FAFC',
  card: '#FFFFFF',
  foreground: '#0F172A',
  muted: '#E9EEF5',
  mutedForeground: '#475569',
  border: '#CBD5E1',
  destructive: '#DC2626',
  sidebar: '#0F1E46',
};

const headingFont = '"EB Garamond", Georgia, "Times New Roman", serif';
const bodyFont = 'Lato, system-ui, -apple-system, "Segoe UI", sans-serif';

const theme = createTheme({
  palette: {
    primary: { main: tokens.primary, dark: tokens.primaryDark, contrastText: '#fff' },
    secondary: { main: tokens.accent, contrastText: '#fff' },
    error: { main: tokens.destructive },
    background: { default: tokens.background, paper: tokens.card },
    text: { primary: tokens.foreground, secondary: tokens.mutedForeground },
    divider: tokens.border,
  },
  shape: { borderRadius: 8 },
  typography: {
    fontFamily: bodyFont,
    fontSize: 14,
    h1: { fontFamily: headingFont, fontWeight: 600 },
    h2: { fontFamily: headingFont, fontWeight: 600 },
    h3: { fontFamily: headingFont, fontWeight: 600 },
    h4: { fontFamily: headingFont, fontWeight: 600, fontSize: '2rem', letterSpacing: '-0.01em' },
    h5: { fontFamily: headingFont, fontWeight: 600 },
    h6: { fontFamily: headingFont, fontWeight: 600, fontSize: '1.2rem' },
    subtitle2: { fontWeight: 700 },
    overline: { fontWeight: 700, letterSpacing: '0.08em' },
    button: { textTransform: 'none', fontWeight: 700 },
  },
  components: {
    MuiCssBaseline: {
      styleOverrides: { body: { backgroundColor: tokens.background } },
    },
    MuiPaper: {
      defaultProps: { elevation: 0 },
      styleOverrides: {
        root: { backgroundImage: 'none' },
        outlined: { borderColor: tokens.border },
      },
    },
    MuiCard: {
      defaultProps: { variant: 'outlined' },
    },
    MuiButton: {
      defaultProps: { disableElevation: true },
      styleOverrides: { root: { minHeight: 40, transition: 'background-color 150ms, border-color 150ms' } },
    },
    MuiIconButton: {
      styleOverrides: { root: { minWidth: 40, minHeight: 40 } },
    },
    MuiTableCell: {
      styleOverrides: {
        head: { fontWeight: 700, color: tokens.mutedForeground, backgroundColor: tokens.muted },
      },
    },
    MuiTableRow: {
      styleOverrides: { root: { '&.MuiTableRow-hover:hover': { backgroundColor: '#F1F5F9' } } },
    },
    MuiChip: {
      styleOverrides: { root: { fontWeight: 700 } },
    },
    MuiTextField: {
      defaultProps: { size: 'small' },
    },
  },
});

export default theme;
