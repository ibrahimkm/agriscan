import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  User,
  Globe,
  Database,
  Cpu,
  Shield,
  HelpCircle,
  LogOut,
  RefreshCw,
  Check,
  WifiOff,
} from 'lucide-react';
import { useAuth } from '../context/AuthContext';
import { useConnectivity } from '../context/ConnectivityContext';
import { useLanguage } from '../context/LanguageContext';
import AppHeader from '../components/navigation/AppHeader';
import OfflineBanner from '../components/common/OfflineBanner';

export const ProfilePage = () => {
  const navigate = useNavigate();
  const { user, logout, updateProfile } = useAuth();
  const { isOnline, syncStatus, triggerSync, pendingCount } = useConnectivity();
  const { language, changeLanguage, t, availableLanguages } = useLanguage();

  const [syncing, setSyncing] = useState(false);

  const handleLanguageChange = (lang) => {
    changeLanguage(lang);
    updateProfile({ preferredLanguage: lang });
  };

  const handleManualSync = async () => {
    setSyncing(true);
    await triggerSync();
    setTimeout(() => setSyncing(false), 800);
  };

  return (
    <div className="min-h-screen bg-[#FAF8F5] pb-24 md:pb-8 select-none">
      <AppHeader title={t('profileSettings')} showBack backTo="/home" />
      <OfflineBanner />

      <main className="max-w-2xl mx-auto p-4 space-y-4">
        {/* User Card */}
        <div className="bg-white border border-[#EAE5DE] rounded-3xl p-5 shadow-xs flex items-center space-x-4">
          <img
            src={user?.avatar || 'https://images.unsplash.com/photo-1507003211169-0a1dd7228f2d?w=150&auto=format&fit=crop&q=80'}
            alt={user?.name || 'Farmer'}
            className="w-16 h-16 rounded-full object-cover border-2 border-[#D4A373] shadow-xs"
          />
          <div className="flex-1">
            <h2 className="text-lg font-bold text-[#14382B]">{user?.name || 'Ravi Sharma'}</h2>
            <p className="text-xs text-[#6B7280]">{user?.email || 'farmer@agriscan.io'}</p>
            <p className="text-xs text-[#C68B59] font-medium mt-0.5">
              {user?.location?.farmName || 'Surya Agro Farms'} · {user?.location?.region || 'Punjab, India'}
            </p>
          </div>
        </div>

        {/* Language Preferences (English, Hindi, Telugu, Tamil) */}
        <div className="bg-white border border-[#EAE5DE] rounded-3xl p-5 shadow-xs space-y-3">
          <div className="flex items-center space-x-2 text-[#14382B]">
            <Globe className="w-5 h-5 text-[#2D6A4F]" />
            <h3 className="text-sm font-bold">{t('languageDialect')}</h3>
          </div>

          <div className="grid grid-cols-2 gap-2.5 pt-1">
            {availableLanguages.map((item) => (
              <button
                key={item.code}
                onClick={() => handleLanguageChange(item.code)}
                className={`p-3.5 rounded-2xl border text-xs font-semibold flex items-center justify-between transition-all ${
                  language === item.code
                    ? 'border-[#14382B] bg-[#EDF7EE] text-[#14382B] ring-2 ring-[#14382B]/20 shadow-xs'
                    : 'border-[#EAE5DE] text-[#4B5563] hover:bg-[#FAF8F5]'
                }`}
              >
                <span>{item.native}</span>
                {language === item.code && <Check className="w-4 h-4 text-[#14382B] stroke-[2.5]" />}
              </button>
            ))}
          </div>
        </div>

        {/* Offline & Data Storage */}
        <div className="bg-white border border-[#EAE5DE] rounded-3xl p-5 shadow-xs space-y-3">
          <div className="flex items-center space-x-2 text-[#14382B]">
            <Database className="w-5 h-5 text-[#C68B59]" />
            <h3 className="text-sm font-bold">{t('offlineStorageTitle')}</h3>
          </div>

          <div className="space-y-2 text-xs text-[#4B5563]">
            <div className="flex items-center justify-between p-3.5 bg-[#FAF8F5] border border-[#EAE5DE] rounded-2xl">
              <div>
                <p className="font-bold text-[#14382B]">{t('localCache')}</p>
                <p className="text-[11px] text-[#6B7280]">
                  {pendingCount > 0
                    ? `${pendingCount} record(s) queued for sync`
                    : '100% Offline Capable · All records stored locally'}
                </p>
              </div>
              <button
                onClick={handleManualSync}
                disabled={syncing || !isOnline}
                className="flex items-center space-x-1 px-3 py-1.5 bg-[#14382B] text-white rounded-xl text-xs font-bold hover:bg-[#1B4332] transition-colors disabled:opacity-40"
              >
                <RefreshCw className={`w-3.5 h-3.5 ${syncing ? 'animate-spin' : ''}`} />
                <span>{t('syncNow')}</span>
              </button>
            </div>
          </div>
        </div>

        {/* Vision Models & Hardware */}
        <div className="bg-white border border-[#EAE5DE] rounded-3xl p-5 shadow-xs space-y-2.5">
          <div className="flex items-center space-x-2 text-[#14382B]">
            <Cpu className="w-5 h-5 text-[#2D6A4F]" />
            <h3 className="text-sm font-bold">{t('aiModelInfo')}</h3>
          </div>

          <div className="space-y-1.5 text-xs text-[#4B5563]">
            <div className="flex justify-between py-1 border-b border-[#F3F4F6]">
              <span>Classification Engine:</span>
              <span className="font-bold text-[#14382B]">AgriScan-Vision-v2.4-Hybrid</span>
            </div>
            <div className="flex justify-between py-1 border-b border-[#F3F4F6]">
              <span>Object Detection:</span>
              <span className="font-bold text-[#14382B]">YOLOv8x-OnDevice-Offline-v3.1</span>
            </div>
            <div className="flex justify-between py-1">
              <span>On-Device Inference Mode:</span>
              <span className="font-bold text-[#15803D]">100% Offline WebAssembly + WebGL Active</span>
            </div>
          </div>
        </div>

        {/* Logout Button */}
        <div className="pt-2">
          <button
            onClick={() => {
              logout();
              navigate('/login', { replace: true });
            }}
            className="w-full py-3.5 rounded-2xl border border-[#FCA5A5] text-[#DC2626] font-bold text-xs md:text-sm hover:bg-[#FEE2E2]/30 transition-colors flex items-center justify-center space-x-2"
          >
            <LogOut className="w-4 h-4" />
            <span>{t('signOut')}</span>
          </button>
        </div>
      </main>
    </div>
  );
};

export default ProfilePage;
