import express from 'express';
import { getCrops, getCropById, createCrop, updateCrop, deleteCrop } from '../controllers/cropController.js';
import { protect } from '../middleware/auth.js';

const router = express.Router();

router.use(protect);

router.route('/')
  .get(getCrops)
  .post(createCrop);

router.route('/:id')
  .get(getCropById)
  .put(updateCrop)
  .delete(deleteCrop);

export default router;
