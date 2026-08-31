import React from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import { AuthProvider } from './context/AuthContext';
import { AnalysisProvider } from './context/AnalysisContext';
import { ToastProvider } from './context/ToastContext';
import { ConfirmDialogProvider } from './context/ConfirmDialogContext';
import { ScriptProvider } from './context/ScriptContext';
import { StoryDayProvider } from './context/StoryDayContext';
import MainLayout from './components/layout/MainLayout';
import ScriptUpload from './components/script/ScriptUpload';
import SceneViewer from './components/scenes/SceneViewer';
import ScriptLibrary from './components/scripts/ScriptLibrary';
import Stripboard from './components/reports/Stripboard';
import ZoomableStripboard from './components/board/ZoomableStripboard';
import ResetPasswordPage from './pages/ResetPasswordPage';
import LoginPage from './pages/LoginPage';
import ProfilePage from './pages/ProfilePage';
import AuthCallbackPage from './pages/AuthCallbackPage';
import ConfirmEmailPage from './pages/ConfirmEmailPage';
import ProtectedRoute from './components/auth/ProtectedRoute';
import AdminRoute from './components/auth/AdminRoute';
import AdminTestPage from './pages/Admin/AdminTestPage';
import AnalyticsDashboard from './pages/Admin/AnalyticsDashboard';
import UserActivityPage from './pages/Admin/UserActivityPage';
import ScriptAnalyticsPage from './pages/Admin/ScriptAnalyticsPage';
import PaymentVerification from './components/admin/PaymentVerification';
import EmailCampaignsPage from './pages/Admin/EmailCampaignsPage';
import './App.css';

// Active imports
import ReportStudio from './components/reports/ReportStudio';
import ShootingSchedulePage from './components/schedule/ShootingSchedulePage';
import SharedReportView from './components/reports/SharedReportView';

// Phase 2+ imports (deferred)
// import CharacterProfile from './components/characters/CharacterProfile';
// import ScriptEditorPage from './pages/ScriptEditorPage';
// import SceneManager from './components/scenes/SceneManager';
// import ShootingScriptPreview from './components/scripts/ShootingScriptPreview';
// import DepartmentWorkspace from './components/workspace/DepartmentWorkspace';
// import SettingsPage from './pages/SettingsPage';
import InvitePage from './pages/InvitePage';
import BillingPage from './pages/BillingPage';
import PaymentResultPage from './pages/PaymentResultPage';
import CastPage from './components/cast/CastPage';
import SeriesListPage from './pages/SeriesListPage';
import SeriesDetailPage from './pages/SeriesDetailPage';
import SeasonPage from './pages/SeasonPage';
import ProductionsListPage from './pages/ProductionsListPage';
import ProductionDetailPage from './pages/ProductionDetailPage';

function App() {
  return (
    <AuthProvider>
      <ToastProvider>
        <ConfirmDialogProvider>
          <AnalysisProvider>
            <ScriptProvider>
              <StoryDayProvider>
              <Router>
                <Routes>
                  {/* Protected routes (require authentication) */}
                  <Route path="/" element={
                    <ProtectedRoute>
                      <MainLayout />
                    </ProtectedRoute>
                  }>
                    {/* Redirect root to scripts (My Scripts is the landing page) */}
                    <Route index element={<Navigate to="/scripts" replace />} />
                    <Route path="upload" element={<ScriptUpload />} />
                    <Route path="scripts" element={<ScriptLibrary />} />
                    <Route path="scenes/:scriptId" element={<SceneViewer />} />
                    <Route path="scripts/:scriptId/stripboard" element={<Stripboard />} />
                    <Route path="scripts/:scriptId/reports" element={<ReportStudio />} />
                    <Route path="scripts/:scriptId/board" element={<ZoomableStripboard />} />
                    <Route path="scripts/:scriptId/schedule" element={<ShootingSchedulePage />} />
                    <Route path="scripts/:scriptId/cast" element={<CastPage />} />
                    <Route path="profile" element={<ProfilePage />} />
                    <Route path="billing" element={<BillingPage />} />
                    <Route path="series" element={<SeriesListPage />} />
                    <Route path="series/:seriesId" element={<SeriesDetailPage />} />
                    <Route path="series/:seriesId/seasons/:seasonId" element={<SeasonPage />} />
                    <Route path="productions" element={<ProductionsListPage />} />
                    <Route path="productions/:productionId" element={<ProductionDetailPage />} />
                    <Route path="payment/success" element={<PaymentResultPage outcome="success" />} />
                    <Route path="payment/cancel" element={<PaymentResultPage outcome="cancel" />} />

                    {/* Phase 2+ routes (deferred - commented out) */}
                    {/* <Route path="scenes/:scriptId/workspace/:departmentCode" element={<DepartmentWorkspace />} /> */}
                    {/* <Route path="scenes/:scriptId/workspace" element={<DepartmentWorkspace />} /> */}
                    {/* <Route path="scripts/:scriptId/edit" element={<ScriptEditorPage />} /> */}
                    {/* <Route path="scripts/:scriptId/manage" element={<SceneManager />} /> */}
                    {/* <Route path="scripts/:scriptId/shooting-script" element={<ShootingScriptPreview />} /> */}
                    {/* <Route path="scripts/:scriptId/characters/:characterName" element={<CharacterProfile />} /> */}
                    {/* <Route path="scripts/:scriptId/workspace/:departmentCode" element={<DepartmentWorkspace />} /> */}
                    {/* <Route path="scripts/:scriptId/workspace" element={<DepartmentWorkspace />} /> */}
                  </Route>

                  {/* Admin routes (superuser only) */}
                  <Route path="admin" element={
                    <AdminRoute>
                      <AnalyticsDashboard />
                    </AdminRoute>
                  } />
                  <Route path="admin/users" element={
                    <AdminRoute>
                      <UserActivityPage />
                    </AdminRoute>
                  } />
                  <Route path="admin/scripts" element={
                    <AdminRoute>
                      <ScriptAnalyticsPage />
                    </AdminRoute>
                  } />
                  <Route path="admin/payments" element={
                    <AdminRoute>
                      <PaymentVerification />
                    </AdminRoute>
                  } />
                  <Route path="admin/test" element={
                    <AdminRoute>
                      <AdminTestPage />
                    </AdminRoute>
                  } />
                  <Route path="admin/emails" element={
                    <AdminRoute>
                      <EmailCampaignsPage />
                    </AdminRoute>
                  } />
                  
                  {/* Phase 2+ routes (deferred) */}
                  {/* <Route path="settings" element={<ProtectedRoute><SettingsPage /></ProtectedRoute>} /> */}
                  
                  {/* Public routes (no authentication required) */}
                  <Route path="login" element={<LoginPage />} />
                  <Route path="reset-password" element={<ResetPasswordPage />} />
                  <Route path="auth/callback" element={<AuthCallbackPage />} />
                  <Route path="auth/confirm" element={<ConfirmEmailPage />} />
                  
                  {/* Shared report view (public) */}
                  <Route path="shared/:shareToken" element={<SharedReportView />} />
                  
                  <Route path="invite/:token" element={<InvitePage />} />
                </Routes>
              </Router>
              </StoryDayProvider>
            </ScriptProvider>
          </AnalysisProvider>
        </ConfirmDialogProvider>
      </ToastProvider>
    </AuthProvider>
  );
}

export default App;
