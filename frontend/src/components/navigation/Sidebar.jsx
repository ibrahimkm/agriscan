import React from 'react';
import { NavLink, useLocation } from 'react-router-dom';
import {
  Home,
  Camera,
  Sprout,
  History,
  User,
  ScanSearch,
  BarChart3,
  Leaf,
  LogOut,
} from 'lucide-react';
import { useAuth } from '../../context/AuthContext';
import { useConnectivity } from '../../context/ConnectivityContext';
import { useLanguage } from '../../context/LanguageContext';

export const Sidebar = () => {
  const location = useLocation();
  const { user, logout } = useAuth();
  const { isOnline } = useConnectivity();
  const { t } = useLanguage();

  const navLinks = [
    { name: t('home'), path: '/home', icon: Home },
    { name: t('diagnose'), path: '/diagnose', icon: Camera, badge: 'Live AI' },
    { name: t('yoloTitle'), path: '/detections', icon: ScanSearch, badge: 'Offline' },
    { name: t('myCrops'), path: '/crops', icon: Sprout },
    { name: t('history'), path: '/history', icon: History },
    { name: t('analytics'), path: '/analytics', icon: BarChart3 },
    { name: t('profile'), path: '/profile', icon: User },
  ];

  return (
    <aside className="hidden md:flex flex-col w-64 lg:w-72 bg-white border-r border-[#EAE5DE] min-h-screen p-5 justify-between select-none">
      <div>
        {/* Brand Header */}
        <div className="flex items-center space-x-3 px-2 py-3 mb-6">
          <div className="w-10 h-10 rounded-2xl bg-[#14382B] flex items-center justify-center text-white shadow-md">
            <Leaf className="w-6 h-6 stroke-[2]" />
          </div>
          <div>
            <h1 className="text-xl font-bold tracking-tight text-[#14382B]">AgriScan</h1>
            <p className="text-xs text-[#6B7280] font-medium">100% Offline Crop AI</p>
          </div>
        </div>

        {/* Sync Pill */}
        <div className="mb-6 px-3 py-2 rounded-xl bg-[#FAF8F5] border border-[#EAE5DE] flex items-center justify-between">
          <div className="flex items-center space-x-2">
            <span
              className={`w-2.5 h-2.5 rounded-full ${
                isOnline ? 'bg-[#22C55E] ring-2 ring-[#DCFCE7]' : 'bg-[#D97706] ring-2 ring-[#FEF3C7]'
              }`}
            />
            <span className="text-xs font-semibold text-[#374151]">
              {isOnline ? t('cloudSynced') : t('offlineMode')}
            </span>
          </div>
          <span className="text-[10px] uppercase font-bold text-[#6B7280] bg-white px-2 py-0.5 rounded-md border border-[#EAE5DE]">
            v2.4
          </span>
        </div>

        {/* Navigation Links */}
        <nav className="space-y-1.5">
          {navLinks.map((item) => {
            const Icon = item.icon;
            const isActive = location.pathname === item.path;

            return (
              <NavLink
                key={item.path}
                to={item.path}
                className={`flex items-center justify-between px-3.5 py-2.5 rounded-xl text-sm font-medium transition-all ${
                  isActive
                    ? 'bg-[#14382B] text-white shadow-sm'
                    : 'text-[#4B5563] hover:bg-[#FAF8F5] hover:text-[#14382B]'
                }`}
              >
                <div className="flex items-center space-x-3">
                  <Icon className={`w-5 h-5 ${isActive ? 'text-white' : 'text-[#6B7280]'}`} />
                  <span>{item.name}</span>
                </div>
                {item.badge && (
                  <span
                    className={`text-[10px] font-bold px-1.5 py-0.5 rounded-md ${
                      isActive ? 'bg-[#2D6A4F] text-white' : 'bg-[#E8F5E9] text-[#1B4332]'
                    }`}
                  >
                    {item.badge}
                  </span>
                )}
              </NavLink>
            );
          })}
        </nav>
      </div>

      {/* User Footer */}
      <div className="pt-4 border-t border-[#EAE5DE]">
        <div className="flex items-center justify-between p-2 rounded-xl bg-[#FAF8F5]">
          <div className="flex items-center space-x-3 overflow-hidden">
            <img
              src={user?.avatar || 'https://images.unsplash.com/photo-1507003211169-0a1dd7228f2d?w=150&auto=format&fit=crop&q=80'}
              alt={user?.name || 'Farmer'}
              className="w-9 h-9 rounded-full object-cover border border-[#D4A373]"
            />
            <div className="truncate">
              <p className="text-xs font-bold text-[#14382B] truncate">{user?.name || 'Ravi Sharma'}</p>
              <p className="text-[10px] text-[#6B7280] truncate">{user?.location?.farmName || 'Surya Agro Farms'}</p>
            </div>
          </div>
          <button
            onClick={() => {
              logout();
              window.location.href = '/login';
            }}
            className="p-1.5 text-[#6B7280] hover:text-[#DC2626] hover:bg-white rounded-lg transition-colors"
            title="Log out"
          >
            <LogOut className="w-4 h-4" />
          </button>
        </div>
      </div>
    </aside>
  );
};

export default Sidebar;
