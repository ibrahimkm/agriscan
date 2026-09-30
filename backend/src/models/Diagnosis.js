import mongoose from 'mongoose';

const diagnosisSchema = new mongoose.Schema(
  {
    userId: {
      type: mongoose.Schema.Types.ObjectId,
      ref: 'User',
      required: true,
    },
    cropId: {
      type: mongoose.Schema.Types.ObjectId,
      ref: 'Crop',
    },
    cropName: {
      type: String,
      required: true,
    },
    cropVariety: {
      type: String,
    },
    fieldBlock: {
      type: String,
      default: 'Block A',
    },
    imageUrl: {
      type: String,
      required: true,
    },
    heatmapImageUrl: {
      type: String,
    },
    maskImageUrl: {
      type: String,
    },
    predictedDisease: {
      type: String,
      required: true,
    },
    scientificName: {
      type: String,
    },
    confidence: {
      type: Number,
      required: true,
      min: 0,
      max: 100,
    },
    severity: {
      type: String,
      enum: ['low', 'moderate', 'severe', 'healthy'],
      default: 'moderate',
    },
    affectedPercentage: {
      type: Number,
      default: 0,
    },
    whatIsIt: {
      type: String,
    },
    symptoms: [String],
    recommendedAction: {
      type: String,
    },
    immediateAction: {
      title: String,
      description: String,
      priority: String,
    },
    treatmentSteps: [
      {
        id: String,
        title: String,
        description: String,
        completed: { type: Boolean, default: false },
      },
    ],
    preventionTips: [String],
    safetyNotice: String,
    modelVersion: {
      type: String,
      default: 'AgriScan-Vision-v2.4-Hybrid',
    },
    diagnosisStatus: {
      type: String,
      enum: ['completed', 'failed', 'processing'],
      default: 'completed',
    },
    syncStatus: {
      type: String,
      enum: ['synced', 'pending'],
      default: 'synced',
    },
    clientOfflineId: {
      type: String,
    },
  },
  { timestamps: true }
);

export default mongoose.model('Diagnosis', diagnosisSchema);
