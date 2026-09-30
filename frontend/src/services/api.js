import axios from 'axios';

const getApiBaseUrl = () => {
  let envUrl = import.meta.env.VITE_API_URL;
  if (envUrl) {
    if (!envUrl.startsWith('http://') && !envUrl.startsWith('https://')) {
      envUrl = `https://${envUrl}`;
    }
    return envUrl.endsWith('/api') ? envUrl : `${envUrl.replace(/\/+$/, '')}/api`;
  }

  // If in browser and not localhost, fallback to deployed backend
  if (typeof window !== 'undefined' && window.location.hostname !== 'localhost' && window.location.hostname !== '127.0.0.1') {
    return 'https://agriscan-backend-3veo.onrender.com/api';
  }

  return 'http://localhost:5001/api';
};

const API_BASE_URL = getApiBaseUrl();

const api = axios.create({
  baseURL: API_BASE_URL,
});

api.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('agriscan_token');
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => Promise.reject(error)
);

api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response && error.response.status === 401) {
      // Clear token if expired
      localStorage.removeItem('agriscan_token');
      localStorage.removeItem('agriscan_user');
    }
    return Promise.reject(error);
  }
);

export default api;
