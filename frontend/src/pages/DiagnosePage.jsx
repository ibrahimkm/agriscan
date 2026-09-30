import React, { useState, useRef } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import {
  Camera,
  RotateCcw,
  Zap,
  ZapOff,
  Image as ImageIcon,
  Check,
  ChevronLeft,
  ScanLine,
} from 'lucide-react';
import AppHeader from '../components/navigation/AppHeader';
import { useLanguage } from '../context/LanguageContext';

export const DiagnosePage = () => {
  const navigate = useNavigate();
  const location = useLocation();
  const fileInputRef = useRef(null);
  const { t, translateCrop } = useLanguage();

  const selectedCrop = location.state?.selectedCrop || 'Tomato';

  const [zoom, setZoom] = useState('1x');
  const [flash, setFlash] = useState(false);
  const [capturedImage, setCapturedImage] = useState(null);

  const sampleLeafImage =
    'https://images.unsplash.com/photo-1592417817098-8f3d6eb2260f?w=800&auto=format&fit=crop&q=80';

  const handleCapture = () => {
    setCapturedImage(sampleLeafImage);
  };

  const handleFileUpload = (e) => {
    const file = e.target.files?.[0];
    if (file) {
      const reader = new FileReader();
      reader.onload = () => {
        setCapturedImage(reader.result);
      };
      reader.readAsDataURL(file);
    }
  };

  const handleConfirm = () => {
    navigate('/analyze', {
      state: {
        capturedImage: capturedImage || sampleLeafImage,
        cropName: selectedCrop,
      },
    });
  };

  const handleRetake = () => {
    setCapturedImage(null);
  };

  return (
    <div className="min-h-screen bg-black text-white flex flex-col justify-between relative select-none">
      {/* Top Controls Bar (Matching Stitch Screen 3) */}
      <div className="absolute top-0 left-0 right-0 z-30 p-4 flex items-center justify-between bg-gradient-to-b from-black/80 to-transparent">
        <button
          onClick={() => navigate('/home')}
          className="p-2 bg-black/40 backdrop-blur-md rounded-full text-white hover:bg-black/60 transition-colors"
          aria-label="Back to Home"
        >
          <ChevronLeft className="w-6 h-6 stroke-[2.5]" />
        </button>

        {/* Selected Crop Badge */}
        <div className="bg-black/50 backdrop-blur-md px-3.5 py-1 rounded-full border border-white/20 text-xs font-bold text-white flex items-center space-x-1.5">
          <span className="w-2 h-2 rounded-full bg-[#22C55E]" />
          <span>{translateCrop(selectedCrop)}</span>
        </div>

        {/* Flash Toggle */}
        <button
          onClick={() => setFlash(!flash)}
          className="p-2 bg-black/40 backdrop-blur-md rounded-full text-white hover:bg-black/60 transition-colors"
          aria-label="Toggle Flash"
        >
          {flash ? <Zap className="w-5 h-5 text-[#EAB308]" /> : <ZapOff className="w-5 h-5 text-white/80" />}
        </button>
      </div>

      {/* Center Viewfinder Screen (Matching Stitch Screen 3) */}
      <div className="relative flex-1 flex items-center justify-center overflow-hidden">
        {/* Background / Camera Stream Preview */}
        <img
          src={capturedImage || sampleLeafImage}
          alt="Viewfinder Stream"
          className={`w-full h-full object-cover transition-transform duration-300 ${
            zoom === '2x' ? 'scale-125' : 'scale-100'
          }`}
        />

        {/* Darkening Mask with Transparent Target Area */}
        <div className="absolute inset-0 bg-black/35 pointer-events-none" />

        {/* Dashed Alignment Oval (Exact Stitch Screen 3 Spec) */}
        {!capturedImage && (
          <div className="absolute w-[80vw] max-w-[320px] aspect-[3/4] border-2 border-dashed border-white/90 rounded-[50%/40%] flex flex-col items-center justify-between p-4 pointer-events-none shadow-[0_0_0_9999px_rgba(0,0,0,0.35)]">
            {/* Top Reticle Marker */}
            <div className="w-4 h-1 bg-white/80 rounded-full" />

            {/* Scanning Laser Animation */}
            <div className="w-full h-0.5 bg-[#22C55E] shadow-[0_0_8px_#22C55E] animate-pulse" />

            {/* Bottom Reticle Marker */}
            <div className="w-4 h-1 bg-white/80 rounded-full" />
          </div>
        )}

        {/* Guided Instruction Text */}
        {!capturedImage && (
          <div className="absolute bottom-24 left-6 right-6 text-center z-20">
            <p className="text-xs md:text-sm font-medium text-white/90 drop-shadow-md bg-black/40 backdrop-blur-md py-2 px-4 rounded-full inline-block border border-white/10">
              {t('positionLeaf')}
            </p>
          </div>
        )}

        {/* 1x / 2x Zoom Toggle Button */}
        {!capturedImage && (
          <div className="absolute bottom-6 right-6 z-20">
            <button
              onClick={() => setZoom(zoom === '1x' ? '2x' : '1x')}
              className="w-10 h-10 rounded-full bg-black/50 backdrop-blur-md border border-white/20 text-white font-bold text-xs flex items-center justify-center hover:bg-black/70 transition-colors"
            >
              {zoom}
            </button>
          </div>
        )}
      </div>

      {/* Bottom Shutter & Action Controls (Matching Stitch Screen 3) */}
      <div className="p-6 bg-gradient-to-t from-black via-black/90 to-transparent z-30 flex items-center justify-between max-w-md mx-auto w-full">
        {capturedImage ? (
          // Post-capture Action Buttons (Retake / Analyze)
          <div className="flex items-center justify-between w-full space-x-4">
            <button
              onClick={handleRetake}
              className="flex-1 py-3.5 rounded-2xl bg-zinc-800 text-white font-bold text-xs md:text-sm hover:bg-zinc-700 transition-colors flex items-center justify-center space-x-2"
            >
              <RotateCcw className="w-4 h-4" />
              <span>{t('retake')}</span>
            </button>

            <button
              onClick={handleConfirm}
              className="flex-1 py-3.5 rounded-2xl bg-[#14382B] text-white font-bold text-xs md:text-sm shadow-lg hover:bg-[#1B4332] transition-colors flex items-center justify-center space-x-2"
            >
              <Check className="w-4 h-4" />
              <span>{t('analyzeLeaf')}</span>
            </button>
          </div>
        ) : (
          // Live Camera Controls (Gallery, Shutter Button, Switch)
          <>
            {/* Gallery Upload */}
            <label className="p-3 bg-white/10 backdrop-blur-md rounded-2xl cursor-pointer hover:bg-white/20 transition-colors">
              <ImageIcon className="w-6 h-6 text-white" />
              <input
                ref={fileInputRef}
                type="file"
                accept="image/*"
                onChange={handleFileUpload}
                className="hidden"
              />
            </label>

            {/* Big Circular Shutter Button */}
            <button
              onClick={handleCapture}
              className="w-20 h-20 rounded-full border-4 border-white/80 p-1 flex items-center justify-center hover:scale-105 active:scale-95 transition-transform"
              aria-label="Capture photo"
            >
              <div className="w-full h-full bg-white rounded-full shadow-lg" />
            </button>

            {/* Manual Sample Load */}
            <button
              onClick={handleCapture}
              className="p-3 bg-white/10 backdrop-blur-md rounded-2xl hover:bg-white/20 transition-colors"
              title="Use Sample Photo"
            >
              <ScanLine className="w-6 h-6 text-white" />
            </button>
          </>
        )}
      </div>
    </div>
  );
};

export default DiagnosePage;
