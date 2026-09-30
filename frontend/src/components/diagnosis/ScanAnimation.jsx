import React, { useState, useEffect } from 'react';
import { Check, Loader2, RotateCw } from 'lucide-react';
import { useLanguage } from '../../context/LanguageContext';

export const ScanAnimation = ({ imageUrl, cropName = 'Tomato', onComplete, onCancel }) => {
  const { t, translateCrop } = useLanguage();
  const [currentStep, setCurrentStep] = useState(0);

  const steps = [
    {
      title: t('step1'),
      description: t('step1Sub'),
    },
    {
      title: t('step2'),
      description: `${t('step2Sub')}`,
    },
    {
      title: t('step3'),
      description: t('step3Sub'),
    },
    {
      title: t('step4'),
      description: t('step4Sub'),
    },
    {
      title: t('step5'),
      description: t('step5Sub'),
    },
  ];

  useEffect(() => {
    const timer = setInterval(() => {
      setCurrentStep((prev) => {
        if (prev < steps.length - 1) {
          return prev + 1;
        } else {
          clearInterval(timer);
          setTimeout(() => {
            if (onComplete) onComplete();
          }, 800);
          return prev;
        }
      });
    }, 1000);

    return () => clearInterval(timer);
  }, []);

  const progressPercentage = Math.round(((currentStep + 1) / steps.length) * 100);

  return (
    <div className="max-w-md mx-auto p-4 space-y-6 select-none">
      {/* Top Image Preview with Pulse Overlay */}
      <div className="relative w-full h-56 rounded-3xl overflow-hidden shadow-md border border-[#EAE5DE] bg-zinc-900">
        <img
          src={imageUrl || 'https://images.unsplash.com/photo-1592417817098-8f3d6eb2260f?w=800&auto=format&fit=crop&q=80'}
          alt="Scanning leaf"
          className="w-full h-full object-cover"
        />

        {/* Scan line laser animation */}
        <div className="absolute inset-0 bg-gradient-to-b from-transparent via-[#22C55E]/20 to-transparent animate-pulse" />

        {/* Top-Right Badge: Analyzing */}
        <div className="absolute top-3 right-3 bg-[#14382B]/90 backdrop-blur-md text-white text-xs font-semibold px-3 py-1.5 rounded-full flex items-center space-x-1.5 shadow-md">
          <RotateCw className="w-3.5 h-3.5 animate-spin text-[#86EFAC]" />
          <span>{t('syncing')}</span>
        </div>
      </div>

      {/* Header & Progress Bar */}
      <div>
        <div className="flex items-center justify-between mb-2">
          <h2 className="text-xl font-bold text-[#14382B]">{t('diagnosticProcess')}</h2>
          <span className="text-xs font-semibold text-[#6B7280]">
            {progressPercentage}% {t('complete')}
          </span>
        </div>
        <div className="w-full h-2 bg-[#EAE5DE] rounded-full overflow-hidden">
          <div
            className="h-full bg-[#14382B] rounded-full transition-all duration-500 ease-out"
            style={{ width: `${progressPercentage}%` }}
          />
        </div>
      </div>

      {/* Staged Checklist Card (Matching Stitch Screen 5) */}
      <div className="bg-[#FAF8F5] border border-[#EFEAE2] rounded-3xl p-5 shadow-xs space-y-5">
        {steps.map((step, idx) => {
          const isDone = idx < currentStep;
          const isCurrent = idx === currentStep;
          const isPending = idx > currentStep;

          return (
            <div key={idx} className="flex items-start space-x-3.5 relative">
              {/* Vertical connector line */}
              {idx < steps.length - 1 && (
                <div
                  className={`absolute left-3.5 top-7 bottom-0 w-0.5 -mb-5 ${
                    isDone ? 'bg-[#22C55E]' : 'bg-[#E5E7EB]'
                  }`}
                />
              )}

              {/* Status Circle */}
              <div className="relative z-10">
                {isDone ? (
                  <div className="w-7 h-7 rounded-full bg-[#DCFCE7] text-[#15803D] flex items-center justify-center shadow-xs">
                    <Check className="w-4 h-4 stroke-[3]" />
                  </div>
                ) : isCurrent ? (
                  <div className="w-7 h-7 rounded-full bg-[#FEF3C7] text-[#D97706] flex items-center justify-center shadow-xs animate-spin">
                    <RotateCw className="w-4 h-4" />
                  </div>
                ) : (
                  <div className="w-7 h-7 rounded-full bg-[#E5E7EB] text-[#9CA3AF] flex items-center justify-center">
                    <span className="w-2 h-2 rounded-full bg-[#9CA3AF]" />
                  </div>
                )}
              </div>

              {/* Step Info */}
              <div className="flex-1">
                <p
                  className={`text-sm font-bold ${
                    isDone
                      ? 'text-[#14382B]'
                      : isCurrent
                      ? 'text-[#14382B]'
                      : 'text-[#9CA3AF]'
                  }`}
                >
                  {step.title}
                </p>
                <p
                  className={`text-xs mt-0.5 leading-relaxed ${
                    isDone || isCurrent ? 'text-[#4B5563]' : 'text-[#9CA3AF]'
                  }`}
                >
                  {step.description}
                </p>
              </div>
            </div>
          );
        })}
      </div>

      {/* Cancel CTA */}
      <div className="pt-2">
        <button
          onClick={onCancel}
          className="w-full py-3.5 rounded-2xl border border-[#D4A373] text-[#C68B59] font-bold text-sm hover:bg-[#FAF8F5] transition-colors"
        >
          {t('cancelAnalysis')}
        </button>
      </div>
    </div>
  );
};

export default ScanAnimation;
