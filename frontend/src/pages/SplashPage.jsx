import React, { useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { Leaf, Sparkles } from 'lucide-react';

export const SplashPage = () => {
  const navigate = useNavigate();

  useEffect(() => {
    const timer = setTimeout(() => {
      const onboarded = localStorage.getItem('agriscan_onboarded');
      if (onboarded) {
        navigate('/home');
      } else {
        navigate('/onboarding');
      }
    }, 1600);

    return () => clearTimeout(timer);
  }, [navigate]);

  return (
    <div className="min-h-screen bg-[#FAF8F5] flex flex-col items-center justify-center p-6 text-center select-none relative overflow-hidden">
      {/* Background soft botanical aura */}
      <div className="absolute w-96 h-96 rounded-full bg-[#D8ECE2]/50 blur-3xl -top-20 -left-20 pointer-events-none" />
      <div className="absolute w-80 h-80 rounded-full bg-[#EBD8C3]/40 blur-3xl -bottom-20 -right-20 pointer-events-none" />

      {/* Main Logo & Icon */}
      <div className="relative z-10 flex flex-col items-center space-y-4 animate-fade-in">
        <div className="w-20 h-20 rounded-3xl bg-[#14382B] text-white flex items-center justify-center shadow-xl ring-8 ring-[#E8F5E9]/60">
          <Leaf className="w-10 h-10 stroke-[2]" />
        </div>

        <div className="space-y-1">
          <h1 className="text-3xl font-extrabold tracking-tight text-[#14382B] font-sans">
            AgriScan
          </h1>
          <p className="text-sm font-medium text-[#D4A373]">
            Intelligent Crop Disease Detection
          </p>
        </div>

        {/* Loading Pill */}
        <div className="pt-8 flex items-center space-x-2 text-xs font-semibold text-[#6B7280]">
          <span className="w-2 h-2 rounded-full bg-[#2D6A4F] animate-ping" />
          <span>Initializing Vision Engine...</span>
        </div>
      </div>
    </div>
  );
};

export default SplashPage;
