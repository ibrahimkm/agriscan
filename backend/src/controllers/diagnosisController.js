import mongoose from 'mongoose';
import Diagnosis from '../models/Diagnosis.js';
import Crop from '../models/Crop.js';
import { mlInference } from '../services/mlInference.js';
import { getImageUrl, saveBase64Image } from '../services/imageStorage.js';

export const createDiagnosis = async (req, res, next) => {
  try {
    let imageUrl = '';
    const { cropName = 'Tomato', cropId, fieldBlock = 'Block A', base64Image, clientOfflineId } = req.body;

    if (req.file) {
      imageUrl = getImageUrl(req, req.file.filename);
    } else if (base64Image) {
      imageUrl = saveBase64Image(base64Image, 'scan');
    } else if (req.body.imageUrl) {
      imageUrl = req.body.imageUrl;
    } else {
      imageUrl = 'https://images.unsplash.com/photo-1592417817098-8f3d6eb2260f?w=800&auto=format&fit=crop&q=80';
    }

    // Run ML inference
    const inferenceResult = await mlInference.runDiseaseDiagnosis({
      cropName,
      imageUrl,
      fieldBlock,
    });

    // Check crop reference
    let cropDoc = null;
    if (cropId && mongoose.Types.ObjectId.isValid(cropId)) {
      cropDoc = await Crop.findOne({ _id: cropId, userId: req.user.id });
    } else {
      cropDoc = await Crop.findOne({ cropName: { $regex: cropName, $options: 'i' }, userId: req.user.id });
    }

    // Create diagnosis record
    const diagnosis = new Diagnosis({
      userId: req.user.id,
      cropId: cropDoc?._id || cropId,
      cropName: inferenceResult.cropName,
      cropVariety: inferenceResult.cropVariety,
      fieldBlock: inferenceResult.fieldBlock,
      imageUrl,
      predictedDisease: inferenceResult.predictedDisease,
      scientificName: inferenceResult.scientificName,
      confidence: inferenceResult.confidence,
      severity: inferenceResult.severity,
      affectedPercentage: inferenceResult.affectedPercentage,
      whatIsIt: inferenceResult.whatIsIt,
      symptoms: inferenceResult.symptoms,
      recommendedAction: inferenceResult.recommendedAction,
      immediateAction: inferenceResult.immediateAction,
      treatmentSteps: inferenceResult.treatmentSteps,
      preventionTips: inferenceResult.preventionTips,
      safetyNotice: inferenceResult.safetyNotice,
      modelVersion: inferenceResult.modelVersion,
      diagnosisStatus: 'completed',
      syncStatus: 'synced',
      clientOfflineId,
    });

    const savedDiagnosis = await diagnosis.save();

    // Update crop health record
    if (cropDoc) {
      cropDoc.healthStatus = diagnosis.severity === 'healthy' ? 'healthy' : diagnosis.severity === 'severe' ? 'diseased' : 'at_risk';
      cropDoc.diagnosesCount = (cropDoc.diagnosesCount || 0) + 1;
      cropDoc.lastDiagnosis = {
        date: savedDiagnosis.createdAt,
        diseaseName: savedDiagnosis.predictedDisease,
        severity: savedDiagnosis.severity,
      };
      await cropDoc.save();
    }

    res.status(201).json({
      success: true,
      data: savedDiagnosis,
    });
  } catch (error) {
    next(error);
  }
};

export const getDiagnoses = async (req, res, next) => {
  try {
    const { cropId, status, limit = 50 } = req.query;
    let query = { userId: req.user.id };

    if (cropId && mongoose.Types.ObjectId.isValid(cropId)) query.cropId = cropId;
    if (status && status !== 'all') query.severity = status;

    const diagnoses = await Diagnosis.find(query)
      .sort({ createdAt: -1 })
      .limit(parseInt(limit, 10))
      .populate('cropId', 'cropName variety healthStatus');

    res.json({
      success: true,
      count: diagnoses.length,
      data: diagnoses,
    });
  } catch (error) {
    next(error);
  }
};

export const getDiagnosisById = async (req, res, next) => {
  try {
    if (!mongoose.Types.ObjectId.isValid(req.params.id)) {
      return res.status(404).json({ success: false, message: 'Diagnosis record not found' });
    }

    const diagnosis = await Diagnosis.findOne({
      _id: req.params.id,
      userId: req.user.id,
    }).populate('cropId');

    if (!diagnosis) {
      return res.status(404).json({ success: false, message: 'Diagnosis record not found' });
    }

    res.json({ success: true, data: diagnosis });
  } catch (error) {
    next(error);
  }
};

export const getDiagnosesByCrop = async (req, res, next) => {
  try {
    if (!mongoose.Types.ObjectId.isValid(req.params.cropId)) {
      return res.json({ success: true, count: 0, data: [] });
    }

    const diagnoses = await Diagnosis.find({
      cropId: req.params.cropId,
      userId: req.user.id,
    }).sort({ createdAt: -1 });

    res.json({ success: true, count: diagnoses.length, data: diagnoses });
  } catch (error) {
    next(error);
  }
};

export const toggleTreatmentStep = async (req, res, next) => {
  try {
    const { id, stepId } = req.params;
    if (!mongoose.Types.ObjectId.isValid(id)) {
      return res.status(404).json({ success: false, message: 'Diagnosis record not found' });
    }

    const diagnosis = await Diagnosis.findOne({ _id: id, userId: req.user.id });

    if (!diagnosis) {
      return res.status(404).json({ success: false, message: 'Diagnosis record not found' });
    }

    const step = diagnosis.treatmentSteps.find((s) => s.id === stepId || s._id?.toString() === stepId);
    if (step) {
      step.completed = !step.completed;
      await diagnosis.save();
    }

    res.json({ success: true, data: diagnosis });
  } catch (error) {
    next(error);
  }
};
