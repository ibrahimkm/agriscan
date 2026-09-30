import React, { useState } from 'react';

export const HeatmapViewer = ({ imageUrl, diseaseName = 'Early Blight', affectedPercentage = 32 }) => {
  const [activeMode, setActiveMode] = useState('original'); // 'original' | 'analysis' | 'affected'

  return (
    <div className="relative w-full h-72 md:h-80 rounded-3xl overflow-hidden shadow-md border border-[#EAE5DE] bg-black">
      {/* Base Image */}
      <img
        src={imageUrl || 'https://images.unsplash.com/photo-1592417817098-8f3d6eb2260f?w=800&auto=format&fit=crop&q=80'}
        alt="Diagnosed Leaf"
        className="w-full h-full object-cover transition-opacity duration-300"
      />

      {/* Mode 2: AI Analysis (Spectral Heatmap Overlay) */}
      {activeMode === 'analysis' && (
        <div className="absolute inset-0 pointer-events-none transition-all duration-300">
          {/* Heat gradient centered on lesion */}
          <div className="absolute inset-0 bg-gradient-radial from-amber-500/40 via-red-600/35 to-emerald-950/20 mix-blend-color-dodge" />
          <svg className="absolute inset-0 w-full h-full" viewBox="0 0 100 100" preserveAspectRatio="none">
            {/* Spectral contour rings */}
            <circle cx="50" cy="45" r="22" fill="rgba(239, 68, 68, 0.45)" filter="blur(8px)" />
            <circle cx="50" cy="45" r="14" fill="rgba(245, 158, 11, 0.6)" filter="blur(4px)" />
            <circle cx="50" cy="45" r="7" fill="rgba(255, 255, 255, 0.7)" filter="blur(2px)" />
            {/* Secondary satellite spot */}
            <circle cx="75" cy="65" r="10" fill="rgba(239, 68, 68, 0.5)" filter="blur(5px)" />
          </svg>
          <div className="absolute top-3 left-3 bg-black/70 backdrop-blur-md px-2.5 py-1 rounded-full text-[10px] text-white font-medium flex items-center space-x-1.5">
            <span className="w-2 h-2 rounded-full bg-red-500 animate-ping" />
            <span>Pathogen Thermal Gradient</span>
          </div>
        </div>
      )}

      {/* Mode 3: Affected Area (Contoured Mask Overlay) */}
      {activeMode === 'affected' && (
        <div className="absolute inset-0 pointer-events-none transition-all duration-300">
          <div className="absolute inset-0 bg-black/40 backdrop-blur-[0.5px]" />
          <svg className="absolute inset-0 w-full h-full" viewBox="0 0 100 100" preserveAspectRatio="none">
            {/* Primary lesion polygon */}
            <ellipse
              cx="50"
              cy="45"
              rx="24"
              ry="22"
              fill="rgba(220, 38, 38, 0.3)"
              stroke="#EF4444"
              strokeWidth="1.2"
              strokeDasharray="2,2"
            />
            {/* Secondary lesion */}
            <ellipse
              cx="75"
              cy="65"
              rx="12"
              ry="11"
              fill="rgba(234, 179, 8, 0.35)"
              stroke="#F59E0B"
              strokeWidth="1.2"
              strokeDasharray="2,2"
            />
          </svg>
          <div className="absolute top-3 left-3 bg-red-950/80 backdrop-blur-md border border-red-500/40 px-2.5 py-1 rounded-full text-[10px] text-red-200 font-semibold flex items-center space-x-1">
            <span>{affectedPercentage}% Leaf Surface Impacted</span>
          </div>
        </div>
      )}

      {/* 3-Way Floating Toggle (Matching Stitch Screen 6) */}
      <div className="absolute bottom-3 left-3 right-3 flex justify-center z-10">
        <div className="bg-white/90 backdrop-blur-md p-1 rounded-full border border-white/60 shadow-lg flex items-center space-x-1">
          <button
            onClick={() => setActiveMode('original')}
            className={`px-4 py-1.5 rounded-full text-xs font-semibold transition-all ${
              activeMode === 'original'
                ? 'bg-[#14382B] text-white shadow-sm'
                : 'text-[#4B5563] hover:text-[#14382B]'
            }`}
          >
            Original
          </button>
          <button
            onClick={() => setActiveMode('analysis')}
            className={`px-4 py-1.5 rounded-full text-xs font-semibold transition-all ${
              activeMode === 'analysis'
                ? 'bg-[#14382B] text-white shadow-sm'
                : 'text-[#4B5563] hover:text-[#14382B]'
            }`}
          >
            AI Analysis
          </button>
          <button
            onClick={() => setActiveMode('affected')}
            className={`px-4 py-1.5 rounded-full text-xs font-semibold transition-all ${
              activeMode === 'affected'
                ? 'bg-[#14382B] text-white shadow-sm'
                : 'text-[#4B5563] hover:text-[#14382B]'
            }`}
          >
            Affected Area
          </button>
        </div>
      </div>
    </div>
  );
};

export default HeatmapViewer;
