import React, { useState } from "react";
import { ShieldCheck, Layers, FileCode, CheckCircle2, AlertTriangle } from "lucide-react";

interface WebhookLog {
  id: string;
  provider: string;
  delivery_id: string;
  event_type: string;
  signature_verified: boolean;
  processing_status: string;
  created_at: string;
}

interface WebhookLogViewerProps {
  logs: WebhookLog[];
}

export const WebhookLogViewer: React.FC<WebhookLogViewerProps> = ({ logs }) => {
  const [selectedLog, setSelectedLog] = useState<WebhookLog | null>(null);

  return (
    <div className="bg-slate-900 border border-slate-800 rounded-xl p-5 text-slate-100 shadow-xl">
      <div className="flex items-center justify-between mb-4 border-b border-slate-800 pb-3">
        <div className="flex items-center gap-2">
          <Layers className="w-5 h-5 text-cyan-400" />
          <h3 className="font-semibold text-lg">GitHub Webhook Delivery Audit Log</h3>
        </div>
        <span className="text-xs bg-cyan-500/10 text-cyan-400 border border-cyan-500/20 px-2.5 py-1 rounded-full font-mono">
          HMAC-SHA256 Verified
        </span>
      </div>

      <div className="overflow-x-auto">
        <table className="w-full text-left border-collapse text-xs">
          <thead>
            <tr className="border-b border-slate-800 text-slate-400 font-semibold uppercase tracking-wider text-[11px]">
              <th className="py-2.5 px-3">Delivery ID</th>
              <th className="py-2.5 px-3">Event</th>
              <th className="py-2.5 px-3">HMAC Signature</th>
              <th className="py-2.5 px-3">Status</th>
              <th className="py-2.5 px-3">Received At</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-800/60 font-mono">
            {logs.length === 0 ? (
              <tr>
                <td colSpan={5} className="py-4 text-center text-slate-500 italic">
                  No webhook deliveries recorded yet.
                </td>
              </tr>
            ) : (
              logs.map((log) => (
                <tr key={log.id} className="hover:bg-slate-950/50 transition cursor-pointer" onClick={() => setSelectedLog(log)}>
                  <td className="py-2.5 px-3 text-cyan-300 truncate max-w-[150px]">{log.delivery_id}</td>
                  <td className="py-2.5 px-3 font-sans text-slate-300 font-medium">{log.event_type}</td>
                  <td className="py-2.5 px-3">
                    {log.signature_verified ? (
                      <span className="inline-flex items-center gap-1 text-[10px] bg-emerald-500/10 text-emerald-400 px-2 py-0.5 rounded-full border border-emerald-500/20">
                        <ShieldCheck className="w-3 h-3" /> Valid HMAC
                      </span>
                    ) : (
                      <span className="inline-flex items-center gap-1 text-[10px] bg-rose-500/10 text-rose-400 px-2 py-0.5 rounded-full border border-rose-500/20">
                        <AlertTriangle className="w-3 h-3" /> Unverified
                      </span>
                    )}
                  </td>
                  <td className="py-2.5 px-3">
                    <span className={`px-2 py-0.5 text-[10px] rounded font-semibold ${
                      log.processing_status === "PROCESSED" ? "bg-emerald-500/20 text-emerald-400" :
                      log.processing_status === "DUPLICATE_IGNORED" ? "bg-amber-500/20 text-amber-400" : "bg-slate-800 text-slate-400"
                    }`}>
                      {log.processing_status}
                    </span>
                  </td>
                  <td className="py-2.5 px-3 text-slate-400 font-sans text-[11px]">
                    {new Date(log.created_at).toLocaleString()}
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
};
