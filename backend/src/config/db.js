import mongoose from 'mongoose';
import { MongoMemoryServer } from 'mongodb-memory-server';

let mongodInstance = null;

export const connectDB = async () => {
  try {
    const mongoUri = process.env.MONGODB_URI;

    if (mongoUri) {
      try {
        const conn = await mongoose.connect(mongoUri, { serverSelectionTimeoutMS: 3000 });
        console.log(`[Database] MongoDB connected to custom URI: ${conn.connection.host}`);
        return conn;
      } catch (err) {
        console.warn(`[Database] Failed to connect to ${mongoUri}: ${err.message}. Falling back to embedded Mongo engine.`);
      }
    }

    // Try default local mongod first
    try {
      const conn = await mongoose.connect('mongodb://127.0.0.1:27017/agriscan', { serverSelectionTimeoutMS: 2000 });
      console.log(`[Database] Local MongoDB connected: ${conn.connection.host}`);
      return conn;
    } catch {
      console.log('[Database] Starting embedded Mongo engine (MongoMemoryServer)...');
      mongodInstance = await MongoMemoryServer.create();
      const uri = mongodInstance.getUri();
      const conn = await mongoose.connect(uri);
      console.log(`[Database] Embedded MongoDB initialized & connected at ${uri}`);
      return conn;
    }
  } catch (error) {
    console.error(`[Database Error] ${error.message}`);
    process.exit(1);
  }
};

export const disconnectDB = async () => {
  await mongoose.disconnect();
  if (mongodInstance) {
    await mongodInstance.stop();
  }
};
