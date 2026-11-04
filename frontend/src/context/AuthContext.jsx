import React, { createContext, useState, useContext, useEffect, useCallback } from 'react';
import { authAPI, errorMessage } from '../services/api';

const AuthContext = createContext(null);

export const AuthProvider = ({ children }) => {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);

  const saveUser = useCallback((userData) => {
    localStorage.setItem('user', JSON.stringify(userData));
    setUser(userData);
  }, []);

  useEffect(() => {
    const token = localStorage.getItem('access_token');
    if (!token) {
      setLoading(false);
      return;
    }
    // The server is the source of truth for role, link and status
    authAPI.getCurrentUser()
      .then((response) => saveUser(response.data))
      .catch(() => setUser(null))
      .finally(() => setLoading(false));
  }, [saveUser]);

  const login = async (credentials) => {
    try {
      const { data } = await authAPI.login(credentials);
      localStorage.setItem('access_token', data.access_token);
      saveUser(data.user);
      return { success: true, user: data.user };
    } catch (error) {
      return { success: false, error: errorMessage(error, 'Login failed') };
    }
  };

  const logout = () => {
    localStorage.removeItem('access_token');
    localStorage.removeItem('user');
    setUser(null);
  };

  const refreshUser = async () => {
    const { data } = await authAPI.getCurrentUser();
    saveUser(data);
    return data;
  };

  const role = user?.role;
  const value = {
    user, loading, login, logout, refreshUser,
    isAdmin: role === 'admin',
    isStaff: role === 'staff',
    isLawyer: role === 'lawyer',
  };

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
};

export const useAuth = () => {
  const context = useContext(AuthContext);
  if (!context) throw new Error('useAuth must be used within AuthProvider');
  return context;
};
