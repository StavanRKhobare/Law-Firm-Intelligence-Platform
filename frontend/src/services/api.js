import axios from 'axios';

const API_BASE_URL = 'http://localhost:8000/api/v1';

// Create axios instance
const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Add token to requests
api.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('access_token');
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => {
    return Promise.reject(error);
  }
);

// Handle response errors
api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      localStorage.removeItem('access_token');
      localStorage.removeItem('user');
      window.location.href = '/login';
    }
    return Promise.reject(error);
  }
);

// Auth APIs
export const authAPI = {
  login: (credentials) => api.post('/auth/login-json', credentials),
  register: (userData) => api.post('/auth/register', userData),
  getCurrentUser: () => api.get('/auth/me'),
  changePassword: (data) => api.post('/auth/change-password', data),
};

// Cases APIs
export const casesAPI = {
  getAll: (params) => api.get('/cases', { params }),
  getById: (id) => api.get(`/cases/${id}`),
  create: (data) => api.post('/cases', data),
  update: (id, data) => api.put(`/cases/${id}`, data),
  delete: (id) => api.delete(`/cases/${id}`),
  updateStatus: (id, status) => api.patch(`/cases/${id}/status`, null, { params: { new_status: status } }),
};

// Lawyers APIs
export const lawyersAPI = {
  getAll: (params) => api.get('/lawyers', { params }),
  getById: (id) => api.get(`/lawyers/${id}`),
  create: (data) => api.post('/lawyers', data),
  update: (id, data) => api.put(`/lawyers/${id}`, data),
  delete: (id) => api.delete(`/lawyers/${id}`),
  getWorkload: (id) => api.get(`/lawyers/${id}/workload`),
};

// Opposing party APIs
export const opposingPartiesAPI = {
  getAll: (params) => api.get('/opposing-parties', { params }),
  getById: (id) => api.get(`/opposing-parties/${id}`),
  create: (data) => api.post('/opposing-parties', data),
  update: (id, data) => api.put(`/opposing-parties/${id}`, data),
  delete: (id) => api.delete(`/opposing-parties/${id}`),
};

// Client APIs
export const clientsAPI = {
  getAll: (params) => api.get('/clients', { params }),
  getById: (id) => api.get(`/clients/${id}`),
  create: (data) => api.post('/clients', data),
  update: (id, data) => api.put(`/clients/${id}`, data),
  delete: (id) => api.delete(`/clients/${id}`),
};

// Evidence APIs
export const evidenceAPI = {
  getAll: (params) => api.get('/evidence', { params }),
  getById: (id) => api.get(`/evidence/${id}`),
  create: (formData) => api.post('/evidence', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
  }),
  update: (id, data) => api.put(`/evidence/${id}`, data),
  delete: (id) => api.delete(`/evidence/${id}`),
  downloadFile: (id) => api.get(`/evidence/${id}/download-file`, { responseType: 'blob' }),
};

// Analytics APIs
export const analyticsAPI = {
  getDashboard: () => api.get('/analytics/dashboard'),
  getCasesByStatus: () => api.get('/analytics/cases/by-status'),
  getCasesByMonth: (params) => api.get('/analytics/cases/by-month', { params }),
  getMatterTypes: (params) => api.get('/analytics/cases/by-matter-type', { params }),
  getCaseload: (params) => api.get('/analytics/locations/caseload', { params }),
  getLawyerPerformance: (params) => api.get('/analytics/lawyers/performance', { params }),
  getPracticeGroupStats: () => api.get('/analytics/practice-groups/statistics'),
};

// AI APIs
export const aiAPI = {
  classifyMatter: (description) => api.post('/ai/classify/matter-type', { description }),
  classifierInfo: () => api.get('/ai/classify/matter-type/info'),
  modelStatus: () => api.get('/ai/models/status'),
};

export default api;