import express from 'express';
import {
  createDetection,
  getDetectionById,
  askDetectionQuestion,
} from '../controllers/detectionController.js';
import { protect } from '../middleware/auth.js';
import { upload } from '../middleware/upload.js';

const router = express.Router();

router.use(protect);

router.post('/', upload.single('image'), createDetection);
router.get('/:id', getDetectionById);
router.post('/:id/ask', askDetectionQuestion);

export default router;
