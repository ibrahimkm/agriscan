import React from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { AuthProvider } from './context/AuthContext';
import { ConnectivityProvider } from './context/ConnectivityContext';
import { LanguageProvider } from './context/LanguageContext';
import ProtectedRoute from './components/auth/ProtectedRoute';

// Layouts & Nav
import BottomNavigation from './components/navigation/BottomNavigation';
import Sidebar from './components/navigation/Sidebar';

// Pages
import SplashPage from './pages/SplashPage';
import OnboardingPage from './pages/OnboardingPage';
import LoginPage from './pages/LoginPage';
import RegisterPage from './pages/RegisterPage';
import HomePage from './pages/HomePage';
import MyCropsPage from './pages/MyCropsPage';
import DiagnosePage from './pages/DiagnosePage';
import AnalysisPage from './pages/AnalysisPage';
import DiagnosisResultPage from './pages/DiagnosisResultPage';
import DiseaseExplanationPage from './pages/DiseaseExplanationPage';
import TreatmentPlanPage from './pages/TreatmentPlanPage';
import YoloAnalysisPage from './pages/YoloAnalysisPage';
import HistoryPage from './pages/HistoryPage';
import AnalyticsPage from './pages/AnalyticsPage';
import ProfilePage from './pages/ProfilePage';

const AppLayout = ({ children }) => {
  return (
    <div className="flex min-h-screen bg-[#FAF8F5]">
      {/* Desktop & Tablet Sidebar */}
      <Sidebar />

      {/* Main Content Area */}
      <div className="flex-1 flex flex-col min-w-0">
        {children}
        {/* Mobile Bottom Navigation Bar */}
        <BottomNavigation />
      </div>
    </div>
  );
};

export const App = () => {
  return (
    <LanguageProvider>
      <AuthProvider>
        <ConnectivityProvider>
          <BrowserRouter>
            <Routes>
              {/* Public Unauthenticated Entry Routes */}
              <Route path="/" element={<SplashPage />} />
              <Route path="/onboarding" element={<OnboardingPage />} />
              <Route path="/login" element={<LoginPage />} />
              <Route path="/register" element={<RegisterPage />} />

              {/* Protected Full-Screen Scanners & Workflows */}
              <Route
                path="/diagnose"
                element={
                  <ProtectedRoute>
                    <DiagnosePage />
                  </ProtectedRoute>
                }
              />
              <Route
                path="/analyze"
                element={
                  <ProtectedRoute>
                    <AnalysisPage />
                  </ProtectedRoute>
                }
              />

              {/* Protected Application Layout Routes */}
              <Route
                path="/home"
                element={
                  <ProtectedRoute>
                    <AppLayout>
                      <HomePage />
                    </AppLayout>
                  </ProtectedRoute>
                }
              />
              <Route
                path="/crops"
                element={
                  <ProtectedRoute>
                    <AppLayout>
                      <MyCropsPage />
                    </AppLayout>
                  </ProtectedRoute>
                }
              />
              <Route
                path="/diagnosis/:id"
                element={
                  <ProtectedRoute>
                    <AppLayout>
                      <DiagnosisResultPage />
                    </AppLayout>
                  </ProtectedRoute>
                }
              />
              <Route
                path="/diagnosis/:id/explanation"
                element={
                  <ProtectedRoute>
                    <AppLayout>
                      <DiseaseExplanationPage />
                    </AppLayout>
                  </ProtectedRoute>
                }
              />
              <Route
                path="/diagnosis/:id/treatment"
                element={
                  <ProtectedRoute>
                    <AppLayout>
                      <TreatmentPlanPage />
                    </AppLayout>
                  </ProtectedRoute>
                }
              />
              <Route
                path="/detections"
                element={
                  <ProtectedRoute>
                    <AppLayout>
                      <YoloAnalysisPage />
                    </AppLayout>
                  </ProtectedRoute>
                }
              />
              <Route
                path="/history"
                element={
                  <ProtectedRoute>
                    <AppLayout>
                      <HistoryPage />
                    </AppLayout>
                  </ProtectedRoute>
                }
              />
              <Route
                path="/analytics"
                element={
                  <ProtectedRoute>
                    <AppLayout>
                      <AnalyticsPage />
                    </AppLayout>
                  </ProtectedRoute>
                }
              />
              <Route
                path="/profile"
                element={
                  <ProtectedRoute>
                    <AppLayout>
                      <ProfilePage />
                    </AppLayout>
                  </ProtectedRoute>
                }
              />

              {/* Catch-all fallback */}
              <Route path="*" element={<Navigate to="/home" replace />} />
            </Routes>
          </BrowserRouter>
        </ConnectivityProvider>
      </AuthProvider>
    </LanguageProvider>
  );
};

export default App;
