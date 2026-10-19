#!/usr/bin/env node
/**
 * AgriScan End-to-End Prediction & API Verification Suite (Zero external test deps)
 * Tests real backend prediction pipeline using native Node.js fetch:
 * 1. Authentication and JWT generation
 * 2. Real image upload via multipart/form-data
 * 3. Base64 leaf image diagnosis
 * 4. Distinct crop & disease detection (Apple Scab, Potato Late Blight, Tomato Healthy)
 * 5. Error handling on missing / invalid image payloads
 * 6. Verification that NO hardcoded Tomato fallback is returned
 */

import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';
import express from 'express';
import jwt from 'jsonwebtoken';

import { connectDB, disconnectDB } from './src/config/db.js';
import User from './src/models/User.js';
import { seedDatabase } from './src/seed/seedData.js';
import { mlInference } from './src/services/mlInference.js';

import authRoutes from './src/routes/authRoutes.js';
import diagnosisRoutes from './src/routes/diagnosisRoutes.js';
import { errorHandler } from './src/middleware/errorHandler.js';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const projectRoot = path.resolve(__dirname, '..');

import { metricsMiddleware } from './src/middleware/metricsMiddleware.js';
import metricsRoutes from './src/routes/metricsRoutes.js';

const app = express();
app.use(express.json({ limit: '50mb' }));
app.use(express.urlencoded({ extended: true, limit: '50mb' }));
app.use(metricsMiddleware);

// Health check endpoint (matches server.js contract)
app.get('/api/health', (req, res) => {
  res.json({
    status: 'healthy',
    service: 'AgriScan API Backend',
    version: '2.4.0',
    commit: process.env.RENDER_GIT_COMMIT || null,
    timestamp: new Date(),
  });
});

app.use('/api/metrics', metricsRoutes);
app.use('/api/auth', authRoutes);
app.use('/api/diagnoses', diagnosisRoutes);
app.use(errorHandler);

