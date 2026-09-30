import React, { useState, useEffect } from 'react';
import {
  UploadCloud,
  Sparkles,
  Bot,
  Layers,
  RotateCw,
  CheckCircle,
  AlertTriangle,
  FileCheck,
  Cpu,
} from 'lucide-react';
import AppHeader from '../components/navigation/AppHeader';
import OfflineBanner from '../components/common/OfflineBanner';
import BoundingBoxOverlay from '../components/yolo/BoundingBoxOverlay';
import QAChatThread from '../components/yolo/QAChatThread';
import SeverityBadge from '../components/common/SeverityBadge';
import { useLanguage } from '../context/LanguageContext';
import { runLocalYoloDetection, answerLocalAgronomistQuestion } from '../services/localMLInference';

export const YoloAnalysisPage = () => {
  const { language, t, translateCrop } = useLanguage();

  const [selectedCrop, setSelectedCrop] = useState('Tomato');
  const [analyzing, setAnalyzing] = useState(false);
  const [detectionResult, setDetectionResult] = useState(null);
  const [selectedBoxIndex, setSelectedBoxIndex] = useState(null);
  const [askingQA, setAskingQA] = useState(false);

  // Initialize or re-localize detections on language change
  useEffect(() => {
    const localRes = runLocalYoloDetection({ cropName: selectedCrop, language });
    const initialQA = answerLocalAgronomistQuestion({
      question: 'How quickly will this spread to adjacent crops?',
      cropName: selectedCrop,
      language,
    });

    setDetectionResult({
      ...localRes,
      _id: 'yolo_local_offline',
      imageUrl: 'https://images.unsplash.com/photo-1592417817098-8f3d6eb2260f?w=800&auto=format&fit=crop&q=80',
      qaThread: [initialQA],
    });
  }, [language, selectedCrop]);

  const handleFileUpload = (e) => {
    const file = e.target.files?.[0];
    if (file) {
      const reader = new FileReader();
      reader.onload = () => {
        runDetection(reader.result);
      };
      reader.readAsDataURL(file);
    }
  };

  const runDetection = (imgData) => {
    setAnalyzing(true);
    setTimeout(() => {
      const localResult = runLocalYoloDetection({ cropName: selectedCrop, language });
      const initialQA = answerLocalAgronomistQuestion({
        question: 'What immediate step should I take for this lesion pattern?',
        cropName: selectedCrop,
        language,
      });

      setDetectionResult({
        ...localResult,
        _id: `yolo_${Date.now()}`,
        imageUrl: imgData,
        qaThread: [initialQA],
      });
      setAnalyzing(false);
    }, 700);
  };

  const handleAskQuestion = (question) => {
    if (!detectionResult) return;
    setAskingQA(true);

    setTimeout(() => {
      const qaResult = answerLocalAgronomistQuestion({
        question,
        cropName: selectedCrop,
        language,
      });

      setDetectionResult((prev) => ({
        ...prev,
        qaThread: [...prev.qaThread, qaResult],
      }));
      setAskingQA(false);
    }, 500);
  };

  return (
    <div className="min-h-screen bg-[#FAF8F5] pb-24 md:pb-8 select-none">
      <AppHeader title={t('yoloTitle')} showBack backTo="/home" />
      <OfflineBanner />

      <main className="max-w-2xl mx-auto p-4 space-y-4">
        {/* Header Title */}
        <div className="space-y-1">
          <div className="inline-flex items-center space-x-1.5 text-xs font-semibold text-[#14382B]">
            <Cpu className="w-4 h-4 text-[#2D6A4F]" />
            <span>{t('offlineInferenceBadge')}</span>
          </div>
          <h2 className="text-2xl md:text-3xl font-extrabold text-[#14382B] tracking-tight">
            {t('yoloHeader')}
          </h2>
          <p className="text-xs md:text-sm text-[#4B5563]">
            {t('yoloSub')}
          </p>
        </div>

        {/* Drag & Drop Upload Zone */}
        <label className="block border-2 border-dashed border-[#D4A373] hover:border-[#14382B] rounded-3xl p-6 bg-white text-center cursor-pointer transition-all shadow-xs group">
          <input
            type="file"
            accept="image/*"
            onChange={handleFileUpload}
            className="hidden"
          />
          <div className="flex flex-col items-center space-y-2">
            <div className="w-12 h-12 rounded-2xl bg-[#FAF8F5] text-[#14382B] group-hover:bg-[#14382B] group-hover:text-white flex items-center justify-center transition-colors">
              <UploadCloud className="w-6 h-6 stroke-[2]" />
            </div>
            <p className="text-sm font-bold text-[#14382B]">
              {t('dragDropText')}
            </p>
            <p className="text-xs text-[#6B7280]">
              Supports high-resolution JPG, PNG, WEBP
            </p>
          </div>
        </label>

        {/* Mid-Analysis Loading State */}
        {analyzing && (
          <div className="bg-white border border-[#EAE5DE] rounded-3xl p-8 text-center space-y-3 shadow-xs">
            <div className="w-12 h-12 rounded-full bg-[#E8F5E9] text-[#14382B] flex items-center justify-center mx-auto animate-spin">
              <RotateCw className="w-6 h-6" />
            </div>
            <h3 className="text-base font-bold text-[#14382B]">
              {t('runningYolo')}
            </h3>
          </div>
        )}

        {/* Detection Visual Result & Bounding Boxes */}
        {detectionResult && !analyzing && (
          <div className="space-y-4">
            {/* Overlay */}
            <BoundingBoxOverlay
              imageUrl={detectionResult.imageUrl}
              detections={detectionResult.detections}
              selectedDetection={selectedBoxIndex}
              onSelect={setSelectedBoxIndex}
            />

            {/* Model Version Caption & Summary */}
            <div className="flex items-center justify-between text-xs text-[#6B7280] px-1">
              <div className="flex items-center space-x-1.5">
                <FileCheck className="w-3.5 h-3.5 text-[#2D6A4F]" />
                <span className="font-semibold">{detectionResult.modelVersion}</span>
              </div>
              <SeverityBadge severity={detectionResult.overallSeverity} />
            </div>

            {/* Detected Classes List */}
            <div className="bg-white border border-[#EAE5DE] rounded-3xl p-4 shadow-xs space-y-2.5">
              <h3 className="text-sm font-bold text-[#14382B]">
                {t('detectedEntities')} ({detectionResult.detections?.length || 0})
              </h3>
              <div className="space-y-1.5">
                {detectionResult.detections?.map((det, i) => (
                  <div
                    key={i}
                    onClick={() => setSelectedBoxIndex(i === selectedBoxIndex ? null : i)}
                    className={`p-2.5 rounded-xl border flex items-center justify-between text-xs cursor-pointer transition-all ${
                      selectedBoxIndex === i
                        ? 'border-[#14382B] bg-[#FAF8F5]'
                        : 'border-[#EAE5DE] hover:bg-[#FAF8F5]'
                    }`}
                  >
                    <div className="flex items-center space-x-2">
                      <span
                        className={`w-2 h-2 rounded-full ${
                          det.severity === 'severe' ? 'bg-red-500' : 'bg-amber-500'
                        }`}
                      />
                      <span className="font-bold text-[#14382B]">{det.classLabel}</span>
                    </div>
                    <span className="font-semibold text-[#6B7280]">
                      {det.confidence}% {t('confidence')}
                    </span>
                  </div>
                ))}
              </div>
            </div>

            {/* Grounded Follow-up Agronomist Q&A Thread */}
            <div className="bg-white border border-[#EAE5DE] rounded-3xl p-4 shadow-xs space-y-3">
              <div className="flex items-center space-x-2 text-[#14382B]">
                <Bot className="w-5 h-5 text-[#2D6A4F]" />
                <h3 className="text-sm font-bold">{t('askAgronomist')}</h3>
              </div>

              <QAChatThread
                qaThread={detectionResult.qaThread}
                onAskQuestion={handleAskQuestion}
                loading={askingQA}
                cropName={translateCrop(detectionResult.cropName)}
              />
            </div>
          </div>
        )}
      </main>
    </div>
  );
};

export default YoloAnalysisPage;
