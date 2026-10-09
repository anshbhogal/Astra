import React, { useState } from "react";
import { X, Bell, Lock, Send } from "lucide-react";

interface NotificationChannelModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSave: (channel: { channel_type: string; name: string; target_url: string }) => void;
}

export const NotificationChannelModal: React.FC<NotificationChannelModalProps> = ({
  isOpen,
  onClose,
  onSave,
}) => {
  const [channelType, setChannelType] = useState("SLACK");
  const [name, setName] = useState("");
  const [targetUrl, setTargetUrl] = useState("");

  if (!isOpen) return null;

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!name || !targetUrl) return;
    onSave({ channel_type: channelType, name, target_url: targetUrl });
    setName("");
    setTargetUrl("");
    onClose();
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm">
      <div className="w-full max-w-md bg-slate-900 border border-slate-800 rounded-xl p-6 text-slate-100 shadow-2xl">
        <div className="flex items-center justify-between pb-3 border-b border-slate-800 mb-4">
          <div className="flex items-center gap-2">
            <Bell className="w-5 h-5 text-indigo-400" />
            <h3 className="font-bold text-lg">Add Notification Channel</h3>
          </div>
          <button onClick={onClose} className="p-1 text-slate-400 hover:text-slate-100 rounded">
            <X className="w-5 h-5" />
          </button>
        </div>

        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-xs font-semibold text-slate-400 mb-1">Channel Type</label>
            <select
              value={channelType}
              onChange={(e) => setChannelType(e.target.value)}
              className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-xs font-sans text-slate-200 focus:outline-none focus:border-indigo-500"
            >
              <option value="SLACK">Slack Incoming Webhook</option>
              <option value="MS_TEAMS">Microsoft Teams Adaptive Card</option>
              <option value="EMAIL">SMTP Email Recipient</option>
            </select>
          </div>

          <div>
            <label className="block text-xs font-semibold text-slate-400 mb-1">Channel Nickname</label>
            <input
              type="text"
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="e.g. #dev-alerts or QA Team Email"
              className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-xs font-sans text-slate-200 focus:outline-none focus:border-indigo-500"
              required
            />
          </div>

          <div>
            <label className="block text-xs font-semibold text-slate-400 mb-1 flex items-center gap-1">
              Target Webhook URL / Email <Lock className="w-3 h-3 text-emerald-400" /> (Encrypted at rest)
            </label>
            <input
              type="text"
              value={targetUrl}
              onChange={(e) => setTargetUrl(e.target.value)}
              placeholder="https://hooks.slack.com/services/..."
              className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-xs font-mono text-slate-200 focus:outline-none focus:border-indigo-500"
              required
            />
          </div>

          <div className="pt-3 border-t border-slate-800 flex justify-end gap-2">
            <button
              type="button"
              onClick={onClose}
              className="px-4 py-2 bg-slate-800 text-slate-300 text-xs font-medium rounded-lg hover:bg-slate-700 transition"
            >
              Cancel
            </button>
            <button
              type="submit"
              className="px-4 py-2 bg-indigo-600 text-white text-xs font-medium rounded-lg hover:bg-indigo-500 transition shadow-lg shadow-indigo-600/20 flex items-center gap-1.5"
            >
              <Send className="w-3.5 h-3.5" /> Save Channel
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};
