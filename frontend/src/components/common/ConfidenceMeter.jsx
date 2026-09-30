import React from 'react';

export const ConfidenceMeter = ({ confidence = 94, size = 'md' }) => {
  return (
    <div className="flex flex-col items-end">
      <span className="text-[11px] font-medium text-[#6B7280]">Confidence</span>
      <div className="bg-[#14382B] text-white font-bold px-3 py-1 rounded-xl text-base tracking-tight shadow-sm">
        {Math.round(confidence)}%
      </div>
    </div>
  );
};

export default ConfidenceMeter;
