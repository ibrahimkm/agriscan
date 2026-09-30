import mongoose from 'mongoose';

const cropSchema = new mongoose.Schema(
  {
    userId: {
      type: mongoose.Schema.Types.ObjectId,
      ref: 'User',
      required: true,
    },
    cropName: {
      type: String,
      required: true,
      trim: true,
    },
    cropType: {
      type: String,
      required: true,
    },
    variety: {
      type: String,
      default: 'Standard Heirloom',
    },
    imageUrl: {
      type: String,
      required: true,
    },
    plantingDate: {
      type: Date,
      default: Date.now,
    },
    fieldInfo: {
      block: { type: String, default: 'Block A' },
      acreage: { type: Number, default: 2.5 },
      soilType: { type: String, default: 'Loamy' },
    },
    healthStatus: {
      type: String,
      enum: ['healthy', 'at_risk', 'diseased'],
      default: 'healthy',
    },
    diagnosesCount: {
      type: Number,
      default: 0,
    },
    lastDiagnosis: {
      date: { type: Date },
      diseaseName: { type: String },
      severity: { type: String },
    },
  },
  { timestamps: true }
);

export default mongoose.model('Crop', cropSchema);
