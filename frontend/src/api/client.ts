import axios from 'axios';

const client = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL || 'https://nutriguard-production-4ba1.up.railway.app',
  timeout: 15000,
});

// Attach JWT on every request
client.interceptors.request.use((config) => {
  const token = localStorage.getItem('ng_token');
  if (token) config.headers.Authorization = `Bearer ${token}`;
  return config;
});

// Handle 401 → redirect to login
client.interceptors.response.use(
  (res) => res,
  (err) => {
    if (err.response?.status === 401) {
      localStorage.removeItem('ng_token');
      window.location.href = '/login';
    }
    return Promise.reject(err);
  }
);

export default client;
