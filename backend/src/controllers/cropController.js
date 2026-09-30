import mongoose from 'mongoose';
import Crop from '../models/Crop.js';

export const getCrops = async (req, res, next) => {
  try {
    const { status, search } = req.query;
    let query = { userId: req.user.id };

    if (status && status !== 'all') {
      query.healthStatus = status.toLowerCase().replace(' ', '_');
    }

    if (search) {
      query.cropName = { $regex: search, $options: 'i' };
    }

    const crops = await Crop.find(query).sort({ updatedAt: -1 });
    res.json({ success: true, count: crops.length, data: crops });
  } catch (error) {
    next(error);
  }
};

export const getCropById = async (req, res, next) => {
  try {
    if (!mongoose.Types.ObjectId.isValid(req.params.id)) {
      return res.status(404).json({ success: false, message: 'Crop not found' });
    }

    const crop = await Crop.findOne({ _id: req.params.id, userId: req.user.id });
    if (!crop) {
      return res.status(404).json({ success: false, message: 'Crop not found' });
    }
    res.json({ success: true, data: crop });
  } catch (error) {
    next(error);
  }
};

export const createCrop = async (req, res, next) => {
  try {
    const { cropName, cropType, variety, imageUrl, fieldInfo, healthStatus } = req.body;

    const crop = await Crop.create({
      userId: req.user.id,
      cropName,
      cropType: cropType || cropName,
      variety: variety || 'Standard Cultivar',
      imageUrl: imageUrl || 'https://images.unsplash.com/photo-1592417817098-8f3d6eb2260f?w=400&auto=format&fit=crop&q=80',
      fieldInfo: fieldInfo || { block: 'Block A', acreage: 1.5, soilType: 'Loam' },
      healthStatus: healthStatus || 'healthy',
    });

    res.status(201).json({ success: true, data: crop });
  } catch (error) {
    next(error);
  }
};

export const updateCrop = async (req, res, next) => {
  try {
    if (!mongoose.Types.ObjectId.isValid(req.params.id)) {
      return res.status(404).json({ success: false, message: 'Crop not found' });
    }

    let crop = await Crop.findOne({ _id: req.params.id, userId: req.user.id });
    if (!crop) {
      return res.status(404).json({ success: false, message: 'Crop not found' });
    }

    crop = await Crop.findByIdAndUpdate(req.params.id, req.body, { new: true, runValidators: true });
    res.json({ success: true, data: crop });
  } catch (error) {
    next(error);
  }
};

export const deleteCrop = async (req, res, next) => {
  try {
    if (!mongoose.Types.ObjectId.isValid(req.params.id)) {
      return res.status(404).json({ success: false, message: 'Crop not found' });
    }

    const crop = await Crop.findOneAndDelete({ _id: req.params.id, userId: req.user.id });
    if (!crop) {
      return res.status(404).json({ success: false, message: 'Crop not found' });
    }
    res.json({ success: true, message: 'Crop deleted successfully' });
  } catch (error) {
    next(error);
  }
};

