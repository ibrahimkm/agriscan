#!/usr/bin/env node
/**
 * AgriScan Metrics & Observability Test Suite
 * Validates in-process Prometheus and JSON metrics collection:
 * 1. Request duration and status metrics
 * 2. Prediction counts, inference latency, confidence distribution
 * 3. Protected endpoint security (unauthorized rejection & key-based access)
 * 4. Zero sensitive data leakage (no passwords, tokens, image buffers, user IDs)
 */

import express from 'express';
import { metricsService } from './src/services/metricsService.js';
import { metricsMiddleware } from './src/middleware/metricsMiddleware.js';
import metricsRoutes from './src/routes/metricsRoutes.js';

async function runMetricsTests() {
  console.log('='.repeat(70));
  console.log('       AGRISCAN METRICS & OBSERVABILITY TEST SUITE');
  console.log('='.repeat(70));

  // Reset metrics for clean test run
  metricsService.reset();

  const app = express();
  app.use(express.json());
  app.use(metricsMiddleware);

  // Setup test routes
  app.use('/api/metrics', metricsRoutes);
  app.get('/api/test/success', (req, res) => res.json({ ok: true }));
  app.get('/api/test/client-error', (req, res) => res.status(400).json({ error: 'bad_request' }));
  app.get('/api/test/server-error', (req, res) => res.status(500).json({ error: 'internal_error' }));

  const server = await new Promise((resolve) => {
    const s = app.listen(0, () => resolve(s));
  });
  const port = server.address().port;
  const baseUrl = `http://127.0.0.1:${port}`;

  const results = [];

  try {
    // ----------------------------------------------------
    // Test 1: Record Simulated HTTP Requests
    // ----------------------------------------------------
    console.log('\n[Test 1] Testing HTTP request duration and status class metrics...');
    await fetch(`${baseUrl}/api/test/success`);
    await fetch(`${baseUrl}/api/test/client-error`);
    await fetch(`${baseUrl}/api/test/server-error`);

    const jsonRes = await fetch(`${baseUrl}/api/metrics?format=json`);
    const jsonMetrics = await jsonRes.json();
    const httpData = jsonMetrics.data.http;

    const test1Passed =
      httpData.totalRequests >= 3 &&
      httpData.errors['4xx'] >= 1 &&
      httpData.errors['5xx'] >= 1 &&
      httpData.avgDurationSeconds >= 0;

    results.push({
      name: 'HTTP request status & duration metrics',
      expected: '>= 3 requests, 1x 4xx, 1x 5xx',
      actual: `${httpData.totalRequests} reqs, ${httpData.errors['4xx']} 4xx, ${httpData.errors['5xx']} 5xx`,
      passed: test1Passed,
    });
    console.log(`  ✓ Test 1: ${test1Passed ? 'PASSED' : 'FAILED'}`);

    // ----------------------------------------------------
    // Test 2: Record ML Predictions & Confidence Distribution
    // ----------------------------------------------------
    console.log('\n[Test 2] Recording simulated ML predictions across confidence buckets...');
    metricsService.recordPrediction({
      cropName: 'Apple',
      diseaseName: 'Apple Scab',
      confidence: 98,
      inferenceDurationSeconds: 0.045,
      imageSizeBytes: 125000,
    });
    metricsService.recordPrediction({
      cropName: 'Potato',
      diseaseName: 'Late Blight',
      confidence: 91,
      inferenceDurationSeconds: 0.052,
      imageSizeBytes: 98000,
    });
    metricsService.recordPrediction({
      cropName: 'Tomato',
      diseaseName: 'Early Blight',
      confidence: 65, // low confidence (<70)
      inferenceDurationSeconds: 0.048,
      imageSizeBytes: 110000,
    });

    const mlJson = (await (await fetch(`${baseUrl}/api/metrics?format=json`)).json()).data.model;
    const test2Passed =
      mlJson.totalPredictions === 3 &&
      mlJson.predictionsByCrop['Apple'] === 1 &&
      mlJson.predictionsByCrop['Potato'] === 1 &&
      mlJson.predictionsByCrop['Tomato'] === 1 &&
      mlJson.lowConfidenceCount === 1 &&
      mlJson.confidenceDistribution['50_to_69'] === 1 &&
      mlJson.confidenceDistribution['95_to_100'] === 1 &&
      mlJson.avgImageSizeBytes > 0;

    results.push({
      name: 'ML prediction counts and confidence distribution',
      expected: '3 predictions, 1 low-confidence (<70)',
      actual: `${mlJson.totalPredictions} preds, ${mlJson.lowConfidenceCount} low-conf`,
      passed: test2Passed,
    });
    console.log(`  ✓ Test 2: ${test2Passed ? 'PASSED' : 'FAILED'}`);

    // ----------------------------------------------------
    // Test 3: Prometheus Text Exposition Format
    // ----------------------------------------------------
    console.log('\n[Test 3] Verifying Prometheus standard text format output...');
    const promRes = await fetch(`${baseUrl}/api/metrics`);
    const promText = await promRes.text();

    const hasServiceInfo = promText.includes('agriscan_service_info{version="2.4.0"');
    const hasHttpRequests = promText.includes('agriscan_http_requests_total');
    const hasMlPredictions = promText.includes('agriscan_ml_predictions_total{crop="Apple",disease="Apple Scab"} 1');
    const hasDurationHistogram = promText.includes('agriscan_ml_inference_duration_seconds_bucket');
    const hasContentType = promRes.headers.get('content-type')?.includes('text/plain');

    const test3Passed =
      promRes.status === 200 &&
      hasServiceInfo &&
      hasHttpRequests &&
      hasMlPredictions &&
      hasDurationHistogram &&
      hasContentType;

    results.push({
      name: 'Prometheus text exposition format',
      expected: 'Valid Prometheus metrics with standard headers and types',
      actual: `Status ${promRes.status}, Content-Type: ${promRes.headers.get('content-type')}`,
      passed: test3Passed,
    });
    console.log(`  ✓ Test 3: ${test3Passed ? 'PASSED' : 'FAILED'}`);

    // ----------------------------------------------------
    // Test 4: Security & Authentication Guard
    // ----------------------------------------------------
    console.log('\n[Test 4] Verifying metric access security with METRICS_API_KEY...');
    process.env.METRICS_API_KEY = 'super_secret_test_metrics_key_999';

    // 4a. Request without key should fail (HTTP 401)
    const unauthRes = await fetch(`${baseUrl}/api/metrics`);
    const unauthPassed = unauthRes.status === 401;

    // 4b. Request with x-metrics-key should succeed (HTTP 200)
    const authHeaderRes = await fetch(`${baseUrl}/api/metrics`, {
      headers: { 'x-metrics-key': 'super_secret_test_metrics_key_999' },
    });
    const authHeaderPassed = authHeaderRes.status === 200;

    // 4c. Request with query param should succeed (HTTP 200)
    const authQueryRes = await fetch(`${baseUrl}/api/metrics?key=super_secret_test_metrics_key_999`);
    const authQueryPassed = authQueryRes.status === 200;

    delete process.env.METRICS_API_KEY;

    const test4Passed = unauthPassed && authHeaderPassed && authQueryPassed;
    results.push({
      name: 'Protected metrics authorization guard',
      expected: '401 on unauthenticated, 200 with valid key',
      actual: `Unauth=${unauthRes.status}, Header=${authHeaderRes.status}, Query=${authQueryRes.status}`,
      passed: test4Passed,
    });
    console.log(`  ✓ Test 4: ${test4Passed ? 'PASSED' : 'FAILED'}`);

    // ----------------------------------------------------
    // Test 5: Sensitive Data Exclusion Verification
    // ----------------------------------------------------
    console.log('\n[Test 5] Verifying zero sensitive data leakage in metrics output...');
    const forbiddenKeywords = ['password', 'secret', 'token', 'jwt', 'buffer', 'base64', 'farmer@agriscan'];
    let leakDetected = false;
    let leakedTerm = '';

    for (const term of forbiddenKeywords) {
      if (promText.toLowerCase().includes(term)) {
        leakDetected = true;
        leakedTerm = term;
        break;
      }
    }

    const test5Passed = !leakDetected;
    results.push({
      name: 'Sensitive data exclusion in metrics payload',
      expected: 'No credentials, tokens, passwords, or personal emails',
      actual: leakDetected ? `LEAK DETECTED: ${leakedTerm}` : 'Zero sensitive terms found',
      passed: test5Passed,
    });
    console.log(`  ✓ Test 5: ${test5Passed ? 'PASSED' : 'FAILED'}`);

    // ----------------------------------------------------
    // Summary
    // ----------------------------------------------------
    console.log('\n' + '='.repeat(70));
    console.log('                   METRICS TEST SUMMARY');
    console.log('='.repeat(70));
    let allPassed = true;
    for (const r of results) {
      const icon = r.passed ? '✓ PASS' : '✗ FAIL';
      if (!r.passed) allPassed = false;
      console.log(`  ${icon} | ${r.name.padEnd(46)} | ${r.actual}`);
    }
    console.log('='.repeat(70));

    if (!allPassed) {
      throw new Error('One or more metrics unit tests failed.');
    }
    console.log('\nAll Metrics & Observability unit tests passed successfully!\n');
  } finally {
    await new Promise((resolve) => server.close(resolve));
  }
}

runMetricsTests().catch((err) => {
  console.error('[Metrics Test Suite Failed]', err);
  process.exit(1);
});
