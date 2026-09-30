import { openDB } from 'idb';

const DB_NAME = 'AgriScanOfflineDB';
const DB_VERSION = 1;

export const initDB = async () => {
  return openDB(DB_NAME, DB_VERSION, {
    upgrade(db) {
      // Offline diagnoses store
      if (!db.objectStoreNames.contains('diagnoses')) {
        const diagStore = db.createObjectStore('diagnoses', { keyPath: 'id' });
        diagStore.createIndex('syncStatus', 'syncStatus');
        diagStore.createIndex('createdAt', 'createdAt');
      }

      // Offline detections store
      if (!db.objectStoreNames.contains('detections')) {
        const detStore = db.createObjectStore('detections', { keyPath: 'id' });
        detStore.createIndex('syncStatus', 'syncStatus');
      }

      // Sync queue
      if (!db.objectStoreNames.contains('syncQueue')) {
        db.createObjectStore('syncQueue', { keyPath: 'queueId', autoIncrement: true });
      }
    },
  });
};

export const saveOfflineDiagnosis = async (diagnosis) => {
  const db = await initDB();
  const offlineRecord = {
    ...diagnosis,
    id: diagnosis.id || `offline_diag_${Date.now()}_${Math.random().toString(36).substr(2, 6)}`,
    syncStatus: 'pending',
    createdAt: diagnosis.createdAt || new Date().toISOString(),
  };

  await db.put('diagnoses', offlineRecord);
  await db.add('syncQueue', {
    type: 'diagnosis',
    data: offlineRecord,
    queuedAt: new Date().toISOString(),
  });

  return offlineRecord;
};

export const getOfflineDiagnoses = async () => {
  const db = await initDB();
  return db.getAllFromIndex('diagnoses', 'createdAt');
};

export const getPendingSyncItems = async () => {
  const db = await initDB();
  return db.getAll('syncQueue');
};

export const clearSyncedQueue = async (queueIds) => {
  const db = await initDB();
  const tx = db.transaction(['syncQueue', 'diagnoses'], 'readwrite');
  for (const qId of queueIds) {
    await tx.objectStore('syncQueue').delete(qId);
  }
  await tx.done;
};

export const markDiagnosisSynced = async (offlineId, serverId) => {
  const db = await initDB();
  const item = await db.get('diagnoses', offlineId);
  if (item) {
    item.syncStatus = 'synced';
    item._id = serverId;
    await db.put('diagnoses', item);
  }
};

export const clearOfflineDiagnoses = async () => {
  const db = await initDB();
  const tx = db.transaction(['diagnoses', 'syncQueue'], 'readwrite');
  await tx.objectStore('diagnoses').clear();
  await tx.objectStore('syncQueue').clear();
  await tx.done;
};

