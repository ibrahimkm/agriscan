import React from 'react';
import { AlertTriangle, AlertCircle, CheckCircle } from 'lucide-react';

export const SeverityBadge = ({ severity = 'moderate', className = '' }) => {
  const normalized = severity?.toLowerCase() || 'moderate';

  if (normalized === 'severe') {
    return (
      <div className={`inline-flex items-center space-x-1.5 px-3 py-1 rounded-full bg-[#FEE2E2] text-[#B91C1C] border border-[#FCA5A5] text-xs font-semibold ${className}`}>
        <AlertCircle className="w-3.5 h-3.5" />
        <span>Severe Risk</span>
      </div>
    );
  }

  if (normalized === 'moderate') {
    return (
      <div className={`inline-flex items-center space-x-1.5 px-3 py-1 rounded-full bg-[#FEF3C7] text-[#92400E] border border-[#FDE68A] text-xs font-semibold ${className}`}>
        <AlertTriangle className="w-3.5 h-3.5" />
        <span>Moderate Severity</span>
      </div>
    );
  }

  if (normalized === 'healthy') {
    return (
      <div className={`inline-flex items-center space-x-1.5 px-3 py-1 rounded-full bg-[#DCFCE7] text-[#166534] border border-[#86EFAC] text-xs font-semibold ${className}`}>
        <CheckCircle className="w-3.5 h-3.5" />
        <span>Healthy Leaf</span>
      </div>
    );
  }

  return (
    <div className={`inline-flex items-center space-x-1.5 px-3 py-1 rounded-full bg-[#F3F4F6] text-[#374151] border border-[#E5E7EB] text-xs font-semibold ${className}`}>
      <span>Low Severity</span>
    </div>
  );
};

export default SeverityBadge;
