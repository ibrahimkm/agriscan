import express from 'express';
import {
  createDiagnosis,
  getDiagnoses,
  getDiagnosisById,
  getDiagnosesByCrop,
  toggleTreatmentStep,
} from '../controllers/diagnosisController.js';
import { protect } from '../middleware/auth.js';
import { upload } from '../middleware/upload.js';

const router = express.Router();

router.use(protect);

router.route('/')
  .get(getDiagnoses)
  .post(upload.single('image'), createDiagnosis);

router.route('/:id')
  .get(getDiagnosisById);

router.get('/crop/:cropId', getDiagnosesByCrop);
router.patch('/:id/steps/:stepId', toggleTreatmentStep);

export default router;
