import React from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { useAuthStore } from './store/authStore';
import { Layout } from './components/layout/Layout';
import { Login } from './pages/Login';
import { DashboardOverview } from './pages/DashboardOverview';
import { ProjectsList } from './pages/ProjectsList';
import { ProjectDetail } from './pages/ProjectDetail';
import { TestRunDetail } from './pages/TestRunDetail';
import { RequirementIntelligence } from './pages/RequirementIntelligence';
import { DefectDashboard } from './pages/DefectDashboard';
import { AnalyticsDashboard } from './pages/AnalyticsDashboard';
import { BenchmarkEvaluationPage } from './pages/BenchmarkEvaluationPage';
import { AdminDashboard } from './pages/AdminDashboard';
import { CodeStudio } from './pages/CodeStudio';
import { ErrorBoundary } from './components/ErrorBoundary';
import { FirstTimePasswordModal } from './components/FirstTimePasswordModal';
import { SessionExpiredModal } from './components/common/SessionExpiredModal';

const ProtectedRoute: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const { token, isSessionExpired } = useAuthStore();
  if (!token && !isSessionExpired) {
    return <Navigate to="/login" replace />;
  }
  return (
    <>
      <FirstTimePasswordModal />
      <SessionExpiredModal />
      <Layout>
        <ErrorBoundary>{children}</ErrorBoundary>
      </Layout>
    </>
  );
};

export default function App() {
  const { token } = useAuthStore();

  return (
    <BrowserRouter>
      <Routes>
        <Route
          path="/login"
          element={token ? <Navigate to="/" replace /> : <Login />}
        />
        <Route
          path="/"
          element={
            <ProtectedRoute>
              <DashboardOverview />
            </ProtectedRoute>
          }
        />
        <Route
          path="/projects"
          element={
            <ProtectedRoute>
              <ProjectsList />
            </ProtectedRoute>
          }
        />
        <Route
          path="/projects/:id"
          element={
            <ProtectedRoute>
              <ProjectDetail />
            </ProtectedRoute>
          }
        />
        <Route
          path="/projects/:id/requirements"
          element={
            <ProtectedRoute>
              <RequirementIntelligence />
            </ProtectedRoute>
          }
        />
        <Route
          path="/projects/:projectId/test-runs/:runId"
          element={
            <ProtectedRoute>
              <TestRunDetail />
            </ProtectedRoute>
          }
        />
        <Route
          path="/projects/:projectId/defects"
          element={
            <ProtectedRoute>
              <DefectDashboard />
            </ProtectedRoute>
          }
        />
        <Route
          path="/analytics"
          element={
            <ProtectedRoute>
              <AnalyticsDashboard />
            </ProtectedRoute>
          }
        />
        <Route
          path="/projects/:projectId/analytics"
          element={
            <ProtectedRoute>
              <AnalyticsDashboard />
            </ProtectedRoute>
          }
        />
        <Route
          path="/benchmarks"
          element={
            <ProtectedRoute>
              <BenchmarkEvaluationPage />
            </ProtectedRoute>
          }
        />
        <Route
          path="/admin"
          element={
            <ProtectedRoute>
              <AdminDashboard />
            </ProtectedRoute>
          }
        />
        <Route
          path="/projects/:id/ide"
          element={
            <ProtectedRoute>
              <CodeStudio />
            </ProtectedRoute>
          }
        />
        <Route
          path="/ide"
          element={
            <ProtectedRoute>
              <CodeStudio />
            </ProtectedRoute>
          }
        />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </BrowserRouter>
  );
}
