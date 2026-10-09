import React from "react";
import { CheckCircle2, XCircle, AlertTriangle, ShieldCheck } from "lucide-react";

interface CIStatusBadgeProps {
  status: string;
}

export const CIStatusBadge: React.FC<CIStatusBadgeProps> = ({ status }) => {
  if (status === "PASS") {
    return (
      <span className="inline-flex items-center gap-1 bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 text-xs px-2.5 py-1 rounded-full font-semibold">
        <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400" /> Gate Passed
      </span>
    );
  }
  if (status === "FAIL") {
    return (
      <span className="inline-flex items-center gap-1 bg-rose-500/10 text-rose-400 border border-rose-500/20 text-xs px-2.5 py-1 rounded-full font-semibold">
        <XCircle className="w-3.5 h-3.5 text-rose-400" /> Gate Failed
      </span>
    );
  }
  if (status === "SAFETY_EXPANDED") {
    return (
      <span className="inline-flex items-center gap-1 bg-amber-500/10 text-amber-400 border border-amber-500/20 text-xs px-2.5 py-1 rounded-full font-semibold">
        <AlertTriangle className="w-3.5 h-3.5 text-amber-400" /> Safety Expanded
      </span>
    );
  }

  return (
    <span className="inline-flex items-center gap-1 bg-slate-800 text-slate-400 text-xs px-2.5 py-1 rounded-full font-semibold">
      <ShieldCheck className="w-3.5 h-3.5" /> {status}
    </span>
  );
};
