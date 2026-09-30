import React, { createContext, useContext, useState, useEffect } from 'react';
import { syncOfflineData } from '../services/syncManager';
import { getPendingSyncItems } from '../services/indexedDB';

const ConnectivityContext = createContext(null);

export const ConnectivityProvider = ({ children }) => {
  const [isOnline, setIsOnline] = useState(navigator.onLine);
  const [syncStatus, setSyncStatus] = useState('synced'); // 'synced' | 'syncing' | 'pending' | 'offline' | 'error'
  const [pendingCount, setPendingCount] = useState(0);

  const checkPending = async () => {
    try {
      const items = await getPendingSyncItems();
      setPendingCount(items ? items.length : 0);
      if (items && items.length > 0) {
        if (navigator.onLine) {
          triggerSync();
        } else {
          setSyncStatus('pending');
        }
      }
    } catch {
      // ignore
    }
  };

  const triggerSync = async () => {
    if (!navigator.onLine) {
      setSyncStatus('offline');
      return;
    }

    setSyncStatus('syncing');
    try {
      const res = await syncOfflineData();
      if (res.success) {
        setSyncStatus('synced');
        checkPending();
      } else {
        setSyncStatus('error');
      }
    } catch {
      setSyncStatus('error');
    }
  };

  useEffect(() => {
    const handleOnline = () => {
      setIsOnline(true);
      triggerSync();
    };

    const handleOffline = () => {
      setIsOnline(false);
      setSyncStatus('offline');
    };

    window.addEventListener('online', handleOnline);
    window.addEventListener('offline', handleOffline);

    checkPending();
    const interval = setInterval(checkPending, 30000);

    return () => {
      window.removeEventListener('online', handleOnline);
      window.removeEventListener('offline', handleOffline);
      clearInterval(interval);
    };
  }, []);

  return (
    <ConnectivityContext.Provider
      value={{
        isOnline,
        syncStatus,
        pendingCount,
        triggerSync,
        checkPending,
      }}
    >
      {children}
    </ConnectivityContext.Provider>
  );
};

export const useConnectivity = () => useContext(ConnectivityContext);
