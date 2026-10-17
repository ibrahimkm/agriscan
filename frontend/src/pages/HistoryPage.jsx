import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  History,
  Calendar,
  CloudCheck,
  CloudUpload,
  ChevronRight,
  TrendingUp,
  RotateCw,
  Trash2,
} from 'lucide-react';
import AppHeader from '../components/navigation/AppHeader';
import OfflineBanner from '../components/common/OfflineBanner';
import SeverityBadge from '../components/common/SeverityBadge';
import { useConnectivity } from '../context/ConnectivityContext';
import { useLanguage } from '../context/LanguageContext';
import { handleImageError } from '../utils/imageUtils';
import { getOfflineDiagnoses, clearOfflineDiagnoses } from '../services/indexedDB';
import api from '../services/api';

export const HistoryPage = () => {
  const navigate = useNavigate();
  const { isOnline } = useConnectivity();
  const { t, translateCrop, translateDisease } = useLanguage();

  const [diagnoses, setDiagnoses] = useState([]);
  const [loading, setLoading] = useState(true);
  const [filterCrop, setFilterCrop] = useState('all');

  const defaultMockHistory = [
    {
      _id: 'mock_1',
      cropName: 'Tomato',
      predictedDisease: 'Early Blight',
      confidence: 94,
      severity: 'moderate',
      affectedPercentage: 32,
      createdAt: '2026-10-24T14:30:00Z',
      syncStatus: 'synced',
      imageUrl: 'https://images.unsplash.com/photo-1592924357228-91a4daadcfea?w=400&auto=format&fit=crop&q=80',
    },
    {
      _id: 'mock_2',
      cropName: 'Soybeans',
      predictedDisease: 'Septoria Brown Spot',
      confidence: 87,
      severity: 'moderate',
      affectedPercentage: 24,
      createdAt: '2026-10-24T09:15:00Z',
      syncStatus: 'synced',
      imageUrl: 'https://images.unsplash.com/photo-1574943320219-553eb213f72d?w=400&auto=format&fit=crop&q=80',
    },
    {
      _id: 'mock_3',
      cropName: 'Potato',
      predictedDisease: 'Tomato Late Blight',
      confidence: 96,
      severity: 'severe',
      affectedPercentage: 45,
      createdAt: '2026-10-22T11:00:00Z',
      syncStatus: 'synced',
      imageUrl: 'https://images.unsplash.com/photo-1518977676601-b53f82aba655?w=400&auto=format&fit=crop&q=80',
    },
  ];

  useEffect(() => {
    const loadAllHistory = async () => {
      try {
        const offlineRecords = await getOfflineDiagnoses();
        let serverRecords = [];

        try {
          const res = await api.get('/diagnoses');
          if (res.data.success) {
            serverRecords = res.data.data;
          }
        } catch {
          // offline
        }

        const combined = [...offlineRecords, ...serverRecords];
        if (combined.length === 0) {
          setDiagnoses(defaultMockHistory);
        } else {
          // deduplicate across offline id, server _id, and clientOfflineId
          const seen = new Set();
          const unique = combined.filter((d) => {
            const id = d._id || d.id;
            const offlineId = d.clientOfflineId || d.id;
            if ((id && seen.has(id)) || (offlineId && seen.has(offlineId))) {
              return false;
            }
            if (id) seen.add(id);
            if (offlineId) seen.add(offlineId);
            return true;
          });
          setDiagnoses(unique);
        }
      } catch {
        setDiagnoses(defaultMockHistory);
      } finally {
        setLoading(false);
      }
    };

    loadAllHistory();
  }, []);

  const handleClearHistory = async () => {
    if (confirm('Clear local history?')) {
      await clearOfflineDiagnoses();
      setDiagnoses(defaultMockHistory);
    }
  };

  const filteredDiagnoses = diagnoses.filter(
    (d) => filterCrop === 'all' || d.cropName.toLowerCase() === filterCrop.toLowerCase()
  );

  return (
    <div className="min-h-screen bg-[#FAF8F5] pb-8 md:pb-8 select-none">
      <AppHeader title={t('diagnosisHistory')} showBack backTo="/home" />
      <OfflineBanner />

      <main className="max-w-2xl mx-auto p-3.5 sm:p-4 space-y-3.5 sm:space-y-4">
        {/* Title & Description */}
        <div className="flex items-start justify-between">
          <div className="space-y-1">
            <h2 className="text-xl sm:text-2xl font-extrabold text-[#14382B] tracking-tight">
              {t('diagnosisHistory')}
            </h2>
            <p className="text-xs md:text-sm text-[#4B5563]">
              {t('historySub')}
            </p>
          </div>

          <button
            onClick={handleClearHistory}
            className="p-2 text-[#9CA3AF] hover:text-[#DC2626] rounded-xl hover:bg-white transition-colors"
            title="Clear Local History"
          >
            <Trash2 className="w-4 h-4" />
          </button>
        </div>

        {/* Timeline Cards List */}
        <div className="space-y-3 sm:space-y-3.5 pt-1">
          {filteredDiagnoses.map((diag, index) => {
            return (
              <div
                key={diag._id || diag.id || index}
                onClick={() =>
                  navigate(`/diagnosis/${diag._id || diag.id || 'sample'}`, {
                    state: { diagnosis: diag },
                  })
                }
                className="bg-white border border-[#EAE5DE] hover:border-[#14382B]/30 rounded-3xl p-3.5 sm:p-4 shadow-xs hover:shadow-md cursor-pointer transition-all flex flex-col sm:flex-row sm:items-center gap-3 sm:gap-4 group overflow-hidden"
              >
                {/* Crop Leaf Image - 100% width on mobile, constrained aspect ratio, two-column on sm+ */}
                <div className="w-full sm:w-32 md:w-36 aspect-[16/10] sm:aspect-square max-h-48 sm:max-h-none rounded-2xl overflow-hidden shadow-xs border border-[#FAF8F5] bg-[#14261C] shrink-0 relative">
                  <img
                    src={
                      diag.imageUrl ||
                      'https://images.unsplash.com/photo-1592924357228-91a4daadcfea?w=400&auto=format&fit=crop&q=80'
                    }
                    alt={diag.cropName}
                    onError={handleImageError}
                    className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-300"
                    loading="lazy"
                  />
                </div>

                {/* Details Hierarchy */}
                <div className="flex-1 min-w-0 flex flex-col justify-between space-y-2">
                  {/* Row 1: Crop Name & Date */}
                  <div className="flex items-center justify-between gap-2">
                    <span className="text-[11px] font-bold text-[#6B7280] uppercase tracking-wider truncate">
                      {translateCrop(diag.cropName)}
                    </span>
                    <span className="text-[10px] text-[#9CA3AF] flex items-center space-x-1 shrink-0">
                      <Calendar className="w-3 h-3" />
                      <span>
                        {diag.createdAt
                          ? new Date(diag.createdAt).toLocaleDateString('en-US', {
                              month: 'short',
                              day: 'numeric',
                            })
                          : 'Recently'}
                      </span>
                    </span>
                  </div>

                  {/* Row 2: Disease Name (wraps naturally) */}
                  <h3 className="text-base sm:text-lg font-bold text-[#14382B] group-hover:text-[#2D6A4F] transition-colors break-words">
                    {translateDisease(diag.predictedDisease)}
                  </h3>

                  {/* Row 3: Badges & Action CTA */}
                  <div className="flex items-center justify-between gap-2 pt-1 flex-wrap sm:flex-nowrap">
                    <div className="flex items-center space-x-2 flex-wrap gap-y-1">
                      <SeverityBadge severity={diag.severity || 'moderate'} />
                      <span className="text-[11px] font-bold text-[#374151] bg-[#FAF8F5] px-2 py-0.5 rounded-md border border-[#EAE5DE]">
                        {diag.confidence}% {t('confidence')}
                      </span>
                    </div>

                    <div className="flex items-center space-x-1 text-xs font-bold text-[#14382B] shrink-0 ml-auto sm:ml-0">
                      <span>{t('viewDetails') || 'View Details'}</span>
                      <ChevronRight className="w-4 h-4 group-hover:translate-x-0.5 transition-transform" />
                    </div>
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      </main>
    </div>
  );
};

export default HistoryPage;
