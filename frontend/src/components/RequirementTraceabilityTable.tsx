import React from 'react';
import { CheckCircle2, AlertTriangle, FileText, Target } from 'lucide-react';

interface TraceabilityItem {
  requirement_id: string;
  req_code: string;
  title: string;
  status: string;
  mapping_status: string;
  target_endpoints: string[];
  rule_tests_count: number;
  ai_tests_count: number;
  coverage_status: string;
}

interface RequirementTraceabilityTableProps {
  items: TraceabilityItem[];
  onSelectRequirement: (id: string) => void;
}

export const RequirementTraceabilityTable: React.FC<RequirementTraceabilityTableProps> = ({
  items,
  onSelectRequirement,
}) => {
  if (!items.length) {
    return (
      <div className="text-center py-12 text-slate-500 text-sm bg-slate-900/50 rounded-xl border border-slate-800">
        No requirements uploaded yet. Click "Upload Document" to parse specifications.
      </div>
    );
  }

  return (
    <div className="overflow-x-auto bg-slate-900 border border-slate-800 rounded-xl">
      <table className="w-full text-left text-xs">
        <thead className="bg-slate-950 text-slate-400 border-b border-slate-800">
          <tr>
            <th className="py-3 px-4 font-semibold">Requirement Code</th>
            <th className="py-3 px-4 font-semibold">Title</th>
            <th className="py-3 px-4 font-semibold">Mapping Status</th>
            <th className="py-3 px-4 font-semibold">Endpoints</th>
            <th className="py-3 px-4 font-semibold text-center">Rule Tests</th>
            <th className="py-3 px-4 font-semibold text-center">AI Tests</th>
            <th className="py-3 px-4 font-semibold text-center">Coverage</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-slate-800 text-slate-300">
          {items.map((item) => (
            <tr
              key={item.requirement_id}
              onClick={() => onSelectRequirement(item.requirement_id)}
              className="hover:bg-slate-800/50 cursor-pointer transition-colors"
            >
              <td className="py-3 px-4 font-mono font-medium text-indigo-400">{item.req_code}</td>
              <td className="py-3 px-4 max-w-xs truncate font-medium text-slate-200">{item.title}</td>
              <td className="py-3 px-4">
                <span
                  className={`inline-flex items-center gap-1 px-2 py-0.5 rounded text-[10px] font-semibold ${
                    item.mapping_status === 'MAPPED'
                      ? 'bg-emerald-950 text-emerald-400 border border-emerald-800'
                      : item.mapping_status === 'AMBIGUOUS'
                      ? 'bg-amber-950 text-amber-400 border border-amber-800'
                      : 'bg-slate-800 text-slate-400'
                  }`}
                >
                  {item.mapping_status === 'AMBIGUOUS' && <AlertTriangle className="w-3 h-3" />}
                  {item.mapping_status}
                </span>
              </td>
              <td className="py-3 px-4 text-slate-400 font-mono">
                {item.target_endpoints.length ? item.target_endpoints.join(', ') : 'Unmapped'}
              </td>
              <td className="py-3 px-4 text-center font-semibold text-slate-300">{item.rule_tests_count}</td>
              <td className="py-3 px-4 text-center font-semibold text-indigo-400">{item.ai_tests_count}</td>
              <td className="py-3 px-4 text-center">
                <span
                  className={`inline-flex items-center gap-1 px-2 py-0.5 rounded text-[10px] font-semibold ${
                    item.coverage_status === 'VERIFIED'
                      ? 'bg-emerald-950 text-emerald-300 border border-emerald-800'
                      : item.coverage_status === 'GENERATED'
                      ? 'bg-indigo-950 text-indigo-300 border border-indigo-800'
                      : 'bg-red-950 text-red-400 border border-red-900'
                  }`}
                >
                  {item.coverage_status === 'VERIFIED' && <CheckCircle2 className="w-3 h-3 text-emerald-400" />}
                  {item.coverage_status}
                </span>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
};
