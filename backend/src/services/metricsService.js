/**
 * AgriScan In-Process Metrics Registry & Collector
 * Production-safe, zero-dependency Prometheus & JSON metrics collection.
 * 
 * Safety invariants:
 * 1. Bounded cardinality: only predefined labels (status_class, method, route template, crop, disease).
 * 2. Zero sensitive data: never logs user IDs, tokens, raw URLs, passwords, or image payloads.
 * 3. Crash-proof: all update methods are internally safeguarded against exceptions.
 */

import crypto from 'crypto';

class MetricsService {
  constructor() {
    this.startTime = Date.now();
    this.modelVersion = 'AgriScan-Vision-EfficientNetB0-PlantVillage-v3.0';
    this.modelChecksum = 'd435d2fe813a346b03202d87c047b2c846c5448118294ef96faac9f619987bdd';

    // HTTP metrics
    this.httpRequestsTotal = new Map(); // key: "method|route|status_class" -> count
    this.httpRequestDurationSum = 0;
    this.httpRequestDurationCount = 0;
    this.httpErrorsTotal = { '4xx': 0, '5xx': 0 };

    // ML inference metrics
    this.mlPredictionsTotal = new Map(); // key: "crop|disease" -> count
    this.mlPredictionErrorsTotal = new Map(); // key: "error_type" -> count
    this.mlInferenceDurationSum = 0;
    this.mlInferenceDurationCount = 0;
    this.mlInferenceDurationBuckets = {
      '0.05': 0, // <= 50ms
      '0.10': 0, // <= 100ms
      '0.25': 0, // <= 250ms
      '0.50': 0, // <= 500ms
      '1.00': 0, // <= 1000ms
      '2.50': 0, // <= 2500ms
      '+Inf': 0,
    };

    // Confidence score distribution
    this.confidenceBuckets = {
      'under_50': 0,  // < 50%
      '50_to_69': 0,  // 50% - 69% (low confidence alert zone)
      '70_to_84': 0,  // 70% - 84% (moderate confidence)
      '85_to_94': 0,  // 85% - 94% (high confidence)
      '95_to_100': 0, // 95% - 100% (very high confidence)
    };
    this.lowConfidenceCount = 0; // count of predictions < 70%

    // Image characteristics (metadata only, no raw images stored)
    this.imagePayloadBytesSum = 0;
    this.imagePayloadCount = 0;

    // Database operation metrics
    this.dbOperationsTotal = {
      read_success: 0,
      read_failure: 0,
      write_success: 0,
      write_failure: 0,
    };
  }

  /**
   * Normalize an Express route to avoid high-cardinality label explosion.
   * e.g. /api/crops/64f1234abcd -> /api/crops/:id
   */
  normalizeRoute(routePath) {
    if (!routePath) return 'unknown';
    return routePath
      .replace(/[0-9a-fA-F]{24}/g, ':id') // MongoDB ObjectIds
      .replace(/[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}/g, ':id') // UUIDs
      .replace(/\/[0-9]+(\/|$)/g, '/:id$1') // Numeric IDs
      .split('?')[0]; // Strip query parameters
  }

  /**
   * Record HTTP request duration and status.
   */
  recordHttpRequest({ method, route, statusCode, durationSeconds }) {
    try {
      const normRoute = this.normalizeRoute(route);
      const statusClass = statusCode >= 500 ? '5xx' : statusCode >= 400 ? '4xx' : statusCode >= 300 ? '3xx' : '2xx';
      const key = `${method.toUpperCase()}|${normRoute}|${statusClass}`;

      this.httpRequestsTotal.set(key, (this.httpRequestsTotal.get(key) || 0) + 1);
      this.httpRequestDurationSum += Number(durationSeconds) || 0;
      this.httpRequestDurationCount += 1;

      if (statusCode >= 500) {
        this.httpErrorsTotal['5xx'] += 1;
      } else if (statusCode >= 400) {
        this.httpErrorsTotal['4xx'] += 1;
      }
    } catch {
      // Metrics collection must never throw
    }
  }

