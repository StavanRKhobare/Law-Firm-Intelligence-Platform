import axios from 'axios';

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000/api/v1';

const api = axios.create({ baseURL: API_BASE_URL });

api.interceptors.request.use((config) => {
  const token = localStorage.getItem('access_token');
  if (token) config.headers.Authorization = `Bearer ${token}`;
  return config;
});

api.interceptors.response.use(
  (response) => response,
  (error) => {
    const status = error.response?.status;
    const onLoginCall = error.config?.url?.startsWith('/auth/login');
    if (status === 401 && !onLoginCall) {
      localStorage.removeItem('access_token');
      localStorage.removeItem('user');
      window.location.href = '/login';
    }
    if (status === 403 && error.response?.data?.detail === 'Password change required'
      && window.location.pathname !== '/change-password') {
      window.location.href = '/change-password';
    }
    return Promise.reject(error);
  }
);

/** A readable message from any failed API call. */
export function errorMessage(error, fallback = 'Something went wrong. Please try again.') {
  const detail = error?.response?.data?.detail;
  if (typeof detail === 'string') return detail;
  if (Array.isArray(detail) && detail.length) {
    return detail.map((d) => {
      const field = (d.loc || []).filter((p) => p !== 'body' && p !== 'query').join(' ');
      const msg = (d.msg || '').replace(/^Value error, /, '');
      return field ? `${field.replace(/_/g, ' ')}: ${msg}` : msg;
    }).join('. ');
  }
  if (error?.code === 'ERR_NETWORK') return 'Cannot reach the server. Check that the backend is running.';
  return fallback;
}

export const authAPI = {
  login: (credentials) => api.post('/auth/login-json', credentials),
  setupStatus: () => api.get('/auth/setup-status'),
  createFirstAdmin: (data) => api.post('/auth/register', data),
  practiceGroups: () => api.get('/auth/practice-groups'),
  submitJoinRequest: (data) => api.post('/auth/join-requests', data),
  getCurrentUser: () => api.get('/auth/me'),
  changePassword: (data) => api.post('/auth/change-password', data),
};

export const teamAPI = {
  directory: () => api.get('/team/directory'),
  members: () => api.get('/team/members'),
  addMember: (data) => api.post('/team/members', data),
  resetPassword: (id) => api.post(`/team/members/${id}/reset-password`),
  changeRole: (id, role) => api.patch(`/team/members/${id}/role`, { role }),
  deactivate: (id) => api.post(`/team/members/${id}/deactivate`),
  activate: (id) => api.post(`/team/members/${id}/activate`),
  joinRequests: (status = 'Pending') => api.get('/team/join-requests', { params: { status } }),
  approve: (id, data) => api.post(`/team/join-requests/${id}/approve`, data),
  reject: (id, data) => api.post(`/team/join-requests/${id}/reject`, data),
};

export const casesAPI = {
  getAll: (params) => api.get('/cases/', { params }),
  getById: (id) => api.get(`/cases/${id}`),
  create: (data) => api.post('/cases/', data),
  update: (id, data) => api.put(`/cases/${id}`, data),
  delete: (id) => api.delete(`/cases/${id}`),
  updateStatus: (id, params) => api.patch(`/cases/${id}/status`, null, { params }),
  counsel: (id) => api.get(`/cases/${id}/lawyers`),
  assign: (id, data) => api.post(`/cases/${id}/lawyers`, data),
  endAssignment: (id, lawyerId) => api.delete(`/cases/${id}/lawyers/${lawyerId}`),
  timeline: (id) => api.get(`/cases/${id}/timeline`),
  addNote: (id, body) => api.post(`/cases/${id}/notes`, { body }),
};

export const hearingsAPI = {
  getAll: (params) => api.get('/hearings/', { params }),
  create: (data) => api.post('/hearings/', data),
  update: (id, data) => api.put(`/hearings/${id}`, data),
  recordResult: (id, data) => api.post(`/hearings/${id}/result`, data),
  delete: (id) => api.delete(`/hearings/${id}`),
};

export const tasksAPI = {
  getAll: (params) => api.get('/tasks/', { params }),
  create: (data) => api.post('/tasks/', data),
  update: (id, data) => api.put(`/tasks/${id}`, data),
  delete: (id) => api.delete(`/tasks/${id}`),
};

export const lawyersAPI = {
  getAll: (params) => api.get('/lawyers/', { params }),
  getById: (id) => api.get(`/lawyers/${id}`),
  update: (id, data) => api.put(`/lawyers/${id}`, data),
};

export const opposingPartiesAPI = {
  getAll: (params) => api.get('/opposing-parties/', { params }),
  getById: (id) => api.get(`/opposing-parties/${id}`),
  create: (data) => api.post('/opposing-parties/', data),
  update: (id, data) => api.put(`/opposing-parties/${id}`, data),
  delete: (id) => api.delete(`/opposing-parties/${id}`),
};

export const clientsAPI = {
  getAll: (params) => api.get('/clients/', { params }),
  getById: (id) => api.get(`/clients/${id}`),
  create: (data) => api.post('/clients/', data),
  update: (id, data) => api.put(`/clients/${id}`, data),
  delete: (id) => api.delete(`/clients/${id}`),
};

export const evidenceAPI = {
  getAll: (params) => api.get('/evidence/', { params }),
  create: (formData) => api.post('/evidence/', formData),
  update: (id, data) => api.put(`/evidence/${id}`, data),
  delete: (id) => api.delete(`/evidence/${id}`),
  uploadFile: (id, formData) => api.post(`/evidence/${id}/upload-file`, formData),
  downloadFile: (id) => api.get(`/evidence/${id}/download-file`, { responseType: 'blob' }),
};

export const referenceAPI = {
  courts: () => api.get('/courts/'),
  addCourt: (data) => api.post('/courts/', data),
  locations: () => api.get('/locations/'),
  addLocation: (data) => api.post('/locations/', data),
  practiceGroups: () => api.get('/practice-groups/'),
  addPracticeGroup: (data) => api.post('/practice-groups/', data),
};

export const workspaceAPI = {
  summary: () => api.get('/workspace/summary'),
  search: (q) => api.get('/search/', { params: { q } }),
  checkConflicts: (data) => api.post('/conflicts/check', data),
};

export const analyticsAPI = {
  firm: () => api.get('/analytics/firm'),
  byMatterType: () => api.get('/analytics/cases/by-matter-type'),
};

export const auditAPI = {
  getAll: (params) => api.get('/audit/', { params }),
};

export const aiAPI = {
  classifyMatter: (description) => api.post('/ai/classify/matter-type', { description }),
};

export default api;
