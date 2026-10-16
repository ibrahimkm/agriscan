import React, { useState, useRef, useEffect, useCallback } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import {
  Camera,
  RotateCcw,
  Zap,
  ZapOff,
  Image as ImageIcon,
  Check,
  ChevronLeft,
  Upload,
  RefreshCw,
  VideoOff,
} from 'lucide-react';
import { useLanguage } from '../context/LanguageContext';

export const DiagnosePage = () => {
  const navigate = useNavigate();
  const location = useLocation();
  const fileInputRef = useRef(null);
  const videoRef = useRef(null);
  const streamRef = useRef(null);
  const { t, translateCrop } = useLanguage();

  const preselectedCrop = location.state?.selectedCrop || null;

  const [cameraStatus, setCameraStatus] = useState('idle'); // 'idle' | 'requesting' | 'active' | 'denied' | 'unsupported' | 'error'
  const [errorMessage, setErrorMessage] = useState('');
  const [zoom, setZoom] = useState('1x');
  const [flash, setFlash] = useState(false);
  const [capturedImage, setCapturedImage] = useState(null);

  // Stop camera tracks cleanly
  const stopCamera = useCallback(() => {
    if (streamRef.current) {
      streamRef.current.getTracks().forEach((track) => {
        track.stop();
      });
      streamRef.current = null;
    }
    if (videoRef.current) {
      videoRef.current.srcObject = null;
    }
  }, []);

  // Initialize and request camera
  const startCamera = useCallback(async () => {
    // Stop any existing stream before starting a new one
    stopCamera();

    if (!navigator?.mediaDevices?.getUserMedia) {
      setCameraStatus('unsupported');
      setErrorMessage(
        'Camera access is not supported by this browser. Camera requires a secure (HTTPS) connection or localhost. You can upload an image from your files instead.'
      );
      return;
    }

    setCameraStatus('requesting');
    setErrorMessage('');

    try {
      const constraints = {
        video: {
          facingMode: { ideal: 'environment' },
          width: { ideal: 1920 },
          height: { ideal: 1080 },
        },
        audio: false,
      };

      const stream = await navigator.mediaDevices.getUserMedia(constraints);
      streamRef.current = stream;

      if (videoRef.current) {
        videoRef.current.srcObject = stream;
        videoRef.current.onloadedmetadata = () => {
          videoRef.current?.play().catch((playErr) => {
            console.warn('[DiagnosePage] Video play failed:', playErr);
          });
          setCameraStatus('active');
        };
      } else {
        setCameraStatus('active');
      }
    } catch (err) {
      console.warn('[DiagnosePage] Camera acquisition failed:', err);
      stopCamera();

      if (err.name === 'NotAllowedError' || err.name === 'PermissionDeniedError') {
        setCameraStatus('denied');
        setErrorMessage(
          'Camera permission was denied. Please allow camera permissions in your browser settings to scan leaves directly, or upload a photo from your gallery.'
        );
      } else if (err.name === 'NotFoundError' || err.name === 'DevicesNotFoundError') {
        setCameraStatus('unsupported');
        setErrorMessage('No camera device was detected. Please upload an image from your gallery or files.');
      } else if (err.name === 'NotReadableError' || err.name === 'TrackStartError') {
        setCameraStatus('error');
        setErrorMessage('Camera is currently in use by another application. Please close other camera apps and retry.');
      } else {
        setCameraStatus('error');
        setErrorMessage(err.message || 'Unable to access device camera.');
      }
    }
  }, [stopCamera]);

  // Clean up media tracks when leaving the component
  useEffect(() => {
    return () => {
      stopCamera();
    };
  }, [stopCamera]);

  // Handle shutter capture
  const handleCapture = () => {
    if (videoRef.current && videoRef.current.videoWidth > 0) {
      const video = videoRef.current;
      const canvas = document.createElement('canvas');
      canvas.width = video.videoWidth;
      canvas.height = video.videoHeight;
      const ctx = canvas.getContext('2d');
      ctx.drawImage(video, 0, 0, canvas.width, canvas.height);
      const dataUrl = canvas.toDataURL('image/jpeg', 0.95);
      setCapturedImage(dataUrl);
      stopCamera();
      setCameraStatus('idle');
    }
  };

  // Handle file upload
  const handleFileUpload = (e) => {
    const file = e.target.files?.[0];
    if (file) {
      if (!file.type.startsWith('image/')) {
        alert('Please select a valid image file (.jpg, .jpeg, .png, .webp)');
        return;
      }
      const reader = new FileReader();
      reader.onload = () => {
        setCapturedImage(reader.result);
        stopCamera();
        setCameraStatus('idle');
      };
      reader.readAsDataURL(file);
    }
  };

  const handleRetake = () => {
    setCapturedImage(null);
    startCamera();
  };

  const handleConfirm = () => {
    if (!capturedImage) return;
    navigate('/analyze', {
      state: {
        capturedImage,
        cropName: preselectedCrop,
      },
    });
  };

  const toggleFlash = async () => {
    const track = streamRef.current?.getVideoTracks()?.[0];
    if (track) {
      const capabilities = track.getCapabilities?.() || {};
      if (capabilities.torch) {
        try {
          await track.applyConstraints({ advanced: [{ torch: !flash }] });
          setFlash(!flash);
          return;
        } catch (e) {
          console.warn('[DiagnosePage] Torch constraint error:', e);
        }
      }
    }
    setFlash(!flash);
  };

  return (
    <div className="min-h-screen bg-black text-white flex flex-col justify-between relative select-none">
      {/* Top Controls Bar */}
      <div className="absolute top-0 left-0 right-0 z-30 p-4 flex items-center justify-between bg-gradient-to-b from-black/80 to-transparent">
        <button
          onClick={() => {
            stopCamera();
            navigate('/home');
          }}
          className="p-2 bg-black/40 backdrop-blur-md rounded-full text-white hover:bg-black/60 transition-colors"
          aria-label="Back to Home"
        >
          <ChevronLeft className="w-6 h-6 stroke-[2.5]" />
        </button>

        {/* Selected Crop or Neutral Badge */}
        <div className="bg-black/50 backdrop-blur-md px-3.5 py-1.5 rounded-full border border-white/20 text-xs font-semibold text-white flex items-center space-x-1.5 shadow-sm">
          <span className="w-2 h-2 rounded-full bg-[#22C55E]" />
          <span>
            {preselectedCrop ? translateCrop(preselectedCrop) : t('readyToScan') || 'Ready to scan'}
          </span>
        </div>

        {/* Flash Toggle */}
        <button
          onClick={toggleFlash}
          className="p-2 bg-black/40 backdrop-blur-md rounded-full text-white hover:bg-black/60 transition-colors"
          aria-label="Toggle Flash"
        >
          {flash ? <Zap className="w-5 h-5 text-[#EAB308]" /> : <ZapOff className="w-5 h-5 text-white/80" />}
        </button>
      </div>

      {/* Center Viewfinder Screen */}
      <div className="relative flex-1 flex items-center justify-center overflow-hidden bg-black">
        {/* State A: Captured Image Preview */}
        {capturedImage ? (
          <img
            src={capturedImage}
            alt="Captured leaf preview"
            className={`w-full h-full object-cover transition-transform duration-300 ${
              zoom === '2x' ? 'scale-125' : 'scale-100'
            }`}
          />
        ) : cameraStatus === 'active' ? (
          /* State B: Live Device Camera Stream */
          <video
            ref={videoRef}
            autoPlay
            playsInline
            muted
            className={`w-full h-full object-cover transition-transform duration-300 ${
              zoom === '2x' ? 'scale-125' : 'scale-100'
            }`}
          />
        ) : cameraStatus === 'requesting' ? (
          /* State C: Loading / Permission Prompt */
          <div className="flex flex-col items-center justify-center p-6 text-center space-y-4">
            <RefreshCw className="w-10 h-10 text-[#22C55E] animate-spin" />
            <p className="text-sm font-semibold text-white/90">Starting device camera...</p>
            <p className="text-xs text-white/60 max-w-xs">Please allow camera permissions if prompted by your browser.</p>
          </div>
        ) : cameraStatus === 'denied' || cameraStatus === 'unsupported' || cameraStatus === 'error' ? (
          /* State D: Permission Denied or Unsupported Screen */
          <div className="flex flex-col items-center justify-center p-6 text-center space-y-4 max-w-sm">
            <div className="w-14 h-14 rounded-full bg-red-950/80 border border-red-500/40 flex items-center justify-center text-red-400">
              <VideoOff className="w-7 h-7" />
            </div>
            <h3 className="text-base font-bold text-white">Camera Access Required</h3>
            <p className="text-xs text-white/70 leading-relaxed">{errorMessage}</p>
            <div className="flex flex-col sm:flex-row gap-2.5 w-full pt-2">
              <button
                onClick={startCamera}
                className="flex-1 py-2.5 px-4 rounded-xl bg-zinc-800 text-white font-semibold text-xs hover:bg-zinc-700 transition-colors flex items-center justify-center space-x-1.5"
              >
                <RefreshCw className="w-3.5 h-3.5" />
                <span>Retry Camera</span>
              </button>
              <button
                onClick={() => fileInputRef.current?.click()}
                className="flex-1 py-2.5 px-4 rounded-xl bg-[#14382B] text-white font-semibold text-xs hover:bg-[#1B4332] transition-colors flex items-center justify-center space-x-1.5"
              >
                <Upload className="w-3.5 h-3.5" />
                <span>Upload Photo</span>
              </button>
            </div>
          </div>
        ) : (
          /* State E: Idle - User prompts to Start Camera or Upload */
          <div className="flex flex-col items-center justify-center p-6 text-center space-y-4 max-w-sm">
            <div className="w-16 h-16 rounded-full bg-emerald-950/70 border border-emerald-500/30 flex items-center justify-center text-emerald-400">
              <Camera className="w-8 h-8" />
            </div>
            <h3 className="text-lg font-bold text-white">Live Foliage Diagnosis</h3>
            <p className="text-xs text-white/70 leading-relaxed">
              Open your camera to scan leaves in real-time with the EfficientNet neural network, or upload an image from your files.
            </p>
            <div className="flex flex-col gap-2.5 w-full pt-2">
              <button
                onClick={startCamera}
                className="w-full py-3 px-5 rounded-2xl bg-[#14382B] text-white font-bold text-sm shadow-lg hover:bg-[#1B4332] transition-colors flex items-center justify-center space-x-2"
              >
                <Camera className="w-4 h-4" />
                <span>Open Device Camera</span>
              </button>
              <button
                onClick={() => fileInputRef.current?.click()}
                className="w-full py-3 px-5 rounded-2xl bg-zinc-800 text-white font-semibold text-xs hover:bg-zinc-700 transition-colors flex items-center justify-center space-x-2"
              >
                <ImageIcon className="w-4 h-4 text-zinc-400" />
                <span>Upload from Gallery / Files</span>
              </button>
            </div>
          </div>
        )}

        {/* Viewfinder Alignment Reticle (only shown during active live stream) */}
        {!capturedImage && cameraStatus === 'active' && (
          <>
            <div className="absolute inset-0 bg-black/25 pointer-events-none" />
            <div className="absolute w-[80vw] max-w-[320px] aspect-[3/4] border-2 border-dashed border-white/90 rounded-[50%/40%] flex flex-col items-center justify-between p-4 pointer-events-none shadow-[0_0_0_9999px_rgba(0,0,0,0.35)]">
              <div className="w-4 h-1 bg-white/80 rounded-full" />
              <div className="w-full h-0.5 bg-[#22C55E] shadow-[0_0_8px_#22C55E] animate-pulse" />
              <div className="w-4 h-1 bg-white/80 rounded-full" />
            </div>

            {/* Guided Instruction Text */}
            <div className="absolute bottom-24 left-6 right-6 text-center z-20 pointer-events-none">
              <p className="text-xs md:text-sm font-medium text-white/90 drop-shadow-md bg-black/50 backdrop-blur-md py-2 px-4 rounded-full inline-block border border-white/10">
                {t('positionLeaf')}
              </p>
            </div>

            {/* 1x / 2x Zoom Toggle Button */}
            <div className="absolute bottom-6 right-6 z-20">
              <button
                onClick={() => setZoom(zoom === '1x' ? '2x' : '1x')}
                className="w-10 h-10 rounded-full bg-black/50 backdrop-blur-md border border-white/20 text-white font-bold text-xs flex items-center justify-center hover:bg-black/70 transition-colors"
                aria-label="Toggle Zoom"
              >
                {zoom}
              </button>
            </div>
          </>
        )}
      </div>

      {/* Hidden File Input for Gallery / Local Image Selection */}
      <input
        ref={fileInputRef}
        type="file"
        accept="image/*"
        onChange={handleFileUpload}
        className="hidden"
      />

      {/* Bottom Shutter & Action Controls */}
      <div
        className="px-4 py-4 sm:p-6 bg-gradient-to-t from-black via-black/90 to-transparent z-30 flex items-center justify-between max-w-md mx-auto w-full"
        style={{ paddingBottom: 'max(env(safe-area-inset-bottom, 0px), 1.25rem)' }}
      >
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
          // Live Camera Controls (Gallery, Shutter Button, Switch Camera / Refresh)
          <div className="flex items-center justify-between w-full">
            {/* Gallery Upload */}
            <button
              onClick={() => fileInputRef.current?.click()}
              className="p-3 bg-white/10 backdrop-blur-md rounded-2xl cursor-pointer hover:bg-white/20 transition-colors"
              title="Upload Photo"
              aria-label="Upload Photo"
            >
              <ImageIcon className="w-6 h-6 text-white" />
            </button>

            {/* Circular Shutter Button */}
            <button
              onClick={cameraStatus === 'active' ? handleCapture : startCamera}
              className={`w-20 h-20 rounded-full border-4 border-white/80 p-1 flex items-center justify-center hover:scale-105 active:scale-95 transition-transform ${
                cameraStatus !== 'active' ? 'opacity-80' : ''
              }`}
              aria-label={cameraStatus === 'active' ? 'Capture leaf photo' : 'Open Camera'}
            >
              <div
                className={`w-full h-full rounded-full shadow-lg ${
                  cameraStatus === 'active' ? 'bg-white' : 'bg-[#22C55E]'
                }`}
              />
            </button>

            {/* Reconnect / Toggle camera button */}
            <button
              onClick={startCamera}
              className="p-3 bg-white/10 backdrop-blur-md rounded-2xl hover:bg-white/20 transition-colors"
              title="Start or Restart Camera"
              aria-label="Restart Camera"
            >
              <Camera className="w-6 h-6 text-white" />
            </button>
          </div>
        )}
      </div>
    </div>
  );
};

export default DiagnosePage;
