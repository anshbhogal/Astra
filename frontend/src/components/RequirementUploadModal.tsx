import React, { useState } from 'react';
import { Upload, FileText, CheckCircle2, AlertCircle, X } from 'lucide-react';
import { api } from '../services/api';

interface RequirementUploadModalProps {
  projectId: string;
  isOpen: boolean;
  onClose: () => void;
  onSuccess: () => void;
}

export const RequirementUploadModal: React.FC<RequirementUploadModalProps> = ({
  projectId,
  isOpen,
  onClose,
  onSuccess,
}) => {
  const [filename, setFilename] = useState('requirements.md');
  const [sourceType, setSourceType] = useState('PRD_MARKDOWN');
  const [content, setContent] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  if (!isOpen) return null;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!content.trim()) {
      setError('Please paste document content or upload a file.');
      return;
    }

    setLoading(true);
    setError(null);

    try {
      await api.post(`/projects/${projectId}/requirements/upload`, {
        filename,
        source_type: sourceType,
        content,
      });
      setLoading(false);
      onSuccess();
      onClose();
    } catch (err: any) {
      setLoading(false);
      setError(err.response?.data?.detail || 'Failed to upload requirements');
    }
  };

  const handleFileUpload = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) {
      setFilename(file.name);
      if (file.name.endsWith('.feature')) {
        setSourceType('GHERKIN_FEATURE');
      } else if (file.name.endsWith('.yaml') || file.name.endsWith('.json')) {
        setSourceType('OPENAPI_SPEC');
      } else {
        setSourceType('PRD_MARKDOWN');
      }

      const reader = new FileReader();
      reader.onload = (event) => {
        setContent(event.target?.result as string || '');
      };
      reader.readAsText(file);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm p-4">
      <div className="bg-slate-900 border border-slate-800 rounded-xl w-full max-w-2xl overflow-hidden shadow-2xl">
        <div className="flex items-center justify-between px-6 py-4 border-b border-slate-800">
          <div className="flex items-center gap-2 text-indigo-400 font-semibold">
            <Upload className="w-5 h-5" />
            <span>Upload Requirement Document</span>
          </div>
          <button onClick={onClose} className="text-slate-400 hover:text-slate-200">
            <X className="w-5 h-5" />
          </button>
        </div>

        <form onSubmit={handleSubmit} className="p-6 space-y-4">
          {error && (
            <div className="p-3 bg-red-950/50 border border-red-800 text-red-300 rounded-lg text-sm flex items-center gap-2">
              <AlertCircle className="w-4 h-4 text-red-400 shrink-0" />
              <span>{error}</span>
            </div>
          )}

          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-xs text-slate-400 uppercase font-bold mb-1">Document Filename</label>
              <input
                type="text"
                value={filename}
                onChange={(e) => setFilename(e.target.value)}
                className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-sm text-slate-200 focus:outline-none focus:border-indigo-500"
              />
            </div>
            <div>
              <label className="block text-xs text-slate-400 uppercase font-bold mb-1">Source Type</label>
              <select
                value={sourceType}
                onChange={(e) => setSourceType(e.target.value)}
                className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-sm text-slate-200 focus:outline-none focus:border-indigo-500"
              >
                <option value="PRD_MARKDOWN">Markdown PRD / User Story</option>
                <option value="GHERKIN_FEATURE">Gherkin .feature File</option>
                <option value="OPENAPI_SPEC">OpenAPI 3.x Specification</option>
              </select>
            </div>
          </div>

          <div>
            <label className="block text-xs text-slate-400 uppercase font-bold mb-1">File Uploader</label>
            <input
              type="file"
              onChange={handleFileUpload}
              accept=".md,.feature,.json,.yaml,.yml,.txt"
              className="block w-full text-xs text-slate-400 file:mr-4 file:py-2 file:px-4 file:rounded-lg file:border-0 file:text-xs file:font-semibold file:bg-indigo-950 file:text-indigo-300 hover:file:bg-indigo-900 cursor-pointer"
            />
          </div>

          <div>
            <label className="block text-xs text-slate-400 uppercase font-bold mb-1">Document Content</label>
            <textarea
              rows={8}
              value={content}
              onChange={(e) => setContent(e.target.value)}
              placeholder="Paste Markdown PRD, Gherkin scenario, or OpenAPI specification..."
              className="w-full bg-slate-950 border border-slate-800 rounded-lg p-3 text-xs font-mono text-slate-300 focus:outline-none focus:border-indigo-500"
            />
          </div>

          <div className="flex justify-end gap-3 pt-2">
            <button
              type="button"
              onClick={onClose}
              className="px-4 py-2 bg-slate-800 hover:bg-slate-700 text-slate-300 rounded-lg text-sm"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={loading}
              className="px-4 py-2 bg-indigo-600 hover:bg-indigo-500 text-white rounded-lg text-sm font-medium flex items-center gap-2 disabled:opacity-50"
            >
              {loading ? 'Parsing...' : 'Upload & Extract Specs'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};
