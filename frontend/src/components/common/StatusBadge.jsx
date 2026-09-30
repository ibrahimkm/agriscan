import React from 'react';

export const StatusBadge = ({ status = 'healthy', showLabel = true, size = 'sm' }) => {
  const normalized = status?.toLowerCase()?.replace(' ', '_') || 'healthy';

  const configs = {
    healthy: {
      dot: 'bg-[#22C55E]',
      text: 'text-[#15803D]',
      bg: 'bg-[#EDF7EE]',
      label: 'Healthy',
    },
    at_risk: {
      dot: 'bg-[#EAB308]',
      text: 'text-[#A16207]',
      bg: 'bg-[#FEF9C3]',
      label: 'At Risk',
    },
    diseased: {
      dot: 'bg-[#EF4444]',
      text: 'text-[#B91C1C]',
      bg: 'bg-[#FEE2E2]',
      label: 'Diseased',
    },
  };

  const current = configs[normalized] || configs.healthy;

  return (
    <div className={`inline-flex items-center space-x-1.5 px-2 py-0.5 rounded-full ${current.bg} ${size === 'xs' ? 'text-[10px]' : 'text-xs'} font-medium ${current.text}`}>
      <span className={`w-1.5 h-1.5 rounded-full ${current.dot}`} />
      {showLabel && <span>{current.label}</span>}
    </div>
  );
};

export default StatusBadge;
