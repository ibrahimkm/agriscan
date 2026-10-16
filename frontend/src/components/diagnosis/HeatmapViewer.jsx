import React, { useState } from 'react';

const FALLBACK_LEAF_IMAGE =
  "data:image/svg+xml;charset=UTF-8,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 400 300' width='400' height='300'%3E%3Crect width='400' height='300' fill='%23193426'/%3E%3Cpath d='M200 40 C120 70 80 160 120 230 C150 270 200 275 200 275 C200 275 250 270 280 230 C320 160 280 70 200 40 Z' fill='%232D6A4F' stroke='%2340916C' stroke-width='4'/%3E%3Cpath d='M200 50 L200 260' stroke='%2352B788' stroke-width='3' stroke-linecap='round'/%3E%3Cpath d='M200 110 Q240 120 260 145' stroke='%2352B788' stroke-width='2' stroke-linecap='round'/%3E%3Cpath d='M200 150 Q160 165 140 190' stroke='%2352B788' stroke-width='2' stroke-linecap='round'/%3E%3Cpath d='M200 190 Q240 205 255 225' stroke='%2352B788' stroke-width='2' stroke-linecap='round'/%3E%3Ctext x='200' y='285' fill='%23D8F3DC' font-size='13' font-family='sans-serif' text-anchor='middle'%3EAgriScan Diagnosed Leaf%3C/text%3E%3C/svg%3E";

export const HeatmapViewer = ({
  imageUrl,
  diseaseName = 'Early Blight',
  affectedPercentage = 32,
  isHealthy = false,
}) => {
  const [activeMode, setActiveMode] = useState('original'); // 'original' | 'analysis' | 'affected'
  const [imgSrc, setImgSrc] = useState(imageUrl || FALLBACK_LEAF_IMAGE);

  const isTrulyHealthy = isHealthy || diseaseName.toLowerCase().includes('healthy');

  return (
    <div className="relative w-full aspect-[4/3] sm:aspect-[16/11] md:h-80 rounded-3xl overflow-hidden shadow-md border border-[#EAE5DE] bg-[#14261C]">
      {/* Base Image with robust fallback */}
      <img
        src={imgSrc}
        alt={`Diagnosed ${diseaseName}`}
        onError={() => setImgSrc(FALLBACK_LEAF_IMAGE)}
        className="w-full h-full object-cover transition-opacity duration-300"
      />

      {/* Mode 2: AI Analysis (Spectral Heatmap Overlay) */}
      {activeMode === 'analysis' && (
        <div className="absolute inset-0 pointer-events-none transition-all duration-300">
          {!isTrulyHealthy ? (
            <>
              {/* Heat gradient centered on lesion */}
              <div className="absolute inset-0 bg-gradient-radial from-amber-500/40 via-red-600/35 to-emerald-950/20 mix-blend-color-dodge" />
              <svg className="absolute inset-0 w-full h-full" viewBox="0 0 100 100" preserveAspectRatio="none">
                <circle cx="50" cy="45" r="22" fill="rgba(239, 68, 68, 0.45)" filter="blur(8px)" />
                <circle cx="50" cy="45" r="14" fill="rgba(245, 158, 11, 0.6)" filter="blur(4px)" />
                <circle cx="50" cy="45" r="7" fill="rgba(255, 255, 255, 0.7)" filter="blur(2px)" />
                <circle cx="75" cy="65" r="10" fill="rgba(239, 68, 68, 0.5)" filter="blur(5px)" />
              </svg>
              <div className="absolute top-3 left-3 bg-black/75 backdrop-blur-md px-2.5 py-1 rounded-full text-[10px] text-white font-medium flex items-center space-x-1.5 shadow-sm">
                <span className="w-2 h-2 rounded-full bg-red-500 animate-ping" />
                <span>Pathogen Thermal Gradient</span>
              </div>
            </>
          ) : (
            <div className="absolute inset-0 flex items-center justify-center bg-black/40 backdrop-blur-[1px]">
              <div className="bg-[#14382B]/90 backdrop-blur-md border border-white/20 px-3 py-1.5 rounded-full text-xs text-white font-medium flex items-center space-x-2 shadow-lg">
                <span className="w-2 h-2 rounded-full bg-[#22C55E]" />
                <span>Uniform Photosynthetic Tissue · Healthy</span>
              </div>
            </div>
          )}
        </div>
      )}

      {/* Mode 3: Affected Area (Contoured Mask Overlay) */}
      {activeMode === 'affected' && (
        <div className="absolute inset-0 pointer-events-none transition-all duration-300">
          {!isTrulyHealthy && affectedPercentage > 0 ? (
            <>
              <div className="absolute inset-0 bg-black/40 backdrop-blur-[0.5px]" />
              <svg className="absolute inset-0 w-full h-full" viewBox="0 0 100 100" preserveAspectRatio="none">
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
              <div className="absolute top-3 left-3 bg-red-950/85 backdrop-blur-md border border-red-500/40 px-2.5 py-1 rounded-full text-[10px] text-red-200 font-semibold flex items-center space-x-1.5 shadow-sm">
                <span>~{affectedPercentage}% Surface Impacted</span>
              </div>
            </>
          ) : (
            <div className="absolute inset-0 flex items-center justify-center bg-black/40 backdrop-blur-[1px]">
              <div className="bg-[#14382B]/90 backdrop-blur-md border border-white/20 px-3 py-1.5 rounded-full text-xs text-white font-medium flex items-center space-x-2 shadow-lg">
                <span className="w-2 h-2 rounded-full bg-[#22C55E]" />
                <span>0% Lesion Surface · Clean Leaf</span>
              </div>
            </div>
          )}
        </div>
      )}

      {/* 3-Way Floating Toggle: Adaptive & Mobile-responsive */}
      <div className="absolute bottom-2.5 left-2 right-2 flex justify-center z-10">
        <div className="bg-white/95 backdrop-blur-md p-1 rounded-full border border-white/70 shadow-lg flex items-center space-x-1 max-w-full overflow-x-auto scrollbar-none">
          <button
            type="button"
            onClick={() => setActiveMode('original')}
            className={`px-2.5 sm:px-4 py-1 sm:py-1.5 rounded-full text-[11px] sm:text-xs font-semibold whitespace-nowrap transition-all ${
              activeMode === 'original'
                ? 'bg-[#14382B] text-white shadow-xs'
                : 'text-[#4B5563] hover:text-[#14382B]'
            }`}
          >
            Original
          </button>
          <button
            type="button"
            onClick={() => setActiveMode('analysis')}
            className={`px-2.5 sm:px-4 py-1 sm:py-1.5 rounded-full text-[11px] sm:text-xs font-semibold whitespace-nowrap transition-all ${
              activeMode === 'analysis'
                ? 'bg-[#14382B] text-white shadow-xs'
                : 'text-[#4B5563] hover:text-[#14382B]'
            }`}
          >
            AI Analysis
          </button>
          <button
            type="button"
            onClick={() => setActiveMode('affected')}
            className={`px-2.5 sm:px-4 py-1 sm:py-1.5 rounded-full text-[11px] sm:text-xs font-semibold whitespace-nowrap transition-all ${
              activeMode === 'affected'
                ? 'bg-[#14382B] text-white shadow-xs'
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
