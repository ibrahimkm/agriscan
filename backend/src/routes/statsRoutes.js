import express from 'express';
import { getDashboardStats } from '../controllers/statsController.js';
import { protect } from '../middleware/auth.js';

const router = express.Router();

router.use(protect);
router.get('/stats', getDashboardStats);

export default router;
