import React from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import { ThemeProvider, CssBaseline } from '@mui/material';
import theme from './theme';
import { AuthProvider, useAuth } from './context/AuthContext';
import { CenteredSpinner, EmptyState, ToastProvider } from './components/ui';
import Layout from './components/Layout';
import Login from './pages/Login';
import Join from './pages/Join';
import ChangePassword from './pages/ChangePassword';
import Dashboard from './pages/Dashboard';
import Calendar from './pages/Calendar';
import Tasks from './pages/Tasks';
import Matters from './pages/Matters';
import MatterDetail from './pages/MatterDetail';
import Documents from './pages/Documents';
import Lawyers from './pages/Lawyers';
import LawyerDetail from './pages/LawyerDetail';
import { ClientDetail, Clients, OpposingParties, OpposingPartyDetail } from './pages/People';
import Analytics from './pages/Analytics';
import Team from './pages/Team';
import AuditLog from './pages/AuditLog';
import Profile from './pages/Profile';

const ProtectedRoute = ({ children, adminOnly }) => {
  const { user, loading, isAdmin } = useAuth();
  if (loading) return <CenteredSpinner />;
  if (!user) return <Navigate to="/login" replace />;
  if (user.must_change_password) return <Navigate to="/change-password" replace />;
  if (adminOnly && !isAdmin) return <Navigate to="/" replace />;
  return children;
};

function AppRoutes() {
  const { user, loading } = useAuth();
  if (loading) return <CenteredSpinner />;

  return (
    <Routes>
      <Route path="/login" element={user ? <Navigate to="/" replace /> : <Login />} />
      <Route path="/join" element={user ? <Navigate to="/" replace /> : <Join />} />
      <Route path="/change-password" element={user ? <ChangePassword /> : <Navigate to="/login" replace />} />
      <Route path="/" element={<ProtectedRoute><Layout /></ProtectedRoute>}>
        <Route index element={<Dashboard />} />
        <Route path="calendar" element={<Calendar />} />
        <Route path="tasks" element={<Tasks />} />
        <Route path="cases" element={<Matters />} />
        <Route path="cases/:id" element={<MatterDetail />} />
        <Route path="documents" element={<Documents />} />
        <Route path="lawyers" element={<Lawyers />} />
        <Route path="lawyers/:id" element={<LawyerDetail />} />
        <Route path="clients" element={<Clients />} />
        <Route path="clients/:id" element={<ClientDetail />} />
        <Route path="opposing-parties" element={<OpposingParties />} />
        <Route path="opposing-parties/:id" element={<OpposingPartyDetail />} />
        <Route path="profile" element={<Profile />} />
        <Route path="analytics" element={<ProtectedRoute adminOnly><Analytics /></ProtectedRoute>} />
        <Route path="team" element={<ProtectedRoute adminOnly><Team /></ProtectedRoute>} />
        <Route path="audit" element={<ProtectedRoute adminOnly><AuditLog /></ProtectedRoute>} />
        <Route path="*" element={<EmptyState>This page doesn’t exist.</EmptyState>} />
      </Route>
    </Routes>
  );
}

function App() {
  return (
    <ThemeProvider theme={theme}>
      <CssBaseline />
      <ToastProvider>
        <AuthProvider>
          <Router>
            <AppRoutes />
          </Router>
        </AuthProvider>
      </ToastProvider>
    </ThemeProvider>
  );
}

export default App;
