import mongoose from 'mongoose';
import bcrypt from 'bcryptjs';

const userSchema = new mongoose.Schema(
  {
    name: {
      type: String,
      required: [true, 'Please provide a name'],
      trim: true,
    },
    email: {
      type: String,
      required: [true, 'Please provide an email or phone'],
      unique: true,
      lowercase: true,
      trim: true,
    },
    phone: {
      type: String,
      trim: true,
    },
    passwordHash: {
      type: String,
      required: [true, 'Please provide a password hash'],
    },
    preferredLanguage: {
      type: String,
      enum: ['en', 'hi', 'es', 'sw', 'bn', 'mr'],
      default: 'en',
    },
    location: {
      farmName: { type: String, default: 'Green Valley Farm' },
      region: { type: String, default: 'Punjab, India' },
      climateZone: { type: String, default: 'Semi-arid' },
      latitude: { type: Number, default: 30.901 },
      longitude: { type: Number, default: 75.8573 },
    },
    avatar: {
      type: String,
      default: 'https://images.unsplash.com/photo-1507003211169-0a1dd7228f2d?w=150&auto=format&fit=crop&q=80',
    },
  },
  { timestamps: true }
);

userSchema.methods.matchPassword = async function (enteredPassword) {
  return await bcrypt.compare(enteredPassword, this.passwordHash);
};

export default mongoose.model('User', userSchema);
