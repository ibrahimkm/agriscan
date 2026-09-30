import React, { useState, useEffect } from 'react';
import { useNavigate, useParams, useLocation } from 'react-router-dom';
import {
  Leaf,
  AlertCircle,
  Shield,
  Info,
  Share2,
  Bookmark,
  Check,
} from 'lucide-react';
import AppHeader from '../components/navigation/AppHeader';
import { useLanguage } from '../context/LanguageContext';
import confetti from 'canvas-confetti';

export const TreatmentPlanPage = () => {
  const navigate = useNavigate();
  const { id } = useParams();
  const location = useLocation();
  const { t, translateCrop, translateDisease } = useLanguage();

  const diagnosis = location.state?.diagnosis || {
    cropName: 'Tomato',
    predictedDisease: 'Early Blight',
    severity: 'moderate',
  };

  const [steps, setSteps] = useState(
    diagnosis.treatmentSteps || [
      {
        id: 'step-1',
        title: 'Apply Fungicide',
        description: 'Apply a copper-based fungicide or chlorothalonil immediately.',
        completed: false,
      },
      {
        id: 'step-2',
        title: 'Improve Airflow',
        description: 'Prune dense foliage to ensure better air circulation around the plants.',
        completed: false,
      },
      {
        id: 'step-3',
        title: 'Adjust Irrigation',
        description: 'Switch to drip irrigation to keep leaves dry. Avoid overhead watering.',
        completed: false,
      },
    ]
  );

  const [saved, setSaved] = useState(false);

  const toggleStep = (stepId) => {
    setSteps((prev) =>
      prev.map((s) => {
        if (s.id === stepId) {
          const nextState = !s.completed;
          if (nextState) {
            confetti({
              particleCount: 40,
              spread: 60,
              origin: { y: 0.8 },
            });
          }
          return { ...s, completed: nextState };
        }
        return s;
      })
    );
  };

  const handleShare = () => {
    if (navigator.share) {
      navigator.share({
        title: `AgriScan Treatment Plan: ${translateDisease(diagnosis.predictedDisease)}`,
        text: `Action plan for ${translateCrop(diagnosis.cropName)}: Apply copper fungicide and improve canopy spacing.`,
        url: window.location.href,
      }).catch(() => {});
    } else {
      navigator.clipboard.writeText(window.location.href);
      alert('Treatment plan URL copied to clipboard!');
    }
  };

  const handleSave = () => {
    setSaved(true);
    confetti({
      particleCount: 70,
      spread: 70,
      origin: { y: 0.7 },
    });
    setTimeout(() => {
      navigate('/history');
    }, 1200);
  };

  return (
    <div className="min-h-screen bg-[#FAF8F5] pb-24 md:pb-8 select-none">
      <AppHeader showBack backTo={`/diagnosis/${id}`} title="AgriScan" />

      <main className="max-w-md mx-auto p-4 space-y-4">
        {/* Top Header Badge & Title (Matching Stitch Screen 7) */}
        <div className="space-y-1.5 pt-1">
          <div className="inline-flex items-center space-x-1.5 text-xs font-semibold text-[#14382B]">
            <Leaf className="w-4 h-4 text-[#2D6A4F]" />
            <span>{t('diagnosisComplete')}</span>
          </div>
          <h2 className="text-2xl md:text-3xl font-extrabold text-[#14382B] tracking-tight">
            {t('treatmentPlanTitle')}
          </h2>
          <p className="text-xs md:text-sm text-[#4B5563] leading-relaxed">
            {translateCrop(diagnosis.cropName)} · {translateDisease(diagnosis.predictedDisease)}
          </p>
        </div>

        {/* Card 1: Immediate Action Required (Matching Stitch Screen 7) */}
        <div className="bg-white border border-[#EAE5DE] rounded-3xl p-4 shadow-xs space-y-3">
          <div className="flex items-start space-x-3">
            <div className="w-8 h-8 rounded-full bg-[#FEE2E2] text-[#DC2626] flex items-center justify-center shrink-0 mt-0.5">
              <AlertCircle className="w-4 h-4 stroke-[2.5]" />
            </div>
            <div>
              <h3 className="text-sm font-bold text-[#14382B]">
                {diagnosis.immediateAction?.title || t('immediateActionReq')}
              </h3>
              <p className="text-xs text-[#4B5563] mt-1 leading-relaxed">
                {diagnosis.immediateAction?.description || 'Remove and destroy heavily infected lower leaves to prevent spore spread.'}
              </p>
              <div className="mt-2.5 inline-flex items-center space-x-1 px-2.5 py-0.5 rounded-full bg-[#FEF2F2] border border-[#FEE2E2] text-[10px] font-bold text-[#DC2626]">
                <span>⚠ {t('highPriority')}</span>
              </div>
            </div>
          </div>
        </div>

        {/* Card 2: Treatment Steps with Interactive Checkboxes (Matching Stitch Screen 7) */}
        <div className="bg-white border border-[#EAE5DE] rounded-3xl p-4 shadow-xs space-y-3">
          <div className="flex items-center space-x-2 text-[#14382B]">
            <div className="flex items-center space-x-0.5">
              <span className="w-1.5 h-1.5 rounded-full bg-[#14382B]" />
              <span className="w-1.5 h-1.5 rounded-full bg-[#14382B]" />
            </div>
            <h3 className="text-sm font-bold">{t('treatmentSteps')}</h3>
          </div>

          <div className="space-y-3 pt-1">
            {steps.map((step) => (
              <div
                key={step.id}
                onClick={() => toggleStep(step.id)}
                className="flex items-start space-x-3 cursor-pointer group"
              >
                <button
                  type="button"
                  className={`w-5 h-5 rounded-md border flex items-center justify-center shrink-0 mt-0.5 transition-colors ${
                    step.completed
                      ? 'bg-[#14382B] border-[#14382B] text-white'
                      : 'border-[#D1D5DB] group-hover:border-[#14382B]'
                  }`}
                >
                  {step.completed && <Check className="w-3.5 h-3.5 stroke-[3]" />}
                </button>

                <div className="flex-1">
                  <p
                    className={`text-xs md:text-sm font-bold ${
                      step.completed ? 'line-through text-[#9CA3AF]' : 'text-[#14382B]'
                    }`}
                  >
                    {step.title}
                  </p>
                  <p
                    className={`text-xs mt-0.5 leading-relaxed ${
                      step.completed ? 'text-[#9CA3AF]' : 'text-[#4B5563]'
                    }`}
                  >
                    {step.description}
                  </p>
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Card 3: Prevention Tips (Matching Stitch Screen 7) */}
        <div className="bg-white border border-[#EAE5DE] rounded-3xl p-4 shadow-xs space-y-2.5">
          <div className="flex items-center space-x-2 text-[#14382B]">
            <Shield className="w-4 h-4 text-[#14382B]" />
            <h3 className="text-sm font-bold">{t('preventionTips')}</h3>
          </div>

          <ul className="space-y-1.5 text-xs md:text-sm text-[#4B5563] pt-1">
            {(diagnosis.preventionTips || [
              'Rotate crops annually (avoid nightshades in the same spot).',
              'Ensure adequate spacing between plants next season.',
              'Apply organic mulch to prevent soil splashing onto leaves.',
            ]).map((tip, idx) => (
              <li key={idx} className="flex items-start space-x-2">
                <span className="w-1.5 h-1.5 rounded-full bg-[#14382B] shrink-0 mt-1.5" />
                <span>{tip}</span>
              </li>
            ))}
          </ul>
        </div>

        {/* Card 4: Safety Notice (Matching Stitch Screen 7) */}
        <div className="bg-[#FAF8F5] border border-[#EAE5DE] rounded-3xl p-4 shadow-xs space-y-1.5">
          <div className="flex items-center space-x-2 text-[#14382B]">
            <Info className="w-4 h-4 text-[#14382B]" />
            <h3 className="text-xs font-bold uppercase tracking-wider">{t('safetyNotice')}</h3>
          </div>
          <p className="text-xs text-[#4B5563] leading-relaxed">
            {t('safetyNoticeDesc')}
          </p>
        </div>

        {/* Bottom CTA Buttons: Share Report & Save Diagnosis (Matching Stitch Screen 7) */}
        <div className="space-y-2.5 pt-3">
          <button
            onClick={handleShare}
            className="w-full py-3.5 rounded-2xl border border-[#D4A373] text-[#C68B59] font-bold text-xs md:text-sm hover:bg-[#FAF8F5] transition-colors flex items-center justify-center space-x-2"
          >
            <Share2 className="w-4 h-4" />
            <span>{t('shareReport')}</span>
          </button>

          <button
            onClick={handleSave}
            disabled={saved}
            className="w-full py-4 rounded-2xl bg-[#14382B] text-white font-bold text-sm md:text-base shadow-md hover:bg-[#1B4332] active:scale-[0.99] transition-all flex items-center justify-center space-x-2 disabled:opacity-80"
          >
            <Bookmark className="w-5 h-5 stroke-[2.2]" />
            <span>{saved ? t('savedToHistory') : t('saveDiagnosis')}</span>
          </button>
        </div>
      </main>
    </div>
  );
};

export default TreatmentPlanPage;
