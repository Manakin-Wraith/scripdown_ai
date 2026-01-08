import React from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import { AuthProvider } from './context/AuthContext';
import { AnalysisProvider } from './context/AnalysisContext';
import { ToastProvider } from './context/ToastContext';
import { ConfirmDialogProvider } from './context/ConfirmDialogContext';
import { ScriptProvider } from './context/ScriptContext';
import MainLayout from './components/layout/MainLayout';
import ScriptUpload from './components/script/ScriptUpload';
import SceneViewer from './components/scenes/SceneViewer';
import ScriptLibrary from './components/scripts/ScriptLibrary';
import Stripboard from './components/reports/Stripboard';
import ResetPasswordPage from './pages/ResetPasswordPage';
import LoginPage from './pages/LoginPage';
import ProfilePage from './pages/ProfilePage';
import AuthCallbackPage from './pages/AuthCallbackPage';
import ConfirmEmailPage from './pages/ConfirmEmailPage';
import ProtectedRoute from './components/auth/ProtectedRoute';
import './App.css';

// Phase 2+ imports (deferred)
// import CharacterProfile from './components/characters/CharacterProfile';
// import ScriptEditorPage from './pages/ScriptEditorPage';
// import SceneManager from './components/scenes/SceneManager';
// import ShootingScriptPreview from './components/scripts/ShootingScriptPreview';
// import ReportBuilder from './components/reports/ReportBuilder';
// import SharedReportView from './components/reports/SharedReportView';
// import DepartmentWorkspace from './components/workspace/DepartmentWorkspace';
// import SettingsPage from './pages/SettingsPage';
// import InvitePage from './pages/InvitePage';
// import PaymentSuccessPage from './pages/PaymentSuccessPage';

function App() {
  return (
    <AuthProvider>
      <ToastProvider>
        <ConfirmDialogProvider>
          <AnalysisProvider>
            <ScriptProvider>
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
                    
                    {/* Phase 2+ routes (deferred - commented out) */}
                    {/* <Route path="scenes/:scriptId/workspace/:departmentCode" element={<DepartmentWorkspace />} /> */}
                    {/* <Route path="scenes/:scriptId/workspace" element={<DepartmentWorkspace />} /> */}
                    {/* <Route path="scripts/:scriptId/edit" element={<ScriptEditorPage />} /> */}
                    {/* <Route path="scripts/:scriptId/manage" element={<SceneManager />} /> */}
                    {/* <Route path="scripts/:scriptId/shooting-script" element={<ShootingScriptPreview />} /> */}
                    {/* <Route path="scripts/:scriptId/characters/:characterName" element={<CharacterProfile />} /> */}
                    {/* <Route path="scripts/:scriptId/reports" element={<ReportBuilder />} /> */}
                    {/* <Route path="scripts/:scriptId/workspace/:departmentCode" element={<DepartmentWorkspace />} /> */}
                    {/* <Route path="scripts/:scriptId/workspace" element={<DepartmentWorkspace />} /> */}
                  </Route>
                  
                  {/* Protected routes outside MainLayout */}
                  <Route path="profile" element={
                    <ProtectedRoute>
                      <ProfilePage />
                    </ProtectedRoute>
                  } />
                  
                  {/* Phase 2+ routes (deferred) */}
                  {/* <Route path="settings" element={<ProtectedRoute><SettingsPage /></ProtectedRoute>} /> */}
                  
                  {/* Public routes (no authentication required) */}
                  <Route path="login" element={<LoginPage />} />
                  <Route path="reset-password" element={<ResetPasswordPage />} />
                  <Route path="auth/callback" element={<AuthCallbackPage />} />
                  <Route path="auth/confirm" element={<ConfirmEmailPage />} />
                  
                  {/* Phase 2+ public routes (deferred) */}
                  {/* <Route path="invite/:token" element={<InvitePage />} /> */}
                  {/* <Route path="shared/:shareToken" element={<SharedReportView />} /> */}
                  {/* <Route path="payment-success" element={<PaymentSuccessPage />} /> */}
                </Routes>
              </Router>
            </ScriptProvider>
          </AnalysisProvider>
        </ConfirmDialogProvider>
      </ToastProvider>
    </AuthProvider>
  );
}

export default App;
