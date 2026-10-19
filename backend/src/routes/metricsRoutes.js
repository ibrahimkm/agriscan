import express from 'express';
import { metricsService } from '../services/metricsService.js';
import jwt from 'jsonwebtoken';

const router = express.Router();

/**
 * Metrics Authorization Middleware
 * Protects operational and ML metrics from unauthorized public scraping.
 * Accepts:
 * 1. Header `x-metrics-key: <METRICS_API_KEY>`
 * 2. Header `Authorization: Bearer <JWT_or_METRICS_KEY>`
 * 3. Query param `?key=<METRICS_API_KEY>`
 * 4. Local loopback in non-production environments
 */
const requireMetricsAuth = (req, res, next) => {
  const configuredKey = process.env.METRICS_API_KEY;
  const providedKey = req.headers['x-metrics-key'] || req.query.key;
  const authHeader = req.headers.authorization;

  // 1. Check direct metrics key match
  if (configuredKey && providedKey && providedKey === configuredKey) {
    return next();
  }

  // 2. Check Bearer token (either metrics key or valid user JWT)
  if (authHeader && authHeader.startsWith('Bearer ')) {
    const token = authHeader.split(' ')[1];
    if (configuredKey && token === configuredKey) {
      return next();
    }
    try {
      const jwtSecret = process.env.JWT_SECRET || 'agriscan_super_secret_jwt_key_2026';
      jwt.verify(token, jwtSecret);
      return next();
    } catch {
      // invalid token
    }
  }

  // 3. Localhost access allowed in development/test when key is not configured
  const isLocalhost = req.ip === '127.0.0.1' || req.ip === '::1' || req.ip === '::ffff:127.0.0.1';
  if (!configuredKey && process.env.NODE_ENV !== 'production' && isLocalhost) {
    return next();
  }

  return res.status(401).json({
    success: false,
    message: 'Unauthorized. Metrics endpoint requires x-metrics-key header or valid authentication.',
  });
};

router.use(requireMetricsAuth);

/**
 * GET /api/metrics
 * Returns Prometheus text format or JSON format if requested.
 */
router.get('/', (req, res) => {
  const format = req.query.format || (req.headers.accept?.includes('application/json') ? 'json' : 'prometheus');

  if (format === 'json') {
    return res.json({
      success: true,
      data: metricsService.toJSON(),
    });
  }

  res.set('Content-Type', 'text/plain; version=0.0.4; charset=utf-8');
  return res.send(metricsService.toPrometheusText());
});

export default router;
