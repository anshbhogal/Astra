import React from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import { AlertTriangle, LogIn, FileCode, CheckCircle2 } from 'lucide-react';
import { useAuthStore } from '../../store/authStore';
import { Button } from './Button';

export const SessionExpiredModal: React.FC = () => {
  const { isSessionExpired, setSessionExpired, logout } = useAuthStore();
  const navigate = useNavigate();
  const location = useLocation();

  if (!isSessionExpired) {
    return null;
  }

  const handleDismissToCopyWork = () => {
    // Dismiss the modal temporarily so developer can inspect or copy unsaved editor tabs
    setSessionExpired(false);
  };

  const handleReauthenticate = () => {
    logout();
    navigate('/login', { state: { returnTo: location.pathname } });
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-sm animate-fadeIn">
      <div className="w-full max-w-lg glass-card-elevated border border-amber-500/40 rounded-3xl p-6 shadow-2xl space-y-5 bg-card/95 text-primary">
        <div className="flex items-start gap-4">
          <div className="w-12 h-12 rounded-2xl bg-amber-500/15 border border-amber-500/30 flex items-center justify-center text-amber-500 shrink-0">
            <AlertTriangle className="w-6 h-6 stroke-[2.2]" />
          </div>
          <div className="space-y-1">
            <div className="flex items-center gap-2">
              <h3 className="text-base font-bold text-primary">Authentication Session Expired</h3>
              <span className="px-2 py-0.5 rounded-full text-[10px] font-bold bg-amber-500/15 text-amber-400 border border-amber-500/30">
                Buffer Protected
              </span>
            </div>
            <p className="text-xs text-secondary leading-relaxed">
              Your access token has expired. To prevent losing unsaved Code Studio files, Monaco editor buffers, or active tabs, your session will <strong>not</strong> be force-reloaded.
            </p>
          </div>
        </div>

        <div className="p-3.5 rounded-xl bg-field border border-border-card text-xs space-y-2">
          <div className="flex items-center gap-2 text-primary font-semibold">
            <FileCode className="w-4 h-4 text-brand" />
            <span>Developer Safe Mode Active</span>
          </div>
          <p className="text-secondary text-[11px] leading-relaxed">
            You can dismiss this dialog to inspect, copy, or save your active files locally before authenticating again. No browser refresh will occur.
          </p>
        </div>

        <div className="flex flex-col sm:flex-row items-center justify-end gap-2.5 pt-2 border-t border-border-card">
          <Button
            variant="ghost"
            size="sm"
            onClick={handleDismissToCopyWork}
            className="w-full sm:w-auto text-xs"
          >
            Dismiss & Copy Unsaved Work
          </Button>
          <Button
            variant="primary"
            size="sm"
            onClick={handleReauthenticate}
            leftIcon={<LogIn className="w-3.5 h-3.5" />}
            className="w-full sm:w-auto text-xs bg-amber-500 hover:bg-amber-600 text-black font-bold"
          >
            Re-authenticate Now
          </Button>
        </div>
      </div>
    </div>
  );
};
