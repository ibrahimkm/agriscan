import mongoose from 'mongoose';

const diseaseSchema = new mongoose.Schema(
  {
    diseaseName: {
      type: String,
      required: true,
      unique: true,
      trim: true,
    },
    scientificName: {
      type: String,
      trim: true,
    },
    cropTypes: [
      {
        type: String,
        required: true,
      },
    ],
    defaultSeverity: {
      type: String,
      enum: ['low', 'moderate', 'severe'],
      default: 'moderate',
    },
    microscopicImageUrl: {
      type: String,
    },
    sampleImageUrl: {
      type: String,
    },
    description: {
      type: String,
      required: true,
    },
    whyItHappens: {
      conditions: [String],
      pathogenSpread: String,
      optimalTemp: String,
      optimalHumidity: String,
    },
    symptoms: {
      summary: [String],
      onLeaves: String,
      onStems: String,
      onFruit: String,
    },
    immediateAction: {
      title: String,
      description: String,
      priority: {
        type: String,
        enum: ['Low Priority', 'Medium Priority', 'High Priority'],
        default: 'High Priority',
      },
    },
    treatmentSteps: [
      {
        id: String,
        title: String,
        description: String,
        category: { type: String, default: 'Chemical/Biological' },
      },
    ],
    preventionTips: [String],
    safetyNotice: {
      type: String,
      default: 'Always wear appropriate protective equipment when applying fungicides. Adhere strictly to the pre-harvest interval (PHI) specified on the product label before harvesting any fruit.',
    },
  },
  { timestamps: true }
);

export default mongoose.model('Disease', diseaseSchema);
