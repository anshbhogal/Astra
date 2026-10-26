import React from 'react';
import { Cpu, FileCode } from 'lucide-react';
import { DiscoveredEndpoint } from './types';

interface DiscoveredEndpointsTableProps {
  endpoints: DiscoveredEndpoint[];
}

const getMethodBadgeClass = (method: string) => {
  switch (method.toUpperCase()) {
    case 'GET':
      return 'bg-status-passed-bg text-status-passed border border-status-passed/30';
    case 'POST':
      return 'bg-brand/10 text-brand border border-brand/30';
    case 'PUT':
      return 'bg-status-flaky-bg text-status-flaky border border-status-flaky/30';
    case 'DELETE':
      return 'bg-status-failed-bg text-status-failed border border-status-failed/30';
    default:
      return 'bg-status-skipped-bg text-status-skipped border border-status-skipped/30';
  }
};

export const DiscoveredEndpointsTable: React.FC<DiscoveredEndpointsTableProps> = ({ endpoints }) => {
  if (endpoints.length === 0) {
    return (
      <div className="bg-card rounded-2xl p-8 text-center space-y-3 border border-border-card shadow-card">
        <Cpu className="w-10 h-10 text-muted mx-auto" />
        <h3 className="text-base font-bold text-primary">No Endpoints Discovered Yet</h3>
        <p className="text-xs text-secondary">Run analysis on this repository to extract route endpoints.</p>
      </div>
    );
  }

  return (
    <div className="bg-card rounded-2xl border border-border-card shadow-card overflow-hidden">
      <table className="w-full text-left text-xs">
        <thead className="bg-field text-secondary border-b border-border-card uppercase text-[10px] font-semibold tracking-wider">
          <tr>
            <th className="px-5 py-3">Method</th>
            <th className="px-5 py-3">Path</th>
            <th className="px-5 py-3">Handler Function</th>
            <th className="px-5 py-3">Source Location</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-border-card text-secondary">
          {endpoints.map((ep) => (
            <tr key={ep.id} className="hover:bg-hover transition-colors">
              <td className="px-5 py-3 font-mono">
                <span className={`px-2.5 py-0.5 rounded text-[11px] font-bold ${getMethodBadgeClass(ep.method)}`}>
                  {ep.method}
                </span>
              </td>
              <td className="px-5 py-3 text-primary font-mono font-semibold">{ep.path}</td>
              <td className="px-5 py-3 text-brand font-mono">{ep.function_name}()</td>
              <td className="px-5 py-3 text-muted font-mono flex items-center gap-1.5">
                <FileCode className="w-3.5 h-3.5 text-muted" />
                {ep.file_path}:{ep.line_number}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
};
