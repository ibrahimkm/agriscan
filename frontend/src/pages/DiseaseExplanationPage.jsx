import React from 'react';
import { useNavigate, useParams, useLocation } from 'react-router-dom';
import {
  ArrowLeft,
  AlertTriangle,
  Info,
  Droplets,
  Cloud,
  Wind,
  Search,
  FileText,
  CheckCircle,
  Leaf,
  Sprout,
  Apple,
} from 'lucide-react';
import AppHeader from '../components/navigation/AppHeader';
import { useLanguage } from '../context/LanguageContext';

export const DiseaseExplanationPage = () => {
  const navigate = useNavigate();
  const { id } = useParams();
  const location = useLocation();
  const { t, translateCrop, translateDisease } = useLanguage();

  const diagnosis = location.state?.diagnosis || {
    cropName: 'Tomato',
    predictedDisease: 'Tomato Late Blight',
    scientificName: 'Phytophthora infestans',
    severity: 'severe',
  };

  return (
    <div className="min-h-screen bg-[#FAF8F5] pb-24 md:pb-8 select-none">
      <AppHeader showBack backTo={`/diagnosis/${id}`} title="AgriScan" />

      <main className="max-w-md mx-auto p-4 space-y-4">
        {/* Back Link & Heading (Matching Stitch Screen 8) */}
        <div>
          <button
            onClick={() => navigate(`/diagnosis/${id}`, { state: { diagnosis } })}
            className="inline-flex items-center space-x-1 text-xs font-semibold text-[#6B7280] hover:text-[#14382B] mb-2"
          >
            <ArrowLeft className="w-3.5 h-3.5" />
            <span>{t('backToScan')}</span>
          </button>
          <h2 className="text-2xl md:text-3xl font-extrabold text-[#14382B] tracking-tight">
            {translateDisease(diagnosis.predictedDisease)}
          </h2>
          <p className="text-sm italic font-serif text-[#6B7280] mt-0.5">
            {diagnosis.scientificName || 'Phytophthora infestans'}
          </p>
        </div>

        {/* Microscopic Pathology Card (Matching Stitch Screen 8) */}
        <div className="relative w-full h-52 rounded-3xl overflow-hidden shadow-md border border-[#EAE5DE] bg-black">
          <img
            src="https://images.unsplash.com/photo-1576086213369-97a306d36557?w=800&auto=format&fit=crop&q=80"
            alt="Microscopic Pathogen Visual"
            className="w-full h-full object-cover opacity-90"
          />
          <div className="absolute inset-0 bg-gradient-to-t from-black/80 via-transparent to-transparent" />
          <div className="absolute bottom-3 left-3 bg-[#14382B]/90 backdrop-blur-md text-white text-xs font-bold px-3 py-1 rounded-full flex items-center space-x-1.5 shadow-md">
            <CheckCircle className="w-3.5 h-3.5 text-[#86EFAC]" />
            <span>{t('highConfidenceMatch')}</span>
          </div>
        </div>

        {/* Severe Risk Alert Banner (Matching Stitch Screen 8) */}
        <div className="bg-[#FEE2E2] border border-[#FCA5A5] rounded-3xl p-4 shadow-xs flex items-start space-x-3">
          <div className="w-8 h-8 rounded-full bg-[#EF4444] text-white flex items-center justify-center shrink-0 mt-0.5">
            <AlertTriangle className="w-4 h-4" />
          </div>
          <div>
            <h3 className="text-sm font-bold text-[#B91C1C]">
              {t('severeRiskTitle')}
            </h3>
            <p className="text-xs text-[#7F1D1D] mt-1 leading-relaxed">
              {t('severeRiskDesc')}
            </p>
          </div>
        </div>

        {/* Section 1: What is it? (Matching Stitch Screen 8) */}
        <div className="bg-white border border-[#EAE5DE] rounded-3xl p-4 shadow-xs space-y-2">
          <div className="flex items-center space-x-2 text-[#14382B]">
            <Info className="w-4 h-4 text-[#14382B]" />
            <h3 className="text-sm font-bold">{t('whatIsIt')}</h3>
          </div>
          <p className="text-xs md:text-sm text-[#4B5563] leading-relaxed">
            {diagnosis.whatIsIt}
          </p>
        </div>

        {/* Section 2: Why it happens (Matching Stitch Screen 8) */}
        <div className="bg-white border border-[#EAE5DE] rounded-3xl p-4 shadow-xs space-y-3">
          <div className="flex items-center space-x-2 text-[#14382B]">
            <Droplets className="w-4 h-4 text-[#14382B]" />
            <h3 className="text-sm font-bold">{t('whyItHappens')}</h3>
          </div>
          <div className="space-y-2 text-xs md:text-sm text-[#374151]">
            <div className="flex items-start space-x-2.5">
              <Cloud className="w-4 h-4 text-[#6B7280] shrink-0 mt-0.5" />
              <div>{t('coolWetWeather')}</div>
            </div>
            <div className="flex items-start space-x-2.5">
              <Wind className="w-4 h-4 text-[#6B7280] shrink-0 mt-0.5" />
              <div>{t('windRain')}</div>
            </div>
          </div>
        </div>

        {/* Section 3: Key Symptoms to Look For (Matching Stitch Screen 8) */}
        <div className="space-y-2.5 pt-1">
          <div className="flex items-center space-x-2 text-[#14382B] px-1">
            <Search className="w-4 h-4 text-[#14382B]" />
            <h3 className="text-base font-bold">{t('keySymptoms')}</h3>
          </div>

          {/* Subcard: On Leaves */}
          <div className="bg-white border border-[#EAE5DE] rounded-2xl p-3.5 shadow-xs space-y-1">
            <div className="flex items-center space-x-2 text-xs font-bold text-[#14382B]">
              <Leaf className="w-3.5 h-3.5 text-[#2D6A4F]" />
              <span>{t('onLeaves')}</span>
            </div>
            <p className="text-xs text-[#4B5563] leading-relaxed">
              Large, irregular water-soaked spots with chlorotic yellow margins.
            </p>
          </div>

          {/* Subcard: On Stems */}
          <div className="bg-white border border-[#EAE5DE] rounded-2xl p-3.5 shadow-xs space-y-1">
            <div className="flex items-center space-x-2 text-xs font-bold text-[#14382B]">
              <Sprout className="w-3.5 h-3.5 text-[#C68B59]" />
              <span>{t('onStems')}</span>
            </div>
            <p className="text-xs text-[#4B5563] leading-relaxed">
              Dark brown to black lesions encircling the stem.
            </p>
          </div>

          {/* Subcard: On Fruit */}
          <div className="bg-white border border-[#EAE5DE] rounded-2xl p-3.5 shadow-xs space-y-1">
            <div className="flex items-center space-x-2 text-xs font-bold text-[#14382B]">
              <Apple className="w-3.5 h-3.5 text-[#DC2626]" />
              <span>{t('onFruit')}</span>
            </div>
            <p className="text-xs text-[#4B5563] leading-relaxed">
              Firm, greasy dark spots rendering fruit unmarketable.
            </p>
          </div>
        </div>

        {/* Bottom Actions (Matching Stitch Screen 8) */}
        <div className="space-y-2.5 pt-3">
          <button
            onClick={() => navigate('/history')}
            className="w-full py-3 rounded-2xl border border-[#D4A373] text-[#C68B59] font-bold text-xs md:text-sm hover:bg-[#FAF8F5] transition-colors"
          >
            {t('logObservation')}
          </button>
          <button
            onClick={() => navigate(`/diagnosis/${id}/treatment`, { state: { diagnosis } })}
            className="w-full py-4 rounded-2xl bg-[#14382B] text-white font-bold text-sm md:text-base shadow-md hover:bg-[#1B4332] active:scale-[0.99] transition-all flex items-center justify-center space-x-2"
          >
            <FileText className="w-5 h-5 stroke-[2.2]" />
            <span>{t('viewTreatmentPlan')}</span>
          </button>
        </div>
      </main>
    </div>
  );
};

export default DiseaseExplanationPage;
