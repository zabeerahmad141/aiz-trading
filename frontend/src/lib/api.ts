import axios from 'axios';
import { useAuthStore } from '@/store/auth';

const api = axios.create({
  baseURL: '/api',
  timeout: 15000,
});

api.interceptors.request.use((config) => {
  const token = useAuthStore.getState().token;
  if (token) config.headers.Authorization = `Bearer ${token}`;
  return config;
});

api.interceptors.response.use(
  (res) => res,
  (err) => {
    if (err.response?.status === 401) {
      useAuthStore.getState().logout();
      window.location.href = '/login';
    }
    return Promise.reject(err);
  }
);

export default api;

// Auth
export const login = (username: string, password: string) =>
  api.post('/auth/login', { username, password });

export const getMe = () => api.get('/auth/me');

// Trading
export const getBotStatus = () => api.get('/trading/status');
export const getTradeHistory = (limit = 50) => api.get(`/trading/history?limit=${limit}`);
export const getOpenPositions = () => api.get('/trading/positions');
export const placeOrder = (data: object) => api.post('/trading/order', data);

// Portfolio
export const getPortfolioSummary = () => api.get('/portfolio/summary');
export const getPnLChart = (period = 'today') => api.get(`/portfolio/pnl-chart?period=${period}`);
export const getPortfolioSessions = (limit = 10) => api.get(`/portfolio/sessions?limit=${limit}`);

// Market
export const getQuotes = () => api.get('/market/quotes');
export const getOHLCV = (symbol: string, period = '1d', interval = '5m') =>
  api.get(`/market/ohlcv/${symbol}?period=${period}&interval=${interval}`);
export const getScreener = () => api.get('/market/screener');
// /api/status is at root level in backend (not under /api prefix router)
// nginx proxies /api/ → backend, so this hits backend:8000/api/status correctly
export const getApiStatus = () => api.get('/status');

// Users (admin)
export const listUsers = () => api.get('/users/');
export const createUser = (data: object) => api.post('/auth/users', data);
export const updateUser = (id: number, data: object) => api.patch(`/users/${id}`, data);
