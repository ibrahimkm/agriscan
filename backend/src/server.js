import express from 'express';
import cors from 'cors';
import morgan from 'morgan';
import dotenv from 'dotenv';
import path from 'path';
import { fileURLToPath } from 'url';
import { connectDB } from './config/db.js';
import { errorHandler } from './middleware/errorHandler.js';
import { seedDatabase } from './seed/seedData.js';
import User from './models/User.js';

// Route imports
import authRoutes from './routes/authRoutes.js';
import cropRoutes from './routes/cropRoutes.js';
import diseaseRoutes from './routes/diseaseRoutes.js';
import diagnosisRoutes from './routes/diagnosisRoutes.js';
import detectionRoutes from './routes/detectionRoutes.js';
import syncRoutes from './routes/syncRoutes.js';
import statsRoutes from './routes/statsRoutes.js';

dotenv.config();

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

const app = express();
const PORT = process.env.PORT || 5001;

// Middleware
app.use(cors({
  origin: '*',
  credentials: true,
}));
app.use(express.json({ limit: '50mb' }));
app.use(express.urlencoded({ extended: true, limit: '50mb' }));
app.use(morgan('dev'));

// Static uploads directory
const uploadsPath = path.join(__dirname, '../uploads');
app.use('/uploads', express.static(uploadsPath));

// Health check
app.get('/api/health', (req, res) => {
  res.json({
    status: 'healthy',
    service: 'AgriScan API Backend',
    version: '2.4.0',
    timestamp: new Date(),
  });
});

// API Routes
app.use('/api/auth', authRoutes);
app.use('/api/crops', cropRoutes);
app.use('/api/diseases', diseaseRoutes);
app.use('/api/diagnoses', diagnosisRoutes);
app.use('/api/detections', detectionRoutes);
app.use('/api/sync', syncRoutes);
app.use('/api/dashboard', statsRoutes);

// Centralized error handler
app.use(errorHandler);

// Bootstrap
const startServer = async () => {
  try {
    await connectDB();

    // Auto-seed if database has no users
    const userCount = await User.countDocuments();
    if (userCount === 0) {
      console.log('[Server] Database is empty. Running initial seed...');
      await seedDatabase();
    }

    app.listen(PORT, () => {
      console.log(`🌿 AgriScan Backend API running on http://localhost:${PORT}`);
    });
  } catch (error) {
    console.error('[Server Start Error]', error);
    process.exit(1);
  }
};

startServer();
