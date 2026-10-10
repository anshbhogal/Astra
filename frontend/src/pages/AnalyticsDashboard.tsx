import React, { useState, useEffect } from 'react';
import { useParams, Link } from 'react-router-dom';
import {
  BarChart3,
  FileText,
  Download,
  RefreshCw,
  FolderGit2,
  ExternalLink,
  Layers,
} from 'lucide-react';
import { api } from '../services/api';
import { QualityScorecard } from '../components/QualityScorecard';
import { MetricsTrendChart } from '../components/MetricsTrendChart';
import { FailureCategoryPie } from '../components/FailureCategoryPie';
import { ReportExportModal } from '../components/ReportExportModal';
import { Button } from '../components/common/Button';

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
      <div className="bg-card rounded-2xl p-6 border border-border-card shadow-card flex flex-col md:flex-row items-start md:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2 text-xs text-brand font-semibold uppercase tracking-wider mb-1">
            <BarChart3 className="w-4 h-4" /> Executive Analytics & Quality Intelligence
          </div>
          <h1 className="text-2xl font-bold text-primary tracking-tight">
            Software Quality & Reliability Dashboard
          </h1>
          <p className="text-xs text-secondary mt-0.5">
            Empirical quality metrics, defect clustering, and formal audit documentation.
          </p>
        </div>

        <div className="flex flex-wrap items-center gap-3 w-full md:w-auto">
          {/* Project Selector Dropdown */}
          <div className="flex items-center gap-2 bg-field border border-border-field rounded-lg px-3 h-10 text-xs">
            <FolderGit2 className="w-4 h-4 text-secondary" />
            <select
              value={selectedProjectId}
              onChange={(e) => setSelectedProjectId(e.target.value)}
              className="bg-transparent text-primary font-medium focus:outline-none cursor-pointer"
            >
              {projects.map((p) => (
                <option key={p.id} value={p.id} className="bg-card text-primary">
                  {p.name}
                </option>
              ))}
            </select>
          </div>

          {/* Export Report Button */}
          <Button
            variant="primary"
            onClick={() => setIsExportModalOpen(true)}
            disabled={!selectedProjectId}
            leftIcon={<FileText className="w-4 h-4" />}
          >
            Generate Audit Report
          </Button>
        </div>
      </div>

      {/* Platform-Wide Overview Strip with 32px Icon Chips */}
      {platformOverview && (
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <div className="bg-card rounded-xl p-5 border border-border-card shadow-card space-y-2">
            <div className="flex items-center justify-between">
              <span className="text-[10px] uppercase font-semibold text-muted tracking-wider">Total Repositories</span>
              <div className="w-8 h-8 rounded-lg bg-brand/10 border border-brand/20 flex items-center justify-center text-brand">
                <FolderGit2 className="w-4 h-4" />
              </div>
            </div>
            <div>
              <p className="text-2xl font-bold text-primary">{platformOverview.total_projects ?? 0}</p>
              <span className="text-[11px] text-muted">Tracked Microservices</span>
            </div>
          </div>

          <div className="bg-card rounded-xl p-5 border border-border-card shadow-card space-y-2">
            <div className="flex items-center justify-between">
              <span className="text-[10px] uppercase font-semibold text-muted tracking-wider">Execution Pipeline</span>
              <div className="w-8 h-8 rounded-lg bg-brand/10 border border-brand/20 flex items-center justify-center text-brand">
                <Layers className="w-4 h-4" />
              </div>
            </div>
            <div>
              <p className="text-2xl font-bold text-brand">{platformOverview.total_test_runs ?? 0}</p>
              <span className="text-[11px] text-muted">Total Test Runs</span>
            </div>
          </div>

          <div className="bg-card rounded-xl p-5 border border-border-card shadow-card space-y-2">
            <div className="flex items-center justify-between">
              <span className="text-[10px] uppercase font-semibold text-muted tracking-wider">Pass Rate Average</span>
              <div className="w-8 h-8 rounded-lg bg-status-passed-bg border border-status-passed/30 flex items-center justify-center text-status-passed">
                <BarChart3 className="w-4 h-4" />
              </div>
            </div>
            <div>
              <p className="text-2xl font-bold text-status-passed">
                {Number(platformOverview.overall_pass_rate ?? 0).toFixed(1)}%
              </p>
              <span className="text-[11px] text-muted">Across {platformOverview.total_tests_executed ?? 0} tests</span>
            </div>
          </div>

          <div className="bg-card rounded-xl p-5 border border-border-card shadow-card space-y-2">
            <div className="flex items-center justify-between">
              <span className="text-[10px] uppercase font-semibold text-muted tracking-wider">Mean Latency</span>
              <div className="w-8 h-8 rounded-lg bg-secondaryAccent/10 border border-secondaryAccent/20 flex items-center justify-center text-secondaryAccent">
                <BarChart3 className="w-4 h-4" />
              </div>
            </div>
            <div>
              <p className="text-2xl font-bold text-primary font-mono">
                {Number(platformOverview.mean_test_duration_ms ?? platformOverview.mean_execution_time_ms ?? 0).toFixed(0)} ms
              </p>
              <span className="text-[11px] text-muted">Target Sandbox Runtime</span>
            </div>
          </div>
        </div>
      )}

      {/* Project Quality Analytics Section */}
      {analyticsData ? (
        <div className="space-y-6">
          {/* Quality Scorecard */}
          <QualityScorecard
            qualityScore={analyticsData.quality_score ?? 0}
            testPassRate={analyticsData.test_pass_rate ?? 0}
            defectDensity={analyticsData.defect_density_per_endpoint ?? 0}
            flakyRatio={analyticsData.flaky_ratio_percent ?? 0}
            requirementCoverage={analyticsData.requirement_coverage_percent ?? 0}
            totalRuns={analyticsData.total_runs ?? 0}
            totalTests={analyticsData.total_tests_executed ?? 0}
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
          <div className="bg-card rounded-2xl border border-border-card p-6 space-y-4 shadow-card">
            <div className="flex items-center justify-between border-b border-border-card pb-4">
              <div className="flex items-center gap-3">
                <div className="p-2 rounded-xl bg-brand/10 text-brand border border-brand/20">
                  <FileText className="w-5 h-5" />
                </div>
                <div>
                  <h3 className="text-base font-bold text-primary">Generated Executive Audit Artifacts</h3>
                  <p className="text-xs text-secondary">Cryptographically signed reports ready for export</p>
                </div>
              </div>
              <button
                onClick={() => fetchSavedReports(selectedProjectId)}
                className="p-2 text-secondary hover:text-primary hover:bg-hover rounded-xl transition-colors"
                title="Refresh audit reports"
              >
                <RefreshCw className="w-4 h-4" />
              </button>
            </div>

            {savedReports.length === 0 ? (
              <div className="text-center py-8 text-muted text-xs">
                No audit reports generated for this project yet. Click "Generate Audit Report" above to compile one.
              </div>
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full text-left text-xs">
                  <thead className="bg-field text-secondary border-b border-border-card uppercase text-[10px] font-semibold tracking-wider">
                    <tr>
                      <th className="px-5 py-3">Report Title</th>
                      <th className="px-5 py-3">Quality Score</th>
                      <th className="px-5 py-3">SHA256 Fingerprint</th>
                      <th className="px-5 py-3">Generated Date</th>
                      <th className="px-5 py-3 text-right">Actions</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-border-card text-secondary">
                    {savedReports.map((report) => (
                      <tr key={report.id} className="hover:bg-hover transition-colors">
                        <td className="px-5 py-3 font-semibold text-primary max-w-[200px] truncate">
                          {report.title}
                        </td>
                        <td className="px-5 py-3">
                          <span className="px-2.5 py-0.5 rounded-full font-bold bg-brand/10 text-brand border border-brand/20">
                            {Number(report.quality_score ?? 0).toFixed(1)} / 100
                          </span>
                        </td>
                        <td className="px-5 py-3 text-muted font-mono text-[11px] truncate max-w-[140px]" title={report.sha256_hash}>
                          {report.sha256_hash ? report.sha256_hash.substring(0, 16) + '...' : 'N/A'}
                        </td>
                        <td className="px-5 py-3 text-muted">
                          {new Date(report.created_at).toLocaleDateString()}
                        </td>
                        <td className="px-5 py-3 text-right">
                          <div className="flex items-center justify-end gap-2">
                            <a
                              href={`/api/v1/analytics/reports/${report.id}/export?format=html`}
                              target="_blank"
                              rel="noreferrer"
                              className="px-3 py-1.5 rounded-lg bg-card border border-border-field hover:bg-hover text-primary text-[11px] font-semibold transition-colors inline-flex items-center gap-1"
                            >
                              <ExternalLink className="w-3 h-3 text-brand" /> HTML
                            </a>
                            <a
                              href={`/api/v1/analytics/reports/${report.id}/export?format=pdf`}
                              target="_blank"
                              rel="noreferrer"
                              className="px-3 py-1.5 rounded-lg bg-brand/10 hover:bg-brand/20 border border-brand/30 text-brand text-[11px] font-semibold transition-colors inline-flex items-center gap-1"
                            >
                              <Download className="w-3 h-3 text-brand" /> PDF
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
        <div className="bg-card rounded-2xl p-12 text-center text-muted text-sm border border-border-card shadow-card">
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
