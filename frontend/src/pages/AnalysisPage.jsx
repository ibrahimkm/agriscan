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

  const capturedImage = location.state?.capturedImage;
  const cropName = location.state?.cropName;
  const [errorMsg, setErrorMsg] = React.useState(null);

  React.useEffect(() => {
    if (!capturedImage) {
      navigate('/diagnose', { replace: true });
    }
  }, [capturedImage, navigate]);

  const handleAnalysisComplete = async () => {
    try {
      let diagnosisResult = null;

      // 1. Primary path: if online, run inference on backend with real EfficientNet ONNX model
      if (isOnline) {
        try {
          const payload = {
            base64Image: capturedImage?.startsWith('data:') ? capturedImage : null,
            imageUrl: !capturedImage?.startsWith('data:') ? capturedImage : null,
            cropName: cropName || undefined,
          };
          const res = await api.post('/diagnoses', payload);
          if (res.data?.success && res.data?.data) {
            diagnosisResult = res.data.data;
          }
        } catch (backendErr) {
          console.warn('[Analysis] Backend diagnosis failed, checking local offline fallback:', backendErr);
        }
      }

      // 2. Fallback path: if backend unavailable or offline, try local on-device inference
      if (!diagnosisResult) {
        try {
          const localResult = await runLocalDiagnosis({ cropName, language, image: capturedImage });
          localResult.imageUrl = capturedImage;
          diagnosisResult = localResult;
        } catch (localErr) {
          console.warn('[Analysis] Local inference also unavailable:', localErr);
        }
      }

      // 3. If both failed, do NOT substitute fake data; show user error
      if (!diagnosisResult) {
        throw new Error('Inference failed: Unable to classify image with the ML model. Please check connectivity and image quality.');
      }

      // 4. Save to IndexedDB for offline history
      const savedOffline = await saveOfflineDiagnosis(diagnosisResult);
      const diagnosisId = diagnosisResult._id || savedOffline.id;

      navigate(`/diagnosis/${diagnosisId}`, { state: { diagnosis: diagnosisResult } });
    } catch (err) {
      console.error('[Analysis Error]', err);
      setErrorMsg(err.message || 'Diagnosis failed. Please retake the leaf image.');
    }
  };

  if (errorMsg) {
    return (
      <div className="min-h-screen bg-[#FAF8F5] select-none flex flex-col items-center justify-center p-6 text-center space-y-4">
        <div className="w-14 h-14 rounded-full bg-red-100 text-red-600 flex items-center justify-center">
          <span className="text-2xl font-bold">!</span>
        </div>
        <h2 className="text-lg font-bold text-[#14382B]">Diagnosis Failed</h2>
        <p className="text-sm text-zinc-600 max-w-xs">{errorMsg}</p>
        <button
          onClick={() => navigate('/diagnose')}
          className="px-6 py-2.5 rounded-full bg-[#14382B] text-white font-semibold text-sm hover:bg-[#1B4332] transition-colors"
        >
          {t('retake') || 'Retake Image'}
        </button>
      </div>
    );
  }

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