  /**
   * Record a successful ML disease diagnosis.
   */
  recordPrediction({ cropName, diseaseName, confidence, inferenceDurationSeconds, imageSizeBytes }) {
    try {
      const cleanCrop = (cropName || 'Unknown').replace(/[^a-zA-Z0-9_ -]/g, '').trim().slice(0, 32);
      const cleanDisease = (diseaseName || 'Unknown').replace(/[^a-zA-Z0-9_ -]/g, '').trim().slice(0, 64);
      const key = `${cleanCrop}|${cleanDisease}`;

      this.mlPredictionsTotal.set(key, (this.mlPredictionsTotal.get(key) || 0) + 1);

      // Duration metrics
      if (typeof inferenceDurationSeconds === 'number' && inferenceDurationSeconds >= 0) {
        this.mlInferenceDurationSum += inferenceDurationSeconds;
        this.mlInferenceDurationCount += 1;

        for (const bucketStr of Object.keys(this.mlInferenceDurationBuckets)) {
          if (bucketStr === '+Inf') {
            this.mlInferenceDurationBuckets['+Inf'] += 1;
          } else if (inferenceDurationSeconds <= parseFloat(bucketStr)) {
            this.mlInferenceDurationBuckets[bucketStr] += 1;
          }
        }
      }

      // Confidence distribution
      const confNum = Number(confidence) || 0;
      if (confNum < 50) {
        this.confidenceBuckets['under_50'] += 1;
      } else if (confNum < 70) {
        this.confidenceBuckets['50_to_69'] += 1;
      } else if (confNum < 85) {
        this.confidenceBuckets['70_to_84'] += 1;
      } else if (confNum < 95) {
        this.confidenceBuckets['85_to_94'] += 1;
      } else {
        this.confidenceBuckets['95_to_100'] += 1;
      }

      if (confNum < 70) {
        this.lowConfidenceCount += 1;
      }

      // Image payload characteristics
      if (typeof imageSizeBytes === 'number' && imageSizeBytes > 0) {
        this.imagePayloadBytesSum += imageSizeBytes;
        this.imagePayloadCount += 1;
      }
    } catch {
      // Metrics collection must never throw
    }
  }

  /**
   * Record an ML prediction error (e.g. invalid image, preprocessing failure).
   */
  recordPredictionError(errorType = 'general_inference_failure') {
    try {
      const cleanType = String(errorType).replace(/[^a-zA-Z0-9_]/g, '_').slice(0, 32);
      this.mlPredictionErrorsTotal.set(cleanType, (this.mlPredictionErrorsTotal.get(cleanType) || 0) + 1);
    } catch {
      // Metrics collection must never throw
    }
  }

  /**
   * Record a database operation outcome.
   */
  recordDbOperation(type = 'read', success = true) {
    try {
      const key = `${type === 'write' ? 'write' : 'read'}_${success ? 'success' : 'failure'}`;
      if (this.dbOperationsTotal[key] !== undefined) {
        this.dbOperationsTotal[key] += 1;
      }
    } catch {
      // Metrics collection must never throw
    }
  }

  /**
   * Format metrics in standard Prometheus text exposition format.
   */
  toPrometheusText() {
    const lines = [];

    // Header info
    lines.push('# HELP agriscan_service_info Build and model metadata.');
    lines.push('# TYPE agriscan_service_info gauge');
    lines.push(
      `agriscan_service_info{version="2.4.0",model_version="${this.modelVersion}",model_checksum="${this.modelChecksum}"} 1`
    );

    lines.push('# HELP agriscan_uptime_seconds Application uptime in seconds.');
    lines.push('# TYPE agriscan_uptime_seconds gauge');
    lines.push(`agriscan_uptime_seconds ${((Date.now() - this.startTime) / 1000).toFixed(2)}`);

    // HTTP requests
    lines.push('# HELP agriscan_http_requests_total Total number of HTTP requests.');
    lines.push('# TYPE agriscan_http_requests_total counter');
    for (const [key, count] of this.httpRequestsTotal.entries()) {
      const [method, route, statusClass] = key.split('|');
      lines.push(`agriscan_http_requests_total{method="${method}",route="${route}",status="${statusClass}"} ${count}`);
    }

    lines.push('# HELP agriscan_http_errors_total Total number of 4xx and 5xx HTTP responses.');
    lines.push('# TYPE agriscan_http_errors_total counter');
    lines.push(`agriscan_http_errors_total{class="4xx"} ${this.httpErrorsTotal['4xx']}`);
    lines.push(`agriscan_http_errors_total{class="5xx"} ${this.httpErrorsTotal['5xx']}`);

    // HTTP request duration
    lines.push('# HELP agriscan_http_request_duration_seconds Total time spent in HTTP requests.');
    lines.push('# TYPE agriscan_http_request_duration_seconds summary');
    lines.push(`agriscan_http_request_duration_seconds_sum ${this.httpRequestDurationSum.toFixed(4)}`);
    lines.push(`agriscan_http_request_duration_seconds_count ${this.httpRequestDurationCount}`);

    // ML Predictions
    lines.push('# HELP agriscan_ml_predictions_total Total ML disease predictions by crop and disease.');
    lines.push('# TYPE agriscan_ml_predictions_total counter');
    for (const [key, count] of this.mlPredictionsTotal.entries()) {
      const [crop, disease] = key.split('|');
      lines.push(`agriscan_ml_predictions_total{crop="${crop}",disease="${disease}"} ${count}`);
    }

    lines.push('# HELP agriscan_ml_prediction_errors_total Total failed ML diagnosis requests.');
    lines.push('# TYPE agriscan_ml_prediction_errors_total counter');
    for (const [type, count] of this.mlPredictionErrorsTotal.entries()) {
      lines.push(`agriscan_ml_prediction_errors_total{type="${type}"} ${count}`);
    }

    // Inference duration histogram
    lines.push('# HELP agriscan_ml_inference_duration_seconds ONNX model execution latency.');
    lines.push('# TYPE agriscan_ml_inference_duration_seconds histogram');
    for (const [bucket, count] of Object.entries(this.mlInferenceDurationBuckets)) {
      lines.push(`agriscan_ml_inference_duration_seconds_bucket{le="${bucket}"} ${count}`);
    }
    lines.push(`agriscan_ml_inference_duration_seconds_sum ${this.mlInferenceDurationSum.toFixed(4)}`);
    lines.push(`agriscan_ml_inference_duration_seconds_count ${this.mlInferenceDurationCount}`);

    // Confidence distribution
    lines.push('# HELP agriscan_ml_confidence_distribution_total Predictions by confidence category.');
    lines.push('# TYPE agriscan_ml_confidence_distribution_total counter');
    for (const [bucket, count] of Object.entries(this.confidenceBuckets)) {
      lines.push(`agriscan_ml_confidence_distribution_total{range="${bucket}"} ${count}`);
    }

    lines.push('# HELP agriscan_ml_low_confidence_total Count of predictions below 70% confidence threshold.');
    lines.push('# TYPE agriscan_ml_low_confidence_total counter');
    lines.push(`agriscan_ml_low_confidence_total ${this.lowConfidenceCount}`);

    // Database operations
    lines.push('# HELP agriscan_db_operations_total Total database operations by type and outcome.');
    lines.push('# TYPE agriscan_db_operations_total counter');
    for (const [key, count] of Object.entries(this.dbOperationsTotal)) {
      const [type, status] = key.split('_');
      lines.push(`agriscan_db_operations_total{operation="${type}",status="${status}"} ${count}`);
    }

    return lines.join('\n') + '\n';
  }

