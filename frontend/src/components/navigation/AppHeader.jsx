import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Menu,
  ArrowLeft,
  Cloud,
  CloudOff,
  RefreshCw,
  User,
  X,
  CheckCircle2,
  Database,
  Wifi,
  WifiOff,
} from 'lucide-react';
import { useConnectivity } from '../../context/ConnectivityContext';
import { useAuth } from '../../context/AuthContext';

export const AppHeader = ({ title = 'AgriScan', showBack = false, onBack, rightAction, backTo = '/home' }) => {
  const navigate = useNavigate();
  const { user } = useAuth();
  const { isOnline, syncStatus, triggerSync, pendingCount } = useConnectivity();
  const [showSyncModal, setShowSyncModal] = useState(false);
  const [isManualSyncing, setIsManualSyncing] = useState(false);

  const handleBack = () => {
    if (onBack) {
      onBack();
    } else {
      navigate(backTo);
    }
  };

  const handleTriggerManualSync = async () => {
    setIsManualSyncing(true);
    await triggerSync();
    setTimeout(() => {
      setIsManualSyncing(false);
    }, 600);
  };

  return (
    <>
      <header className="sticky top-0 z-40 bg-[#FAF8F5]/90 backdrop-blur-md border-b border-[#EAE5DE] px-4 py-3 flex items-center justify-between select-none">
        <div className="flex items-center space-x-3">
          {showBack ? (
            <button
              onClick={handleBack}
              className="p-1.5 -ml-1 text-[#14382B] hover:bg-[#EAE5DE]/60 rounded-full transition-colors"
              aria-label="Go Back"
            >
              <ArrowLeft className="w-5 h-5 stroke-[2.2]" />
            </button>
          ) : (
            <button
              onClick={() => navigate('/profile')}
              className="p-1.5 -ml-1 text-[#14382B] hover:bg-[#EAE5DE]/60 rounded-full transition-colors flex items-center space-x-1.5"
              aria-label="Open Profile"
              title="View Farmer Profile"
            >
              <Menu className="w-6 h-6 stroke-[2]" />
            </button>
          )}
          {showBack && title !== 'AgriScan' && (
            <span className="text-xs font-semibold uppercase tracking-wider text-[#6B7280]">
              {title}
            </span>
          )}
        </div>

        <div className="absolute left-1/2 -translate-x-1/2">
          <button
            onClick={() => navigate('/home')}
            className="text-lg md:text-xl font-bold tracking-tight text-[#14382B] font-sans hover:opacity-80 transition-opacity"
          >
            {title === 'AgriScan' || !showBack ? 'AgriScan' : title}
          </button>
        </div>

        <div className="flex items-center space-x-1.5">
          {rightAction ? (
            rightAction
          ) : (
            <>
              {/* Cloud Sync Icon Button */}
              <button
                onClick={() => setShowSyncModal(true)}
                title="View Cloud Sync Status"
                className="relative p-1.5 text-[#14382B] hover:bg-[#EAE5DE]/60 rounded-full transition-colors"
              >
                {syncStatus === 'syncing' || isManualSyncing ? (
                  <RefreshCw className="w-5 h-5 animate-spin text-[#2D6A4F]" />
                ) : isOnline ? (
                  <div className="relative">
                    <Cloud className="w-5 h-5 stroke-[1.8]" />
                    <span className="absolute -top-0.5 -right-0.5 w-2 h-2 rounded-full bg-[#22C55E] border-2 border-[#FAF8F5]" />
                  </div>
                ) : (
                  <div className="relative text-[#D97706]">
                    <CloudOff className="w-5 h-5 stroke-[1.8]" />
                    <span className="absolute -top-0.5 -right-0.5 w-2 h-2 rounded-full bg-[#D97706] border-2 border-[#FAF8F5]" />
                  </div>
                )}
              </button>

              {/* Profile Avatar / Icon */}
              <button
                onClick={() => navigate('/profile')}
                title="Farmer Profile & Settings"
                className="p-1 hover:ring-2 hover:ring-[#14382B]/20 rounded-full transition-all"
              >
                {user?.avatar ? (
                  <img
                    src={user.avatar}
                    alt={user.name || 'Profile'}
                    className="w-7 h-7 rounded-full object-cover border border-[#D4A373]"
                  />
                ) : (
                  <div className="w-7 h-7 rounded-full bg-[#14382B] text-white flex items-center justify-center text-xs font-bold">
                    <User className="w-4 h-4" />
                  </div>
                )}
              </button>
            </>
          )}
        </div>
      </header>

      {/* Cloud Sync & Connectivity Modal Dialog */}
      {showSyncModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/50 backdrop-blur-xs animate-fade-in select-none">
          <div className="bg-white border border-[#EAE5DE] rounded-3xl p-5 max-w-sm w-full shadow-2xl space-y-4">
            <div className="flex items-center justify-between border-b border-[#F3F4F6] pb-3">
              <div className="flex items-center space-x-2">
                <div className="w-8 h-8 rounded-xl bg-[#E8F5E9] text-[#14382B] flex items-center justify-center">
                  <Cloud className="w-4 h-4" />
                </div>
                <div>
                  <h3 className="text-sm font-bold text-[#14382B]">Cloud Synchronization</h3>
                  <p className="text-[11px] text-[#6B7280]">AgriScan Offline-First Network</p>
                </div>
              </div>
              <button
                onClick={() => setShowSyncModal(false)}
                className="p-1.5 text-[#9CA3AF] hover:text-[#14382B] rounded-lg transition-colors"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            {/* Network State Card */}
            <div className="p-3 rounded-2xl bg-[#FAF8F5] border border-[#EAE5DE] space-y-2 text-xs">
              <div className="flex items-center justify-between">
                <span className="font-semibold text-[#4B5563]">Connectivity:</span>
                <div className="flex items-center space-x-1.5 font-bold">
                  {isOnline ? (
                    <>
                      <Wifi className="w-4 h-4 text-[#15803D]" />
                      <span className="text-[#15803D]">Online (Connected)</span>
                    </>
                  ) : (
                    <>
                      <WifiOff className="w-4 h-4 text-[#D97706]" />
                      <span className="text-[#D97706]">Offline Mode</span>
                    </>
                  )}
                </div>
              </div>

              <div className="flex items-center justify-between">
                <span className="font-semibold text-[#4B5563]">Pending Uploads:</span>
                <span className="font-bold text-[#14382B]">
                  {pendingCount} diagnosis record(s)
                </span>
              </div>

              <div className="flex items-center justify-between">
                <span className="font-semibold text-[#4B5563]">Status:</span>
                <span className="font-bold text-[#14382B] capitalize">
                  {syncStatus === 'syncing' ? 'Synchronizing...' : syncStatus}
                </span>
              </div>
            </div>

            {/* Sync Action */}
            <div className="space-y-2 pt-1">
              <button
                onClick={handleTriggerManualSync}
                disabled={isManualSyncing || !isOnline}
                className="w-full py-3 rounded-2xl bg-[#14382B] text-white font-bold text-xs md:text-sm shadow-md hover:bg-[#1B4332] active:scale-[0.99] transition-all flex items-center justify-center space-x-2 disabled:opacity-50"
              >
                <RefreshCw className={`w-4 h-4 ${isManualSyncing ? 'animate-spin' : ''}`} />
                <span>{isManualSyncing ? 'Syncing with Cloud...' : 'Sync Now'}</span>
              </button>

              <button
                onClick={() => setShowSyncModal(false)}
                className="w-full py-2.5 rounded-2xl border border-[#EAE5DE] text-[#6B7280] font-semibold text-xs hover:bg-[#FAF8F5] transition-colors"
              >
                Close
              </button>
            </div>
          </div>
        </div>
      )}
    </>
  );
};

export default AppHeader;
