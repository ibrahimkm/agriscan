import express from 'express';
import { getDiseases, getDiseaseById } from '../controllers/diseaseController.js';

const router = express.Router();

router.get('/', getDiseases);
router.get('/:id', getDiseaseById);

export default router;
