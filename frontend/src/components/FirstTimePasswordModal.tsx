import React, { useState } from 'react';
import { KeyRound, ShieldCheck, Check, X, Eye, EyeOff, LogOut, ArrowRight } from 'lucide-react';
import { api } from '../services/api';
import { useAuthStore } from '../store/authStore';
import { Button } from './common/Button';

export const FirstTimePasswordModal: React.FC = () => {
  const { user, updateUser, logout } = useAuthStore();
  const [newPassword, setNewPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  if (!user?.must_change_password) {
    return null;
  }

  // Password requirement checks
  const hasMinLength = newPassword.length >= 8;
  const hasUpper = /[A-Z]/.test(newPassword);
  const hasLower = /[a-z]/.test(newPassword);
  const hasNumber = /\d/.test(newPassword);
  const hasSpecial = /[!@#$%^&*()_+\-=\[\]{};':"\\|,.<>\/?~` ]/.test(newPassword);
  const passwordsMatch = newPassword === confirmPassword && newPassword.length > 0;

  const isFormValid =
    hasMinLength &&
    hasUpper &&
    hasLower &&
    hasNumber &&
    hasSpecial &&
    passwordsMatch;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!isFormValid) {
      setError('Please satisfy all password complexity criteria before saving.');
      return;
    }

    setLoading(true);
    setError(null);
    try {
      await api.post('/auth/change-password', {
        new_password: newPassword,
      });

      updateUser({ must_change_password: false });
    } catch (err: any) {
      const detail = err.response?.data?.detail;
      if (typeof detail === 'string') {
        setError(detail);
      } else if (Array.isArray(detail)) {
        setError(detail.map((d: any) => d.msg || JSON.stringify(d)).join(', '));
      } else {
        setError('Failed to update password. Please check complexity requirements.');
      }
    } finally {
      setLoading(false);
    }
  };

  const checklistItem = (label: string, met: boolean) => (
    <div className={`flex items-center gap-2 text-xs transition-colors ${met ? 'text-emerald-400 font-medium' : 'text-muted'}`}>
      <div className={`w-4 h-4 rounded-full flex items-center justify-center text-[10px] ${met ? 'bg-emerald-500/20 text-emerald-400' : 'bg-field text-muted border border-border-card'}`}>
        {met ? <Check className="w-2.5 h-2.5 stroke-[3]" /> : <X className="w-2.5 h-2.5 opacity-50" />}
      </div>
      <span>{label}</span>
    </div>
  );

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-md animate-fade-in">
      <div className="relative w-full max-w-lg bg-card border border-border-card rounded-3xl p-7 shadow-glass-elevated space-y-6">
        {/* Header Strip */}
        <div className="flex items-start gap-4">
          <div className="w-12 h-12 rounded-2xl bg-amber-500/15 border border-amber-500/30 flex items-center justify-center text-amber-400 shrink-0">
            <KeyRound className="w-6 h-6" />
          </div>
          <div className="space-y-1">
            <div className="flex items-center gap-2">
              <h2 className="text-lg font-bold text-primary">First-Time Login Security Setup</h2>
              <span className="px-2 py-0.5 rounded-full text-[10px] font-bold bg-amber-500/15 text-amber-700 dark:text-amber-400 border border-amber-500/30 uppercase tracking-wider">
                Action Required
              </span>
            </div>
            <p className="text-xs text-secondary leading-relaxed">
              An administrator generated your account credentials. For platform security, you must choose a new permanent password before proceeding.
            </p>
          </div>
        </div>

        {error && (
          <div className="p-3.5 rounded-xl bg-status-failed-bg border border-status-failed/30 text-status-failed text-xs font-medium">
            {error}
          </div>
        )}

        <form onSubmit={handleSubmit} className="space-y-5">
          {/* New Password Input */}
          <div className="space-y-1.5">
            <label className="block text-xs font-semibold text-secondary">
              New Password
            </label>
            <div className="relative">
              <input
                type={showPassword ? 'text' : 'password'}
                value={newPassword}
                onChange={(e) => setNewPassword(e.target.value)}
                placeholder="Enter new permanent password"
                required
                className="w-full h-11 bg-field text-primary text-sm rounded-xl border border-border-field hover:border-brand focus:border-brand focus:ring-1 focus:ring-brand pl-3.5 pr-11 outline-none transition-colors"
              />
              <button
                type="button"
                onClick={() => setShowPassword(!showPassword)}
                className="absolute inset-y-0 right-0 pr-3.5 flex items-center text-muted hover:text-primary transition-colors"
              >
                {showPassword ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
              </button>
            </div>
          </div>

          {/* Confirm Password Input */}
          <div className="space-y-1.5">
            <label className="block text-xs font-semibold text-secondary">
              Confirm New Password
            </label>
            <input
              type={showPassword ? 'text' : 'password'}
              value={confirmPassword}
              onChange={(e) => setConfirmPassword(e.target.value)}
              placeholder="Confirm new permanent password"
              required
              className="w-full h-11 bg-field text-primary text-sm rounded-xl border border-border-field hover:border-brand focus:border-brand focus:ring-1 focus:ring-brand px-3.5 outline-none transition-colors"
            />
          </div>

          {/* Requirements Checklist Card */}
          <div className="p-4 rounded-2xl bg-field/60 border border-border-card space-y-2.5">
            <div className="flex items-center gap-1.5 text-xs font-semibold text-primary">
              <ShieldCheck className="w-4 h-4 text-brand" />
              <span>Password Complexity Policy</span>
            </div>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 pt-1">
              {checklistItem('Minimum 8 characters', hasMinLength)}
              {checklistItem('Uppercase letter (A-Z)', hasUpper)}
              {checklistItem('Lowercase letter (a-z)', hasLower)}
              {checklistItem('At least one number (0-9)', hasNumber)}
              {checklistItem('Special character (!@#$%^&*)', hasSpecial)}
              {checklistItem('Passwords match', passwordsMatch)}
            </div>
          </div>

          {/* Action Buttons */}
          <div className="flex items-center justify-between pt-2">
            <Button
              type="button"
              variant="secondary"
              size="sm"
              onClick={logout}
              leftIcon={<LogOut className="w-4 h-4" />}
            >
              Sign Out
            </Button>
            <Button
              type="submit"
              variant="primary"
              size="md"
              disabled={!isFormValid || loading}
              isLoading={loading}
              rightIcon={<ArrowRight className="w-4 h-4" />}
            >
              Set Permanent Password
            </Button>
          </div>
        </form>
      </div>
    </div>
  );
};
