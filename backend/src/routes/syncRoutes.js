import express from 'express';
import { batchSync } from '../controllers/syncController.js';
import { protect } from '../middleware/auth.js';

const router = express.Router();

router.use(protect);
router.post('/', batchSync);

export default router;
