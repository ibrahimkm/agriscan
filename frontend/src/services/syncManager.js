import api from './api';
import { getPendingSyncItems, clearSyncedQueue, markDiagnosisSynced } from './indexedDB';

export const syncOfflineData = async () => {
  try {
    const queueItems = await getPendingSyncItems();
    if (!queueItems || queueItems.length === 0) {
      return { success: true, count: 0 };
    }

    const diagnosesPayload = queueItems
      .filter((q) => q.type === 'diagnosis')
      .map((q) => q.data);

    const detectionsPayload = queueItems
      .filter((q) => q.type === 'detection')
      .map((q) => q.data);

    if (diagnosesPayload.length === 0 && detectionsPayload.length === 0) {
      return { success: true, count: 0 };
    }

    const response = await api.post('/sync', {
      diagnoses: diagnosesPayload,
      detections: detectionsPayload,
    });

    if (response.data.success) {
      // Mark synced in IndexedDB
      for (const res of response.data.syncedDiagnoses || []) {
        await markDiagnosisSynced(res.clientOfflineId, res.serverId);
      }

      // Clear processed queue IDs
      const queueIds = queueItems.map((q) => q.queueId);
      await clearSyncedQueue(queueIds);

      return {
        success: true,
        count: (response.data.syncedDiagnoses?.length || 0) + (response.data.syncedDetections?.length || 0),
      };
    }

    return { success: false, message: 'Sync rejected by server' };
  } catch (error) {
    console.error('[SyncManager Error]', error);
    return { success: false, error: error.message };
  }
};
