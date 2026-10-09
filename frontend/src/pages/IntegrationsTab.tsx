import React, { useState, useEffect } from "react";
import { GitBranch, Bell, Shield, Key, Plus, RefreshCw, Send } from "lucide-react";
import { WebhookLogViewer } from "../components/WebhookLogViewer";
import { NotificationChannelModal } from "../components/NotificationChannelModal";
import { CIStatusBadge } from "../components/CIStatusBadge";

interface IntegrationsTabProps {
  projectId: string;
}

export const IntegrationsTab: React.FC<IntegrationsTabProps> = ({ projectId }) => {
  const [channels, setChannels] = useState<any[]>([]);
  const [logs, setLogs] = useState<any[]>([]);
  const [modalOpen, setModalOpen] = useState(false);
  const [loading, setLoading] = useState(false);

  const webhookUrl = `${window.location.origin}/api/v1/webhooks/github`;

  const fetchData = async () => {
    setLoading(true);
    try {
      const [chResp, logResp] = await Promise.all([
        fetch(`/api/v1/projects/${projectId}/notifications`),
        fetch(`/api/v1/projects/${projectId}/webhooks/logs`),
      ]);

      if (chResp.ok) {
        const chData = await chResp.json();
        setChannels(chData.channels || []);
      }
      if (logResp.ok) {
        const logData = await logResp.json();
        setLogs(logData.logs || []);
      }
    } catch (err) {
      console.error("Error fetching integrations data:", err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
  }, [projectId]);

  const handleSaveChannel = async (channel: { channel_type: string; name: string; target_url: string }) => {
    try {
      const resp = await fetch(`/api/v1/projects/${projectId}/notifications`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(channel),
      });
      if (resp.ok) {
        fetchData();
      }
    } catch (err) {
      console.error("Error saving notification channel:", err);
    }
  };

  const handleTestPing = async (channelId: string) => {
    try {
      await fetch(`/api/v1/notifications/${channelId}/test`, { method: "POST" });
      alert("Test ping notification dispatched!");
    } catch (err) {
      alert("Failed to send test ping.");
    }
  };

  return (
    <div className="space-y-6 text-slate-100">
      {/* Header & Webhook Setup Card */}
      <div className="bg-slate-900 border border-slate-800 rounded-xl p-5 shadow-xl">
        <div className="flex items-center justify-between mb-4 border-b border-slate-800 pb-3">
          <div className="flex items-center gap-2">
            <GitBranch className="w-5 h-5 text-indigo-400" />
            <h2 className="text-lg font-bold">Phase 9: CI/CD Pipeline & Webhook Integration</h2>
          </div>
          <button
            onClick={fetchData}
            disabled={loading}
            className="p-1.5 text-slate-400 hover:text-slate-100 rounded-lg hover:bg-slate-800 transition"
          >
            <RefreshCw className={`w-4 h-4 ${loading ? "animate-spin" : ""}`} />
          </button>
        </div>

        <div className="bg-slate-950 p-4 rounded-lg border border-slate-800 space-y-3">
          <h3 className="text-xs font-semibold text-slate-300 uppercase tracking-wider flex items-center gap-1.5">
            <Key className="w-4 h-4 text-emerald-400" /> GitHub Repository Webhook Endpoint
          </h3>
          <div className="flex items-center gap-2">
            <input
              type="text"
              readOnly
              value={webhookUrl}
              className="flex-1 bg-slate-900 border border-slate-800 rounded-lg px-3 py-2 text-xs font-mono text-cyan-300 focus:outline-none"
            />
            <button
              onClick={() => navigator.clipboard.writeText(webhookUrl)}
              className="px-3 py-2 bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-medium rounded-lg transition"
            >
              Copy URL
            </button>
          </div>
          <p className="text-[11px] text-slate-400">
            Configure this URL under GitHub Repository Settings → Webhooks. Select events: <code className="text-indigo-300">Pull request</code> and <code className="text-indigo-300">Push</code>. HMAC-SHA256 signature verification enforced.
          </p>
        </div>
      </div>

      {/* Notification Channels List */}
      <div className="bg-slate-900 border border-slate-800 rounded-xl p-5 shadow-xl">
        <div className="flex items-center justify-between mb-4 border-b border-slate-800 pb-3">
          <div className="flex items-center gap-2">
            <Bell className="w-5 h-5 text-amber-400" />
            <h3 className="font-semibold text-lg">Configured Notification Channels</h3>
          </div>
          <button
            onClick={() => setModalOpen(true)}
            className="px-3 py-1.5 bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-medium rounded-lg transition flex items-center gap-1.5 shadow-lg shadow-indigo-600/20"
          >
            <Plus className="w-4 h-4" /> Add Channel
          </button>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {channels.length === 0 ? (
            <div className="col-span-2 text-center py-6 text-slate-500 italic text-xs">
              No notification targets configured yet. Click 'Add Channel' to connect Slack, Teams, or Email alerts.
            </div>
          ) : (
            channels.map((ch) => (
              <div key={ch.id} className="bg-slate-950 border border-slate-800 rounded-lg p-4 flex items-center justify-between">
                <div>
                  <div className="flex items-center gap-2">
                    <span className="font-semibold text-sm">{ch.name}</span>
                    <span className="text-[10px] bg-indigo-500/20 text-indigo-300 px-2 py-0.5 rounded font-mono">
                      {ch.channel_type}
                    </span>
                  </div>
                  <span className="text-xs font-mono text-slate-400 mt-1 block truncate max-w-[200px]">
                    {ch.masked_target}
                  </span>
                </div>
                <button
                  onClick={() => handleTestPing(ch.id)}
                  className="px-2.5 py-1.5 bg-slate-800 hover:bg-slate-700 text-slate-300 text-xs font-medium rounded-lg transition flex items-center gap-1"
                >
                  <Send className="w-3 h-3 text-cyan-400" /> Ping
                </button>
              </div>
            ))
          )}
        </div>
      </div>

      {/* Webhook Delivery Audit Log */}
      <WebhookLogViewer logs={logs} />

      <NotificationChannelModal
        isOpen={modalOpen}
        onClose={() => setModalOpen(false)}
        onSave={handleSaveChannel}
      />
    </div>
  );
};
