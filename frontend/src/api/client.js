import axios from 'axios';

const parsedTimeout = Number.parseInt(import.meta.env.VITE_API_TIMEOUT_MS || '30000', 10);
const timeout = Number.isFinite(parsedTimeout) && parsedTimeout > 0 ? parsedTimeout : 30000;

const api = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL || 'http://127.0.0.1:8000/api',
  timeout,
});

api.interceptors.request.use((config) => {
  const token = localStorage.getItem('access_token');
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      localStorage.removeItem('access_token');
      localStorage.removeItem('current_user');
    }
    return Promise.reject(error);
  }
);

export default api;
