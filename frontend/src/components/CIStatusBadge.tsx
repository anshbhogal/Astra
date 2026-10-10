import React from "react";
import { CheckCircle2, XCircle, AlertTriangle, ShieldCheck } from "lucide-react";

interface CIStatusBadgeProps {
  status: string;
}

export const CIStatusBadge: React.FC<CIStatusBadgeProps> = ({ status }) => {
  if (status === "PASS") {
    return (
      <span className="inline-flex items-center gap-1.5 bg-status-passed-bg text-status-passed border border-status-passed/30 text-xs px-2.5 py-1 rounded-full font-semibold">
        <CheckCircle2 className="w-3.5 h-3.5" /> Gate Passed
      </span>
    );
  }
  if (status === "FAIL") {
    return (
      <span className="inline-flex items-center gap-1.5 bg-status-failed-bg text-status-failed border border-status-failed/30 text-xs px-2.5 py-1 rounded-full font-semibold">
        <XCircle className="w-3.5 h-3.5" /> Gate Failed
      </span>
    );
  }
  if (status === "SAFETY_EXPANDED") {
    return (
      <span className="inline-flex items-center gap-1.5 bg-status-flaky-bg text-status-flaky border border-status-flaky/30 text-xs px-2.5 py-1 rounded-full font-semibold">
        <AlertTriangle className="w-3.5 h-3.5" /> Safety Expanded
      </span>
    );
  }

  return (
    <span className="inline-flex items-center gap-1.5 bg-field text-secondary border border-border-card text-xs px-2.5 py-1 rounded-full font-semibold">
      <ShieldCheck className="w-3.5 h-3.5" /> {status}
    </span>
  );
};
