import React, { useState, useEffect } from 'react';
import { X, Sliders, Shield, Zap, Sparkles, Check, Info, Hash } from 'lucide-react';
import { api } from '../services/api';

interface TestGenerationDrawerProps {
  isOpen: boolean;
  onClose: () => void;
  projectId: string;
  endpointCount: number;
  onSuiteGenerated: () => void;
}

export const TestGenerationDrawer: React.FC<TestGenerationDrawerProps> = ({
  isOpen,
  onClose,
  projectId,
  endpointCount,
  onSuiteGenerated,
}) => {
  const [preset, setPreset] = useState<'MINIMAL' | 'STANDARD' | 'THOROUGH' | 'SECURITY' | 'MAXIMUM'>('STANDARD');
  const [includeHappyPath, setIncludeHappyPath] = useState(true);
  const [includeBoundaryTests, setIncludeBoundaryTests] = useState(true);
  const [includeMissingRequired, setIncludeMissingRequired] = useState(true);
  const [includeInvalidTypes, setIncludeInvalidTypes] = useState(true);
  const [includeFormatViolations, setIncludeFormatViolations] = useState(true);
  const [includeSecurityProbes, setIncludeSecurityProbes] = useState(false); // Default OFF
  const [securityConfirmed, setSecurityConfirmed] = useState(false);
  const [pairwiseStrength, setPairwiseStrength] = useState<number>(2);
  const [maxCasesPerEndpoint, setMaxCasesPerEndpoint] = useState<number>(20);
  const [seed, setSeed] = useState<number>(42);
  const [isGenerating, setIsGenerating] = useState(false);
  const [jobId, setJobId] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  // Apply preset choices
  const handlePresetChange = (selected: 'MINIMAL' | 'STANDARD' | 'THOROUGH' | 'SECURITY' | 'MAXIMUM') => {
    setPreset(selected);
    if (selected === 'MINIMAL') {
      setIncludeHappyPath(true);
      setIncludeBoundaryTests(false);
      setIncludeMissingRequired(true);
      setIncludeInvalidTypes(false);
      setIncludeFormatViolations(false);
      setIncludeSecurityProbes(false);
      setPairwiseStrength(1);
      setMaxCasesPerEndpoint(10);
    } else if (selected === 'THOROUGH') {
      setIncludeHappyPath(true);
      setIncludeBoundaryTests(true);
      setIncludeMissingRequired(true);
      setIncludeInvalidTypes(true);
      setIncludeFormatViolations(true);
      setIncludeSecurityProbes(false);
      setPairwiseStrength(2);
      setMaxCasesPerEndpoint(35);
    } else if (selected === 'SECURITY') {
      setIncludeHappyPath(true);
      setIncludeBoundaryTests(true);
      setIncludeMissingRequired(true);
      setIncludeInvalidTypes(true);
      setIncludeFormatViolations(true);
      setIncludeSecurityProbes(true);
      setSecurityConfirmed(true);
      setPairwiseStrength(2);
      setMaxCasesPerEndpoint(40);
    } else if (selected === 'MAXIMUM') {
      setIncludeHappyPath(true);
      setIncludeBoundaryTests(true);
      setIncludeMissingRequired(true);
      setIncludeInvalidTypes(true);
      setIncludeFormatViolations(true);
      setIncludeSecurityProbes(true);
      setSecurityConfirmed(true);
      setPairwiseStrength(3);
      setMaxCasesPerEndpoint(100);
    } else {
      setIncludeHappyPath(true);
      setIncludeBoundaryTests(true);
      setIncludeMissingRequired(true);
      setIncludeInvalidTypes(true);
      setIncludeFormatViolations(true);
      setIncludeSecurityProbes(false);
      setPairwiseStrength(2);
      setMaxCasesPerEndpoint(20);
    }
  };

  // Live estimated test count preview calculation
  const calculateEstimatedTests = () => {
    let perEp = 0;
    if (includeHappyPath) perEp += 1;
    if (includeBoundaryTests) perEp += 4;
    if (includeMissingRequired) perEp += 2;
    if (includeInvalidTypes) perEp += 2;
    if (includeFormatViolations) perEp += 2;
    if (includeSecurityProbes) perEp += 4;
    if (pairwiseStrength >= 2) perEp += 6;

    return endpointCount * Math.min(perEp, maxCasesPerEndpoint);
  };

  const handleGenerate = async () => {
    if (includeSecurityProbes && !securityConfirmed) {
      setError('You must confirm security testing authorization to enable security probes.');
      return;
    }

    setIsGenerating(true);
    setError(null);

    try {
      const payload = {
        name: `Advanced Suite (${preset})`,
        preset,
        include_happy_path: includeHappyPath,
        include_boundary_tests: includeBoundaryTests,
        include_missing_required: includeMissingRequired,
        include_invalid_types: includeInvalidTypes,
        include_format_violations: includeFormatViolations,
        include_security_probes: includeSecurityProbes,
        pairwise_strength: pairwiseStrength,
        max_cases_per_endpoint: maxCasesPerEndpoint,
        max_total_cases: 500,
        seed,
      };

      const res = await api.post(`/projects/${projectId}/test-suites/generate-advanced`, payload);
      setJobId(res.data.id);
      
      // Wait slightly then finish
      setTimeout(() => {
        setIsGenerating(false);
        onSuiteGenerated();
        onClose();
      }, 1500);
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to dispatch advanced test suite generation.');
      setIsGenerating(false);
    }
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 overflow-hidden bg-black/60 backdrop-blur-sm transition-opacity">
      <div className="fixed inset-y-0 right-0 flex max-w-full pl-10">
        <div className="w-screen max-w-md bg-gray-900 border-l border-gray-800 text-gray-100 shadow-2xl flex flex-col">
          {/* Header */}
          <div className="p-6 border-b border-gray-800 flex items-center justify-between bg-gray-900/50">
            <div className="flex items-center gap-3">
              <div className="p-2 bg-indigo-500/10 rounded-lg text-indigo-400">
                <Sliders className="w-5 h-5" />
              </div>
              <div>
                <h2 className="text-lg font-semibold text-white">Advanced Suite Generator</h2>
                <p className="text-xs text-gray-400">Phase 4 Rule-Based Payload Engine</p>
              </div>
            </div>
            <button
              onClick={onClose}
              className="p-1 text-gray-400 hover:text-white rounded-lg hover:bg-gray-800 transition"
            >
              <X className="w-5 h-5" />
            </button>
          </div>

          {/* Body */}
          <div className="flex-1 overflow-y-auto p-6 space-y-6">
            {error && (
              <div className="p-4 bg-red-500/10 border border-red-500/20 rounded-xl text-red-400 text-sm">
                {error}
              </div>
            )}

            {/* Presets */}
            <div>
              <label className="block text-xs font-semibold uppercase tracking-wider text-gray-400 mb-3">
                Strategy Preset
              </label>
              <div className="grid grid-cols-3 gap-2">
                {(['MINIMAL', 'STANDARD', 'THOROUGH', 'SECURITY', 'MAXIMUM'] as const).map((p) => (
                  <button
                    key={p}
                    onClick={() => handlePresetChange(p)}
                    className={`py-2 px-3 text-xs font-medium rounded-lg border transition ${
                      preset === p
                        ? 'bg-indigo-600/20 border-indigo-500 text-indigo-300'
                        : 'bg-gray-800/50 border-gray-700/50 text-gray-400 hover:bg-gray-800'
                    }`}
                  >
                    {p}
                  </button>
                ))}
              </div>
            </div>

            {/* Strategy Toggles */}
            <div className="space-y-3">
              <label className="block text-xs font-semibold uppercase tracking-wider text-gray-400 mb-2">
                Test Case Generators
              </label>

              <label className="flex items-center justify-between p-3 bg-gray-800/40 rounded-xl border border-gray-700/40 cursor-pointer">
                <span className="text-sm font-medium text-gray-200">Happy Path Tests</span>
                <input
                  type="checkbox"
                  checked={includeHappyPath}
                  onChange={(e) => setIncludeHappyPath(e.target.checked)}
                  className="w-4 h-4 rounded text-indigo-600 bg-gray-900 border-gray-700 focus:ring-indigo-500"
                />
              </label>

              <label className="flex items-center justify-between p-3 bg-gray-800/40 rounded-xl border border-gray-700/40 cursor-pointer">
                <span className="text-sm font-medium text-gray-200">Boundary Value Analysis (EP+BVA)</span>
                <input
                  type="checkbox"
                  checked={includeBoundaryTests}
                  onChange={(e) => setIncludeBoundaryTests(e.target.checked)}
                  className="w-4 h-4 rounded text-indigo-600 bg-gray-900 border-gray-700 focus:ring-indigo-500"
                />
              </label>

              <label className="flex items-center justify-between p-3 bg-gray-800/40 rounded-xl border border-gray-700/40 cursor-pointer">
                <span className="text-sm font-medium text-gray-200">Missing Required Parameters</span>
                <input
                  type="checkbox"
                  checked={includeMissingRequired}
                  onChange={(e) => setIncludeMissingRequired(e.target.checked)}
                  className="w-4 h-4 rounded text-indigo-600 bg-gray-900 border-gray-700 focus:ring-indigo-500"
                />
              </label>

              <label className="flex items-center justify-between p-3 bg-gray-800/40 rounded-xl border border-gray-700/40 cursor-pointer">
                <span className="text-sm font-medium text-gray-200">Type Mutations & Coercion</span>
                <input
                  type="checkbox"
                  checked={includeInvalidTypes}
                  onChange={(e) => setIncludeInvalidTypes(e.target.checked)}
                  className="w-4 h-4 rounded text-indigo-600 bg-gray-900 border-gray-700 focus:ring-indigo-500"
                />
              </label>

              <label className="flex items-center justify-between p-3 bg-gray-800/40 rounded-xl border border-gray-700/40 cursor-pointer">
                <span className="text-sm font-medium text-gray-200">Format Violations (UUID, Email, Date)</span>
                <input
                  type="checkbox"
                  checked={includeFormatViolations}
                  onChange={(e) => setIncludeFormatViolations(e.target.checked)}
                  className="w-4 h-4 rounded text-indigo-600 bg-gray-900 border-gray-700 focus:ring-indigo-500"
                />
              </label>

              {/* Opt-In Security Probes */}
              <div className="p-3 bg-amber-500/5 rounded-xl border border-amber-500/20 space-y-2">
                <label className="flex items-center justify-between cursor-pointer">
                  <div className="flex items-center gap-2">
                    <Shield className="w-4 h-4 text-amber-400" />
                    <span className="text-sm font-medium text-amber-200">Opt-In Passive Security Probes</span>
                  </div>
                  <input
                    type="checkbox"
                    checked={includeSecurityProbes}
                    onChange={(e) => setIncludeSecurityProbes(e.target.checked)}
                    className="w-4 h-4 rounded text-amber-600 bg-gray-900 border-amber-700 focus:ring-amber-500"
                  />
                </label>
                {includeSecurityProbes && (
                  <label className="flex items-center gap-2 text-xs text-amber-300/80 cursor-pointer pt-1">
                    <input
                      type="checkbox"
                      checked={securityConfirmed}
                      onChange={(e) => setSecurityConfirmed(e.target.checked)}
                      className="w-3.5 h-3.5 rounded text-amber-600"
                    />
                    I confirm authorization to run non-destructive security probes.
                  </label>
                )}
              </div>
            </div>

            {/* Combinatorial Strength & Seed */}
            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="block text-xs font-semibold uppercase tracking-wider text-gray-400 mb-2">
                  Combinatorial Strength
                </label>
                <select
                  value={pairwiseStrength}
                  onChange={(e) => setPairwiseStrength(Number(e.target.value))}
                  className="w-full bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-xs text-gray-200 focus:ring-indigo-500"
                >
                  <option value={1}>1-Wise (Parameter Coverage)</option>
                  <option value={2}>2-Wise (Pairwise IPOG)</option>
                  <option value={3}>3-Wise (Triple Combination)</option>
                </select>
              </div>

              <div>
                <label className="block text-xs font-semibold uppercase tracking-wider text-gray-400 mb-2">
                  Deterministic Seed
                </label>
                <input
                  type="number"
                  value={seed}
                  onChange={(e) => setSeed(Number(e.target.value))}
                  className="w-full bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-xs text-gray-200 focus:ring-indigo-500"
                />
              </div>
            </div>

            {/* Live Estimate Preview Badge */}
            <div className="p-4 bg-indigo-500/10 border border-indigo-500/20 rounded-xl flex items-center justify-between">
              <div>
                <span className="text-xs font-medium text-indigo-400 uppercase tracking-wider">Estimated Suite Size</span>
                <p className="text-xl font-bold text-white">~{calculateEstimatedTests()} Test Cases</p>
              </div>
              <Sparkles className="w-6 h-6 text-indigo-400" />
            </div>
          </div>

          {/* Footer */}
          <div className="p-6 border-t border-gray-800 bg-gray-900/80 flex items-center justify-between">
            <button
              onClick={onClose}
              className="px-4 py-2 text-sm text-gray-400 hover:text-white transition"
            >
              Cancel
            </button>
            <button
              onClick={handleGenerate}
              disabled={isGenerating}
              className="px-5 py-2.5 bg-indigo-600 hover:bg-indigo-500 text-white rounded-xl font-medium text-sm transition flex items-center gap-2 shadow-lg shadow-indigo-600/25 disabled:opacity-50"
            >
              {isGenerating ? (
                <>
                  <div className="w-4 h-4 border-2 border-white/20 border-t-white rounded-full animate-spin" />
                  Generating Suite...
                </>
              ) : (
                <>
                  <Zap className="w-4 h-4" />
                  Generate Advanced Suite
                </>
              )}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};
