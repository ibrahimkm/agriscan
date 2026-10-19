import { metricsService } from '../services/metricsService.js';

/**
 * Express middleware to record request duration and status.
 * Wrapped in try/catch to ensure metrics recording can never crash a request.
 */
export const metricsMiddleware = (req, res, next) => {
  const startHrTime = process.hrtime.bigint();

  res.on('finish', () => {
    try {
      const durationSeconds = Number(process.hrtime.bigint() - startHrTime) / 1e9;
      // Prefer Express matched route path if available, otherwise raw path
      const routePath = req.baseUrl || req.path || 'unknown';

      // Record HTTP metrics
      metricsService.recordHttpRequest({
        method: req.method,
        route: routePath,
        statusCode: res.statusCode,
        durationSeconds,
      });
    } catch {
      // Metrics collection must never throw
    }
  });

  next();
};

export default metricsMiddleware;
