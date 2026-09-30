import React, { useState, useEffect } from 'react';
import {
  BarChart3,
  TrendingUp,
  Activity,
  AlertTriangle,
  PieChart,
  Calendar,
  ShieldCheck,
} from 'lucide-react';
import AppHeader from '../components/navigation/AppHeader';
import OfflineBanner from '../components/common/OfflineBanner';
import { useLanguage } from '../context/LanguageContext';
import api from '../services/api';

export const AnalyticsPage = () => {
  const { t, translateDisease } = useLanguage();

  const [stats, setStats] = useState({
    totalDiagnoses: 28,
    healthyRate: 75,
    topPathogens: [
      { name: 'Early Blight', count: 9, percentage: 32 },
      { name: 'Septoria Brown Spot', count: 6, percentage: 21 },
      { name: 'Tomato Late Blight', count: 4, percentage: 14 },
      { name: 'Rice Blast', count: 2, percentage: 7 },
    ],
    severityDistribution: {
      healthy: 18,
      moderate: 7,
      severe: 3,
    },
  });

  useEffect(() => {
    const fetchAnalytics = async () => {
      try {
        const res = await api.get('/dashboard/stats');
        if (res.data.success && res.data.data) {
          // If server provides richer analytics, merge them
        }
      } catch {
        // use default state
      }
    };
    fetchAnalytics();
  }, []);

  return (
    <div className="min-h-screen bg-[#FAF8F5] pb-24 md:pb-8 select-none">
      <AppHeader title={t('farmHealthAnalytics')} showBack backTo="/home" />
      <OfflineBanner />

      <main className="max-w-2xl mx-auto p-4 space-y-4">
        {/* Header */}
        <div className="space-y-1">
          <h2 className="text-2xl font-extrabold text-[#14382B] tracking-tight">
            {t('farmHealthAnalytics')}
          </h2>
          <p className="text-xs md:text-sm text-[#4B5563]">
            {t('analyticsSub')}
          </p>
        </div>

        {/* Top Summary Cards */}
        <div className="grid grid-cols-2 gap-3">
          <div className="bg-white border border-[#EAE5DE] rounded-3xl p-4 shadow-xs space-y-1">
            <div className="flex items-center space-x-1.5 text-xs font-bold text-[#6B7280]">
              <ShieldCheck className="w-4 h-4 text-[#22C55E]" />
              <span>{t('healthyDistribution')}</span>
            </div>
            <p className="text-3xl font-extrabold text-[#14382B]">
              {stats.healthyRate}%
            </p>
          </div>

          <div className="bg-white border border-[#EAE5DE] rounded-3xl p-4 shadow-xs space-y-1">
            <div className="flex items-center space-x-1.5 text-xs font-bold text-[#6B7280]">
              <Activity className="w-4 h-4 text-[#D97706]" />
              <span>{t('canopyRiskIndex')}</span>
            </div>
            <p className="text-3xl font-extrabold text-[#D97706]">
              {t('moderateSeverity')}
            </p>
          </div>
        </div>

        {/* Pathogen Frequency Bar Chart */}
        <div className="bg-white border border-[#EAE5DE] rounded-3xl p-5 shadow-xs space-y-4">
          <div className="flex items-center justify-between">
            <h3 className="text-sm font-bold text-[#14382B]">{t('pathogenDistribution')}</h3>
            <span className="text-xs text-[#6B7280]">30-Day Window</span>
          </div>

          <div className="space-y-3 pt-1">
            {stats.topPathogens.map((item, idx) => (
              <div key={idx} className="space-y-1">
                <div className="flex justify-between text-xs font-semibold">
                  <span className="text-[#14382B]">{translateDisease(item.name)}</span>
                  <span className="text-[#6B7280]">{item.count} cases ({item.percentage}%)</span>
                </div>
                <div className="w-full h-2.5 bg-[#FAF8F5] border border-[#EAE5DE] rounded-full overflow-hidden">
                  <div
                    className="h-full bg-[#14382B] rounded-full"
                    style={{ width: `${item.percentage}%` }}
                  />
                </div>
              </div>
            ))}
          </div>
        </div>
      </main>
    </div>
  );
};

export default AnalyticsPage;
