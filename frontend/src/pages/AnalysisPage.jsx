import React from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import AppHeader from '../components/navigation/AppHeader';
import ScanAnimation from '../components/diagnosis/ScanAnimation';
import api from '../services/api';
import { saveOfflineDiagnosis } from '../services/indexedDB';
import { useConnectivity } from '../context/ConnectivityContext';
import { useLanguage } from '../context/LanguageContext';
import { runLocalDiagnosis } from '../services/localMLInference';

export const AnalysisPage = () => {
  const navigate = useNavigate();
  const location = useLocation();
  const { isOnline } = useConnectivity();
  const { language, t } = useLanguage();

  const capturedImage = location.state?.capturedImage || 'https://images.unsplash.com/photo-1592417817098-8f3d6eb2260f?w=800&auto=format&fit=crop&q=80';
  const cropName = location.state?.cropName || 'Tomato';

  const handleAnalysisComplete = async () => {
    try {
      // Run on-device local offline neural network diagnosis engine (ONNX WASM)
      const localResult = await runLocalDiagnosis({ cropName, language, image: capturedImage });
      localResult.imageUrl = capturedImage;

      // Save locally to IndexedDB immediately (100% offline reliability)
      const savedOffline = await saveOfflineDiagnosis(localResult);

      // If online, optionally sync to backend
      if (isOnline) {
        api.post('/diagnoses', {
          cropName,
          base64Image: capturedImage.startsWith('data:') ? capturedImage : null,
          imageUrl: !capturedImage.startsWith('data:') ? capturedImage : null,
          clientOfflineId: savedOffline.id,
        }).then((res) => {
          if (res.data?.success) {
            savedOffline._id = res.data.data._id;
          }
        }).catch(() => {});
      }

      navigate(`/diagnosis/${savedOffline.id}`, { state: { diagnosis: savedOffline } });
    } catch (err) {
      console.error('[Analysis Error]', err);
      navigate('/home');
    }
  };

  return (
    <div className="min-h-screen bg-[#FAF8F5] select-none">
      <AppHeader title={t('diagnosticProcess')} showBack backTo="/diagnose" />

      <main className="max-w-md mx-auto py-4">
        <ScanAnimation
          imageUrl={capturedImage}
          cropName={cropName}
          onComplete={handleAnalysisComplete}
          onCancel={() => navigate('/diagnose')}
        />
      </main>
    </div>
  );
};

export default AnalysisPage;
