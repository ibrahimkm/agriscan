import React from 'react';
import { NavLink, useLocation } from 'react-router-dom';
import { Home, Camera, Sprout, History, User } from 'lucide-react';
import { useLanguage } from '../../context/LanguageContext';

export const BottomNavigation = () => {
  const location = useLocation();
  const { t } = useLanguage();

  const navItems = [
    { name: t('home'), path: '/home', icon: Home },
    { name: t('diagnose'), path: '/diagnose', icon: Camera, isPrimary: true },
    { name: t('myCrops'), path: '/crops', icon: Sprout },
    { name: t('history'), path: '/history', icon: History },
    { name: t('profile'), path: '/profile', icon: User },
  ];

  return (
    <nav className="md:hidden fixed bottom-0 left-0 right-0 z-40 bg-white/95 backdrop-blur-lg border-t border-[#EAE5DE] px-3 py-2 shadow-[0_-4px_16px_rgba(0,0,0,0.03)] select-none">
      <div className="max-w-md mx-auto flex items-center justify-around">
        {navItems.map((item) => {
          const Icon = item.icon;
          const isActive =
            location.pathname === item.path ||
            (item.path === '/crops' && location.pathname.startsWith('/crops')) ||
            (item.path === '/profile' && location.pathname.startsWith('/profile'));

          if (item.isPrimary) {
            return (
              <NavLink
                key={item.path}
                to={item.path}
                className="flex flex-col items-center group -mt-5"
              >
                <div
                  className={`w-14 h-12 rounded-2xl flex items-center justify-center shadow-lg transition-all duration-200 ${
                    isActive
                      ? 'bg-[#14382B] text-white ring-4 ring-[#E8F5E9]'
                      : 'bg-[#1B4332] text-white hover:bg-[#14382B]'
                  }`}
                >
                  <Icon className="w-6 h-6 stroke-[2]" />
                </div>
                <span
                  className={`text-[10px] font-semibold mt-1 transition-colors ${
                    isActive ? 'text-[#14382B]' : 'text-[#6B7280]'
                  }`}
                >
                  {item.name}
                </span>
              </NavLink>
            );
          }

          return (
            <NavLink
              key={item.path}
              to={item.path}
              className={`flex flex-col items-center py-1 px-2 rounded-xl transition-all duration-150 ${
                isActive
                  ? 'text-[#14382B]'
                  : 'text-[#6B7280] hover:text-[#1B4332]'
              }`}
            >
              <div
                className={`p-1 rounded-xl transition-all ${
                  isActive ? 'bg-[#14382B] text-white shadow-sm' : 'text-[#4B5563]'
                }`}
              >
                <Icon className="w-5 h-5 stroke-[2]" />
              </div>
              <span className={`text-[10px] font-medium mt-0.5 truncate max-w-[64px] text-center ${isActive ? 'font-bold text-[#14382B]' : ''}`}>
                {item.name}
              </span>
            </NavLink>
          );
        })}
      </div>
    </nav>
  );
};

export default BottomNavigation;
