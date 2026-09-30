import React from 'react';
import { WifiOff, RefreshCw } from 'lucide-react';
import { useConnectivity } from '../../context/ConnectivityContext';

export const OfflineBanner = () => {
  const { isOnline, syncStatus, triggerSync, pendingCount } = useConnectivity();

  if (isOnline && syncStatus !== 'error' && pendingCount === 0) return null;

  return (
    <div className="bg-[#FEF3C7] border-b border-[#FDE68A] px-4 py-2 text-xs text-[#92400E] flex items-center justify-between transition-all">
      <div className="flex items-center space-x-2">
        <WifiOff className="w-4 h-4 text-[#D97706] flex-shrink-0" />
        <span>
          {!isOnline
            ? 'Offline Mode — Scans are stored locally on your device.'
            : pendingCount > 0
            ? `${pendingCount} offline diagnosis ready to sync.`
            : 'Sync issue. Retrying connection...'}
        </span>
      </div>
      <button
        onClick={triggerSync}
        className="flex items-center space-x-1 px-2.5 py-1 bg-white hover:bg-[#FAF8F5] border border-[#FDE68A] rounded-lg font-semibold text-[#92400E] shadow-2xs transition-colors"
      >
        <RefreshCw className={`w-3 h-3 ${syncStatus === 'syncing' ? 'animate-spin' : ''}`} />
        <span>Sync Now</span>
      </button>
    </div>
  );
};

export default OfflineBanner;
