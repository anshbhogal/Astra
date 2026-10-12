import React, { useState, useEffect } from 'react';
import {
  Server,
  Power,
  RotateCw,
  CheckCircle2,
  AlertTriangle,
  Layers,
  Terminal,
  ExternalLink,
  Copy,
  Check,
  Cpu,
  Activity,
} from 'lucide-react';
import { api } from '../services/api';
import { Button } from './common/Button';
import { Modal } from './common/Modal';
import { Input } from './common/Input';

interface SandboxServerControlProps {
  projectId: string;
  projectName: string;
  onServerStateChange?: (isRunning: boolean, port: number | null) => void;
}

export interface ServerStatusData {
  project_id: string;
  status: 'RUNNING' | 'STOPPED';
  port: number | null;
  base_url: string | null;
  mode: string | null;
  custom_command?: string | null;
  started_at?: string | null;
  uptime_seconds: number;
}

export const SandboxServerControl: React.FC<SandboxServerControlProps> = ({
  projectId,
  projectName,
  onServerStateChange,
}) => {
  const [serverStatus, setServerStatus] = useState<ServerStatusData>({
    project_id: projectId,
    status: 'STOPPED',
    port: null,
    base_url: null,
    mode: null,
    uptime_seconds: 0,
  });
  const [loading, setLoading] = useState(true);
  const [actionLoading, setActionLoading] = useState(false);
  const [isModalOpen, setIsModalOpen] = useState(false);

  // Form states in Start Server Modal
  const [allocatedPort, setAllocatedPort] = useState<number>(5000);
  const [scanningPort, setScanningPort] = useState(false);
  const [selectedMode, setSelectedMode] = useState<'HYBRID' | 'ENDPOINT_SANDBOX' | 'NATIVE_COMMAND'>('HYBRID');
  const [customCommand, setCustomCommand] = useState('python app.py');
  const [copied, setCopied] = useState(false);

  useEffect(() => {
    fetchStatus();
  }, [projectId]);

  useEffect(() => {
    let timer: ReturnType<typeof setInterval> | null = null;
    if (serverStatus.status === 'RUNNING') {
      timer = setInterval(() => {
        fetchStatus(false);
      }, 3000);
    }
    return () => {
      if (timer) clearInterval(timer);
    };
  }, [serverStatus.status, projectId]);

  const fetchStatus = async (showLoading = true) => {
    if (showLoading) setLoading(true);
    try {
      const res = await api.get(`/projects/${projectId}/sandbox/status`);
      setServerStatus(res.data);
      if (onServerStateChange) {
        onServerStateChange(res.data.status === 'RUNNING', res.data.port);
      }
    } catch (err) {
      setServerStatus({
        project_id: projectId,
        status: 'STOPPED',
        port: null,
        base_url: null,
        mode: null,
        uptime_seconds: 0,
      });
    } finally {
      if (showLoading) setLoading(false);
    }
  };

  const handleOpenStartModal = async () => {
    setIsModalOpen(true);
    await fetchAvailablePort();
  };

  const fetchAvailablePort = async () => {
    setScanningPort(true);
    try {
      const res = await api.get(`/projects/${projectId}/sandbox/available-port`);
      if (res.data.suggested_port) {
        setAllocatedPort(res.data.suggested_port);
      }
    } catch (err) {
      setAllocatedPort(5000);
    } finally {
      setScanningPort(false);
    }
  };

  const handleStartServer = async () => {
    setActionLoading(true);
    try {
      const res = await api.post(`/projects/${projectId}/sandbox/start`, {
        port: allocatedPort,
        mode: selectedMode,
        custom_command: selectedMode === 'NATIVE_COMMAND' ? customCommand : undefined,
      });
      setServerStatus(res.data);
      setIsModalOpen(false);
      if (onServerStateChange) {
        onServerStateChange(res.data.status === 'RUNNING', res.data.port);
      }
    } catch (err: any) {
      alert(err.response?.data?.detail || 'Failed to start sandbox server.');
    } finally {
      setActionLoading(false);
    }
  };

  const handleStopServer = async () => {
    if (!confirm('Are you sure you want to stop the active target sandbox server?')) return;
    setActionLoading(true);
    try {
      await api.post(`/projects/${projectId}/sandbox/stop`);
      await fetchStatus();
    } catch (err: any) {
      alert(err.response?.data?.detail || 'Failed to stop sandbox server.');
    } finally {
      setActionLoading(false);
    }
  };

  const handleCopyUrl = () => {
    if (serverStatus.base_url) {
      navigator.clipboard.writeText(serverStatus.base_url);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    }
  };

  const isRunning = serverStatus.status === 'RUNNING';

  return (
    <>
      <div className="bg-card rounded-2xl p-5 border border-border-card shadow-card space-y-4">
        {/* Header & Status Indicator */}
        <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3">
          <div className="flex items-center gap-3">
            <div
              className={`w-10 h-10 rounded-xl flex items-center justify-center shrink-0 border ${
                isRunning
                  ? 'bg-status-passed-bg border-status-passed/30 text-status-passed'
                  : 'bg-field border-border-card text-muted'
              }`}
            >
              <Server className="w-5 h-5" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h3 className="text-sm font-bold text-primary">Target Sandbox Server</h3>
                <span
                  className={`inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-[10px] font-bold border ${
                    isRunning
                      ? 'bg-status-passed-bg text-status-passed border-status-passed/30'
                      : 'bg-field text-muted border-border-card'
                  }`}
                >
                  <span
                    className={`w-1.5 h-1.5 rounded-full ${
                      isRunning ? 'bg-status-passed animate-ping' : 'bg-muted'
                    }`}
                  />
                  {isRunning ? 'SERVER RUNNING' : 'SERVER NOT RUNNING'}
                </span>
              </div>
              <p className="text-xs text-secondary mt-0.5">
                {isRunning
                  ? `Active on port ${serverStatus.port} • Ready for live HTTP test executions`
                  : 'Start a target server on an auto-allocated free port before launching test runs.'}
              </p>
            </div>
          </div>

          {/* Action Buttons */}
          <div className="flex items-center gap-2 w-full sm:w-auto">
            {isRunning ? (
              <Button
                variant="danger"
                size="sm"
                onClick={handleStopServer}
                disabled={actionLoading}
                isLoading={actionLoading}
                leftIcon={<Power className="w-3.5 h-3.5" />}
              >
                Turn Off Server
              </Button>
            ) : (
              <Button
                variant="primary"
                size="sm"
                onClick={handleOpenStartModal}
                disabled={loading || actionLoading}
                leftIcon={<Power className="w-3.5 h-3.5" />}
              >
                Start Target Server
              </Button>
            )}
          </div>
        </div>

        {/* Running Server Details Panel */}
        {isRunning && (
          <div className="p-3.5 rounded-xl bg-field border border-border-card grid grid-cols-1 sm:grid-cols-3 gap-3 text-xs">
            <div>
              <span className="text-[10px] uppercase font-semibold text-muted block">Listening Address</span>
              <div className="flex items-center gap-2 mt-0.5">
                <span className="font-mono font-bold text-brand">{serverStatus.base_url}</span>
                <button
                  type="button"
                  onClick={handleCopyUrl}
                  className="p-1 rounded text-muted hover:text-primary transition-colors"
                  title="Copy Base URL"
                >
                  {copied ? <Check className="w-3.5 h-3.5 text-status-passed" /> : <Copy className="w-3.5 h-3.5" />}
                </button>
              </div>
            </div>

            <div>
              <span className="text-[10px] uppercase font-semibold text-muted block">Execution Mode</span>
              <span className="font-semibold text-primary block mt-0.5">
                {serverStatus.mode === 'ENDPOINT_SANDBOX' && 'Auto Endpoint Sandbox'}
                {serverStatus.mode === 'NATIVE_COMMAND' && 'Native Process Runner'}
                {serverStatus.mode === 'HYBRID' && 'Adaptive Hybrid Sandbox'}
              </span>
            </div>

            <div>
              <span className="text-[10px] uppercase font-semibold text-muted block">Liveness Health</span>
              <div className="flex items-center gap-1.5 text-status-passed font-semibold mt-0.5">
                <CheckCircle2 className="w-3.5 h-3.5" />
                <span>Healthy (HTTP 200)</span>
              </div>
            </div>
          </div>
        )}
      </div>

      {/* Start Server Modal */}
      {isModalOpen && (
        <Modal
          isOpen={isModalOpen}
          onClose={() => setIsModalOpen(false)}
          title={`Start Sandbox Server: ${projectName}`}
        >
          <div className="space-y-4 text-xs">
            {/* Auto-allocated Port Section */}
            <div className="space-y-1.5">
              <div className="flex items-center justify-between">
                <label className="font-semibold text-primary">Target Port (Auto-Allocated)</label>
                <button
                  type="button"
                  onClick={fetchAvailablePort}
                  disabled={scanningPort}
                  className="inline-flex items-center gap-1 text-[11px] text-brand hover:underline"
                >
                  <RotateCw className={`w-3 h-3 ${scanningPort ? 'animate-spin' : ''}`} />
                  Re-scan free port
                </button>
              </div>
              <div className="flex items-center gap-2">
                <Input
                  type="number"
                  value={allocatedPort}
                  onChange={(e) => setAllocatedPort(Number(e.target.value))}
                  placeholder="5000"
                  className="font-mono"
                />
                <span className="text-muted font-mono whitespace-nowrap">
                  &rarr; http://localhost:{allocatedPort}
                </span>
              </div>
              <p className="text-[11px] text-muted">
                System scanned active socket bindings and automatically picked free port{' '}
                <strong className="text-primary font-mono">{allocatedPort}</strong>.
              </p>
            </div>

            {/* Launch Mode Selection (All 3 Options Provided) */}
            <div className="space-y-2">
              <label className="font-semibold text-primary block">Select Server Startup Mode</label>
              <div className="grid grid-cols-1 gap-2.5">
                {/* 1. Hybrid (Recommended) */}
                <label
                  onClick={() => setSelectedMode('HYBRID')}
                  className={`p-3 rounded-xl border cursor-pointer transition-all flex items-start gap-3 ${
                    selectedMode === 'HYBRID'
                      ? 'bg-brand/5 border-brand ring-1 ring-brand'
                      : 'bg-field border-border-card hover:bg-hover'
                  }`}
                >
                  <input
                    type="radio"
                    name="server_mode"
                    checked={selectedMode === 'HYBRID'}
                    onChange={() => setSelectedMode('HYBRID')}
                    className="mt-0.5 text-brand"
                  />
                  <div>
                    <div className="flex items-center gap-2">
                      <span className="font-bold text-primary">Hybrid Adaptive (Recommended)</span>
                      <span className="px-1.5 py-0.2 rounded text-[9px] font-bold bg-brand text-on-brand">
                        DEFAULT
                      </span>
                    </div>
                    <p className="text-secondary text-[11px] mt-0.5">
                      Attempts to run the native codebase; if no entrypoint is found, automatically serves the project's
                      discovered API endpoints in an emulated live sandbox.
                    </p>
                  </div>
                </label>

                {/* 2. Endpoint Sandbox */}
                <label
                  onClick={() => setSelectedMode('ENDPOINT_SANDBOX')}
                  className={`p-3 rounded-xl border cursor-pointer transition-all flex items-start gap-3 ${
                    selectedMode === 'ENDPOINT_SANDBOX'
                      ? 'bg-brand/5 border-brand ring-1 ring-brand'
                      : 'bg-field border-border-card hover:bg-hover'
                  }`}
                >
                  <input
                    type="radio"
                    name="server_mode"
                    checked={selectedMode === 'ENDPOINT_SANDBOX'}
                    onChange={() => setSelectedMode('ENDPOINT_SANDBOX')}
                    className="mt-0.5 text-brand"
                  />
                  <div>
                    <span className="font-bold text-primary">Automated Endpoint Emulation</span>
                    <p className="text-secondary text-[11px] mt-0.5">
                      Dynamically spins up an isolated ASGI service serving all AST-scanned routes (e.g. /signup,
                      /login) with simulated responses and health probe.
                    </p>
                  </div>
                </label>

                {/* 3. Native Command */}
                <label
                  onClick={() => setSelectedMode('NATIVE_COMMAND')}
                  className={`p-3 rounded-xl border cursor-pointer transition-all flex items-start gap-3 ${
                    selectedMode === 'NATIVE_COMMAND'
                      ? 'bg-brand/5 border-brand ring-1 ring-brand'
                      : 'bg-field border-border-card hover:bg-hover'
                  }`}
                >
                  <input
                    type="radio"
                    name="server_mode"
                    checked={selectedMode === 'NATIVE_COMMAND'}
                    onChange={() => setSelectedMode('NATIVE_COMMAND')}
                    className="mt-0.5 text-brand"
                  />
                  <div>
                    <span className="font-bold text-primary">Native Process Command</span>
                    <p className="text-secondary text-[11px] mt-0.5">
                      Launches the project's real entrypoint command in a background process using the allocated port.
                    </p>
                  </div>
                </label>
              </div>
            </div>

            {/* Custom Command Input (if NATIVE_COMMAND is active) */}
            {selectedMode === 'NATIVE_COMMAND' && (
              <div className="space-y-1.5 p-3 rounded-xl bg-field border border-border-card">
                <label className="font-semibold text-primary block flex items-center gap-1.5">
                  <Terminal className="w-3.5 h-3.5 text-brand" /> Custom Launch Command
                </label>
                <Input
                  value={customCommand}
                  onChange={(e) => setCustomCommand(e.target.value)}
                  placeholder="python app.py or npm start"
                  className="font-mono text-xs"
                />
                <p className="text-[10px] text-muted">
                  PORT={allocatedPort} will be injected into the process environment.
                </p>
              </div>
            )}

            {/* Footer Buttons */}
            <div className="flex items-center justify-end gap-3 pt-3 border-t border-border-card">
              <Button
                variant="ghost"
                size="sm"
                onClick={() => setIsModalOpen(false)}
                disabled={actionLoading}
              >
                Cancel
              </Button>
              <Button
                variant="primary"
                size="sm"
                onClick={handleStartServer}
                disabled={actionLoading || !allocatedPort}
                isLoading={actionLoading}
                leftIcon={<Power className="w-3.5 h-3.5" />}
              >
                Start Server on Port {allocatedPort}
              </Button>
            </div>
          </div>
        </Modal>
      )}
    </>
  );
};
