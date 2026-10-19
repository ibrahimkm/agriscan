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
  SwitchCamera,
} from 'lucide-react';
import { useLanguage } from '../context/LanguageContext';

export const DiagnosePage = () => {
  const navigate = useNavigate();
  const location = useLocation();
  const fileInputRef = useRef(null);
  const videoRef = useRef(null);
  const streamRef = useRef(null);
  const isMountedRef = useRef(true);
  const activeSessionIdRef = useRef(0);
  const initTimeoutRef = useRef(null);
  const frameCallbackIdRef = useRef(null);
  const { t, translateCrop } = useLanguage();

  const preselectedCrop = location.state?.selectedCrop || null;

  // Explicit lifecycle states:
  // 'idle' | 'requesting_permission' | 'starting' | 'active' (ready) | 'capturing' | 'denied' | 'unsupported' | 'error'
  const [cameraStatus, setCameraStatus] = useState('idle');
  const [errorMessage, setErrorMessage] = useState('');
  const [errorType, setErrorType] = useState(null); // 'permission' | 'unsupported' | 'in_use' | 'timeout' | 'playback' | 'unknown'
  const [isVideoReady, setIsVideoReady] = useState(false);
  const [zoom, setZoom] = useState('1x');
  const [flash, setFlash] = useState(false);
  const [facingMode, setFacingMode] = useState('environment'); // 'environment' | 'user'
  const [capturedImage, setCapturedImage] = useState(null);

  // Stop all camera tracks cleanly and reset stream references
  const stopCamera = useCallback(() => {
    // Invalidate any active startup session
    activeSessionIdRef.current += 1;

    // Clear initialization timeout
    if (initTimeoutRef.current) {
      clearTimeout(initTimeoutRef.current);
      initTimeoutRef.current = null;
    }

    // Cancel any registered video frame callback
    if (frameCallbackIdRef.current && videoRef.current?.cancelVideoFrameCallback) {
      try {
        videoRef.current.cancelVideoFrameCallback(frameCallbackIdRef.current);
      } catch {
        // ignore
      }
      frameCallbackIdRef.current = null;
    }

    if (streamRef.current) {
      try {
        streamRef.current.getTracks().forEach((track) => {
          track.stop();
        });
      } catch (e) {
        console.warn('[DiagnosePage] Error stopping tracks:', e);
      }
      streamRef.current = null;
    }

    if (videoRef.current) {
      try {
        videoRef.current.pause();
        videoRef.current.srcObject = null;
        videoRef.current.onloadedmetadata = null;
        videoRef.current.oncanplay = null;
        videoRef.current.onplaying = null;
        videoRef.current.ontimeupdate = null;
      } catch {
        // ignore
      }
    }
    setIsVideoReady(false);
  }, []);

  // Initialize and request camera stream with progressive fallback
  const startCamera = useCallback(async (requestedFacing = facingMode) => {
    // 1. Stop any existing stream AND invalidate all prior sessions FIRST
    stopCamera();

    // 2. Generate a fresh session ID for this new attempt
    const currentSessionId = ++activeSessionIdRef.current;

    // 3. Verify secure context and browser media support
    const isSecure =
      window.isSecureContext ||
      window.location.hostname === 'localhost' ||
      window.location.hostname === '127.0.0.1';

    if (!navigator?.mediaDevices?.getUserMedia) {
      setCameraStatus('unsupported');
      setErrorType('unsupported');
      setErrorMessage(
        !isSecure
          ? 'Camera access requires a secure connection (HTTPS). Please open AgriScan over HTTPS or upload a photo from your gallery.'
          : 'Camera access is not supported by this browser. You can upload an image from your files instead.'
      );
      return;
    }

    setCameraStatus('requesting_permission');
    setErrorMessage('');
    setErrorType(null);
    setIsVideoReady(false);

    // 4. Arm initialization timeout (10 seconds)
    initTimeoutRef.current = setTimeout(() => {
      if (!isMountedRef.current || currentSessionId !== activeSessionIdRef.current) return;
      console.warn('[DiagnosePage] Camera frame initialization timed out after 10s.');
      stopCamera();
      setCameraStatus('error');
      setErrorType('timeout');
      setErrorMessage(
        'Camera initialization timed out. The camera hardware may be busy or unresponsive. Please tap Retry Camera or upload a photo from your gallery.'
      );
    }, 10000);

    try {
      // 5. Try ideal rear-facing (or requested) camera with standard mobile resolution
      let stream = null;
      try {
        const constraints =
          requestedFacing === 'user'
            ? {
                video: {
                  facingMode: { ideal: 'user' },
                  width: { ideal: 1280 },
                  height: { ideal: 720 },
                },
                audio: false,
              }
            : {
                video: {
                  facingMode: { ideal: 'environment' },
                  width: { ideal: 1280 },
                  height: { ideal: 720 },
                },
                audio: false,
              };
        stream = await navigator.mediaDevices.getUserMedia(constraints);
      } catch (envErr) {
        console.warn('[DiagnosePage] Preferred camera constraints failed, attempting fallback:', envErr?.name);
        // Progressive fallback: generic video input without restrictive constraints
        stream = await navigator.mediaDevices.getUserMedia({
          video: true,
          audio: false,
        });
      }

      // Check if session was cancelled or component unmounted while awaiting user permission
      if (!isMountedRef.current || currentSessionId !== activeSessionIdRef.current) {
        stream.getTracks().forEach((track) => track.stop());
        return;
      }

      streamRef.current = stream;
      setCameraStatus('starting');

      // Handle external stream interruption
      stream.getVideoTracks().forEach((track) => {
        track.onended = () => {
          if (isMountedRef.current && currentSessionId === activeSessionIdRef.current) {
            stopCamera();
            setCameraStatus('idle');
          }
        };
      });

      const video = videoRef.current;
      if (video) {
        video.srcObject = stream;
        video.setAttribute('playsinline', 'true');
        video.setAttribute('webkit-playsinline', 'true');
        video.muted = true;

        // Video readiness checker: confirms video frame dimensions before marking ready
        const markReady = () => {
          if (!isMountedRef.current || currentSessionId !== activeSessionIdRef.current) return;
          if (video && video.videoWidth > 0 && video.videoHeight > 0) {
            if (initTimeoutRef.current) {
              clearTimeout(initTimeoutRef.current);
              initTimeoutRef.current = null;
            }
            setIsVideoReady(true);
            setCameraStatus('active');
          }
        };

        video.onloadedmetadata = () => {
          markReady();
          video
            .play()
            .then(() => markReady())
            .catch((playErr) => {
              if (playErr?.name !== 'AbortError') {
                console.warn('[DiagnosePage] video.play() error on metadata:', playErr);
              }
              markReady();
            });
        };

        video.oncanplay = markReady;
        video.onplaying = markReady;
        video.ontimeupdate = markReady;

        // Modern browsers: requestVideoFrameCallback confirms first rendered frame
        if ('requestVideoFrameCallback' in video) {
          frameCallbackIdRef.current = video.requestVideoFrameCallback(() => {
            markReady();
          });
        }

        // Direct play invocation
        video
          .play()
          .then(() => markReady())
          .catch((playErr) => {
            if (playErr?.name !== 'AbortError') {
              console.warn('[DiagnosePage] Direct video.play() error:', playErr);
            }
          });
      } else {
        if (initTimeoutRef.current) {
          clearTimeout(initTimeoutRef.current);
          initTimeoutRef.current = null;
        }
        setCameraStatus('active');
        setIsVideoReady(true);
      }
    } catch (err) {
      if (!isMountedRef.current || currentSessionId !== activeSessionIdRef.current) return;

      console.warn('[DiagnosePage] Camera acquisition error:', err);
      stopCamera();

      if (err.name === 'NotAllowedError' || err.name === 'PermissionDeniedError') {
        setCameraStatus('denied');
        setErrorType('permission');
        setErrorMessage(
          'Camera permission was blocked. Please tap the lock/settings icon next to your browser address bar to allow Camera access for AgriScan, or upload an image from your gallery.'
        );
      } else if (err.name === 'NotFoundError' || err.name === 'DevicesNotFoundError') {
        setCameraStatus('unsupported');
        setErrorType('unsupported');
        setErrorMessage('No camera device was detected on your hardware. Please upload an image from your files.');
      } else if (err.name === 'NotReadableError' || err.name === 'TrackStartError') {
        setCameraStatus('error');
        setErrorType('in_use');
        setErrorMessage(
          'Camera is currently in use by another application or tab. Please close other camera apps and retry.'
        );
      } else {
        setCameraStatus('error');
        setErrorType('unknown');
        setErrorMessage(err.message || 'Unable to access device camera.');
      }
    }
  }, [facingMode, stopCamera]);

  // Clean up media tracks when leaving the component and auto-start on mount
  useEffect(() => {
    isMountedRef.current = true;
    startCamera();
    return () => {
      isMountedRef.current = false;
      stopCamera();
    };
  }, [startCamera, stopCamera]);

  // Toggle between front and rear cameras cleanly
  const handleToggleFacingMode = useCallback(() => {
    const nextMode = facingMode === 'environment' ? 'user' : 'environment';
    setFacingMode(nextMode);
    startCamera(nextMode);
  }, [facingMode, startCamera]);

  // Handle shutter capture: reads frame from active video element to off-screen canvas
  const handleCapture = () => {
    const video = videoRef.current;
    if (video && video.videoWidth > 0 && video.videoHeight > 0) {
      try {
        setCameraStatus('capturing');
        const canvas = document.createElement('canvas');
        canvas.width = video.videoWidth;
        canvas.height = video.videoHeight;
        const ctx = canvas.getContext('2d');
        if (!ctx) {
          setCameraStatus('active');
          return;
        }

        ctx.drawImage(video, 0, 0, canvas.width, canvas.height);
        const dataUrl = canvas.toDataURL('image/jpeg', 0.95);

        // Validate nonempty capture
        if (!dataUrl || dataUrl === 'data:,' || dataUrl.length < 200) {
          console.warn('[DiagnosePage] Canvas capture returned empty data URL.');
          setCameraStatus('active');
          return;
        }

        setCapturedImage(dataUrl);
        stopCamera();
        setCameraStatus('idle');
      } catch (err) {
        console.error('[DiagnosePage] Capture frame error:', err);
        setCameraStatus('active');
      }
    } else {
      console.warn('[DiagnosePage] Cannot capture from 0x0 video dimensions.');
    }
  };

  // Handle file upload from gallery
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

  const isReady = cameraStatus === 'active' && isVideoReady;

  return (
    <div className="h-screen h-[100dvh] max-h-[100dvh] w-full bg-black text-white flex flex-col justify-between relative select-none overflow-hidden">
      {/* Top Controls Bar */}
      <div className="absolute top-0 left-0 right-0 z-30 p-3.5 sm:p-4 flex items-center justify-between bg-gradient-to-b from-black/80 to-transparent">
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

        {/* Selected Crop or Truthful Dynamic Status Badge */}
        <div className="bg-black/50 backdrop-blur-md px-3.5 py-1.5 rounded-full border border-white/20 text-xs font-semibold text-white flex items-center space-x-1.5 shadow-sm">
          <span
            className={`w-2 h-2 rounded-full ${
              isReady
                ? 'bg-[#22C55E]'
                : cameraStatus === 'denied' || cameraStatus === 'unsupported' || cameraStatus === 'error'
                ? 'bg-red-500'
                : cameraStatus === 'idle'
                ? 'bg-zinc-400'
                : 'bg-amber-400 animate-pulse'
            }`}
          />
          <span>
            {preselectedCrop
              ? translateCrop(preselectedCrop)
              : isReady
              ? t('readyToScan') || 'Ready to scan'
              : cameraStatus === 'requesting_permission' || cameraStatus === 'requesting'
              ? 'Requesting permission...'
              : cameraStatus === 'starting'
              ? 'Starting camera...'
              : cameraStatus === 'capturing'
              ? 'Capturing...'
              : cameraStatus === 'denied'
              ? 'Permission required'
              : cameraStatus === 'unsupported' || cameraStatus === 'error'
              ? 'Camera unavailable'
              : 'Camera ready'}
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
      <div className="relative flex-1 min-h-0 w-full flex items-center justify-center overflow-hidden bg-black">
        {/* Continuously Mounted Video Feed - Positioned absolute so layout engine computes videoWidth */}
        <video
          ref={videoRef}
          autoPlay
          playsInline
          muted
          className={`absolute inset-0 w-full h-full object-cover transition-opacity duration-300 ${
            zoom === '2x' ? 'scale-125' : 'scale-100'
          } ${cameraStatus === 'active' && !capturedImage ? 'opacity-100 z-0' : 'opacity-0 pointer-events-none -z-10'}`}
        />

        {/* State A: Captured Image Preview */}
        {capturedImage && (
          <img
            src={capturedImage}
            alt="Captured leaf preview"
            className={`max-w-full max-h-full w-full h-full object-contain transition-transform duration-300 z-10 ${
              zoom === '2x' ? 'scale-125' : 'scale-100'
            }`}
          />
        )}

        {/* State C: Loading / Permission Prompt Overlay */}
        {!capturedImage &&
          (cameraStatus === 'requesting_permission' ||
            cameraStatus === 'starting' ||
            cameraStatus === 'requesting') && (
            <div className="flex flex-col items-center justify-center p-6 text-center space-y-4 z-20">
              <RefreshCw className="w-10 h-10 text-[#22C55E] animate-spin" />
              <p className="text-sm font-semibold text-white/90">Starting device camera...</p>
              <p className="text-xs text-white/60 max-w-xs">
                {cameraStatus === 'starting'
                  ? 'Initializing video feed...'
                  : 'Please allow camera permissions if prompted by your browser.'}
              </p>
            </div>
          )}

        {/* State D: Permission Denied or Unsupported Screen */}
        {!capturedImage &&
          (cameraStatus === 'denied' || cameraStatus === 'unsupported' || cameraStatus === 'error') && (
            <div className="flex flex-col items-center justify-center p-6 text-center space-y-4 max-w-sm z-20">
              <div className="w-14 h-14 rounded-full bg-red-950/80 border border-red-500/40 flex items-center justify-center text-red-400">
                <VideoOff className="w-7 h-7" />
              </div>
              <h3 className="text-base font-bold text-white">
                {errorType === 'permission'
                  ? 'Camera Permission Required'
                  : errorType === 'timeout'
                  ? 'Camera Startup Timed Out'
                  : errorType === 'in_use'
                  ? 'Camera Already In Use'
                  : 'Camera Access Required'}
              </h3>
              <p className="text-xs text-white/70 leading-relaxed">{errorMessage}</p>
              <div className="flex flex-col sm:flex-row gap-2.5 w-full pt-2">
                <button
                  onClick={() => startCamera()}
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
          )}

        {/* State E: Idle - User prompts to Start Camera or Upload */}
        {!capturedImage && cameraStatus === 'idle' && (
          <div className="flex flex-col items-center justify-center p-6 text-center space-y-4 max-w-sm z-20">
            <div className="w-16 h-16 rounded-full bg-emerald-950/70 border border-emerald-500/30 flex items-center justify-center text-emerald-400">
              <Camera className="w-8 h-8" />
            </div>
            <h3 className="text-lg font-bold text-white">Live Foliage Diagnosis</h3>
            <p className="text-xs text-white/70 leading-relaxed">
              Open your camera to scan leaves in real-time with the EfficientNet neural network, or upload an image from your files.
            </p>
            <div className="flex flex-col gap-2.5 w-full pt-2">
              <button
                onClick={() => startCamera()}
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
            <div className="absolute inset-0 bg-black/25 pointer-events-none z-10" />
            <div className="absolute w-[80vw] max-w-[320px] aspect-[3/4] border-2 border-dashed border-white/90 rounded-[50%/40%] flex flex-col items-center justify-between p-4 pointer-events-none shadow-[0_0_0_9999px_rgba(0,0,0,0.35)] z-10">
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
        className="shrink-0 px-4 py-4 sm:p-6 bg-gradient-to-t from-black via-black/90 to-transparent z-30 flex items-center justify-between max-w-md mx-auto w-full"
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

            {/* Circular Shutter Button - Enabled when stream is active & video is ready */}
            <button
              onClick={cameraStatus === 'active' && isVideoReady ? handleCapture : () => startCamera()}
              className={`w-20 h-20 rounded-full border-4 border-white/80 p-1 flex items-center justify-center hover:scale-105 active:scale-95 transition-transform ${
                cameraStatus === 'requesting_permission' || cameraStatus === 'starting'
                  ? 'opacity-50 cursor-wait'
                  : ''
              }`}
              aria-label={cameraStatus === 'active' && isVideoReady ? 'Capture leaf photo' : 'Open Camera'}
            >
              <div
                className={`w-full h-full rounded-full shadow-lg ${
                  cameraStatus === 'active' && isVideoReady
                    ? 'bg-white'
                    : cameraStatus === 'requesting_permission' || cameraStatus === 'starting'
                    ? 'bg-[#22C55E] animate-pulse'
                    : 'bg-[#22C55E]'
                }`}
              />
            </button>

            {/* Switch Camera Button (Front / Rear) */}
            <button
              onClick={handleToggleFacingMode}
              className="p-3 bg-white/10 backdrop-blur-md rounded-2xl hover:bg-white/20 transition-colors"
              title={facingMode === 'environment' ? 'Switch to Front Camera' : 'Switch to Rear Camera'}
              aria-label="Switch Camera"
            >
              <SwitchCamera className="w-6 h-6 text-white" />
            </button>
          </div>
        )}
      </div>
    </div>
  );
};

export default DiagnosePage;
