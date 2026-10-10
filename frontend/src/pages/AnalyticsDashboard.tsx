import React, { useState, useEffect } from 'react';
import { useParams, Link } from 'react-router-dom';
import {
  BarChart3,
  TrendingUp,
  Award,
  ShieldCheck,
  FileText,
  Download,
  RefreshCw,
  FolderGit2,
  Calendar,
  ExternalLink,
  ChevronRight,
  Layers,
} from 'lucide-react';
import { api } from '../services/api';
import { QualityScorecard } from '../components/QualityScorecard';
import { MetricsTrendChart, TrendPoint } from '../components/MetricsTrendChart';
import { FailureCategoryPie, FailureCategoryItem } from '../components/FailureCategoryPie';
import { ReportExportModal } from '../components/ReportExportModal';

export const AnalyticsDashboard: React.FC = () => {
  const { projectId: routeProjectId } = useParams<{ projectId?: string }>();

  const [projects, setProjects] = useState<any[]>([]);
  const [selectedProjectId, setSelectedProjectId] = useState<string>(routeProjectId || '');
  const [timeRange, setTimeRange] = useState<string>('30d');
  const [loading, setLoading] = useState<boolean>(true);
  const [platformOverview, setPlatformOverview] = useState<any | null>(null);
  const [analyticsData, setAnalyticsData] = useState<any | null>(null);
  const [savedReports, setSavedReports] = useState<any[]>([]);
  const [isExportModalOpen, setIsExportModalOpen] = useState<boolean>(false);

  useEffect(() => {
    fetchInitialData();
  }, []);

  useEffect(() => {
    if (selectedProjectId) {
      fetchProjectAnalytics(selectedProjectId, timeRange);
      fetchSavedReports(selectedProjectId);
    }
  }, [selectedProjectId, timeRange]);

  const fetchInitialData = async () => {
    setLoading(true);
    try {
      const [overviewRes, projectsRes] = await Promise.all([
        api.get('/analytics/overview'),
        api.get('/projects/'),
      ]);
      setPlatformOverview(overviewRes.data);
      const projList = projectsRes.data.items || [];
      setProjects(projList);

      if (!selectedProjectId && projList.length > 0) {
        setSelectedProjectId(projList[0].id);
      }
    } catch (err) {
      console.error('Failed to load initial analytics data', err);
    } finally {
      setLoading(false);
    }
  };

  const fetchProjectAnalytics = async (projId: string, range: string) => {
    try {
      const res = await api.get(`/analytics/projects/${projId}?time_range=${range}`);
      setAnalyticsData(res.data);
    } catch (err) {
      console.error('Failed to fetch project analytics', err);
    }
  };

  const fetchSavedReports = async (projId: string) => {
    try {
      const res = await api.get(`/analytics/projects/${projId}/reports`);
      setSavedReports(res.data || []);
    } catch (err) {
      console.error('Failed to fetch saved reports', err);
    }
  };

  const selectedProject = projects.find((p) => p.id === selectedProjectId);

  return (
    <div className="space-y-6 pb-12">
      {/* Top Header & Project Selector */}
      <div className="glass-card rounded-2xl p-6 border border-slate-800 flex flex-col md:flex-row items-start md:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2 text-xs text-indigo-400 font-semibold uppercase tracking-wider mb-1">
            <BarChart3 className="w-4 h-4" /> Executive Analytics & Quality Intelligence
          </div>
          <h1 className="text-2xl font-extrabold text-white tracking-tight">
            Software Quality & Reliability Dashboard
          </h1>
          <p className="text-xs text-slate-400 mt-0.5">
            Phase 10 empirical quality metrics, defect clustering, and formal audit documentation.
          </p>
        </div>

        <div className="flex flex-wrap items-center gap-3 w-full md:w-auto">
          {/* Project Selector Dropdown */}
          <div className="flex items-center gap-2 bg-slate-950 border border-slate-800 rounded-xl px-3 py-2 text-xs">
            <FolderGit2 className="w-4 h-4 text-slate-400" />
            <select
              value={selectedProjectId}
              onChange={(e) => setSelectedProjectId(e.target.value)}
              className="bg-transparent text-white font-medium focus:outline-none cursor-pointer"
            >
              {projects.map((p) => (
                <option key={p.id} value={p.id} className="bg-slate-900 text-white">
                  {p.name}
                </option>
              ))}
            </select>
          </div>

          {/* Export Report Button */}
          <button
            onClick={() => setIsExportModalOpen(true)}
            disabled={!selectedProjectId}
            className="px-4 py-2 rounded-xl bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-bold transition-all shadow-lg shadow-indigo-500/25 flex items-center gap-2 shrink-0 disabled:opacity-50"
          >
            <FileText className="w-4 h-4" /> Generate Audit Report
          </button>
        </div>
      </div>

      {/* Platform-Wide Overview Strip */}
      {platformOverview && (
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <div className="glass-card rounded-xl p-4 border border-slate-800 space-y-1">
            <span className="text-[10px] uppercase font-bold text-slate-400 tracking-wider">Total Repositories</span>
            <p className="text-2xl font-extrabold text-white font-mono">{platformOverview.total_projects}</p>
            <span className="text-[11px] text-slate-500">Tracked Microservices</span>
          </div>
          <div className="glass-card rounded-xl p-4 border border-slate-800 space-y-1">
            <span className="text-[10px] uppercase font-bold text-slate-400 tracking-wider">Execution Pipeline</span>
            <p className="text-2xl font-extrabold text-indigo-400 font-mono">{platformOverview.total_test_runs}</p>
            <span className="text-[11px] text-slate-500">Total Test Runs</span>
          </div>
          <div className="glass-card rounded-xl p-4 border border-slate-800 space-y-1">
            <span className="text-[10px] uppercase font-bold text-slate-400 tracking-wider">Pass Rate Average</span>
            <p className="text-2xl font-extrabold text-emerald-400 font-mono">
              {platformOverview.overall_pass_rate.toFixed(1)}%
            </p>
            <span className="text-[11px] text-slate-500">Across {platformOverview.total_tests_executed} tests</span>
          </div>
          <div className="glass-card rounded-xl p-4 border border-slate-800 space-y-1">
            <span className="text-[10px] uppercase font-bold text-slate-400 tracking-wider">Mean Latency</span>
            <p className="text-2xl font-extrabold text-teal-400 font-mono">
              {platformOverview.mean_test_duration_ms.toFixed(0)} ms
            </p>
            <span className="text-[11px] text-slate-500">Target Sandbox Runtime</span>
          </div>
        </div>
      )}

      {/* Project Quality Analytics Section */}
      {analyticsData ? (
        <div className="space-y-6">
          {/* Quality Scorecard */}
          <QualityScorecard
            qualityScore={analyticsData.quality_score}
            testPassRate={analyticsData.test_pass_rate}
            defectDensity={analyticsData.defect_density_per_endpoint}
            flakyRatio={analyticsData.flaky_ratio_percent}
            requirementCoverage={analyticsData.requirement_coverage_percent}
            totalRuns={analyticsData.total_runs}
            totalTests={analyticsData.total_tests_executed}
            testsAvoided={analyticsData.regression_telemetry?.tests_avoided_count || 0}
            timeSavedMs={analyticsData.regression_telemetry?.estimated_time_saved_ms || 0}
            ciGatePassRate={analyticsData.ci_quality_gate?.pass_rate_percent || 100}
          />

          {/* Historical Trends & Defect Breakdown Grid */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            <MetricsTrendChart
              trendData={analyticsData.pass_rate_trend || []}
              timeRange={timeRange}
              onTimeRangeChange={setTimeRange}
            />
            <FailureCategoryPie
              categories={analyticsData.failure_category_breakdown || []}
              totalFailures={analyticsData.failed_tests || 0}
            />
          </div>

          {/* Saved Quality Reports & Audit Trail */}
          <div className="glass-card rounded-2xl border border-slate-800 p-6 space-y-4 shadow-xl">
            <div className="flex items-center justify-between border-b border-slate-800/80 pb-4">
              <div className="flex items-center gap-3">
                <div className="p-2 rounded-xl bg-indigo-500/10 text-indigo-400 border border-indigo-500/20">
                  <FileText className="w-5 h-5" />
                </div>
                <div>
                  <h3 className="text-base font-bold text-white">Generated Executive Audit Artifacts</h3>
                  <p className="text-xs text-slate-400">Cryptographically signed reports ready for export</p>
                </div>
              </div>
              <button
                onClick={() => fetchSavedReports(selectedProjectId)}
                className="p-2 text-slate-400 hover:text-slate-200 hover:bg-slate-800 rounded-xl transition-colors"
                title="Refresh audit reports"
              >
                <RefreshCw className="w-4 h-4" />
              </button>
            </div>

            {savedReports.length === 0 ? (
              <div className="text-center py-8 text-slate-500 text-xs">
                No audit reports generated for this project yet. Click "Generate Audit Report" above to compile one.
              </div>
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full text-left text-xs font-mono">
                  <thead className="bg-slate-950/80 text-slate-400 border-b border-slate-800 uppercase text-[10px]">
                    <tr>
                      <th className="px-4 py-3">Report Title</th>
                      <th className="px-4 py-3">Quality Score</th>
                      <th className="px-4 py-3">SHA256 Fingerprint</th>
                      <th className="px-4 py-3">Generated Date</th>
                      <th className="px-4 py-3 text-right">Actions</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-800/60 text-slate-300">
                    {savedReports.map((report) => (
                      <tr key={report.id} className="hover:bg-slate-800/40 transition-colors">
                        <td className="px-4 py-3 font-bold text-white max-w-[200px] truncate">
                          {report.title}
                        </td>
                        <td className="px-4 py-3">
                          <span className="px-2 py-0.5 rounded font-bold bg-indigo-500/10 text-indigo-400 border border-indigo-500/20">
                            {report.quality_score.toFixed(1)} / 100
                          </span>
                        </td>
                        <td className="px-4 py-3 text-slate-400 text-[11px] truncate max-w-[140px]" title={report.sha256_hash}>
                          {report.sha256_hash ? report.sha256_hash.substring(0, 16) + '...' : 'N/A'}
                        </td>
                        <td className="px-4 py-3 text-slate-500">
                          {new Date(report.created_at).toLocaleDateString()}
                        </td>
                        <td className="px-4 py-3 text-right">
                          <div className="flex items-center justify-end gap-2">
                            <a
                              href={`/api/v1/analytics/reports/${report.id}/export?format=html`}
                              target="_blank"
                              rel="noreferrer"
                              className="px-2.5 py-1 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-300 text-[11px] font-semibold transition-colors inline-flex items-center gap-1"
                            >
                              <ExternalLink className="w-3 h-3 text-indigo-400" /> HTML
                            </a>
                            <a
                              href={`/api/v1/analytics/reports/${report.id}/export?format=pdf`}
                              target="_blank"
                              rel="noreferrer"
                              className="px-2.5 py-1 rounded-lg bg-indigo-600/20 hover:bg-indigo-600/30 border border-indigo-500/30 text-indigo-300 text-[11px] font-semibold transition-colors inline-flex items-center gap-1"
                            >
                              <Download className="w-3 h-3 text-indigo-400" /> PDF
                            </a>
                          </div>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        </div>
      ) : (
        <div className="glass-card rounded-2xl p-12 text-center text-slate-500 text-sm border border-slate-800">
          Loading project analytics and telemetry...
        </div>
      )}

      {/* Export Modal */}
      {selectedProjectId && (
        <ReportExportModal
          isOpen={isExportModalOpen}
          onClose={() => {
            setIsExportModalOpen(false);
            fetchSavedReports(selectedProjectId);
          }}
          projectId={selectedProjectId}
          projectName={selectedProject?.name || 'Project'}
        />
      )}
    </div>
  );
};
