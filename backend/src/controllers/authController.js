import jwt from 'jsonwebtoken';
import bcrypt from 'bcryptjs';
import User from '../models/User.js';
import Crop from '../models/Crop.js';

const generateToken = (id) => {
  return jwt.sign({ id }, process.env.JWT_SECRET || 'agriscan_super_secret_jwt_key_2026', {
    expiresIn: '30d',
  });
};

export const register = async (req, res, next) => {
  try {
    const { name, email, phone, password, preferredLanguage, location } = req.body;

    if (!name || !email || !password) {
      return res.status(400).json({ success: false, message: 'Please provide name, email, and password' });
    }

    const userExists = await User.findOne({ email: email.toLowerCase() });
    if (userExists) {
      return res.status(400).json({ success: false, message: 'An account with this email already exists' });
    }

    const salt = await bcrypt.genSalt(10);
    const passwordHash = await bcrypt.hash(password, salt);

    const user = await User.create({
      name,
      email: email.toLowerCase(),
      phone: phone || '',
      passwordHash,
      preferredLanguage: preferredLanguage || 'en',
      location: location || {
        farmName: `${name}'s Farm`,
        region: 'Punjab, India',
        climateZone: 'Semi-arid',
      },
    });

    // Auto-create initial crops for the newly registered farmer
    await Crop.create([
      {
        userId: user._id,
        cropName: 'Tomato',
        cropType: 'Solanum lycopersicum',
        variety: 'Heirloom San Marzano',
        imageUrl: 'https://images.unsplash.com/photo-1592417817098-8f3d6eb2260f?w=400&auto=format&fit=crop&q=80',
        fieldInfo: { block: 'Block A', acreage: 2.0, soilType: 'Sandy Loam' },
        healthStatus: 'healthy',
        diagnosesCount: 0,
      },
      {
        userId: user._id,
        cropName: 'Wheat',
        cropType: 'Triticum aestivum',
        variety: 'Standard Cultivar',
        imageUrl: 'https://images.unsplash.com/photo-1574323347407-f5e1ad6d020b?w=400&auto=format&fit=crop&q=80',
        fieldInfo: { block: 'Block B', acreage: 4.5, soilType: 'Alluvial Soil' },
        healthStatus: 'healthy',
        diagnosesCount: 0,
      },
      {
        userId: user._id,
        cropName: 'Potato',
        cropType: 'Solanum tuberosum',
        variety: 'Kufri Jyoti',
        imageUrl: 'https://images.unsplash.com/photo-1518977676601-b53f82aba655?w=400&auto=format&fit=crop&q=80',
        fieldInfo: { block: 'Block C', acreage: 1.8, soilType: 'Silt Loam' },
        healthStatus: 'healthy',
        diagnosesCount: 0,
      },
    ]);

    res.status(201).json({
      success: true,
      token: generateToken(user._id),
      user: {
        id: user._id,
        name: user.name,
        email: user.email,
        phone: user.phone,
        preferredLanguage: user.preferredLanguage,
        location: user.location,
        avatar: user.avatar,
      },
    });
  } catch (error) {
    next(error);
  }
};

export const login = async (req, res, next) => {
  try {
    const { email, password } = req.body;

    if (!email || !password) {
      return res.status(400).json({ success: false, message: 'Please provide email and password' });
    }

    const user = await User.findOne({ email: email.toLowerCase() });
    if (!user) {
      return res.status(401).json({ success: false, message: 'Invalid email or password' });
    }

    const isMatch = await user.matchPassword(password);
    if (!isMatch) {
      return res.status(401).json({ success: false, message: 'Invalid email or password' });
    }

    res.json({
      success: true,
      token: generateToken(user._id),
      user: {
        id: user._id,
        name: user.name,
        email: user.email,
        phone: user.phone,
        preferredLanguage: user.preferredLanguage,
        location: user.location,
        avatar: user.avatar,
      },
    });
  } catch (error) {
    next(error);
  }
};

export const getMe = async (req, res, next) => {
  try {
    const user = await User.findById(req.user.id).select('-passwordHash');
    res.json({ success: true, user });
  } catch (error) {
    next(error);
  }
};

export const updateProfile = async (req, res, next) => {
  try {
    const { name, phone, preferredLanguage, location, avatar } = req.body;
    const user = await User.findById(req.user.id);

    if (!user) {
      return res.status(404).json({ success: false, message: 'User not found' });
    }

    if (name) user.name = name;
    if (phone) user.phone = phone;
    if (preferredLanguage) user.preferredLanguage = preferredLanguage;
    if (location) user.location = { ...user.location, ...location };
    if (avatar) user.avatar = avatar;

    await user.save();

    res.json({
      success: true,
      user: {
        id: user._id,
        name: user.name,
        email: user.email,
        phone: user.phone,
        preferredLanguage: user.preferredLanguage,
        location: user.location,
        avatar: user.avatar,
      },
    });
  } catch (error) {
    next(error);
  }
};