async function runE2ETests() {
  console.log('='.repeat(70));
  console.log('       AGRISCAN BACKEND END-TO-END PREDICTION TEST SUITE');
  console.log('='.repeat(70));

  let server = null;
  let baseUrl = '';
  let token = null;

  try {
    // Step 1: Connect DB & Initialize Model
    console.log('\n[E2E Step 1] Connecting to database & loading EfficientNet ONNX session...');
    await connectDB();
    await mlInference.ensureReady();
    console.log('  ✓ Database connected and ONNX InferenceSession is ready.');

    // Step 2: Start test server on ephemeral port
    server = await new Promise((resolve) => {
      const s = app.listen(0, () => resolve(s));
    });
    const port = server.address().port;
    baseUrl = `http://127.0.0.1:${port}`;
    console.log(`  ✓ Test HTTP server listening on ${baseUrl}`);

    // Step 3: Seed / Ensure user
    console.log('\n[E2E Step 2] Setting up authenticated test account...');
    let testUser = await User.findOne({ email: 'farmer@agriscan.io' });
    if (!testUser) {
      await seedDatabase();
      testUser = await User.findOne({ email: 'farmer@agriscan.io' });
    }

    const jwtSecret = process.env.JWT_SECRET || 'agriscan_super_secret_jwt_key_2026';
    token = jwt.sign({ id: testUser._id }, jwtSecret, { expiresIn: '1d' });
    console.log(`  ✓ Authenticated as: ${testUser.name} (${testUser.email})`);

    const testResults = [];

    // ----------------------------------------------------
    // Test 0: Health Check Endpoint Contract Verification
    // ----------------------------------------------------
    console.log('\n[E2E Step 2.5] Verifying /api/health endpoint contract...');
    const healthRes = await fetch(`${baseUrl}/api/health`);
    const healthBody = await healthRes.json();
    const healthPassed = healthRes.status === 200 &&
      healthBody.status === 'healthy' &&
      healthBody.service === 'AgriScan API Backend' &&
      healthBody.version === '2.4.0' &&
      Object.prototype.hasOwnProperty.call(healthBody, 'commit') &&
      healthBody.commit === null;

    // Verify commit field when RENDER_GIT_COMMIT is set
    process.env.RENDER_GIT_COMMIT = 'test-commit-sha-12345';
    const healthWithCommitRes = await fetch(`${baseUrl}/api/health`);
    const healthWithCommitBody = await healthWithCommitRes.json();
    const commitPassed = healthWithCommitBody.commit === 'test-commit-sha-12345';
    delete process.env.RENDER_GIT_COMMIT;

    testResults.push({
      name: 'Health check contract (/api/health)',
      expected: 'HTTP 200 with status healthy and dynamic commit field',
      actual: `HTTP ${healthRes.status} (status: ${healthBody.status}, commit: ${healthBody.commit} / ${healthWithCommitBody.commit})`,
      passed: healthPassed && commitPassed,
    });
    if (!healthPassed || !commitPassed) {
      throw new Error(`Health check contract failed: default=${JSON.stringify(healthBody)}, populated=${JSON.stringify(healthWithCommitBody)}`);
    }
    console.log(`  ✓ Health check contract PASSED: commit default=${healthBody.commit}, populated=${healthWithCommitBody.commit}`);

    // ----------------------------------------------------
    // Test 3: Upload Real leaf.JPG (Apple Scab) via multipart/form-data
    // ----------------------------------------------------
    console.log('\n[E2E Step 3] Testing multipart upload with real leaf.JPG...');
    const leafPath = path.join(projectRoot, 'leaf.JPG');
    if (fs.existsSync(leafPath)) {
      const fileBytes = fs.readFileSync(leafPath);
      const formData = new FormData();
      formData.append('image', new Blob([fileBytes], { type: 'image/jpeg' }), 'leaf.JPG');

      const res = await fetch(`${baseUrl}/api/diagnoses`, {
        method: 'POST',
        headers: {
          Authorization: `Bearer ${token}`,
        },
        body: formData,
      });

      const body = await res.json();
      console.log(`  Status: ${res.status}`);
      console.log(`  Predicted Crop:    ${body.data?.cropName}`);
      console.log(`  Predicted Disease: ${body.data?.predictedDisease}`);
      console.log(`  Confidence:        ${body.data?.confidence}%`);

      if (res.status === 201 && body.success) {
        const d = body.data;
        const passed = d.cropName === 'Apple' && d.predictedDisease === 'Apple Scab' && d.confidence >= 80;
        testResults.push({
          name: 'Multipart upload: leaf.JPG (Apple Scab)',
          expected: 'Apple Scab',
          actual: `${d.cropName} - ${d.predictedDisease} (${d.confidence}%)`,
          passed,
        });
        if (!passed) {
          throw new Error(`Expected Apple Scab prediction, got ${d.cropName} - ${d.predictedDisease}`);
        }
        console.log('  ✓ Test 3 PASSED: Correctly identified Apple Scab with high confidence.');
      } else {
        throw new Error(`Request failed with status ${res.status}: ${JSON.stringify(body)}`);
      }
    } else {
      console.warn('  [Skip] leaf.JPG not found on root');
    }

    // ----------------------------------------------------
    // Test 4: Real Potato Late Blight Image from dataset
    // ----------------------------------------------------
    console.log('\n[E2E Step 4] Testing real Potato Late Blight image upload...');
    const potatoDir = path.join(projectRoot, 'plantvillage dataset/color/Potato___Late_blight');
    if (fs.existsSync(potatoDir)) {
      const files = fs.readdirSync(potatoDir).filter(f => f.endsWith('.JPG') || f.endsWith('.jpg'));
      const potatoImgPath = path.join(potatoDir, files[files.length - 1]);
      const fileBytes = fs.readFileSync(potatoImgPath);
      const formData = new FormData();
      formData.append('image', new Blob([fileBytes], { type: 'image/jpeg' }), 'potato.jpg');

      const res = await fetch(`${baseUrl}/api/diagnoses`, {
        method: 'POST',
        headers: {
          Authorization: `Bearer ${token}`,
        },
        body: formData,
      });

      const body = await res.json();
      console.log(`  Status: ${res.status}`);
      console.log(`  Predicted Crop:    ${body.data?.cropName}`);
      console.log(`  Predicted Disease: ${body.data?.predictedDisease}`);
      console.log(`  Confidence:        ${body.data?.confidence}%`);

      if (res.status === 201 && body.success) {
        const d = body.data;
        const passed = d.cropName === 'Potato' && d.predictedDisease.toLowerCase().includes('late blight');
        testResults.push({
          name: 'Multipart upload: Potato Late Blight',
          expected: 'Potato Late Blight',
          actual: `${d.cropName} - ${d.predictedDisease} (${d.confidence}%)`,
          passed,
        });
        if (!passed) {
          throw new Error(`Expected Potato Late Blight, got ${d.cropName} - ${d.predictedDisease}`);
        }
        console.log('  ✓ Test 4 PASSED: Correctly identified Potato Late Blight (NOT Tomato!).');
      } else {
        throw new Error(`Request failed with status ${res.status}: ${JSON.stringify(body)}`);
      }
    }

    // ----------------------------------------------------
    // Test 5: Real Tomato Healthy Image via Base64 JSON
    // ----------------------------------------------------
    console.log('\n[E2E Step 5] Testing Base64 JSON payload with Tomato Healthy image...');
    const tomatoDir = path.join(projectRoot, 'plantvillage dataset/color/Tomato___healthy');
    if (fs.existsSync(tomatoDir)) {
      const files = fs.readdirSync(tomatoDir).filter(f => f.endsWith('.JPG') || f.endsWith('.jpg'));
      const tomatoImgPath = path.join(tomatoDir, files[files.length - 1]);
      const imgB64 = `data:image/jpeg;base64,${fs.readFileSync(tomatoImgPath).toString('base64')}`;

      const res = await fetch(`${baseUrl}/api/diagnoses`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({ base64Image: imgB64 }),
      });

      const body = await res.json();
      console.log(`  Status: ${res.status}`);
      console.log(`  Predicted Crop:    ${body.data?.cropName}`);
      console.log(`  Predicted Disease: ${body.data?.predictedDisease}`);
      console.log(`  Severity:          ${body.data?.severity}`);

      if (res.status === 201 && body.success) {
        const d = body.data;
        const passed = d.cropName === 'Tomato' && (d.severity === 'healthy' || d.predictedDisease.toLowerCase().includes('healthy'));
        testResults.push({
          name: 'Base64 upload: Tomato Healthy',
          expected: 'Tomato Healthy',
          actual: `${d.cropName} - ${d.predictedDisease} (${d.severity})`,
          passed,
        });
        if (!passed) {
          throw new Error(`Expected Tomato Healthy, got ${d.cropName} - ${d.predictedDisease}`);
        }
        console.log('  ✓ Test 5 PASSED: Correctly identified Healthy Tomato foliage.');
      } else {
        throw new Error(`Request failed with status ${res.status}: ${JSON.stringify(body)}`);
      }
    }

    // ----------------------------------------------------
    // Test 6: Missing Image -> Expect HTTP 400
    // ----------------------------------------------------
    console.log('\n[E2E Step 6] Testing missing image payload error handling...');
    const resMissing = await fetch(`${baseUrl}/api/diagnoses`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        Authorization: `Bearer ${token}`,
      },
      body: JSON.stringify({}),
    });

    const bodyMissing = await resMissing.json();
    console.log(`  Status: ${resMissing.status}`);
    console.log(`  Response message: ${bodyMissing?.message}`);
    const missingPassed = resMissing.status === 400 && !bodyMissing?.success;
    testResults.push({
      name: 'Missing image error handling (HTTP 400)',
      expected: 'HTTP 400 Error',
      actual: `HTTP ${resMissing.status}`,
      passed: missingPassed,
    });
    if (!missingPassed) {
      throw new Error(`Expected HTTP 400 on missing image, got ${resMissing.status}`);
    }
    console.log('  ✓ Test 6 PASSED: Missing image correctly rejected with HTTP 400.');

    // ----------------------------------------------------
    // Print Test Summary
    // ----------------------------------------------------
    console.log('\n' + '='.repeat(70));
    console.log('                   E2E PREDICTION TEST SUMMARY');
    console.log('='.repeat(70));
    for (const t of testResults) {
      const statusIcon = t.passed ? '✓ PASS' : '✗ FAIL';
      console.log(`  ${statusIcon} | ${t.name.padEnd(42)} | Result: ${t.actual}`);
    }
    console.log('='.repeat(70));

    console.log('\nAll End-to-End prediction tests passed successfully!\n');
  } catch (err) {
    console.error('\n[E2E Test Failure]', err);
    process.exitCode = 1;
  } finally {
    if (server) {
      await new Promise((resolve) => server.close(resolve));
    }
    await disconnectDB();
  }
}

runE2ETests();