  /**
   * Return structured JSON summary of metrics for programmatic consumption.
   */
  toJSON() {
    const avgHttpDuration =
      this.httpRequestDurationCount > 0 ? this.httpRequestDurationSum / this.httpRequestDurationCount : 0;
    const avgInferenceDuration =
      this.mlInferenceDurationCount > 0 ? this.mlInferenceDurationSum / this.mlInferenceDurationCount : 0;
    const avgImageSizeBytes =
      this.imagePayloadCount > 0 ? Math.round(this.imagePayloadBytesSum / this.imagePayloadCount) : 0;

    const predictionsByCrop = {};
    const predictionsByDisease = {};
    let totalPredictions = 0;

    for (const [key, count] of this.mlPredictionsTotal.entries()) {
      const [crop, disease] = key.split('|');
      predictionsByCrop[crop] = (predictionsByCrop[crop] || 0) + count;
      predictionsByDisease[disease] = (predictionsByDisease[disease] || 0) + count;
      totalPredictions += count;
    }

    return {
      service: 'AgriScan API Backend',
      version: '2.4.0',
      uptimeSeconds: Math.round((Date.now() - this.startTime) / 1000),
      model: {
        version: this.modelVersion,
        checksum: this.modelChecksum,
        totalPredictions,
        avgInferenceDurationSeconds: parseFloat(avgInferenceDuration.toFixed(4)),
        lowConfidenceCount: this.lowConfidenceCount,
        lowConfidenceRate: totalPredictions > 0 ? parseFloat((this.lowConfidenceCount / totalPredictions).toFixed(4)) : 0,
        confidenceDistribution: { ...this.confidenceBuckets },
        predictionsByCrop,
        predictionsByDisease,
        avgImageSizeBytes,
      },
      http: {
        totalRequests: this.httpRequestDurationCount,
        avgDurationSeconds: parseFloat(avgHttpDuration.toFixed(4)),
        errors: { ...this.httpErrorsTotal },
      },
      database: { ...this.dbOperationsTotal },
      timestamp: new Date().toISOString(),
    };
  }

  /**
   * Reset in-memory counters (useful for isolated unit tests).
   */
  reset() {
    this.httpRequestsTotal.clear();
    this.httpRequestDurationSum = 0;
    this.httpRequestDurationCount = 0;
    this.httpErrorsTotal = { '4xx': 0, '5xx': 0 };
    this.mlPredictionsTotal.clear();
    this.mlPredictionErrorsTotal.clear();
    this.mlInferenceDurationSum = 0;
    this.mlInferenceDurationCount = 0;
    for (const b of Object.keys(this.mlInferenceDurationBuckets)) {
      this.mlInferenceDurationBuckets[b] = 0;
    }
    for (const b of Object.keys(this.confidenceBuckets)) {
      this.confidenceBuckets[b] = 0;
    }
    this.lowConfidenceCount = 0;
    this.imagePayloadBytesSum = 0;
    this.imagePayloadCount = 0;
    for (const k of Object.keys(this.dbOperationsTotal)) {
      this.dbOperationsTotal[k] = 0;
    }
  }
}

export const metricsService = new MetricsService();
export default metricsService;
