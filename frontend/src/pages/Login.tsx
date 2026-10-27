import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Lock, Mail, User as UserIcon, Shield, ArrowRight, Sparkles, CheckCircle, FlaskConical, Code2 } from 'lucide-react';
import { api } from '../services/api';
import { useAuthStore, UserRole } from '../store/authStore';
import { Button } from '../components/common/Button';
import { Input } from '../components/common/Input';

export const Login: React.FC = () => {
  const [isRegister, setIsRegister] = useState(false);
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [fullName, setFullName] = useState('');
  const [role, setRole] = useState<UserRole>('DEVELOPER');

  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [successMessage, setSuccessMessage] = useState<string | null>(null);

  const { setAuth } = useAuthStore();
  const navigate = useNavigate();

  const extractErrorMessage = (detail: any): string => {
    if (!detail) return 'An error occurred during authentication.';
    if (typeof detail === 'string') return detail;
    if (Array.isArray(detail)) {
      return detail
        .map((d: any) => {
          if (typeof d === 'string') return d;
          if (typeof d === 'object' && d !== null) {
            return d.msg || d.message || JSON.stringify(d);
          }
          return String(d);
        })
        .join(', ');
    }
    if (typeof detail === 'object' && detail !== null) {
      return detail.message || detail.msg || JSON.stringify(detail);
    }
    return String(detail);
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError(null);
    setSuccessMessage(null);

    try {
      if (isRegister) {
        // Enforce password complexity criteria
        const hasMinLen = password.length >= 8;
        const hasUpper = /[A-Z]/.test(password);
        const hasLower = /[a-z]/.test(password);
        const hasNum = /\d/.test(password);
        const hasSpecial = /[!@#$%^&*()_+\-=\[\]{};':"\\|,.<>\/?~` ]/.test(password);

        if (!hasMinLen || !hasUpper || !hasLower || !hasNum || !hasSpecial) {
          setError('Password must be at least 8 characters and contain a mix of uppercase, lowercase, numbers, and special characters (!@#$%^&*).');
          setLoading(false);
          return;
        }

        // Register Flow - Account created as pending admin approval
        await api.post('/auth/register', {
          email,
          password,
          full_name: fullName,
          role,
        });

        setIsRegister(false);
        setSuccessMessage('Registration submitted successfully! Your account is pending administrator approval. You can log in once an admin activates your account.');
      } else {
        // Login Flow
        const loginRes = await api.post('/auth/login', { email, password });
        setAuth(loginRes.data.user, loginRes.data.access_token);
        navigate('/');
      }
    } catch (err: any) {
      setError(extractErrorMessage(err.response?.data?.detail));
    } finally {
      setLoading(false);
    }
  };

  const handleQuickLogin = async (presetEmail: string) => {
    setEmail(presetEmail);
    setPassword('Password123!');
    setLoading(true);
    setError(null);
    try {
      const loginRes = await api.post('/auth/login', { email: presetEmail, password: 'Password123!' });
      setAuth(loginRes.data.user, loginRes.data.access_token);
      navigate('/');
    } catch (err: any) {
      setError(extractErrorMessage(err.response?.data?.detail));
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-app flex items-center justify-center p-4 selection:bg-brand selection:text-on-brand relative overflow-hidden transition-colors duration-150">
      {/* Subtle background ambient accents */}
      <div className="absolute top-1/4 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[30rem] h-[30rem] bg-brand/5 rounded-full blur-3xl pointer-events-none" />
      <div className="absolute bottom-1/4 left-1/3 w-72 h-72 bg-secondaryAccent/5 rounded-full blur-3xl pointer-events-none" />

      <div className="relative w-full max-w-md glass-restrained rounded-3xl p-8 border border-border-card shadow-tactile space-y-6 z-10 before:absolute before:inset-x-8 before:top-0 before:h-[2px] before:bg-gradient-to-r before:from-transparent before:via-brand before:to-transparent before:opacity-70">
        {/* Header */}
        <div className="text-center space-y-3">
          <div className="flex justify-center mb-1">
            <img
              src="/astra-logo.svg"
              alt="ASTRA - Automated Software Testing"
              className="h-14 w-auto object-contain dark:hidden drop-shadow-sm"
            />
            <img
              src="/astra-logo-dark.svg"
              alt="ASTRA - Automated Software Testing"
              className="h-14 w-auto object-contain hidden dark:block drop-shadow-sm"
            />
          </div>
          <p className="text-xs text-secondary tracking-tight">
            {isRegister ? 'Enroll your credentials to manage software pipelines' : 'Authenticate to access the autonomous quality cockpit'}
          </p>
        </div>

        {/* Tab Toggle (Recessed Tactile Well) */}
        <div className="grid grid-cols-2 p-1 tactile-well text-xs font-semibold">
          <button
            type="button"
            onClick={() => { setIsRegister(false); setError(null); }}
            className={`py-2 rounded-lg transition-all ${!isRegister ? 'bg-brand text-on-brand shadow-tactile-sm relative before:absolute before:inset-x-0 before:top-0 before:h-px before:bg-white/25 before:rounded-t-lg' : 'text-secondary hover:text-primary'}`}
          >
            Sign In
          </button>
          <button
            type="button"
            onClick={() => { setIsRegister(true); setError(null); }}
            className={`py-2 rounded-lg transition-all ${isRegister ? 'bg-brand text-on-brand shadow-tactile-sm relative before:absolute before:inset-x-0 before:top-0 before:h-px before:bg-white/25 before:rounded-t-lg' : 'text-secondary hover:text-primary'}`}
          >
            Register
          </button>
        </div>

        {/* 3 Quick Login Buttons for Testing Phase */}
        {!isRegister && (
          <div className="p-3.5 rounded-2xl tactile-well space-y-2.5">
            <div className="flex items-center justify-between">
              <span className="text-[10px] font-bold uppercase tracking-wider text-muted flex items-center gap-1.5">
                <Sparkles className="w-3.5 h-3.5 text-brand" />
                Quick Login &bull; Testing Phase
              </span>
              <span className="text-[10px] text-muted font-mono bg-card px-2 py-0.5 rounded-md border border-border-card shadow-tactile-sm">
                1-Click Auth
              </span>
            </div>
            <div className="grid grid-cols-3 gap-2">
              {/* 1. Admin Quick Login */}
              <button
                type="button"
                disabled={loading}
                onClick={() => handleQuickLogin('admin@astra.local')}
                className="group relative flex flex-col items-center justify-center p-2.5 rounded-xl bg-card border border-rose-500/25 hover:border-rose-500 hover:bg-rose-500/10 text-primary transition-all duration-150 shadow-tactile-sm active:translate-y-px active:shadow-tactile-pressed disabled:opacity-50 overflow-hidden before:absolute before:inset-x-0 before:top-0 before:h-px before:bg-white/20"
                title="Quick login as System Administrator (admin@astra.local)"
              >
                <div className="w-8 h-8 rounded-lg bg-rose-500/15 text-rose-500 flex items-center justify-center mb-1 group-hover:scale-105 transition-transform shadow-inner">
                  <Shield className="w-4 h-4" />
                </div>
                <span className="text-xs font-bold text-rose-600 dark:text-rose-400">Admin</span>
                <span className="text-[9px] text-muted font-mono truncate max-w-full">admin@</span>
              </button>

              {/* 2. Tester Quick Login */}
              <button
                type="button"
                disabled={loading}
                onClick={() => handleQuickLogin('tester@astra.local')}
                className="group relative flex flex-col items-center justify-center p-2.5 rounded-xl bg-card border border-emerald-500/25 hover:border-emerald-500 hover:bg-emerald-500/10 text-primary transition-all duration-150 shadow-tactile-sm active:translate-y-px active:shadow-tactile-pressed disabled:opacity-50 overflow-hidden before:absolute before:inset-x-0 before:top-0 before:h-px before:bg-white/20"
                title="Quick login as Quality Assurance Tester (tester@astra.local)"
              >
                <div className="w-8 h-8 rounded-lg bg-emerald-500/15 text-emerald-500 flex items-center justify-center mb-1 group-hover:scale-105 transition-transform shadow-inner">
                  <FlaskConical className="w-4 h-4" />
                </div>
                <span className="text-xs font-bold text-emerald-600 dark:text-emerald-400">Tester</span>
                <span className="text-[9px] text-muted font-mono truncate max-w-full">tester@</span>
              </button>

              {/* 3. Developer Quick Login */}
              <button
                type="button"
                disabled={loading}
                onClick={() => handleQuickLogin('dev@astra.local')}
                className="group relative flex flex-col items-center justify-center p-2.5 rounded-xl bg-card border border-sky-500/25 hover:border-sky-500 hover:bg-sky-500/10 text-primary transition-all duration-150 shadow-tactile-sm active:translate-y-px active:shadow-tactile-pressed disabled:opacity-50 overflow-hidden before:absolute before:inset-x-0 before:top-0 before:h-px before:bg-white/20"
                title="Quick login as Software Developer (dev@astra.local)"
              >
                <div className="w-8 h-8 rounded-lg bg-sky-500/15 text-sky-500 flex items-center justify-center mb-1 group-hover:scale-105 transition-transform shadow-inner">
                  <Code2 className="w-4 h-4" />
                </div>
                <span className="text-xs font-bold text-sky-600 dark:text-sky-400">Developer</span>
                <span className="text-[9px] text-muted font-mono truncate max-w-full">dev@</span>
              </button>
            </div>
          </div>
        )}

        {/* Success / Pending Approval Notification */}
        {successMessage && (
          <div className="p-3.5 rounded-xl bg-emerald-500/10 border border-emerald-500/30 text-emerald-400 text-xs font-medium flex items-start gap-2.5">
            <CheckCircle className="w-4 h-4 shrink-0 mt-0.5" />
            <span>{successMessage}</span>
          </div>
        )}

        {/* Error Notification */}
        {error && (
          <div className="p-3 rounded-xl bg-status-failed-bg border border-status-failed/30 text-status-failed text-xs font-medium">
            {typeof error === 'string' ? error : JSON.stringify(error)}
          </div>
        )}

        {/* Auth Form */}
        <form onSubmit={handleSubmit} className="space-y-4">
          {isRegister && (
            <Input
              label="Full Name"
              type="text"
              placeholder="Jane Doe"
              value={fullName}
              onChange={(e) => setFullName(e.target.value)}
              leftIcon={<UserIcon className="w-4 h-4" />}
              required
            />
          )}

          <Input
            label="Email Address"
            type="email"
            placeholder="developer@company.com"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            leftIcon={<Mail className="w-4 h-4" />}
            required
          />

          <Input
            label="Password"
            type="password"
            placeholder="••••••••••••"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            leftIcon={<Lock className="w-4 h-4" />}
            required
          />

          {isRegister && (
            <p className="text-[11px] text-muted -mt-2 leading-tight">
              Password must be at least 8 characters and include uppercase, lowercase, numbers, and special characters (!@#$%^&*).
            </p>
          )}

          {isRegister && (
            <div className="space-y-1.5">
              <label className="block text-xs font-semibold text-secondary">
                Workspace Role
              </label>
              <div className="relative">
                <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none text-muted">
                  <Shield className="w-4 h-4" />
                </div>
                <select
                  value={role}
                  onChange={(e) => setRole(e.target.value as UserRole)}
                  className="w-full h-10 bg-field text-primary text-sm rounded-lg border border-border-field hover:border-brand focus:ring-2 focus:ring-brand focus:ring-offset-2 focus:ring-offset-card pl-10 pr-3.5 outline-none transition-colors"
                >
                  <option value="DEVELOPER">Developer (Collaborate & Patch Bugs)</option>
                  <option value="TESTER">QA Tester (Trigger & Review Automated Tests)</option>
                  <option value="VIEWER">Viewer (Inspect Reports & Defect Logs)</option>
                </select>
              </div>
              <p className="text-[10px] text-muted">
                Note: Administrator accounts cannot be self-requested and require direct leadership provisioning.
              </p>
            </div>
          )}

          <Button
            type="submit"
            variant="primary"
            className="w-full py-3 h-11"
            isLoading={loading}
            rightIcon={<ArrowRight className="w-4 h-4" />}
          >
            {isRegister ? 'Create Account' : 'Authenticate Console'}
          </Button>
        </form>

        <div className="text-center text-xs text-muted">
          ASTRA Automated Software Quality Engine &copy; 2026
        </div>
      </div>
    </div>
  );
};
