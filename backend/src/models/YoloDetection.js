import mongoose from 'mongoose';

const yoloDetectionSchema = new mongoose.Schema(
  {
    userId: {
      type: mongoose.Schema.Types.ObjectId,
      ref: 'User',
      required: true,
    },
    diagnosisId: {
      type: mongoose.Schema.Types.ObjectId,
      ref: 'Diagnosis',
    },
    cropName: {
      type: String,
      default: 'Tomato',
    },
    imageUrl: {
      type: String,
      required: true,
    },
    detections: [
      {
        classLabel: { type: String, required: true },
        confidence: { type: Number, required: true },
        severity: { type: String, enum: ['low', 'moderate', 'severe'], default: 'moderate' },
        boundingBox: {
          x: { type: Number, required: true }, // percentage 0-100 or 0-1
          y: { type: Number, required: true },
          width: { type: Number, required: true },
          height: { type: Number, required: true },
        },
      },
    ],
    overallSeverity: {
      type: String,
      enum: ['low', 'moderate', 'severe', 'healthy'],
      default: 'moderate',
    },
    affectedPercentage: {
      type: Number,
      default: 28,
    },
    modelVersion: {
      type: String,
      default: 'YOLOv8x-Agri-Disease-v3.1',
    },
    qaThread: [
      {
        question: { type: String, required: true },
        answer: { type: String, required: true },
        askedAt: { type: Date, default: Date.now },
        suggestedActions: [String],
      },
    ],
  },
  { timestamps: true }
);

export default mongoose.model('YoloDetection', yoloDetectionSchema);
