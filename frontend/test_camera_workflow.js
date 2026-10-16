#!/usr/bin/env node
/**
 * Automated Verification of Frontend Camera & Prediction Workflow
 * Verifies:
 * 1. Absence of hardcoded Unsplash image placeholders in DiagnosePage & AnalysisPage
 * 2. Proper getUserMedia integration with facingMode environment
 * 3. Camera permission denial and unsupported device handling
 * 4. Safe neutral badges in DiagnosePage (no default Tomato)
 * 5. LanguageContext step2Sub neutral foliar pathology text
 * 6. AnalysisPage real backend prediction dispatch
 */

import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const projectRoot = path.resolve(__dirname, '..');

const diagnosePagePath = path.join(__dirname, 'src/pages/DiagnosePage.jsx');
const analysisPagePath = path.join(__dirname, 'src/pages/AnalysisPage.jsx');
const localMLPath = path.join(__dirname, 'src/services/localMLInference.js');
const languageContextPath = path.join(__dirname, 'src/context/LanguageContext.jsx');
const cameraCapturePath = path.join(__dirname, 'src/components/camera/CameraCapture.jsx');
const scanAnimationPath = path.join(__dirname, 'src/components/diagnosis/ScanAnimation.jsx');

console.log('='.repeat(70));
console.log('     AGRISCAN FRONTEND CAMERA & INFERENCE INTEGRITY SUITE');
console.log('='.repeat(70));

const tests = [];

function test(name, fn) {
  try {
    fn();
    tests.push({ name, passed: true });
    console.log(`  ✓ PASS | ${name}`);
  } catch (err) {
    tests.push({ name, passed: false, error: err.message });
    console.error(`  ✗ FAIL | ${name}: ${err.message}`);
  }
}

// 1. DiagnosePage checks
test('DiagnosePage has no hardcoded Unsplash sample image URL', () => {
  const content = fs.readFileSync(diagnosePagePath, 'utf8');
  if (content.includes('images.unsplash.com')) {
    throw new Error('DiagnosePage still contains hardcoded Unsplash image URL!');
  }
});

test('DiagnosePage does not default selectedCrop to Tomato', () => {
  const content = fs.readFileSync(diagnosePagePath, 'utf8');
  if (content.includes("selectedCrop || 'Tomato'") || content.includes('selectedCrop = "Tomato"')) {
    throw new Error('DiagnosePage still has hardcoded selectedCrop || Tomato default!');
  }
});

test('DiagnosePage implements navigator.mediaDevices.getUserMedia with environment facingMode', () => {
  const content = fs.readFileSync(diagnosePagePath, 'utf8');
  if (!content.includes('navigator?.mediaDevices?.getUserMedia') && !content.includes('navigator.mediaDevices.getUserMedia')) {
    throw new Error('DiagnosePage lacks navigator.mediaDevices.getUserMedia call!');
  }
  if (!content.includes("'environment'") && !content.includes('"environment"')) {
    throw new Error('DiagnosePage does not request rear-facing environment camera!');
  }
});

test('DiagnosePage handles camera permission denial and unsupported devices', () => {
  const content = fs.readFileSync(diagnosePagePath, 'utf8');
  if (!content.includes('NotAllowedError') && !content.includes('PermissionDeniedError')) {
    throw new Error('DiagnosePage lacks NotAllowedError / PermissionDeniedError handler!');
  }
  if (!content.includes('unsupported')) {
    throw new Error('DiagnosePage lacks unsupported camera state handling!');
  }
});

test('DiagnosePage captures video frames to canvas without sending placeholders', () => {
  const content = fs.readFileSync(diagnosePagePath, 'utf8');
  if (!content.includes('canvas.getContext') || !content.includes('ctx.drawImage')) {
    throw new Error('DiagnosePage does not draw real video frame onto canvas!');
  }
  if (!content.includes('canvas.toDataURL')) {
    throw new Error('DiagnosePage does not convert canvas to image data URL!');
  }
});

// 2. AnalysisPage checks
test('AnalysisPage has no hardcoded Unsplash sample image URL', () => {
  const content = fs.readFileSync(analysisPagePath, 'utf8');
  if (content.includes('images.unsplash.com')) {
    throw new Error('AnalysisPage still contains hardcoded Unsplash image URL!');
  }
});

test('AnalysisPage awaits real backend POST /diagnoses response', () => {
  const content = fs.readFileSync(analysisPagePath, 'utf8');
  if (!content.includes("await api.post('/diagnoses'")) {
    throw new Error("AnalysisPage does not await api.post('/diagnoses')!");
  }
});

// 3. ScanAnimation checks
test('ScanAnimation does not fall back to Unsplash URL', () => {
  const content = fs.readFileSync(scanAnimationPath, 'utf8');
  if (content.includes('images.unsplash.com')) {
    throw new Error('ScanAnimation still contains hardcoded Unsplash image URL!');
  }
});

// 4. localMLInference checks
test('localMLInference does not fall back to hardcoded Tomato Early Blight', () => {
  const content = fs.readFileSync(localMLPath, 'utf8');
  if (content.includes("diseaseKey = 'Early Blight'") && content.includes("cropName.toLowerCase().includes('tomato')")) {
    throw new Error('localMLInference still has hardcoded Early Blight fallback rule!');
  }
});

// 5. LanguageContext step2Sub checks
test('LanguageContext step2Sub contains neutral foliar analysis text across languages', () => {
  const content = fs.readFileSync(languageContextPath, 'utf8');
  if (content.includes('Confirmed as Solanum lycopersicum (Tomato).')) {
    throw new Error('LanguageContext English step2Sub still hardcodes Tomato!');
  }
  if (content.includes('टमाटर (Solanum lycopersicum) के रूप में सत्यापित।')) {
    throw new Error('LanguageContext Hindi step2Sub still hardcodes Tomato!');
  }
});

// 6. CameraCapture component checks
test('CameraCapture component does not contain sampleLeaves array or Unsplash URL', () => {
  const content = fs.readFileSync(cameraCapturePath, 'utf8');
  if (content.includes('sampleLeaves') || content.includes('images.unsplash.com')) {
    throw new Error('CameraCapture still contains sampleLeaves / Unsplash URLs!');
  }
});

console.log('='.repeat(70));
const total = tests.length;
const passed = tests.filter(t => t.passed).length;
console.log(`Summary: ${passed}/${total} frontend integrity tests passed.`);
console.log('='.repeat(70));

if (passed !== total) {
  process.exit(1);
}
