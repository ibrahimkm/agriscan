import { processBatchSync } from '../services/syncService.js';

export const batchSync = async (req, res, next) => {
  try {
    const { diagnoses = [], detections = [] } = req.body;

    if (!Array.isArray(diagnoses) && !Array.isArray(detections)) {
      return res.status(400).json({ success: false, message: 'Invalid payload. Array of diagnoses or detections required.' });
    }

    const result = await processBatchSync(req.user.id, { diagnoses, detections });
    res.json({
      success: true,
      ...result,
    });
  } catch (error) {
    next(error);
  }
};
