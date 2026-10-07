import React from 'react';
import { X, HelpCircle, FileCode, CheckCircle2, Shield, Info } from 'lucide-react';

interface TestProvenanceModalProps {
  isOpen: boolean;
  onClose: () => void;
  testCaseName: string;
  testType: string;
  metadata: any;
}

export const TestProvenanceModal: React.FC<TestProvenanceModalProps> = ({
  isOpen,
  onClose,
  testCaseName,
  testType,
  metadata,
}) => {
  if (!isOpen) return null;

  const mutations = metadata?.mutations || [];

  return (
    <div className="fixed inset-0 z-50 overflow-y-auto bg-black/70 backdrop-blur-sm flex items-center justify-center p-4">
      <div className="bg-gray-900 border border-gray-800 rounded-2xl max-w-xl w-full p-6 text-gray-100 shadow-2xl relative">
        <button
          onClick={onClose}
          className="absolute top-4 right-4 p-1 text-gray-400 hover:text-white rounded-lg hover:bg-gray-800 transition"
        >
          <X className="w-5 h-5" />
        </button>

        <div className="flex items-center gap-3 mb-6">
          <div className="p-2.5 bg-indigo-500/10 rounded-xl text-indigo-400">
            <HelpCircle className="w-6 h-6" />
          </div>
          <div>
            <h3 className="text-lg font-bold text-white">Why was this test generated?</h3>
            <p className="text-xs text-gray-400">{testCaseName}</p>
          </div>
        </div>

        <div className="space-y-4">
          <div className="p-4 bg-gray-800/50 rounded-xl border border-gray-700/50 space-y-2">
            <div className="flex items-center justify-between text-xs">
              <span className="text-gray-400">Test Category</span>
              <span className="font-semibold text-indigo-400 px-2 py-0.5 bg-indigo-500/10 rounded-full">{testType}</span>
            </div>
            <div className="flex items-center justify-between text-xs">
              <span className="text-gray-400">Generator Engine</span>
              <span className="font-mono text-gray-300">v{metadata?.generator_version || '4.0.0'}</span>
            </div>
            <div className="flex items-center justify-between text-xs">
              <span className="text-gray-400">Deterministic Seed</span>
              <span className="font-mono text-gray-300">{metadata?.seed || 42}</span>
            </div>
          </div>

          <div className="space-y-3">
            <h4 className="text-xs font-semibold uppercase tracking-wider text-gray-400">Parameter Mutations</h4>
            {mutations.length > 0 ? (
              mutations.map((m: any, idx: number) => (
                <div key={idx} className="p-4 bg-gray-800/30 rounded-xl border border-gray-700/30 space-y-2 text-xs">
                  <div className="flex items-center justify-between font-mono text-white font-semibold">
                    <span>Target Field: {m.field_path}</span>
                    <span className="px-2 py-0.5 bg-amber-500/10 text-amber-300 rounded">{m.reason}</span>
                  </div>
                  <div className="grid grid-cols-2 gap-2 text-gray-300 font-mono text-[11px] pt-1">
                    <div>
                      <span className="text-gray-500">Original Value: </span>
                      {JSON.stringify(m.original_value)}
                    </div>
                    <div>
                      <span className="text-gray-500">Mutated Value: </span>
                      <span className="text-amber-400">{JSON.stringify(m.mutated_value)}</span>
                    </div>
                  </div>
                  {m.constraint_rule && (
                    <div className="text-[11px] text-gray-400 pt-1">
                      <span className="text-gray-500">Constraint Rule: </span>
                      <code>{m.constraint_rule}</code>
                    </div>
                  )}
                </div>
              ))
            ) : (
              <p className="text-xs text-gray-500 italic">No parameter mutations recorded for this test specification.</p>
            )}
          </div>
        </div>

        <div className="mt-6 pt-4 border-t border-gray-800 flex justify-end">
          <button
            onClick={onClose}
            className="px-4 py-2 bg-gray-800 hover:bg-gray-700 text-white rounded-xl text-xs font-medium transition"
          >
            Close Provenance
          </button>
        </div>
      </div>
    </div>
  );
};
