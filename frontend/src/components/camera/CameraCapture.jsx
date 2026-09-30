import React, { useState, useRef, useEffect } from 'react';
import { Camera, Image as ImageIcon, Zap, ZapOff, Info, RotateCcw, X, Check } from 'lucide-react';

export const CameraCapture = ({ onCapture, onCancel }) => {
  const [zoom, setZoom] = useState('1x');
  const [flash, setFlash] = useState(false);
  const [streamActive, setStreamActive] = useState(false);
  const [capturedImage, setCapturedImage] = useState(null);
  const [permissionError, setPermissionError] = useState(false);
  const videoRef = useRef(null);
  const fileInputRef = useRef(null);

  // Sample realistic leaf images for easy testing in browser without physical camera
  const sampleLeaves = [
    { name: 'Tomato Leaf (Early Blight)', url: 'https://images.unsplash.com/photo-1592417817098-8f3d6eb2260f?w=800&auto=format&fit=crop&q=80' },
    { name: 'Soybean Leaf (Septoria)', url: 'https://images.unsplash.com/photo-1574943320219-553eb213f72d?w=800&auto=format&fit=crop&q=80' },
    { name: 'Potato Leaf (Late Blight)', url: 'https://images.unsplash.com/photo-1518977676601-b53f82aba655?w=800&auto=format&fit=crop&q=80' },
  ];

  const [activeLeafIndex, setActiveLeafIndex] = useState(0);

  useEffect(() => {
    startCamera();
    return () => {
      stopCamera();
    };
  }, []);

  const startCamera = async () => {
    try {
      if (navigator.mediaDevices && navigator.mediaDevices.getUserMedia) {
        const stream = await navigator.mediaDevices.getUserMedia({
          video: { facingMode: 'environment' },
        });
        if (videoRef.current) {
          videoRef.current.srcObject = stream;
          setStreamActive(true);
        }
      }
    } catch {
      // Permission denied or virtual environment
      setPermissionError(true);
      setStreamActive(false);
    }
  };

  const stopCamera = () => {
    if (videoRef.current && videoRef.current.srcObject) {
      const tracks = videoRef.current.srcObject.getTracks();
      tracks.forEach((track) => track.stop());
    }
  };

  const handleCapture = () => {
    if (streamActive && videoRef.current) {
      const canvas = document.createElement('canvas');
      canvas.width = videoRef.current.videoWidth || 640;
      canvas.height = videoRef.current.videoHeight || 480;
      const ctx = canvas.getContext('2d');
      ctx.drawImage(videoRef.current, 0, 0, canvas.width, canvas.height);
      const dataUrl = canvas.toDataURL('image/jpeg');
      setCapturedImage(dataUrl);
    } else {
      // Use current preview sample leaf
      const currentUrl = sampleLeaves[activeLeafIndex].url;
      setCapturedImage(currentUrl);
    }
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

  const confirmCapture = () => {
    if (capturedImage) {
      onCapture(capturedImage);
    }
  };

  return (
    <div className="relative w-full h-[calc(100vh-60px)] md:h-[680px] bg-black text-white flex flex-col justify-between overflow-hidden md:rounded-3xl shadow-2xl">
      {/* Top Banner Guide (Matching Stitch Viewfinder) */}
      <div className="absolute top-4 left-4 right-4 z-20">
        <div className="bg-[#FAF8F5]/90 backdrop-blur-md text-[#14382B] p-3.5 rounded-2xl flex items-start space-x-3 shadow-lg border border-white/40">
          <Info className="w-5 h-5 text-[#2D6A4F] shrink-0 mt-0.5" />
          <p className="text-xs md:text-sm font-medium leading-relaxed">
            Position the leaf within the frame in good light for an accurate scan.
          </p>
        </div>
      </div>

      {/* Viewfinder Main Feed */}
      <div className="relative w-full h-full flex items-center justify-center bg-zinc-900">
        {capturedImage ? (
          <img
            src={capturedImage}
            alt="Captured leaf"
            className="w-full h-full object-cover"
          />
        ) : streamActive ? (
          <video
            ref={videoRef}
            autoPlay
            playsInline
            muted
            className={`w-full h-full object-cover transition-transform duration-300 ${
              zoom === '2x' ? 'scale-150' : 'scale-100'
            }`}
          />
        ) : (
          <div className="relative w-full h-full">
            <img
              src={sampleLeaves[activeLeafIndex].url}
              alt="Leaf Viewfinder"
              className={`w-full h-full object-cover transition-transform duration-300 ${
                zoom === '2x' ? 'scale-125' : 'scale-100'
              }`}
            />
            {/* Quick sample cycler overlay for testing */}
            <div className="absolute bottom-24 left-4 right-4 z-10 flex justify-center">
              <div className="bg-black/60 backdrop-blur-md px-3 py-1.5 rounded-full flex items-center space-x-2 text-xs">
                <span className="text-zinc-300">Preset:</span>
                <button
                  onClick={() => setActiveLeafIndex((i) => (i + 1) % sampleLeaves.length)}
                  className="font-semibold text-[#86EFAC] underline underline-offset-2"
                >
                  {sampleLeaves[activeLeafIndex].name} ↻
                </button>
              </div>
            </div>
          </div>
        )}

        {/* Dashed Oval & Framing Reticle (Matching Stitch Design) */}
        {!capturedImage && (
          <div className="absolute inset-0 pointer-events-none flex items-center justify-center">
            {/* Dashed Oval */}
            <div className="w-[280px] h-[390px] md:w-[320px] md:h-[430px] rounded-[50%] border-2 border-dashed border-white/70 animate-pulse-subtle flex items-center justify-center">
              {/* Center target dot */}
              <div className="w-2.5 h-2.5 rounded-full bg-white/80 shadow-md" />
            </div>

            {/* Outer Corner Brackets */}
            <div className="absolute w-[300px] h-[410px] md:w-[340px] md:h-[450px]">
              {/* Top-left */}
              <div className="absolute top-0 left-0 w-8 h-8 border-t-3 border-l-3 border-white rounded-tl-xl" />
              {/* Top-right */}
              <div className="absolute top-0 right-0 w-8 h-8 border-t-3 border-r-3 border-white rounded-tr-xl" />
              {/* Bottom-left */}
              <div className="absolute bottom-0 left-0 w-8 h-8 border-b-3 border-l-3 border-white rounded-bl-xl" />
              {/* Bottom-right */}
              <div className="absolute bottom-0 right-0 w-8 h-8 border-b-3 border-r-3 border-white rounded-br-xl" />
            </div>
          </div>
        )}
      </div>

      {/* Bottom Controls Bar (Matching Stitch Viewfinder) */}
      <div className="absolute bottom-0 left-0 right-0 z-20 pb-8 pt-6 px-6 bg-gradient-to-t from-black/90 via-black/40 to-transparent">
        {capturedImage ? (
          /* Post-Capture Review State */
          <div className="flex items-center justify-around max-w-sm mx-auto">
            <button
              onClick={() => setCapturedImage(null)}
              className="flex flex-col items-center space-y-1 text-zinc-300 hover:text-white"
            >
              <div className="w-12 h-12 rounded-full bg-white/20 backdrop-blur-md flex items-center justify-center">
                <RotateCcw className="w-6 h-6" />
              </div>
              <span className="text-xs">Retake</span>
            </button>

            <button
              onClick={confirmCapture}
              className="flex flex-col items-center space-y-1 text-white font-semibold"
            >
              <div className="w-16 h-16 rounded-full bg-[#1B4332] text-white flex items-center justify-center shadow-lg ring-4 ring-[#86EFAC]/40 hover:scale-105 transition-transform">
                <Check className="w-8 h-8 stroke-[3]" />
              </div>
              <span className="text-sm text-[#86EFAC]">Analyze Leaf</span>
            </button>
          </div>
        ) : (
          /* Camera Viewfinder State */
          <div className="space-y-4 max-w-md mx-auto">
            {/* Zoom Selector (1x / 2x) */}
            <div className="flex justify-center">
              <button
                onClick={() => setZoom((z) => (z === '1x' ? '2x' : '1x'))}
                className="w-10 h-10 rounded-full bg-black/60 backdrop-blur-md border border-white/20 text-white font-bold text-xs flex items-center justify-center shadow-md hover:bg-black/80 transition-all"
              >
                {zoom}
              </button>
            </div>

            {/* Bottom Actions: Gallery / Shutter / Flash */}
            <div className="flex items-center justify-between px-4">
              {/* Gallery upload */}
              <button
                onClick={() => fileInputRef.current?.click()}
                className="flex flex-col items-center space-y-1 text-zinc-200 hover:text-white group"
              >
                <div className="w-11 h-11 rounded-2xl bg-white/15 backdrop-blur-md flex items-center justify-center group-hover:bg-white/25 transition-all">
                  <ImageIcon className="w-5 h-5" />
                </div>
                <span className="text-[11px] font-medium">Gallery</span>
                <input
                  ref={fileInputRef}
                  type="file"
                  accept="image/*"
                  onChange={handleFileUpload}
                  className="hidden"
                />
              </button>

              {/* Shutter Button */}
              <button
                onClick={handleCapture}
                className="w-20 h-20 rounded-full border-4 border-white flex items-center justify-center p-1 shadow-2xl hover:scale-105 active:scale-95 transition-transform"
                aria-label="Capture photo"
              >
                <div className="w-full h-full rounded-full bg-white shadow-inner" />
              </button>

              {/* Flash toggle */}
              <button
                onClick={() => setFlash((f) => !f)}
                className="flex flex-col items-center space-y-1 text-zinc-200 hover:text-white group"
              >
                <div className="w-11 h-11 rounded-2xl bg-white/15 backdrop-blur-md flex items-center justify-center group-hover:bg-white/25 transition-all">
                  {flash ? (
                    <Zap className="w-5 h-5 text-amber-300 fill-amber-300" />
                  ) : (
                    <ZapOff className="w-5 h-5" />
                  )}
                </div>
                <span className="text-[11px] font-medium">Flash</span>
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

export default CameraCapture;
