import mongoose from 'mongoose';
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
      const offlineId = item.id || item.clientOfflineId;

      // Check if this diagnosis already exists in the database
      let existingDoc = null;
      if (item._id && mongoose.Types.ObjectId.isValid(item._id)) {
        existingDoc = await Diagnosis.findOne({ _id: item._id, userId });
      } else if (offlineId) {
        existingDoc = await Diagnosis.findOne({
          userId,
          $or: [{ clientOfflineId: offlineId }, { _id: mongoose.Types.ObjectId.isValid(offlineId) ? offlineId : null }],
        });
      }

      if (existingDoc) {
        syncedDiagnoses.push({
          clientOfflineId: offlineId,
          serverId: existingDoc._id,
          status: 'synced',
        });
        continue;
      }

      let cropDoc = null;
      if (item.cropId && mongoose.Types.ObjectId.isValid(item.cropId)) {
        cropDoc = await Crop.findOne({ _id: item.cropId, userId });
      } else if (item.cropName) {
        const escapedCrop = item.cropName.replace(/[-[\]{}()*+?.,\\^$|#\s]/g, '\\$&');
        cropDoc = await Crop.findOne({ userId, cropName: { $regex: escapedCrop, $options: 'i' } });
      }

      // Clone item and strip client _id to avoid duplicate key conflicts
      const { _id, ...cleanItem } = item;

      const diagnosis = new Diagnosis({
        ...cleanItem,
        userId,
        cropId: cropDoc?._id || (item.cropId && mongoose.Types.ObjectId.isValid(item.cropId) ? item.cropId : undefined),
        syncStatus: 'synced',
        clientOfflineId: offlineId,
      });

      const saved = await diagnosis.save();
      syncedDiagnoses.push({
        clientOfflineId: offlineId,
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
