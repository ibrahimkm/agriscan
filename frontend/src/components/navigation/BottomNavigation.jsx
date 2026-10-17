import React from 'react';
import { NavLink, useLocation } from 'react-router-dom';
import { Home, Camera, Sprout, History, User } from 'lucide-react';
import { useLanguage } from '../../context/LanguageContext';

export const BottomNavigation = () => {
  const location = useLocation();
  const { t } = useLanguage();

  const navItems = [
    { name: t('home'), path: '/home', icon: Home, id: 'nav-home' },
    { name: t('diagnose'), path: '/diagnose', icon: Camera, isPrimary: true, id: 'nav-diagnose' },
    { name: t('myCrops'), path: '/crops', icon: Sprout, id: 'nav-crops' },
    { name: t('history'), path: '/history', icon: History, id: 'nav-history' },
    { name: t('profile'), path: '/profile', icon: User, id: 'nav-profile' },
  ];

  return (
    <nav
      aria-label="Mobile Bottom Navigation"
      className="md:hidden fixed bottom-0 left-0 right-0 z-40 bg-white/95 backdrop-blur-md border-t border-[#EAE5DE] shadow-[0_-2px_12px_rgba(0,0,0,0.05)] select-none transition-all"
      style={{ paddingBottom: 'max(env(safe-area-inset-bottom, 0px), 8px)' }}
    >
      <div className="w-full max-w-lg mx-auto grid grid-cols-5 items-center justify-items-center px-1">
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
                id={item.id}
                to={item.path}
                aria-label={item.name}
                aria-current={isActive ? 'page' : undefined}
                className="w-full col-span-1 flex flex-col items-center justify-center pt-1.5 pb-1 px-0.5 group focus:outline-none"
              >
                {/* Visual Icon Container - prominent green camera button sharing identical horizontal baseline */}
                <div className="h-8 flex items-center justify-center w-full">
                  <div
                    className={`w-11 h-8 rounded-xl flex items-center justify-center shadow-xs transition-transform duration-150 active:scale-95 ${
                      isActive
                        ? 'bg-[#14382B] text-white ring-2 ring-[#22C55E]/40'
                        : 'bg-[#1B4332] text-white hover:bg-[#14382B]'
                    }`}
                  >
                    <Icon className="w-5 h-5 stroke-[2.2]" />
                  </div>
                </div>
                {/* Centered Label */}
                <div className="h-3.5 flex items-center justify-center w-full mt-1">
                  <span
                    className={`text-[10px] leading-none font-medium truncate max-w-full px-0.5 text-center transition-colors ${
                      isActive ? 'text-[#14382B] font-bold' : 'text-[#6B7280]'
                    }`}
                  >
                    {item.name}
                  </span>
                </div>
              </NavLink>
            );
          }

          return (
            <NavLink
              key={item.path}
              id={item.id}
              to={item.path}
              aria-label={item.name}
              aria-current={isActive ? 'page' : undefined}
              className="w-full col-span-1 flex flex-col items-center justify-center pt-1.5 pb-1 px-0.5 group focus:outline-none"
            >
              {/* Visual Icon Container - sharing identical vertical baseline height */}
              <div className="h-8 flex items-center justify-center w-full">
                <div
                  className={`w-9 h-8 rounded-xl flex items-center justify-center transition-all duration-150 ${
                    isActive
                      ? 'bg-[#EDF7EE] text-[#14382B] shadow-xs'
                      : 'text-[#6B7280] group-hover:text-[#14382B] group-hover:bg-[#FAF8F5]'
                  }`}
                >
                  <Icon className="w-5 h-5 stroke-[2] transition-transform duration-150 group-active:scale-95" />
                </div>
              </div>
              {/* Centered Label */}
              <div className="h-3.5 flex items-center justify-center w-full mt-1">
                <span
                  className={`text-[10px] leading-none font-medium truncate max-w-full px-0.5 text-center transition-colors ${
                    isActive ? 'font-bold text-[#14382B]' : 'text-[#6B7280]'
                  }`}
                >
                  {item.name}
                </span>
              </div>
            </NavLink>
          );
        })}
      </div>
    </nav>
  );
};

export default BottomNavigation;
