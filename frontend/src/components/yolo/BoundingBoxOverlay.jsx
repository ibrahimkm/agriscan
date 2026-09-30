import React from 'react';

export const BoundingBoxOverlay = ({ imageUrl, detections = [], selectedDetection, onSelect }) => {
  return (
    <div className="relative w-full aspect-[4/3] rounded-3xl overflow-hidden shadow-md border border-[#EAE5DE] bg-black group select-none">
      {/* Base Image */}
      <img
        src={imageUrl || 'https://images.unsplash.com/photo-1592417817098-8f3d6eb2260f?w=800&auto=format&fit=crop&q=80'}
        alt="YOLO Detection Input"
        className="w-full h-full object-cover"
      />

      {/* SVG Bounding Boxes Overlay */}
      <svg className="absolute inset-0 w-full h-full pointer-events-none" viewBox="0 0 100 100" preserveAspectRatio="none">
        {detections.map((det, i) => {
          const { x, y, width, height } = det.boundingBox;
          const isSelected = selectedDetection === i;
          const strokeColor = det.severity === 'severe' ? '#EF4444' : '#F59E0B';

          return (
            <g key={i} className="pointer-events-auto cursor-pointer" onClick={() => onSelect && onSelect(i)}>
              {/* Outer Glow */}
              <rect
                x={x}
                y={y}
                width={width}
                height={height}
                fill={isSelected ? `${strokeColor}33` : `${strokeColor}15`}
                stroke={strokeColor}
                strokeWidth={isSelected ? '0.9' : '0.6'}
                strokeDasharray={isSelected ? 'none' : '2,1'}
                rx="1.5"
              />
              {/* Corner accent reticles */}
              <circle cx={x} cy={y} r="0.8" fill={strokeColor} />
              <circle cx={x + width} cy={y} r="0.8" fill={strokeColor} />
              <circle cx={x} cy={y + height} r="0.8" fill={strokeColor} />
              <circle cx={x + width} cy={y + height} r="0.8" fill={strokeColor} />
            </g>
          );
        })}
      </svg>

      {/* HTML Labels (positioned precisely) */}
      <div className="absolute inset-0 pointer-events-none">
        {detections.map((det, i) => {
          const { x, y } = det.boundingBox;
          const isSelected = selectedDetection === i;
          const bgClass = det.severity === 'severe' ? 'bg-red-600' : 'bg-amber-600';

          return (
            <div
              key={i}
              className="absolute pointer-events-auto cursor-pointer"
              style={{
                left: `${Math.max(2, Math.min(x, 70))}%`,
                top: `${Math.max(2, y - 5)}%`,
              }}
              onClick={() => onSelect && onSelect(i)}
            >
              <div
                className={`${bgClass} text-white text-[10px] md:text-xs font-bold px-2 py-0.5 rounded-md shadow-md flex items-center space-x-1.5 transition-transform ${
                  isSelected ? 'scale-110 ring-2 ring-white' : 'hover:scale-105'
                }`}
              >
                <span>{det.classLabel}</span>
                <span className="opacity-80">({det.confidence}%)</span>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
};

export default BoundingBoxOverlay;
