import React, { lazy, Suspense } from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import { AuthProvider } from './context/AuthContext';
import { AnalysisProvider } from './context/AnalysisContext';
import { ToastProvider } from './context/ToastContext';
import { ConfirmDialogProvider } from './context/ConfirmDialogContext';
import { ScriptProvider } from './context/ScriptContext';
import { StoryDayProvider } from './context/StoryDayContext';
import MainLayout from './components/layout/MainLayout';
import LoginPage from './pages/LoginPage';
import ProtectedRoute from './components/auth/ProtectedRoute';
import AdminRoute from './components/auth/AdminRoute';
import './App.css';

// Active imports

// Phase 2+ imports (deferred)
// import CharacterProfile from './components/characters/CharacterProfile';
// import ScriptEditorPage from './pages/ScriptEditorPage';
// import ShootingScriptPreview from './components/scripts/ShootingScriptPreview';
// import DepartmentWorkspace from './components/workspace/DepartmentWorkspace';
// import SettingsPage from './pages/SettingsPage';

// Route-level code splitting: each page loads on demand.
const ScriptUpload = lazy(() => import('./components/script/ScriptUpload'));
const SceneViewer = lazy(() => import('./components/scenes/SceneViewer'));
const ScriptLibrary = lazy(() => import('./components/scripts/ScriptLibrary'));
const Stripboard = lazy(() => import('./components/reports/Stripboard'));
const ZoomableStripboard = lazy(() => import('./components/board/ZoomableStripboard'));
const ResetPasswordPage = lazy(() => import('./pages/ResetPasswordPage'));
const ProfilePage = lazy(() => import('./pages/ProfilePage'));
const AuthCallbackPage = lazy(() => import('./pages/AuthCallbackPage'));
const ConfirmEmailPage = lazy(() => import('./pages/ConfirmEmailPage'));
const AdminTestPage = lazy(() => import('./pages/Admin/AdminTestPage'));
const AnalyticsDashboard = lazy(() => import('./pages/Admin/AnalyticsDashboard'));
const UserActivityPage = lazy(() => import('./pages/Admin/UserActivityPage'));
const ScriptAnalyticsPage = lazy(() => import('./pages/Admin/ScriptAnalyticsPage'));
const PaymentVerification = lazy(() => import('./components/admin/PaymentVerification'));
const EmailCampaignsPage = lazy(() => import('./pages/Admin/EmailCampaignsPage'));
const ReportStudio = lazy(() => import('./components/reports/ReportStudio'));
const ShootingSchedulePage = lazy(() => import('./components/schedule/ShootingSchedulePage'));
const SharedReportView = lazy(() => import('./components/reports/SharedReportView'));
const SceneManager = lazy(() => import('./components/scenes/SceneManager'));
const InvitePage = lazy(() => import('./pages/InvitePage'));
const ProductionInviteAccept = lazy(() => import('./pages/ProductionInviteAccept'));
const BillingPage = lazy(() => import('./pages/BillingPage'));
const PaymentResultPage = lazy(() => import('./pages/PaymentResultPage'));
const CastRoute = lazy(() => import('./components/cast/CastRoute'));
const SeriesListPage = lazy(() => import('./pages/SeriesListPage'));
const SeriesDetailPage = lazy(() => import('./pages/SeriesDetailPage'));
const SeasonPage = lazy(() => import('./pages/SeasonPage'));
const ProductionsListPage = lazy(() => import('./pages/ProductionsListPage'));
const ProductionDetailPage = lazy(() => import('./pages/ProductionDetailPage'));
const ContactsListPage = lazy(() => import('./pages/ContactsListPage'));
const LocationsListPage = lazy(() => import('./pages/LocationsListPage'));
const ContactPane = lazy(() => import('./components/contacts/ContactPane'));
const LocationPane = lazy(() => import('./components/locations/LocationPane'));

function RouteFallback() {
  return <div style={{ padding: '2rem', textAlign: 'center', opacity: 0.6 }}>Loading…</div>;
}

function App() {
  return (
    <AuthProvider>
      <ToastProvider>
        <ConfirmDialogProvider>
          <AnalysisProvider>
            <ScriptProvider>
              <StoryDayProvider>
              <Router>
                <Suspense fallback={<RouteFallback />}>
                <Routes>
                  {/* Protected routes (require authentication) */}
                  <Route path="/" element={
                    <ProtectedRoute>
                      <MainLayout />
                    </ProtectedRoute>
                  }>
                    {/* Redirect root to scripts (Scripts is the landing page) */}
                    <Route index element={<Navigate to="/scripts" replace />} />
                    <Route path="upload" element={<ScriptUpload />} />
                    <Route path="scripts" element={<ScriptLibrary />} />
                    <Route path="scenes/:scriptId" element={<SceneViewer />} />
                    <Route path="scripts/:scriptId/stripboard" element={<Stripboard />} />
                    <Route path="scripts/:scriptId/reports" element={<ReportStudio />} />
                    <Route path="scripts/:scriptId/board" element={<ZoomableStripboard />} />
                    <Route path="scripts/:scriptId/manage" element={<SceneManager />} />
                    <Route path="scripts/:scriptId/schedule" element={<ShootingSchedulePage />} />
                    <Route path="scripts/:scriptId/cast" element={<CastRoute />} />
                    <Route path="profile" element={<ProfilePage />} />
                    <Route path="billing" element={<BillingPage />} />
                    <Route path="series" element={<SeriesListPage />} />
                    <Route path="series/:seriesId" element={<SeriesDetailPage />} />
                    <Route path="series/:seriesId/seasons/:seasonId" element={<SeasonPage />} />
                    <Route path="productions" element={<ProductionsListPage />} />
                    <Route path="productions/:productionId/:tab?/:subId?" element={<ProductionDetailPage />} />
                    <Route path="contacts" element={<ContactsListPage />}>
                      <Route path="new" element={<ContactPane mode="new" />} />
                      <Route path=":contactId" element={<ContactPane mode="view" />} />
                      <Route path=":contactId/edit" element={<ContactPane mode="edit" />} />
                    </Route>
                    <Route path="locations" element={<LocationsListPage />}>
                      <Route path="new" element={<LocationPane mode="new" />} />
                      <Route path=":locationId" element={<LocationPane mode="view" />} />
                      <Route path=":locationId/edit" element={<LocationPane mode="edit" />} />
                    </Route>
                    <Route path="payment/success" element={<PaymentResultPage outcome="success" />} />
                    <Route path="payment/cancel" element={<PaymentResultPage outcome="cancel" />} />

                    {/* Phase 2+ routes (deferred - commented out) */}
                    {/* <Route path="scenes/:scriptId/workspace/:departmentCode" element={<DepartmentWorkspace />} /> */}
                    {/* <Route path="scenes/:scriptId/workspace" element={<DepartmentWorkspace />} /> */}
                    {/* <Route path="scripts/:scriptId/edit" element={<ScriptEditorPage />} /> */}
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
                  <Route path="production-invites/:token" element={<ProductionInviteAccept />} />
                </Routes>
                </Suspense>
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
