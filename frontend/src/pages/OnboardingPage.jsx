import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { ArrowRight, Sparkles, ShieldCheck, Sprout } from 'lucide-react';
import { useAuth } from '../context/AuthContext';

export const OnboardingPage = () => {
  const navigate = useNavigate();
  const { isAuthenticated } = useAuth();
  const [currentSlide, setCurrentSlide] = useState(0);

  const slides = [
    {
      title: 'Identify crop diseases instantly.',
      subtitle: 'Point your camera at a leaf and let our advanced AI diagnose the issue in seconds.',
      image: 'https://images.unsplash.com/photo-1592417817098-8f3d6eb2260f?w=800&auto=format&fit=crop&q=80',
      badge: 'Real-time AI Diagnosis',
    },
    {
      title: 'Actionable treatment and prevention.',
      subtitle: 'Receive clear, farmer-tested remedies, chemical dosages, and long-term soil prevention guidelines.',
      image: 'https://images.unsplash.com/photo-1574943320219-553eb213f72d?w=800&auto=format&fit=crop&q=80',
      badge: 'Botanical Protocols',
    },
    {
      title: 'Reliable in the field, even offline.',
      subtitle: 'Scan your crops anywhere without cellular data. All diagnoses automatically sync when connectivity returns.',
      image: 'https://images.unsplash.com/photo-1574323347407-f5e1ad6d020b?w=800&auto=format&fit=crop&q=80',
      badge: 'Offline-First Sync',
    },
  ];

  const handleFinish = () => {
    localStorage.setItem('agriscan_onboarded', 'true');
    if (isAuthenticated) {
      navigate('/home');
    } else {
      navigate('/login');
    }
  };

  const handleNext = () => {
    if (currentSlide < slides.length - 1) {
      setCurrentSlide((s) => s + 1);
    } else {
      handleFinish();
    }
  };

  return (
    <div className="min-h-screen bg-[#FAF8F5] flex flex-col justify-between p-6 max-w-md mx-auto select-none">
      {/* Top Header (Matching Stitch Screen 1) */}
      <div className="flex items-center justify-between pt-2">
        <h1 className="text-xl font-bold tracking-tight text-[#14382B]">AgriScan</h1>
        <button
          onClick={handleFinish}
          className="text-xs font-semibold text-[#6B7280] hover:text-[#14382B] transition-colors"
        >
          Skip
        </button>
      </div>

      {/* Center Carousel Slide */}
      <div className="my-auto space-y-6">
        {/* Visual Hero Card */}
        <div className="relative w-full aspect-[4/4.2] rounded-3xl overflow-hidden shadow-xl border border-[#EAE5DE] bg-zinc-900 group">
          <img
            src={slides[currentSlide].image}
            alt={slides[currentSlide].title}
            className="w-full h-full object-cover transition-transform duration-700 ease-out scale-105"
          />

          {/* Futuristic Overlay Glow */}
          <div className="absolute inset-0 bg-gradient-to-t from-black/80 via-black/20 to-transparent" />

          {/* Badge */}
          <div className="absolute bottom-4 left-4 bg-white/90 backdrop-blur-md px-3.5 py-1.5 rounded-full text-xs font-bold text-[#14382B] shadow-md flex items-center space-x-1.5">
            <Sparkles className="w-3.5 h-3.5 text-[#2D6A4F]" />
            <span>{slides[currentSlide].badge}</span>
          </div>
        </div>

        {/* Text Content (Matching Stitch Typography) */}
        <div className="space-y-3 text-center px-2">
          <h2 className="text-2xl md:text-3xl font-extrabold text-[#14382B] tracking-tight leading-tight">
            {slides[currentSlide].title}
          </h2>
          <p className="text-sm text-[#4B5563] leading-relaxed max-w-sm mx-auto font-sans">
            {slides[currentSlide].subtitle}
          </p>
        </div>
      </div>

      {/* Bottom Controls */}
      <div className="space-y-6 pb-4">
        {/* Step Indicator Dots */}
        <div className="flex justify-center items-center space-x-2">
          {slides.map((_, idx) => (
            <button
              key={idx}
              onClick={() => setCurrentSlide(idx)}
              className={`h-2 rounded-full transition-all duration-300 ${
                idx === currentSlide
                  ? 'w-6 bg-[#14382B]'
                  : 'w-2 bg-[#D1D5DB]'
              }`}
              aria-label={`Slide ${idx + 1}`}
            />
          ))}
        </div>

        {/* Next / Get Started Action */}
        <button
          onClick={handleNext}
          className="w-full py-4 rounded-2xl bg-[#14382B] text-white font-bold text-sm shadow-lg hover:bg-[#1B4332] active:scale-[0.98] transition-all flex items-center justify-center space-x-2"
        >
          <span>{currentSlide === slides.length - 1 ? 'Get Started' : 'Continue'}</span>
          <ArrowRight className="w-4 h-4 stroke-[2.5]" />
        </button>
      </div>
    </div>
  );
};

export default OnboardingPage;
