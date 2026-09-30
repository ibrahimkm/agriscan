import Diagnosis from '../models/Diagnosis.js';
import YoloDetection from '../models/YoloDetection.js';
import Crop from '../models/Crop.js';

export const processBatchSync = async (userId, syncPayload) => {
  const { diagnoses = [], detections = [] } = syncPayload;
  const syncedDiagnoses = [];
  const syncedDetections = [];
  const errors = [];

  // Process offline diagnoses
  for (const item of diagnoses) {
    try {
      let cropDoc = null;
      if (item.cropId) {
        cropDoc = await Crop.findById(item.cropId);
      } else if (item.cropName) {
        cropDoc = await Crop.findOne({ userId, cropName: item.cropName });
      }

      const diagnosis = new Diagnosis({
        ...item,
        userId,
        cropId: cropDoc?._id || item.cropId,
        syncStatus: 'synced',
        clientOfflineId: item.id || item.clientOfflineId,
      });

      const saved = await diagnosis.save();
      syncedDiagnoses.push({
        clientOfflineId: item.id || item.clientOfflineId,
        serverId: saved._id,
        status: 'synced',
      });

      // Update crop health status if applicable
      if (cropDoc) {
        cropDoc.healthStatus = item.severity === 'healthy' ? 'healthy' : item.severity === 'severe' ? 'diseased' : 'at_risk';
        cropDoc.diagnosesCount = (cropDoc.diagnosesCount || 0) + 1;
        cropDoc.lastDiagnosis = {
          date: saved.createdAt,
          diseaseName: saved.predictedDisease,
          severity: saved.severity,
        };
        await cropDoc.save();
      }
    } catch (err) {
      errors.push({ type: 'diagnosis', id: item.id, error: err.message });
    }
  }

  // Process offline detections
  for (const item of detections) {
    try {
      const detection = new YoloDetection({
        ...item,
        userId,
      });
      const saved = await detection.save();
      syncedDetections.push({
        clientOfflineId: item.id || item.clientOfflineId,
        serverId: saved._id,
        status: 'synced',
      });
    } catch (err) {
      errors.push({ type: 'detection', id: item.id, error: err.message });
    }
  }

  return {
    success: errors.length === 0,
    syncedDiagnoses,
    syncedDetections,
    errors,
    syncedAt: new Date(),
  };
};
