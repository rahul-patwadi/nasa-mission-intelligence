export const environment = {
  production: true,
  // Relative + same-origin: nginx (frontend/nginx.conf) proxies /api/* to the
  // backend service, so no CORS is needed in production.
  apiBaseUrl: '/api',
};
