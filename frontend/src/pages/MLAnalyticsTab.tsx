import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { Cpu, Zap, ShieldAlert, GitPullRequest, Play, RefreshCw, AlertTriangle } from 'lucide-react';
import { PriorityHeatmapCard } from '../components/PriorityHeatmapCard';
import { FlakyTestsDrawer } from '../components/FlakyTestsDrawer';
import { HealingInspectorModal } from '../components/HealingInspectorModal';
import { Button } from '../components/common/Button';

interface MLAnalyticsTabProps {
  projectId: string;
}

export const MLAnalyticsTab: React.FC<MLAnalyticsTabProps> = ({ projectId }) => {
  const [strategy, setStrategy] = useState('BALANCED');
  const [prioritizedSuite, setPrioritizedSuite] = useState<any[]>([]);
  const [flakyTests, setFlakyTests] = useState<any[]>([]);
  const [healingCandidates, setHealingCandidates] = useState<any[]>([]);
  const [selectedCandidate, setSelectedCandidate] = useState<any | null>(null);

  const [isDrawerOpen, setIsDrawerOpen] = useState(false);
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [loading, setLoading] = useState(false);
  const [training, setTraining] = useState(false);

  const token = localStorage.getItem('token');
  const authHeaders = { Authorization: `Bearer ${token}` };

  const fetchData = async () => {
    setLoading(true);
    try {
      // 1. Fetch prioritization
      const resP = await axios.get(`/api/v1/projects/${projectId}/ml/prioritize?strategy=${strategy}`, { headers: authHeaders });
      setPrioritizedSuite(resP.data.prioritized_suite || []);

      // 2. Fetch flaky tests
      const resF = await axios.get(`/api/v1/projects/${projectId}/ml/flaky-tests`, { headers: authHeaders });
      setFlakyTests(resF.data.flaky_tests || []);

      // 3. Fetch healing candidates
      const resH = await axios.get(`/api/v1/projects/${projectId}/ml/healing-candidates`, { headers: authHeaders });
      setHealingCandidates(resH.data || []);
    } catch (err) {
      console.error('Failed to fetch ML analytics data', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
  }, [projectId, strategy]);

  const handleTrainModel = async () => {
    setTraining(true);
    try {
      await axios.post(`/api/v1/projects/${projectId}/ml/train?async_mode=false`, {}, { headers: authHeaders });
      await fetchData();
    } catch (err) {
      console.error('Failed to train ML model', err);
    } finally {
      setTraining(false);
    }
  };

  const handleToggleQuarantine = async (testCaseId: string, quarantine: boolean) => {
    try {
      await axios.post(
        `/api/v1/projects/${projectId}/ml/flaky-tests/${testCaseId}/quarantine`,
        { quarantine },
        { headers: authHeaders }
      );
      await fetchData();
    } catch (err) {
      console.error('Failed to toggle quarantine', err);
    }
  };

  const handleApproveHealing = async (candidateId: string) => {
    try {
      await axios.post(`/api/v1/projects/${projectId}/ml/healing-candidates/${candidateId}/apply`, {}, { headers: authHeaders });
      await fetchData();
    } catch (err) {
      console.error('Failed to approve healing candidate', err);
    }
  };

  const handleRollbackHealing = async (candidateId: string) => {
    try {
      await axios.post(`/api/v1/projects/${projectId}/ml/healing-candidates/${candidateId}/rollback`, {}, { headers: authHeaders });
      await fetchData();
    } catch (err) {
      console.error('Failed to rollback healing candidate', err);
    }
  };

  return (
    <div className="space-y-6">
      {/* Top Banner */}
      <div className="bg-card border border-border-card rounded-2xl p-6 shadow-card flex flex-col md:flex-row items-start md:items-center justify-between gap-4">
        <div className="flex items-center space-x-4">
          <div className="w-12 h-12 rounded-2xl bg-brand/10 border border-brand/20 flex items-center justify-center text-brand">
            <Cpu className="w-6 h-6" />
          </div>
          <div>
            <h2 className="text-xl font-bold text-primary">ML Intelligence & Agentic Healing Pipeline</h2>
            <p className="text-xs text-secondary mt-0.5">
              XGBoost Test Prioritization • State-Machine Flakiness Quarantine • Spec Healing Gate
            </p>
          </div>
        </div>

        <div className="flex items-center space-x-3 flex-wrap">
          <Button
            variant="secondary"
            onClick={() => setIsDrawerOpen(true)}
            leftIcon={<ShieldAlert className="w-4 h-4 text-status-flaky" />}
          >
            Quarantine Inspector ({flakyTests.length})
          </Button>

          <Button
            variant="primary"
            onClick={handleTrainModel}
            disabled={training}
            isLoading={training}
            leftIcon={<Play className="w-4 h-4 fill-current" />}
          >
            {training ? 'Training Model...' : 'Train XGBoost Model'}
          </Button>
        </div>
      </div>

      {/* Main Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="lg:col-span-2">
          <PriorityHeatmapCard
            items={prioritizedSuite}
            strategy={strategy}
            onStrategyChange={setStrategy}
          />
        </div>

        {/* Healing Candidates List */}
        <div className="bg-card border border-border-card rounded-2xl p-6 shadow-card space-y-4">
          <div className="flex items-center justify-between border-b border-border-card pb-4">
            <div className="flex items-center space-x-2.5">
              <GitPullRequest className="w-5 h-5 text-brand" />
              <h3 className="text-base font-bold text-primary">Spec Repair Candidates</h3>
            </div>
            <span className="px-2.5 py-0.5 rounded-full text-xs font-bold bg-brand/10 text-brand border border-brand/20">
              {healingCandidates.length}
            </span>
          </div>

          <div className="space-y-3 max-h-[380px] overflow-y-auto pr-1">
            {healingCandidates.length === 0 ? (
              <div className="text-center py-10 text-muted text-xs">
                No specification patch candidates pending review.
              </div>
            ) : (
              healingCandidates.map((cand) => (
                <div
                  key={cand.id}
                  onClick={() => {
                    setSelectedCandidate(cand);
                    setIsModalOpen(true);
                  }}
                  className="bg-field border border-border-card rounded-xl p-3.5 hover:border-brand cursor-pointer transition-all space-y-2 group"
                >
                  <div className="flex items-center justify-between">
                    <span className="font-mono text-xs text-primary font-semibold truncate max-w-[200px]">
                      Case: {cand.test_case_id}
                    </span>
                    <span className={`px-2 py-0.5 rounded-full text-[10px] font-bold ${
                      cand.status === 'APPROVED' ? 'bg-status-passed-bg text-status-passed border border-status-passed/30' : 'bg-brand/10 text-brand border border-brand/20'
                    }`}>
                      {cand.status}
                    </span>
                  </div>

                  <p className="text-xs text-secondary line-clamp-1">
                    Patch ops: {cand.patch_operations.map((o: any) => o.op_type).join(', ')}
                  </p>
                </div>
              ))
            )}
          </div>
        </div>
      </div>

      {/* Drawers & Modals */}
      <FlakyTestsDrawer
        isOpen={isDrawerOpen}
        onClose={() => setIsDrawerOpen(false)}
        flakyTests={flakyTests}
        onToggleQuarantine={handleToggleQuarantine}
      />

      <HealingInspectorModal
        candidate={selectedCandidate}
        isOpen={isModalOpen}
        onClose={() => setIsModalOpen(false)}
        onApprove={handleApproveHealing}
        onRollback={handleRollbackHealing}
      />
    </div>
  );
};
