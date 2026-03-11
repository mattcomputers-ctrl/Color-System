import axios from 'axios';

const API_URL = process.env.REACT_APP_API_URL || '/api/v1';

const api = axios.create({
  baseURL: API_URL,
  headers: { 'Content-Type': 'application/json' },
});

// Add auth token to requests
api.interceptors.request.use((config) => {
  const token = localStorage.getItem('token');
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// Handle 401 responses
api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      localStorage.removeItem('token');
      localStorage.removeItem('user');
      if (window.location.pathname !== '/login') {
        window.location.href = '/login';
      }
    }
    return Promise.reject(error);
  }
);

// Auth
export const authAPI = {
  login: (email, password) => api.post('/auth/login', { email, password }),
  getMe: () => api.get('/auth/me'),
  changePassword: (currentPassword, newPassword) =>
    api.post('/auth/change-password', {
      current_password: currentPassword,
      new_password: newPassword,
    }),
};

// Series
export const seriesAPI = {
  list: (params = {}) => api.get('/series', { params }),
  get: (id) => api.get(`/series/${id}`),
  create: (data) => api.post('/series', data),
  update: (id, data) => api.put(`/series/${id}`, data),
  delete: (id) => api.delete(`/series/${id}`),
};

// Bases
export const basesAPI = {
  listBySeries: (seriesId, params = {}) => api.get(`/bases/series/${seriesId}`, { params }),
  get: (id) => api.get(`/bases/${id}`),
  create: (seriesId, data) => api.post(`/bases/series/${seriesId}`, data),
  update: (id, data) => api.put(`/bases/${id}`, data),
  addConcentration: (baseId, data) => api.post(`/bases/${baseId}/concentrations`, data),
  uploadCxf: (concId, file) => {
    const formData = new FormData();
    formData.append('file', file);
    return api.post(`/bases/concentrations/${concId}/upload-cxf`, formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    });
  },
  getSpectral: (concId, version = null) =>
    api.get(`/bases/concentrations/${concId}/spectral`, { params: { version } }),
  getSpectralHistory: (concId) =>
    api.get(`/bases/concentrations/${concId}/spectral/history`),
};

// Pantone
export const pantoneAPI = {
  listTargets: (params = {}) => api.get('/pantone/targets', { params }),
  createTarget: (data) => api.post('/pantone/targets', data),
  createTargetFromCxf: (formData) =>
    api.post('/pantone/targets', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    }),
  listFormulas: (params = {}) => api.get('/pantone/formulas', { params }),
  getFormula: (id) => api.get(`/pantone/formulas/${id}`),
  formulate: (targetId, seriesId) =>
    api.post('/pantone/formulate', { target_id: targetId, series_id: seriesId }),
  approveFormula: (id, notes = '') =>
    api.post(`/pantone/formulas/${id}/approve`, { notes }),
};

// Custom Match
export const customMatchAPI = {
  listJobs: (params = {}) => api.get('/custom-match/jobs', { params }),
  getJob: (id) => api.get(`/custom-match/jobs/${id}`),
  matchFromLab: (data) => api.post('/custom-match/match-lab', data),
  matchFromCxf: (formData) =>
    api.post('/custom-match/match-cxf', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    }),
};

// Admin
export const adminAPI = {
  listUsers: () => api.get('/admin/users'),
  createUser: (data) => api.post('/admin/users', data),
  updateUser: (id, data) => api.put(`/admin/users/${id}`, data),
  deactivateUser: (id) => api.delete(`/admin/users/${id}`),
  listRoles: () => api.get('/admin/roles'),
  getAuditLog: (params = {}) => api.get('/admin/audit-log', { params }),
  getDashboardStats: () => api.get('/admin/dashboard-stats'),
};

// Export
export const exportAPI = {
  pantoneFormulaPdf: (formulaId) =>
    api.get(`/export/pantone-formula/${formulaId}/pdf`, { responseType: 'blob' }),
  pantoneFormulasExcel: (params = {}) =>
    api.get('/export/pantone-formulas/excel', { params, responseType: 'blob' }),
  customMatchPdf: (jobId) =>
    api.get(`/export/custom-match/${jobId}/pdf`, { responseType: 'blob' }),
};

export default api;
