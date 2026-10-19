import React, { useState, useRef, useEffect, useCallback } from 'react';
import { Info, RotateCcw, X, Check, VideoOff, RefreshCw, Upload } from 'lucide-react';

export const CameraCapture = ({ onCapture, onCancel }) => {
  const [zoom, setZoom] = useState('1x');
  const [cameraStatus, setCameraStatus] = useState('idle'); // 'idle' | 'requesting' | 'active' | 'denied' | 'unsupported' | 'error'
  const [errorMessage, setErrorMessage] = useState('');
  const [isVideoReady, setIsVideoReady] = useState(false);
  const [capturedImage, setCapturedImage] = useState(null);
  const videoRef = useRef(null);
  const streamRef = useRef(null);
  const fileInputRef = useRef(null);
  const isMountedRef = useRef(true);
  const activeSessionIdRef = useRef(0);
  const initTimeoutRef = useRef(null);

  const stopCamera = useCallback(() => {
    activeSessionIdRef.current += 1;
    if (initTimeoutRef.current) {
      clearTimeout(initTimeoutRef.current);
      initTimeoutRef.current = null;
    }
    if (streamRef.current) {
      try {
        streamRef.current.getTracks().forEach((track) => track.stop());
      } catch (e) {
        console.warn('[CameraCapture] Error stopping tracks:', e);
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

  const startCamera = useCallback(async () => {
    // 1. Invalidate previous sessions and stop existing tracks FIRST
    stopCamera();

    // 2. Generate a fresh session ID for this specific attempt
    const currentSessionId = ++activeSessionIdRef.current;

    const isSecure =
      window.isSecureContext ||
      window.location.hostname === 'localhost' ||
      window.location.hostname === '127.0.0.1';

    if (!navigator?.mediaDevices?.getUserMedia) {
      setCameraStatus('unsupported');
      setErrorMessage(
        !isSecure
          ? 'Camera access requires a secure connection (HTTPS). Please open AgriScan over HTTPS or upload a photo from your files.'
          : 'Camera access is not supported by your browser.'
      );
      return;
    }

    setCameraStatus('requesting');
    setErrorMessage('');
    setIsVideoReady(false);

    // Timeout fallback after 10s
    initTimeoutRef.current = setTimeout(() => {
      if (!isMountedRef.current || currentSessionId !== activeSessionIdRef.current) return;
      stopCamera();
      setCameraStatus('error');
      setErrorMessage('Camera initialization timed out. Please tap Retry or upload a file.');
    }, 10000);

    try {
      let stream = null;
      try {
        stream = await navigator.mediaDevices.getUserMedia({
          video: { facingMode: { ideal: 'environment' }, width: { ideal: 1280 }, height: { ideal: 720 } },
          audio: false,
        });
      } catch {
        stream = await navigator.mediaDevices.getUserMedia({ video: true, audio: false });
      }

      if (!isMountedRef.current || currentSessionId !== activeSessionIdRef.current) {
        stream.getTracks().forEach((track) => track.stop());
        return;
      }

      streamRef.current = stream;

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

        const checkReadiness = () => {
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
          checkReadiness();
          video
            .play()
            .then(() => checkReadiness())
            .catch((err) => {
              if (err?.name !== 'AbortError') {
                console.warn('[CameraCapture] Video play error:', err);
              }
              checkReadiness();
            });
        };

        video.oncanplay = checkReadiness;
        video.onplaying = checkReadiness;
        video.ontimeupdate = checkReadiness;

        if ('requestVideoFrameCallback' in video) {
          video.requestVideoFrameCallback(() => checkReadiness());
        }

        video
          .play()
          .then(() => checkReadiness())
          .catch((err) => {
            if (err?.name !== 'AbortError') {
              console.warn('[CameraCapture] Immediate play error:', err);
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
      stopCamera();
      if (err.name === 'NotAllowedError' || err.name === 'PermissionDeniedError') {
        setCameraStatus('denied');
        setErrorMessage('Camera permission was blocked. Please allow camera permissions in browser settings or upload from files.');
      } else if (err.name === 'NotFoundError' || err.name === 'DevicesNotFoundError') {
        setCameraStatus('unsupported');
        setErrorMessage('No camera hardware found on this device.');
      } else if (err.name === 'NotReadableError' || err.name === 'TrackStartError') {
        setCameraStatus('error');
        setErrorMessage('Camera is currently in use by another app or tab.');
      } else {
        setCameraStatus('error');
        setErrorMessage(err.message || 'Unable to access camera.');
      }
    }
  }, [stopCamera]);

  useEffect(() => {
    isMountedRef.current = true;
    startCamera();
    return () => {
      isMountedRef.current = false;
      stopCamera();
    };
  }, [startCamera, stopCamera]);

  const handleCapture = () => {
    const video = videoRef.current;
    if (cameraStatus === 'active' && video && video.videoWidth > 0 && video.videoHeight > 0) {
      const canvas = document.createElement('canvas');
      canvas.width = video.videoWidth;
      canvas.height = video.videoHeight;
      const ctx = canvas.getContext('2d');
      if (!ctx) return;
      ctx.drawImage(video, 0, 0, canvas.width, canvas.height);
      const dataUrl = canvas.toDataURL('image/jpeg', 0.95);

      if (!dataUrl || dataUrl === 'data:,' || dataUrl.length < 200) {
        console.warn('[CameraCapture] Empty frame captured.');
        return;
      }

      setCapturedImage(dataUrl);
      stopCamera();
    }
  };

  const handleFileUpload = (e) => {
    const file = e.target.files?.[0];
    if (file) {
      const reader = new FileReader();
      reader.onload = () => {
        setCapturedImage(reader.result);
        stopCamera();
      };
      reader.readAsDataURL(file);
    }
  };

  const handleRetake = () => {
    setCapturedImage(null);
    startCamera();
  };

  const confirmCapture = () => {
    if (capturedImage && onCapture) {
      onCapture(capturedImage);
    }
  };

  return (
    <div className="relative w-full h-[calc(100dvh-60px)] md:h-[680px] max-w-full bg-black text-white flex flex-col justify-between overflow-hidden md:rounded-3xl shadow-2xl">
      {/* Top Banner Guide */}
      <div className="absolute top-4 left-4 right-4 z-20 flex items-center justify-between">
        <div className="bg-[#FAF8F5]/90 backdrop-blur-md text-[#14382B] p-3 rounded-2xl flex items-center space-x-2.5 shadow-lg border border-white/40 flex-1 mr-3">
          <Info className="w-5 h-5 text-[#2D6A4F] shrink-0" />
          <p className="text-xs md:text-sm font-medium leading-tight">
            Position leaf inside the frame in good natural lighting.
          </p>
        </div>
        {onCancel && (
          <button
            onClick={() => {
              stopCamera();
              onCancel();
            }}
            className="p-3 bg-black/60 backdrop-blur-md rounded-2xl text-white hover:bg-black/80 transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
        )}
      </div>

      {/* Viewfinder Main Feed */}
      <div className="relative w-full h-full flex items-center justify-center bg-zinc-950 overflow-hidden">
        {/* Continuously Mounted Video Element */}
        <video
          ref={videoRef}
          autoPlay
          playsInline
          muted
          className={`absolute inset-0 w-full h-full object-cover transition-opacity duration-300 ${
            zoom === '2x' ? 'scale-150' : 'scale-100'
          } ${cameraStatus === 'active' && !capturedImage ? 'opacity-100 z-0' : 'opacity-0 pointer-events-none -z-10'}`}
        />

        {capturedImage ? (
          <img
            src={capturedImage}
            alt="Captured leaf preview"
            className="max-w-full max-h-full w-full h-full object-contain"
          />
        ) : cameraStatus === 'requesting' ? (
          <div className="flex flex-col items-center justify-center p-6 text-center space-y-3 z-10">
            <RefreshCw className="w-8 h-8 text-[#22C55E] animate-spin" />
            <p className="text-xs font-semibold text-zinc-300">Connecting to camera...</p>
          </div>
        ) : cameraStatus !== 'active' ? (
          <div className="flex flex-col items-center justify-center p-6 text-center space-y-3 max-w-xs z-10">
            <VideoOff className="w-10 h-10 text-red-400" />
            <h4 className="text-sm font-bold text-white">Camera Unavailable</h4>
            <p className="text-xs text-zinc-400">{errorMessage || 'Could not access device camera.'}</p>
            <div className="flex gap-2 pt-2 w-full">
              <button
                onClick={startCamera}
                className="flex-1 py-2 px-3 rounded-xl bg-zinc-800 text-xs font-semibold hover:bg-zinc-700"
              >
                Retry
              </button>
              <button
                onClick={() => fileInputRef.current?.click()}
                className="flex-1 py-2 px-3 rounded-xl bg-[#14382B] text-xs font-semibold hover:bg-[#1B4332]"
              >
                Upload File
              </button>
            </div>
          </div>
        ) : null}

        {/* Reticle */}
        {!capturedImage && cameraStatus === 'active' && (
          <div className="absolute inset-0 pointer-events-none flex items-center justify-center">
            <div className="w-[280px] h-[390px] md:w-[320px] md:h-[430px] rounded-[50%] border-2 border-dashed border-white/70 animate-pulse flex items-center justify-center">
              <div className="w-2.5 h-2.5 rounded-full bg-white/80 shadow-md" />
            </div>
          </div>
        )}
      </div>

      <input
        ref={fileInputRef}
        type="file"
        accept="image/*"
        onChange={handleFileUpload}
        className="hidden"
      />

      {/* Shutter / Action Bar */}
      <div className="p-4 bg-gradient-to-t from-black via-black/80 to-transparent z-20 flex items-center justify-between">
        {capturedImage ? (
          <div className="flex gap-3 w-full">
            <button
              onClick={handleRetake}
              className="flex-1 py-3 rounded-xl bg-zinc-800 text-white font-semibold text-xs flex items-center justify-center space-x-1.5"
            >
              <RotateCcw className="w-4 h-4" />
              <span>Retake</span>
            </button>
            <button
              onClick={confirmCapture}
              className="flex-1 py-3 rounded-xl bg-[#14382B] text-white font-semibold text-xs flex items-center justify-center space-x-1.5"
            >
              <Check className="w-4 h-4" />
              <span>Diagnose Leaf</span>
            </button>
          </div>
        ) : (
          <div className="flex items-center justify-between w-full max-w-xs mx-auto">
            <button
              onClick={() => fileInputRef.current?.click()}
              className="p-3 bg-zinc-800/80 rounded-2xl hover:bg-zinc-700 transition-colors"
              title="Upload file"
              aria-label="Upload file"
            >
              <Upload className="w-5 h-5 text-white" />
            </button>

            <button
              onClick={cameraStatus === 'active' && isVideoReady ? handleCapture : startCamera}
              aria-label={cameraStatus === 'active' ? 'Capture leaf photo' : 'Open Camera'}
              className="w-16 h-16 rounded-full border-4 border-white/80 p-1 flex items-center justify-center hover:scale-105 active:scale-95 transition-transform"
            >
              <div
                className={`w-full h-full rounded-full ${
                  cameraStatus === 'active' && isVideoReady ? 'bg-white' : 'bg-[#22C55E]'
                }`}
              />
            </button>

            <button
              onClick={() => setZoom(zoom === '1x' ? '2x' : '1x')}
              className="p-3 bg-zinc-800/80 rounded-2xl hover:bg-zinc-700 transition-colors text-xs font-bold"
              aria-label="Toggle Zoom"
            >
              {zoom}
            </button>
          </div>
        )}
      </div>
    </div>
  );
};

export default CameraCapture;
