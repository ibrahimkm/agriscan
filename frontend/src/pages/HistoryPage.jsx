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
      imageUrl: 'https://images.unsplash.com/photo-1592417817098-8f3d6eb2260f?w=400&auto=format&fit=crop&q=80',
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
          // deduplicate
          const seen = new Set();
          const unique = combined.filter((d) => {
            const id = d._id || d.id;
            if (seen.has(id)) return false;
            seen.add(id);
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
    <div className="min-h-screen bg-[#FAF8F5] pb-24 md:pb-8 select-none">
      <AppHeader title={t('diagnosisHistory')} showBack backTo="/home" />
      <OfflineBanner />

      <main className="max-w-2xl mx-auto p-4 space-y-4">
        {/* Title & Description */}
        <div className="flex items-start justify-between">
          <div className="space-y-1">
            <h2 className="text-2xl font-extrabold text-[#14382B] tracking-tight">
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
        <div className="space-y-3 pt-2">
          {filteredDiagnoses.map((diag, index) => {
            const isSynced = diag.syncStatus === 'synced' || !!diag._id;

            return (
              <div
                key={diag._id || diag.id || index}
                onClick={() =>
                  navigate(`/diagnosis/${diag._id || diag.id || 'sample'}`, {
                    state: { diagnosis: diag },
                  })
                }
                className="bg-white border border-[#EAE5DE] hover:border-[#14382B]/30 rounded-3xl p-4 shadow-xs hover:shadow-md cursor-pointer transition-all flex items-center space-x-3.5 group"
              >
                {/* Crop Leaf Thumbnail */}
                <div className="w-16 h-16 rounded-2xl overflow-hidden shadow-xs border border-[#FAF8F5] shrink-0">
                  <img
                    src={
                      diag.imageUrl ||
                      'https://images.unsplash.com/photo-1592417817098-8f3d6eb2260f?w=400&auto=format&fit=crop&q=80'
                    }
                    alt={diag.cropName}
                    className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-300"
                  />
                </div>

                {/* Details */}
                <div className="flex-1 min-w-0">
                  <div className="flex items-center justify-between">
                    <span className="text-[11px] font-bold text-[#6B7280] uppercase tracking-wider">
                      {translateCrop(diag.cropName)}
                    </span>
                    <span className="text-[10px] text-[#9CA3AF] flex items-center space-x-1">
                      <Calendar className="w-3 h-3" />
                      <span>
                        {new Date(diag.createdAt || Date.now()).toLocaleDateString('en-US', {
                          month: 'short',
                          day: 'numeric',
                        })}
                      </span>
                    </span>
                  </div>

                  <h3 className="text-sm md:text-base font-bold text-[#14382B] truncate group-hover:text-[#2D6A4F] transition-colors">
                    {translateDisease(diag.predictedDisease)}
                  </h3>

                  <div className="flex items-center space-x-2 mt-1">
                    <SeverityBadge severity={diag.severity || 'moderate'} />
                    <span className="text-[11px] font-bold text-[#374151]">
                      {diag.confidence}% {t('confidence')}
                    </span>
                  </div>
                </div>

                {/* Arrow */}
                <ChevronRight className="w-5 h-5 text-[#9CA3AF] group-hover:text-[#14382B] group-hover:translate-x-0.5 transition-all" />
              </div>
            );
          })}
        </div>
      </main>
    </div>
  );
};

export default HistoryPage;
