import React, { useState } from 'react';
import { Sparkles, Code2, FileCode } from 'lucide-react';
import { Button } from '../common/Button';
import { Input } from '../common/Input';
import { DiscoveredFunction } from './types';

interface DiscoveredFunctionsTableProps {
  functions: DiscoveredFunction[];
  canRunTests: boolean;
  runningUnitTests: boolean;
  onRunUnitTests: () => void;
}

export const DiscoveredFunctionsTable: React.FC<DiscoveredFunctionsTableProps> = ({
  functions,
  canRunTests,
  runningUnitTests,
  onRunUnitTests,
}) => {
  const [search, setSearch] = useState('');

  const filtered = functions.filter(
    (fn) =>
      fn.qualified_name.toLowerCase().includes(search.toLowerCase()) ||
      fn.file_path.toLowerCase().includes(search.toLowerCase())
  );

  return (
    <div className="space-y-4">
      <div className="bg-card rounded-2xl p-5 border border-border-card shadow-card space-y-4">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
          <div>
            <h3 className="text-base font-bold text-primary flex items-center gap-2">
              <Sparkles className="w-4 h-4 text-brand" />
              Discovered Functions ({functions.length})
            </h3>
            <p className="text-xs text-secondary">
              Functions extracted via AST analysis with cyclomatic complexity, purity estimation, and side-effect detection.
            </p>
          </div>

          <div className="flex items-center gap-2">
            <Input
              placeholder="Search function or file..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              className="w-64 text-xs"
            />
            <Button
              variant="primary"
              onClick={onRunUnitTests}
              disabled={!canRunTests || runningUnitTests || functions.length === 0}
              isLoading={runningUnitTests}
              leftIcon={<Sparkles className="w-3.5 h-3.5 fill-current" />}
              title={!canRunTests ? 'Only Testers and Admins can execute unit test suites' : undefined}
            >
              Generate & Run Suite
            </Button>
          </div>
        </div>

        {functions.length === 0 ? (
          <div className="p-8 text-center space-y-3">
            <Code2 className="w-10 h-10 text-muted mx-auto" />
            <h3 className="text-base font-bold text-primary">No Functions Discovered Yet</h3>
            <p className="text-xs text-secondary">Run analysis on this repository to extract callable functions.</p>
          </div>
        ) : (
          <div className="overflow-x-auto rounded-xl border border-border-card">
            <table className="w-full text-left text-xs">
              <thead className="bg-field text-secondary border-b border-border-card uppercase text-[10px] font-semibold tracking-wider">
                <tr>
                  <th className="px-5 py-3">Function Signature</th>
                  <th className="px-5 py-3">File Location</th>
                  <th className="px-5 py-3">Complexity</th>
                  <th className="px-5 py-3">Purity</th>
                  <th className="px-5 py-3">Side Effects</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-border-card text-secondary">
                {filtered.map((fn) => {
                  const isHighComp = fn.cyclomatic_complexity > 5;
                  const isPure = fn.purity_estimate >= 0.9;
                  return (
                    <tr key={fn.function_id} className="hover:bg-hover transition-colors">
                      <td className="px-5 py-3 font-mono">
                        <span className="text-primary font-bold">{fn.qualified_name}</span>
                        <span className="text-muted text-[11px]">
                          ({fn.parameters.map((p) => `${p.name}${p.type_annotation ? ': ' + p.type_annotation : ''}`).join(', ')})
                        </span>
                        {fn.return_schema && fn.return_schema !== 'Any' && (
                          <span className="text-brand text-[11px]"> → {fn.return_schema}</span>
                        )}
                      </td>
                      <td className="px-5 py-3 text-muted font-mono flex items-center gap-1.5">
                        <FileCode className="w-3.5 h-3.5 text-muted" />
                        {fn.file_path}:{fn.line_number}
                      </td>
                      <td className="px-5 py-3">
                        <span
                          className={`px-2 py-0.5 rounded text-[10px] font-bold font-mono ${
                            fn.cyclomatic_complexity <= 3
                              ? 'bg-status-passed-bg text-status-passed'
                              : isHighComp
                              ? 'bg-status-failed-bg text-status-failed'
                              : 'bg-amber-500/10 text-amber-500'
                          }`}
                        >
                          CC: {fn.cyclomatic_complexity}
                        </span>
                      </td>
                      <td className="px-5 py-3">
                        <span
                          className={`px-2 py-0.5 rounded text-[10px] font-bold ${
                            isPure
                              ? 'bg-status-passed-bg text-status-passed'
                              : 'bg-field text-secondary border border-border-card'
                          }`}
                        >
                          {isPure ? 'Pure Function' : `${Math.round(fn.purity_estimate * 100)}% Pure`}
                        </span>
                      </td>
                      <td className="px-5 py-3">
                        <div className="flex flex-wrap gap-1">
                          {fn.side_effects && fn.side_effects.length > 0 ? (
                            fn.side_effects.map((se) => (
                              <span
                                key={se}
                                className="px-1.5 py-0.5 rounded text-[9px] font-mono bg-field border border-border-card text-muted"
                              >
                                {se}
                              </span>
                            ))
                          ) : (
                            <span className="text-muted text-[11px]">None (Deterministic)</span>
                          )}
                        </div>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
};
