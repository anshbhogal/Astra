import React, { useState } from 'react';
import { Settings, Cpu, Shield, DollarSign, X, Check } from 'lucide-react';

interface LLMConfigDrawerProps {
  isOpen: boolean;
  onClose: () => void;
  onSave: (config: any) => void;
}

export const LLMConfigDrawer: React.FC<LLMConfigDrawerProps> = ({
  isOpen,
  onClose,
  onSave,
}) => {
  const [provider, setProvider] = useState('gemini');
  const [model, setModel] = useState('gemini-1.5-pro');
  const [temperature, setTemperature] = useState(0.1);
  const [maxTokens, setMaxTokens] = useState(100000);
  const [enableAI, setEnableAI] = useState(true);

  if (!isOpen) return null;

  const handleSave = () => {
    onSave({
      provider,
      model,
      temperature,
      max_tokens: maxTokens,
      enable_ai: enableAI,
    });
    onClose();
  };

  return (
    <div className="fixed inset-0 z-50 flex justify-end bg-black/60 backdrop-blur-sm">
      <div className="bg-slate-900 border-l border-slate-800 w-full max-w-md h-full flex flex-col shadow-2xl">
        <div className="flex items-center justify-between px-6 py-4 border-b border-slate-800">
          <div className="flex items-center gap-2 text-indigo-400 font-semibold">
            <Cpu className="w-5 h-5" />
            <span>AI Provider & Budget Settings</span>
          </div>
          <button onClick={onClose} className="text-slate-400 hover:text-slate-200">
            <X className="w-5 h-5" />
          </button>
        </div>

        <div className="flex-1 overflow-y-auto p-6 space-y-6 text-sm text-slate-300">
          <div className="flex items-center justify-between p-3 bg-slate-950 border border-slate-800 rounded-lg">
            <div>
              <div className="font-semibold text-slate-200">Enable AI Boundary Exploration</div>
              <div className="text-xs text-slate-400">Synthesize business rule edge cases with LLM</div>
            </div>
            <input
              type="checkbox"
              checked={enableAI}
              onChange={(e) => setEnableAI(e.target.checked)}
              className="w-4 h-4 accent-indigo-600 rounded cursor-pointer"
            />
          </div>

          <div>
            <label className="block text-xs font-bold text-slate-400 uppercase mb-2">Active LLM Provider</label>
            <div className="grid grid-cols-2 gap-2">
              {[
                { id: 'gemini', name: 'Google Gemini', desc: 'Cloud Production' },
                { id: 'ollama', name: 'Ollama (Local)', desc: 'Zero Cost / Private' },
              ].map((p) => (
                <button
                  key={p.id}
                  type="button"
                  onClick={() => {
                    setProvider(p.id);
                    setModel(p.id === 'gemini' ? 'gemini-1.5-pro' : 'llama3.1');
                  }}
                  className={`p-3 rounded-lg border text-left transition-all ${
                    provider === p.id
                      ? 'border-indigo-500 bg-indigo-950/40 text-indigo-300'
                      : 'border-slate-800 bg-slate-950 text-slate-400 hover:border-slate-700'
                  }`}
                >
                  <div className="font-semibold text-xs text-slate-200">{p.name}</div>
                  <div className="text-[10px] text-slate-500">{p.desc}</div>
                </button>
              ))}
            </div>
          </div>

          <div>
            <label className="block text-xs font-bold text-slate-400 uppercase mb-1">Model Identifier</label>
            <input
              type="text"
              value={model}
              onChange={(e) => setModel(e.target.value)}
              className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-xs text-slate-200 font-mono"
            />
          </div>

          <div>
            <div className="flex justify-between items-center mb-1">
              <label className="text-xs font-bold text-slate-400 uppercase">Temperature ({temperature})</label>
              <span className="text-[10px] text-slate-500">Deterministic ($\approx 0.1$)</span>
            </div>
            <input
              type="range"
              min="0"
              max="0.5"
              step="0.05"
              value={temperature}
              onChange={(e) => setTemperature(parseFloat(e.target.value))}
              className="w-full accent-indigo-600 cursor-pointer"
            />
          </div>

          <div className="border-t border-slate-800 pt-4 space-y-3">
            <div className="flex items-center gap-2 text-xs font-bold text-slate-400 uppercase">
              <Shield className="w-4 h-4 text-emerald-400" />
              <span>Safety & Prompt Guard</span>
            </div>
            <div className="p-3 bg-emerald-950/30 border border-emerald-800/50 rounded-lg text-xs text-emerald-300 space-y-1">
              <div className="font-medium">• Prompt Guard: Untrusted PRDs isolated in &lt;UNTRUSTED_DOCUMENT&gt;</div>
              <div className="font-medium">• Secret Sanitizer: API keys & JWT tokens redacted automatically</div>
            </div>
          </div>

          <div className="border-t border-slate-800 pt-4 space-y-3">
            <div className="flex items-center gap-2 text-xs font-bold text-slate-400 uppercase">
              <DollarSign className="w-4 h-4 text-indigo-400" />
              <span>AI Token Budget Cap</span>
            </div>
            <input
              type="number"
              value={maxTokens}
              onChange={(e) => setMaxTokens(parseInt(e.target.value) || 100000)}
              className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-xs text-slate-200"
            />
          </div>
        </div>

        <div className="p-4 border-t border-slate-800 flex justify-end gap-3">
          <button onClick={onClose} className="px-4 py-2 bg-slate-800 hover:bg-slate-700 text-slate-300 rounded-lg text-sm">
            Cancel
          </button>
          <button onClick={handleSave} className="px-4 py-2 bg-indigo-600 hover:bg-indigo-500 text-white rounded-lg text-sm font-medium flex items-center gap-2">
            <Check className="w-4 h-4" />
            Save Configuration
          </button>
        </div>
      </div>
    </div>
  );
};
