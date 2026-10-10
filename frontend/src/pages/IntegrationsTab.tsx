import React, { useState, useEffect } from "react";
import { GitBranch, Bell, Key, Plus, RefreshCw, Send } from "lucide-react";
import { WebhookLogViewer } from "../components/WebhookLogViewer";
import { NotificationChannelModal } from "../components/NotificationChannelModal";
import { Button } from "../components/common/Button";

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
    <div className="space-y-6">
      {/* Header & Webhook Setup Card */}
      <div className="bg-card border border-border-card rounded-2xl p-6 shadow-card space-y-4">
        <div className="flex items-center justify-between border-b border-border-card pb-4">
          <div className="flex items-center gap-3">
            <div className="w-9 h-9 rounded-xl bg-brand/10 text-brand border border-brand/20 flex items-center justify-center">
              <GitBranch className="w-5 h-5" />
            </div>
            <div>
              <h2 className="text-lg font-bold text-primary">CI/CD Pipeline & Webhook Integration</h2>
              <p className="text-xs text-secondary">Automated PR status checks and webhook telemetry triggers</p>
            </div>
          </div>
          <button
            onClick={fetchData}
            disabled={loading}
            className="p-2 text-secondary hover:text-primary rounded-xl hover:bg-hover transition-colors"
          >
            <RefreshCw className={`w-4 h-4 ${loading ? "animate-spin" : ""}`} />
          </button>
        </div>

        <div className="bg-field p-4 rounded-xl border border-border-card space-y-3">
          <h3 className="text-xs font-semibold text-secondary uppercase tracking-wider flex items-center gap-1.5">
            <Key className="w-4 h-4 text-status-passed" /> GitHub Repository Webhook Endpoint
          </h3>
          <div className="flex items-center gap-2">
            <input
              type="text"
              readOnly
              value={webhookUrl}
              className="flex-1 bg-card border border-border-field rounded-lg px-3.5 py-2 text-xs font-mono text-brand focus:outline-none"
            />
            <Button
              variant="primary"
              size="sm"
              onClick={() => navigator.clipboard.writeText(webhookUrl)}
            >
              Copy URL
            </Button>
          </div>
          <p className="text-xs text-muted">
            Configure this URL under GitHub Repository Settings → Webhooks. Select events: <code className="text-brand font-semibold">Pull request</code> and <code className="text-brand font-semibold">Push</code>. HMAC-SHA256 signature verification enforced.
          </p>
        </div>
      </div>

      {/* Notification Channels List */}
      <div className="bg-card border border-border-card rounded-2xl p-6 shadow-card space-y-4">
        <div className="flex items-center justify-between border-b border-border-card pb-4">
          <div className="flex items-center gap-3">
            <div className="w-9 h-9 rounded-xl bg-status-flaky-bg text-status-flaky border border-status-flaky/30 flex items-center justify-center">
              <Bell className="w-5 h-5" />
            </div>
            <div>
              <h3 className="font-bold text-base text-primary">Configured Notification Channels</h3>
              <p className="text-xs text-secondary">Alert dispatch routing on test failures and quality regressions</p>
            </div>
          </div>
          <Button
            variant="primary"
            size="sm"
            onClick={() => setModalOpen(true)}
            leftIcon={<Plus className="w-4 h-4" />}
          >
            Add Channel
          </Button>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {channels.length === 0 ? (
            <div className="col-span-2 text-center py-8 text-muted italic text-xs">
              No notification targets configured yet. Click 'Add Channel' to connect Slack, Teams, or Email alerts.
            </div>
          ) : (
            channels.map((ch) => (
              <div key={ch.id} className="bg-field border border-border-card rounded-xl p-4 flex items-center justify-between">
                <div>
                  <div className="flex items-center gap-2">
                    <span className="font-semibold text-sm text-primary">{ch.name}</span>
                    <span className="text-[10px] bg-brand/10 text-brand px-2 py-0.5 rounded font-mono font-bold">
                      {ch.channel_type}
                    </span>
                  </div>
                  <span className="text-xs font-mono text-muted mt-1 block truncate max-w-[200px]">
                    {ch.masked_target}
                  </span>
                </div>
                <Button
                  variant="secondary"
                  size="sm"
                  onClick={() => handleTestPing(ch.id)}
                  leftIcon={<Send className="w-3 h-3 text-brand" />}
                >
                  Ping
                </Button>
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
