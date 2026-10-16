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
    <nav
      className="md:hidden fixed bottom-0 left-0 right-0 z-40 bg-white/95 backdrop-blur-lg border-t border-[#EAE5DE] shadow-[0_-4px_20px_rgba(0,0,0,0.06)] select-none transition-all"
      style={{ paddingBottom: 'max(env(safe-area-inset-bottom, 0px), 6px)' }}
    >
      <div className="w-full max-w-md mx-auto px-1 grid grid-cols-5 items-end justify-items-center">
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
                className="w-full col-span-1 flex flex-col items-center justify-center -mt-4 pb-1 group"
              >
                <div
                  className={`w-12 h-11 sm:w-13 sm:h-12 rounded-2xl flex items-center justify-center shadow-lg transition-transform duration-150 active:scale-95 ${
                    isActive
                      ? 'bg-[#14382B] text-white ring-4 ring-[#E8F5E9]'
                      : 'bg-[#1B4332] text-white hover:bg-[#14382B]'
                  }`}
                >
                  <Icon className="w-5 h-5 sm:w-6 sm:h-6 stroke-[2]" />
                </div>
                <span
                  className={`text-[10px] leading-tight font-semibold mt-1 truncate max-w-full px-0.5 text-center transition-colors ${
                    isActive ? 'text-[#14382B] font-bold' : 'text-[#6B7280]'
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
              className={`w-full col-span-1 flex flex-col items-center justify-center py-1 px-0.5 transition-all duration-150 ${
                isActive
                  ? 'text-[#14382B]'
                  : 'text-[#6B7280] hover:text-[#1B4332]'
              }`}
            >
              <div
                className={`w-8 h-8 rounded-xl flex items-center justify-center transition-all ${
                  isActive ? 'bg-[#14382B] text-white shadow-xs' : 'text-[#4B5563]'
                }`}
              >
                <Icon className="w-4 h-4 sm:w-5 sm:h-5 stroke-[2]" />
              </div>
              <span
                className={`text-[10px] leading-tight font-medium mt-1 truncate max-w-full px-0.5 text-center transition-colors ${
                  isActive ? 'font-bold text-[#14382B]' : ''
                }`}
              >
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
