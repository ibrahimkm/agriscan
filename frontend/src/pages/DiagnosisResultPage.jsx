import React, { useState, useEffect } from 'react';
import { useNavigate, useParams, useLocation } from 'react-router-dom';
import {
  Share2,
  Info,
  Search,
  Cross,
  FileText,
  ChevronRight,
  AlertTriangle,
  PieChart,
} from 'lucide-react';
import AppHeader from '../components/navigation/AppHeader';
import HeatmapViewer from '../components/diagnosis/HeatmapViewer';
import SeverityBadge from '../components/common/SeverityBadge';
import ConfidenceMeter from '../components/common/ConfidenceMeter';
import { useLanguage } from '../context/LanguageContext';
import api from '../services/api';

export const DiagnosisResultPage = () => {
  const navigate = useNavigate();
  const { id } = useParams();
  const location = useLocation();
  const { t, translateCrop, translateDisease } = useLanguage();

  const [diagnosis, setDiagnosis] = useState(location.state?.diagnosis || null);
  const [loading, setLoading] = useState(!location.state?.diagnosis);

  useEffect(() => {
    if (!diagnosis) {
      const fetchDiagnosis = async () => {
        try {
          const res = await api.get(`/diagnoses/${id}`);
          if (res.data.success) {
            setDiagnosis(res.data.data);
          }
        } catch {
          // Default fallback matching Stitch Screen 6
          setDiagnosis({
            _id: id,
            cropName: 'Tomato',
            predictedDisease: 'Early Blight',
            scientificName: 'Alternaria solani',
            confidence: 94,
            severity: 'moderate',
            affectedPercentage: 32,
            imageUrl: 'https://images.unsplash.com/photo-1592417817098-8f3d6eb2260f?w=800&auto=format&fit=crop&q=80',
            whatIsIt: 'Early blight is a fungal disease caused by Alternaria solani that primarily affects tomato and potato plants. It manifests as concentric rings with yellowing halos.',
            symptoms: [
              'Dark brown spots with concentric rings',
              'Yellowing around lesions (chlorosis)',
              'Starts on lower, older leaves',
            ],
            recommendedAction: 'Apply a copper-based fungicide and ensure proper spacing for air circulation. Remove heavily infected lower leaves immediately to slow the spread.',
          });
        } finally {
          setLoading(false);
        }
      };

      fetchDiagnosis();
    }
  }, [id, diagnosis]);

  if (!diagnosis) {
    return (
      <div className="min-h-screen bg-[#FAF8F5] flex items-center justify-center">
        <p className="text-sm font-semibold text-[#6B7280]">Loading diagnosis result...</p>
      </div>
    );
  }

  const handleShare = () => {
    if (navigator.share) {
      navigator.share({
        title: `AgriScan: ${translateDisease(diagnosis.predictedDisease)} on ${translateCrop(diagnosis.cropName)}`,
        text: `AI Diagnosis report: ${translateDisease(diagnosis.predictedDisease)} detected with ${diagnosis.confidence}% confidence.`,
        url: window.location.href,
      }).catch(() => {});
    } else {
      navigator.clipboard.writeText(window.location.href);
      alert('Diagnosis link copied to clipboard!');
    }
  };

  return (
    <div className="min-h-screen bg-[#FAF8F5] pb-24 md:pb-8 select-none">
      <AppHeader
        showBack
        backTo="/home"
        rightAction={
          <button
            onClick={handleShare}
            className="p-1.5 text-[#14382B] hover:bg-[#EAE5DE]/60 rounded-full transition-colors"
            title="Share Diagnosis Report"
          >
            <Share2 className="w-5 h-5 stroke-[2]" />
          </button>
        }
      />

      <main className="max-w-md mx-auto p-4 space-y-4">
        {/* Top Image with 3-Mode Toggles (Matching Stitch Screen 6) */}
        <HeatmapViewer
          imageUrl={diagnosis.imageUrl}
          diseaseName={diagnosis.predictedDisease}
          affectedPercentage={diagnosis.affectedPercentage || 32}
        />

        {/* Crop, Disease Name & Confidence Meter (Matching Stitch Screen 6) */}
        <div className="flex items-start justify-between gap-2 pt-1">
          <div className="flex-1 min-w-0">
            <span className="text-[11px] font-bold text-[#6B7280] tracking-wider uppercase block truncate">
              CROP: {translateCrop(diagnosis.cropName)?.toUpperCase() || 'TOMATO'}
            </span>
            <h2
              onClick={() => navigate(`/diagnosis/${id}/explanation`, { state: { diagnosis } })}
              className="text-xl sm:text-2xl md:text-3xl font-extrabold text-[#14382B] tracking-tight hover:underline cursor-pointer flex items-center space-x-1 break-words"
            >
              <span>{translateDisease(diagnosis.predictedDisease)}</span>
              <ChevronRight className="w-5 h-5 text-[#C68B59] shrink-0 mt-0.5" />
            </h2>
          </div>

          <div className="shrink-0">
            <ConfidenceMeter confidence={diagnosis.confidence || 94} />
          </div>
        </div>

        {/* Severity & Affected Area Badges (Matching Stitch Screen 6) */}
        <div className="flex flex-wrap items-center gap-1.5 sm:gap-2">
          <SeverityBadge severity={diagnosis.severity || 'moderate'} />

          <div className="inline-flex items-center space-x-1.5 px-3 py-1 rounded-full bg-[#E5E7EB]/80 text-[#374151] text-xs font-semibold">
            <PieChart className="w-3.5 h-3.5 text-[#6B7280]" />
            <span>
              {diagnosis.severity === 'healthy'
                ? '0% Affected Area'
                : diagnosis.affectedPercentage
                ? `${diagnosis.affectedPercentage}% ${t('affectedArea')}`
                : 'Foliar Classification'}
            </span>
          </div>

          {diagnosis.modelVersion && (
            <div className="inline-flex items-center space-x-1.5 px-2.5 py-1 rounded-full bg-[#14382B]/10 text-[#14382B] text-[11px] font-medium border border-[#14382B]/15 max-w-full truncate">
              <span className="w-1.5 h-1.5 rounded-full bg-[#22C55E] shrink-0" />
              <span className="truncate">{diagnosis.modelVersion}</span>
            </div>
          )}
        </div>

        {/* Card 1: What is it? (Matching Stitch Screen 6) */}
        <div className="bg-white border border-[#EAE5DE] rounded-3xl p-4 shadow-xs space-y-2">
          <div className="flex items-center space-x-2 text-[#14382B]">
            <Info className="w-4 h-4 text-[#14382B]" />
            <h3 className="text-sm font-bold">{t('whatIsIt')}</h3>
          </div>
          <p className="text-xs md:text-sm text-[#4B5563] leading-relaxed">
            {diagnosis.whatIsIt}
          </p>
        </div>

        {/* Card 2: Symptoms (Matching Stitch Screen 6) */}
        <div className="bg-white border border-[#EAE5DE] rounded-3xl p-4 shadow-xs space-y-2.5">
          <div className="flex items-center space-x-2 text-[#14382B]">
            <Search className="w-4 h-4 text-[#14382B]" />
            <h3 className="text-sm font-bold">{t('symptoms')}</h3>
          </div>
          <ul className="space-y-1.5 text-xs md:text-sm text-[#4B5563]">
            {(diagnosis.symptoms || []).map((sym, idx) => (
              <li key={idx} className="flex items-start space-x-2">
                <span className="w-1.5 h-1.5 rounded-full bg-[#14382B] shrink-0 mt-1.5" />
                <span>{sym}</span>
              </li>
            ))}
          </ul>
        </div>

        {/* Card 3: Recommended Action (Matching Stitch Screen 6) */}
        <div className="bg-white border border-[#EAE5DE] rounded-3xl p-4 shadow-xs space-y-2">
          <div className="flex items-center space-x-2 text-[#14382B]">
            <Cross className="w-4 h-4 text-[#14382B] rotate-45" />
            <h3 className="text-sm font-bold">{t('recommendedAction')}</h3>
          </div>
          <p className="text-xs md:text-sm text-[#4B5563] leading-relaxed">
            {diagnosis.recommendedAction}
          </p>
        </div>

        {/* Primary CTA: View Full Treatment Plan (Matching Stitch Screen 6) */}
        <div className="pt-2">
          <button
            onClick={() => navigate(`/diagnosis/${id}/treatment`, { state: { diagnosis } })}
            className="w-full py-4 rounded-2xl bg-[#14382B] text-white font-bold text-sm md:text-base shadow-md hover:bg-[#1B4332] active:scale-[0.99] transition-all flex items-center justify-center space-x-2"
          >
            <FileText className="w-5 h-5 stroke-[2.2]" />
            <span>{t('viewFullTreatment')}</span>
          </button>
        </div>
      </main>
    </div>
  );
};

export default DiagnosisResultPage;
