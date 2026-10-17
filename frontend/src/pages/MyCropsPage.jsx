import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { Search, Plus, Sprout, ChevronRight } from 'lucide-react';
import AppHeader from '../components/navigation/AppHeader';
import OfflineBanner from '../components/common/OfflineBanner';
import { useLanguage } from '../context/LanguageContext';
import { handleImageError } from '../utils/imageUtils';
import api from '../services/api';

export const MyCropsPage = () => {
  const navigate = useNavigate();
  const { t, translateCrop } = useLanguage();

  const [crops, setCrops] = useState([]);
  const [search, setSearch] = useState('');
  const [selectedFilter, setSelectedFilter] = useState('all'); // 'all' | 'healthy' | 'at_risk' | 'diseased'
  const [loading, setLoading] = useState(true);

  const defaultCrops = [
    {
      _id: 'tomato_1',
      cropName: 'Tomato',
      cropType: 'Solanum lycopersicum',
      imageUrl: 'https://images.unsplash.com/photo-1592924357228-91a4daadcfea?w=400&auto=format&fit=crop&q=80',
      healthStatus: 'at_risk',
      diagnosesCount: 12,
    },
    {
      _id: 'rice_1',
      cropName: 'Rice',
      cropType: 'Oryza sativa',
      imageUrl: 'https://images.unsplash.com/photo-1586201375761-83865001e31c?w=400&auto=format&fit=crop&q=80',
      healthStatus: 'healthy',
      diagnosesCount: 5,
    },
    {
      _id: 'potato_1',
      cropName: 'Potato',
      cropType: 'Solanum tuberosum',
      imageUrl: 'https://images.unsplash.com/photo-1518977676601-b53f82aba655?w=400&auto=format&fit=crop&q=80',
      healthStatus: 'diseased',
      diagnosesCount: 8,
    },
    {
      _id: 'cotton_1',
      cropName: 'Cotton',
      cropType: 'Gossypium hirsutum',
      imageUrl: 'https://images.unsplash.com/photo-1606041008023-472dfb5e530f?w=400&auto=format&fit=crop&q=80',
      healthStatus: 'healthy',
      diagnosesCount: 2,
    },
    {
      _id: 'maize_1',
      cropName: 'Maize',
      cropType: 'Zea mays',
      imageUrl: 'https://images.unsplash.com/photo-1551754655-cd27e38d2076?w=400&auto=format&fit=crop&q=80',
      healthStatus: 'healthy',
      diagnosesCount: 15,
    },
    {
      _id: 'wheat_1',
      cropName: 'Wheat',
      cropType: 'Triticum aestivum',
      imageUrl: 'https://images.unsplash.com/photo-1574323347407-f5e1ad6d020b?w=400&auto=format&fit=crop&q=80',
      healthStatus: 'at_risk',
      diagnosesCount: 4,
    },
  ];

  useEffect(() => {
    const fetchCrops = async () => {
      try {
        const res = await api.get('/crops');
        if (res.data.success && res.data.data.length > 0) {
          setCrops(res.data.data);
        } else {
          setCrops(defaultCrops);
        }
      } catch {
        setCrops(defaultCrops);
      } finally {
        setLoading(false);
      }
    };
    fetchCrops();
  }, []);

  const filteredCrops = crops.filter((crop) => {
    const matchesSearch = crop.cropName.toLowerCase().includes(search.toLowerCase());
    const matchesFilter =
      selectedFilter === 'all' ||
      crop.healthStatus === selectedFilter;
    return matchesSearch && matchesFilter;
  });

  return (
    <div className="min-h-screen bg-[#FAF8F5] pb-8 md:pb-8 select-none">
      <AppHeader title={t('myCropsTitle')} />
      <OfflineBanner />

      <main className="max-w-2xl mx-auto p-3.5 sm:p-4 space-y-3.5 sm:space-y-4">
        {/* Title Section (Matching Stitch Screen 4) */}
        <div className="space-y-1">
          <h2 className="text-xl sm:text-2xl font-extrabold text-[#14382B] tracking-tight">
            {t('myCropsTitle')}
          </h2>
          <p className="text-xs md:text-sm text-[#4B5563] leading-relaxed">
            {t('myCropsSub')}
          </p>
        </div>

        {/* Search Input */}
        <div className="relative">
          <Search className="w-4 h-4 text-[#9CA3AF] absolute left-3.5 top-3.5" />
          <input
            type="text"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder={t('searchCrops')}
            className="w-full bg-white border border-[#EAE5DE] focus:border-[#14382B] focus:ring-2 focus:ring-[#14382B]/10 rounded-2xl pl-10 pr-4 py-2.5 text-xs sm:text-sm text-[#1F2937] placeholder-[#9CA3AF] outline-none shadow-xs transition-all"
          />
        </div>

        {/* Status Filter Chips (Matching Stitch Screen 4) */}
        <div className="flex space-x-2 overflow-x-auto pb-1 scrollbar-none">
          <button
            onClick={() => setSelectedFilter('all')}
            className={`px-3 sm:px-4 py-1.5 rounded-full text-xs font-semibold shrink-0 transition-all ${
              selectedFilter === 'all'
                ? 'bg-[#14382B] text-white shadow-xs'
                : 'bg-white border border-[#EAE5DE] text-[#4B5563] hover:bg-[#FAF8F5]'
            }`}
          >
            {t('allCrops')}
          </button>

          <button
            onClick={() => setSelectedFilter('healthy')}
            className={`px-3 sm:px-3.5 py-1.5 rounded-full text-xs font-semibold shrink-0 transition-all ${
              selectedFilter === 'healthy'
                ? 'bg-[#14382B] text-white shadow-xs'
                : 'bg-white border border-[#EAE5DE] text-[#4B5563] hover:bg-[#FAF8F5]'
            }`}
          >
            {t('healthy')}
          </button>

          <button
            onClick={() => setSelectedFilter('at_risk')}
            className={`px-3 sm:px-3.5 py-1.5 rounded-full text-xs font-semibold shrink-0 flex items-center space-x-1.5 transition-all ${
              selectedFilter === 'at_risk'
                ? 'bg-[#14382B] text-white shadow-xs'
                : 'bg-white border border-[#EAE5DE] text-[#4B5563] hover:bg-[#FAF8F5]'
            }`}
          >
            <span className="w-2 h-2 rounded-full bg-[#EAB308]" />
            <span>{t('atRisk')}</span>
          </button>

          <button
            onClick={() => setSelectedFilter('diseased')}
            className={`px-3 sm:px-3.5 py-1.5 rounded-full text-xs font-semibold shrink-0 flex items-center space-x-1.5 transition-all ${
              selectedFilter === 'diseased'
                ? 'bg-[#14382B] text-white shadow-xs'
                : 'bg-white border border-[#EAE5DE] text-[#4B5563] hover:bg-[#FAF8F5]'
            }`}
          >
            <span className="w-2 h-2 rounded-full bg-[#EF4444]" />
            <span>{t('diseased')}</span>
          </button>
        </div>

        {/* 2-Column Grid of Crop Cards (Matching Stitch Screen 4) */}
        <div className="grid grid-cols-2 gap-2.5 sm:gap-3.5 pt-1">
          {filteredCrops.map((crop) => {
            const isHealthy = crop.healthStatus === 'healthy';
            const isRisk = crop.healthStatus === 'at_risk';

            return (
              <div
                key={crop._id}
                onClick={() => navigate('/diagnose', { state: { selectedCrop: crop.cropName } })}
                className="bg-white border border-[#EAE5DE] rounded-3xl p-3 sm:p-4 shadow-xs hover:shadow-md hover:border-[#14382B]/30 cursor-pointer transition-all flex flex-col justify-between space-y-2.5 sm:space-y-3 relative group"
              >
                {/* Top: Crop image & Status dot */}
                <div className="flex items-start justify-between">
                  <div className="w-12 h-12 sm:w-14 sm:h-14 rounded-2xl overflow-hidden shadow-xs border border-[#FAF8F5] bg-[#EDF7EE]">
                    <img
                      src={crop.imageUrl}
                      alt={crop.cropName}
                      onError={handleImageError}
                      className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-300"
                      loading="lazy"
                    />
                  </div>
                  <span
                    className={`w-2.5 h-2.5 rounded-full mt-1 ${
                      isHealthy
                        ? 'bg-[#22C55E]'
                        : isRisk
                        ? 'bg-[#EAB308]'
                        : 'bg-[#EF4444]'
                    }`}
                  />
                </div>

                {/* Bottom: Name & Diagnoses count */}
                <div className="min-w-0">
                  <h3 className="text-sm sm:text-base font-bold text-[#14382B] truncate">
                    {translateCrop(crop.cropName)}
                  </h3>
                  <p className="text-[10px] sm:text-[11px] text-[#6B7280] truncate">
                    {crop.diagnosesCount || 0} {t('previousDiagnoses')}
                  </p>
                </div>
              </div>
            );
          })}
        </div>
      </main>
    </div>
  );
};

export default MyCropsPage;
