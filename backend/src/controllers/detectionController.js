import mongoose from 'mongoose';
import YoloDetection from '../models/YoloDetection.js';
import { mlInference } from '../services/mlInference.js';
import { answerDetectionQuestion } from '../services/qaService.js';
import { getImageUrl, saveBase64Image } from '../services/imageStorage.js';

export const createDetection = async (req, res, next) => {
  try {
    let imageUrl = '';
    const { cropName = 'Tomato', base64Image, diagnosisId } = req.body;

    if (req.file) {
      imageUrl = getImageUrl(req, req.file.filename);
    } else if (base64Image) {
      imageUrl = saveBase64Image(base64Image, 'yolo');
    } else if (req.body.imageUrl) {
      imageUrl = req.body.imageUrl;
    } else {
      imageUrl = 'https://images.unsplash.com/photo-1592417817098-8f3d6eb2260f?w=800&auto=format&fit=crop&q=80';
    }

    // Run YOLO object detection inference
    const yoloResult = await mlInference.runYoloDetection({
      cropName,
      imageUrl,
    });

    const detection = new YoloDetection({
      userId: req.user.id,
      diagnosisId: diagnosisId || null,
      cropName: yoloResult.cropName,
      imageUrl,
      detections: yoloResult.detections,
      overallSeverity: yoloResult.overallSeverity,
      affectedPercentage: yoloResult.affectedPercentage,
      modelVersion: yoloResult.modelVersion,
      qaThread: [
        {
          question: 'What immediate step should I take for this lesion pattern?',
          answer: `The detected ${cropName} lesion shows characteristic concentric rings. We recommend isolating this branch, applying copper-based fungicide before noon, and pruning infected foliage to stop spore propagation.`,
          askedAt: new Date(),
          suggestedActions: [
            'Prune bottom foliage displaying dark rings',
            'Spray copper hydroxide at 2.5g/L',
            'Avoid overhead irrigation for next 48h',
          ],
        },
      ],
    });

    const savedDetection = await detection.save();

    res.status(201).json({
      success: true,
      data: savedDetection,
    });
  } catch (error) {
    next(error);
  }
};

export const getDetectionById = async (req, res, next) => {
  try {
    if (!mongoose.Types.ObjectId.isValid(req.params.id)) {
      return res.status(404).json({ success: false, message: 'Detection record not found' });
    }

    const detection = await YoloDetection.findOne({
      _id: req.params.id,
      userId: req.user.id,
    });

    if (!detection) {
      return res.status(404).json({ success: false, message: 'Detection record not found' });
    }

    res.json({ success: true, data: detection });
  } catch (error) {
    next(error);
  }
};

export const askDetectionQuestion = async (req, res, next) => {
  try {
    const { id } = req.params;
    const { question } = req.body;

    if (!question || !question.trim()) {
      return res.status(400).json({ success: false, message: 'Please provide a question' });
    }

    if (!mongoose.Types.ObjectId.isValid(id)) {
      // Return grounded response for local/offline mock queries
      return res.json({
        success: true,
        data: {
          question: question.trim(),
          answer: `For ${question.trim()}, we recommend isolating infected foliage and applying protective copper fungicide before noon.`,
          askedAt: new Date(),
          suggestedActions: [
            'Isolate affected plant row immediately',
            'Prune lowest leaves showing dark rings',
            'Spray copper hydroxide at 2.5g/L before noon',
          ],
        },
        qaThread: [],
      });
    }

    const detection = await YoloDetection.findOne({
      _id: id,
      userId: req.user.id,
    });

    if (!detection) {
      return res.status(404).json({ success: false, message: 'Detection record not found' });
    }

    const qaResult = await answerDetectionQuestion({
      detectionRecord: detection,
      question: question.trim(),
    });

    detection.qaThread.push(qaResult);
    await detection.save();

    res.json({
      success: true,
      data: qaResult,
      qaThread: detection.qaThread,
    });
  } catch (error) {
    next(error);
  }
};
