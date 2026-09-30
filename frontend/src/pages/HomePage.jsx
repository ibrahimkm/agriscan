import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Camera,
  Thermometer,
  Droplets,
  CheckCircle2,
  ChevronRight,
  TrendingUp,
  AlertCircle,
  Scan,
} from 'lucide-react';
import { useAuth } from '../context/AuthContext';
import { useConnectivity } from '../context/ConnectivityContext';
import { useLanguage } from '../context/LanguageContext';
import AppHeader from '../components/navigation/AppHeader';
import OfflineBanner from '../components/common/OfflineBanner';
import api from '../services/api';

export const HomePage = () => {
  const navigate = useNavigate();
  const { user } = useAuth();
  const { isOnline } = useConnectivity();
  const { t, translateCrop, translateDisease } = useLanguage();

  const [stats, setStats] = useState({
    summary: { healthy: 3, atRisk: 1, diseased: 0 },
    environmentalMetrics: { temperature: '24°C', soilMoisture: 'Optimal' },
  });
  const [crops, setCrops] = useState([]);
  const [recentDiagnosis, setRecentDiagnosis] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchDashboardData = async () => {
      try {
        const [statsRes, cropsRes, diagRes] = await Promise.all([
          api.get('/dashboard/stats').catch(() => null),
          api.get('/crops').catch(() => null),
          api.get('/diagnoses?limit=1').catch(() => null),
        ]);

        if (statsRes?.data?.success) {
          setStats(statsRes.data.data);
        }

        if (cropsRes?.data?.success && cropsRes.data.data.length > 0) {
          setCrops(cropsRes.data.data);
        } else {
          // Default fallback crops matching Stitch UI
          setCrops([
            {
              _id: 'crop_wheat',
              cropName: 'Winter Wheat',
              healthStatus: 'healthy',
              imageUrl: 'https://images.unsplash.com/photo-1574323347407-f5e1ad6d020b?w=400&auto=format&fit=crop&q=80',
            },
            {
              _id: 'crop_soy',
              cropName: 'Soybeans',
              healthStatus: 'at_risk',
              imageUrl: 'https://images.unsplash.com/photo-1574943320219-553eb213f72d?w=400&auto=format&fit=crop&q=80',
            },
            {
              _id: 'crop_sunflower',
              cropName: 'Sunflower',
              healthStatus: 'healthy',
              imageUrl: 'https://images.unsplash.com/photo-1597848212624-a19eb35e2651?w=400&auto=format&fit=crop&q=80',
            },
          ]);
        }

        if (diagRes?.data?.success && diagRes.data.data.length > 0) {
          setRecentDiagnosis(diagRes.data.data[0]);
        } else {
          // Default fallback recent diagnosis matching Stitch UI
          setRecentDiagnosis({
            _id: 'diag_soybean_1',
            cropName: 'Soybeans',
            fieldBlock: 'Block B',
            predictedDisease: 'Septoria Brown Spot',
            confidence: 87,
            severity: 'moderate',
            createdAt: '2026-10-24T09:15:00Z',
          });
        }
      } catch (err) {
        console.warn('[Dashboard Load]', err);
      } finally {
        setLoading(false);
      }
    };

    fetchDashboardData();
  }, []);

  const firstName = user?.name ? user.name.split(' ')[0] : 'Ravi';

  return (
    <div className="min-h-screen bg-[#FAF8F5] pb-24 md:pb-8 select-none">
      <AppHeader />
      <OfflineBanner />

      <main className="max-w-2xl mx-auto p-4 space-y-4">
        {/* Top Greeting Card (Matching Stitch Screen 2) */}
        <div className="bg-white border border-[#EAE5DE] rounded-3xl p-5 shadow-xs space-y-2">
          <div className="flex items-center justify-between">
            <h2 className="text-xl md:text-2xl font-bold text-[#14382B] tracking-tight">
              {t('goodMorning')}, {firstName}.
            </h2>
            <div className="inline-flex items-center space-x-1 px-2.5 py-0.5 rounded-full bg-[#EDF7EE] text-[#15803D] text-xs font-semibold">
              <CheckCircle2 className="w-3.5 h-3.5" />
              <span>{isOnline ? t('online') : t('offline')}</span>
            </div>
          </div>
          <p className="text-sm text-[#4B5563]">
            {t('farmResilient')}
          </p>
        </div>

        {/* Health Summary Strip (Matching Stitch Screen 2) */}
        <div className="bg-[#FAF8F5] border border-[#EAE5DE] rounded-2xl py-2.5 px-4 flex items-center justify-around text-xs font-medium text-[#374151] shadow-xs">
          <div className="flex items-center space-x-1.5">
            <span className="w-2 h-2 rounded-full bg-[#22C55E]" />
            <span>{stats.summary?.healthy ?? 3} {t('healthy')}</span>
          </div>
          <span className="text-[#D1D5DB]">·</span>
          <div className="flex items-center space-x-1.5">
            <span className="w-2 h-2 rounded-full bg-[#EAB308]" />
            <span>{stats.summary?.atRisk ?? 1} {t('atRisk')}</span>
          </div>
          <span className="text-[#D1D5DB]">·</span>
          <div className="flex items-center space-x-1.5">
            <span className="w-2 h-2 rounded-full bg-[#EF4444]" />
            <span>{stats.summary?.diseased ?? 0} {t('diseased')}</span>
          </div>
        </div>

        {/* Sensor Metrics Row (Temperature & Moisture) */}
        <div className="grid grid-cols-2 gap-3">
          {/* Temperature */}
          <div className="bg-white border border-[#EAE5DE] rounded-2xl p-4 shadow-xs space-y-1">
            <div className="flex items-center space-x-1.5 text-[11px] font-bold text-[#6B7280] uppercase tracking-wider">
              <Thermometer className="w-4 h-4 text-[#C68B59]" />
              <span>{t('temperature')}</span>
            </div>
            <p className="text-2xl font-bold text-[#14382B]">
              {stats.environmentalMetrics?.temperature || '24°C'}
            </p>
          </div>

          {/* Soil Moisture */}
          <div className="bg-white border border-[#EAE5DE] rounded-2xl p-4 shadow-xs space-y-1">
            <div className="flex items-center space-x-1.5 text-[11px] font-bold text-[#6B7280] uppercase tracking-wider">
              <Droplets className="w-4 h-4 text-[#C68B59]" />
              <span>{t('soilMoisture')}</span>
            </div>
            <p className="text-2xl font-bold text-[#14382B]">
              {t('optimal')}
            </p>
          </div>
        </div>

        {/* Primary CTA Button: Diagnose a Crop (Matching Stitch Screen 2) */}
        <button
          onClick={() => navigate('/diagnose')}
          className="w-full py-4 rounded-2xl bg-[#14382B] text-white font-bold text-base shadow-md hover:bg-[#1B4332] active:scale-[0.99] transition-all flex items-center justify-center space-x-2"
        >
          <Camera className="w-5 h-5 stroke-[2.2]" />
          <span>{t('diagnoseCropCTA')}</span>
        </button>

        {/* My Crops Horizontal Carousel (Matching Stitch Screen 2) */}
        <div className="space-y-3 pt-2">
          <div className="flex items-center justify-between">
            <h3 className="text-lg font-bold text-[#14382B]">{t('myCrops')}</h3>
            <button
              onClick={() => navigate('/crops')}
              className="text-xs font-semibold text-[#C68B59] hover:text-[#A46B3C] transition-colors"
            >
              {t('viewAll')}
            </button>
          </div>

          <div className="flex space-x-3 overflow-x-auto pb-2 scrollbar-none">
            {crops.map((crop) => {
              const isHealthy = crop.healthStatus === 'healthy';
              const isRisk = crop.healthStatus === 'at_risk';

              return (
                <div
                  key={crop._id}
                  onClick={() => navigate('/crops')}
                  className="shrink-0 w-36 bg-white border border-[#EAE5DE] rounded-2xl p-3 shadow-xs hover:border-[#14382B]/30 cursor-pointer transition-all flex flex-col items-center text-center space-y-2"
                >
                  <div className="w-16 h-16 rounded-full overflow-hidden border-2 border-[#FAF8F5] shadow-xs">
                    <img
                      src={crop.imageUrl}
                      alt={crop.cropName}
                      className="w-full h-full object-cover"
                    />
                  </div>
                  <div>
                    <h4 className="text-xs font-bold text-[#14382B] truncate w-28">
                      {translateCrop(crop.cropName)}
                    </h4>
                    <div className="flex items-center justify-center space-x-1 mt-0.5">
                      <span
                        className={`w-1.5 h-1.5 rounded-full ${
                          isHealthy
                            ? 'bg-[#22C55E]'
                            : isRisk
                            ? 'bg-[#EAB308]'
                            : 'bg-[#EF4444]'
                        }`}
                      />
                      <span className="text-[10px] font-medium text-[#6B7280]">
                        {isHealthy ? t('healthy') : isRisk ? t('atRisk') : t('diseased')}
                      </span>
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        </div>

        {/* Recent Diagnosis Section (Matching Stitch Screen 2) */}
        {recentDiagnosis && (
          <div className="space-y-3 pt-2">
            <h3 className="text-lg font-bold text-[#14382B]">{t('recentDiagnosis')}</h3>
            <div
              onClick={() => navigate(`/diagnosis/${recentDiagnosis._id || 'sample'}`)}
              className="bg-white border-l-4 border-l-[#EAB308] border-y border-r border-[#EAE5DE] rounded-2xl p-4 shadow-xs cursor-pointer hover:shadow-md transition-all space-y-2.5"
            >
              <div className="flex items-center justify-between">
                <div>
                  <h4 className="text-xs font-bold text-[#6B7280]">
                    {translateCrop(recentDiagnosis.cropName)} - {recentDiagnosis.fieldBlock || 'Block B'}
                  </h4>
                  <p className="text-sm font-bold text-[#14382B]">
                    {t('suspected')}: <span className="text-[#14382B]">{translateDisease(recentDiagnosis.predictedDisease)}</span>
                  </p>
                </div>
                <span className="text-[11px] text-[#9CA3AF]">
                  {new Date(recentDiagnosis.createdAt || Date.now()).toLocaleDateString('en-US', {
                    month: 'short',
                    day: 'numeric',
                    hour: '2-digit',
                    minute: '2-digit',
                  })}
                </span>
              </div>

              <div className="flex items-center justify-between pt-1 border-t border-[#F3F4F6]">
                <div className="inline-flex items-center space-x-1 px-2.5 py-0.5 rounded-md bg-[#FAF8F5] border border-[#EAE5DE] text-[11px] font-bold text-[#374151]">
                  <TrendingUp className="w-3 h-3 text-[#C68B59]" />
                  <span>{recentDiagnosis.confidence}% {t('confidence')}</span>
                </div>

                <div className="flex items-center space-x-1 text-xs font-bold text-[#14382B]">
                  <span>{t('viewDetails')}</span>
                  <ChevronRight className="w-4 h-4" />
                </div>
              </div>
            </div>
          </div>
        )}
      </main>
    </div>
  );
};

export default HomePage;
