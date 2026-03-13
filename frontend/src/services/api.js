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

// Handle error responses
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
    // Ensure error.message contains the server error if available
    if (error.response?.data?.error) {
      error.serverMessage = error.response.data.error;
    } else if (error.response?.status === 503) {
      error.serverMessage = 'Database connection error. Check server configuration.';
    } else if (!error.response) {
      error.serverMessage = 'Cannot reach the server. Check that the service is running.';
    }
    return Promise.reject(error);
  }
);

// Health check — tests database connectivity
export const healthAPI = {
  check: () => api.get('/health'),
};

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
  listSubstrates: (seriesId) => api.get(`/series/${seriesId}/substrates`),
  addSubstrate: (seriesId, data) => api.post(`/series/${seriesId}/substrates`, data),
  updateSubstrate: (seriesId, assocId, data) => api.put(`/series/${seriesId}/substrates/${assocId}`, data),
  removeSubstrate: (seriesId, assocId) => api.delete(`/series/${seriesId}/substrates/${assocId}`),
};

// Bases
export const basesAPI = {
  listBySeries: (seriesId, params = {}) => api.get(`/bases/series/${seriesId}`, { params }),
  get: (id) => api.get(`/bases/${id}`),
  create: (seriesId, data) => api.post(`/bases/series/${seriesId}`, data),
  update: (id, data) => api.put(`/bases/${id}`, data),
  delete: (id) => api.delete(`/bases/${id}`),
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
  getFormula: (id, config = {}) => api.get(`/pantone/formulas/${id}`, config),
  formulate: (targetId, seriesId, substrateId = null) =>
    api.post('/pantone/formulate', { target_id: targetId, series_id: seriesId, substrate_id: substrateId }),
  formulateAll: (seriesId, library = null, substrateId = null) =>
    api.post('/pantone/formulate-all', { series_id: seriesId, library, substrate_id: substrateId }, { timeout: 600000 }),
  approveFormula: (id, notes = '') =>
    api.post(`/pantone/formulas/${id}/approve`, { notes }),
};

// Substrates
export const substratesAPI = {
  list: (params = {}) => api.get('/substrates', { params }),
  get: (id, config = {}) => api.get(`/substrates/${id}`, config),
  create: (data) => api.post('/substrates', data),
  createFromCxf: (formData) =>
    api.post('/substrates', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    }),
  update: (id, data) => api.put(`/substrates/${id}`, data),
  delete: (id) => api.delete(`/substrates/${id}`),
};

// Custom Match
export const customMatchAPI = {
  listJobs: (params = {}) => api.get('/custom-match/jobs', { params }),
  getJob: (id, config = {}) => api.get(`/custom-match/jobs/${id}`, config),
  matchFromLab: (data) => api.post('/custom-match/match-lab', data),
  matchFromCxf: (formData) =>
    api.post('/custom-match/match-cxf', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    }),
};

// Tolerance Profiles
export const toleranceAPI = {
  list: (params = {}) => api.get('/tolerance-profiles', { params }),
  get: (id) => api.get(`/tolerance-profiles/${id}`),
  create: (data) => api.post('/tolerance-profiles', data),
  update: (id, data) => api.put(`/tolerance-profiles/${id}`, data),
  delete: (id) => api.delete(`/tolerance-profiles/${id}`),
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
