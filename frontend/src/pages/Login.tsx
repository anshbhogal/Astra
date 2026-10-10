import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Lock, Mail, User as UserIcon, Shield, ArrowRight, Sparkles } from 'lucide-react';
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

    try {
      if (isRegister) {
        // Register Flow
        await api.post('/auth/register', {
          email,
          password,
          full_name: fullName,
          role,
        });

        // Auto Login after registration
        const loginRes = await api.post('/auth/login', { email, password });
        setAuth(loginRes.data.user, loginRes.data.access_token);
      } else {
        // Login Flow
        const loginRes = await api.post('/auth/login', { email, password });
        setAuth(loginRes.data.user, loginRes.data.access_token);
      }
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
      <div className="absolute top-1/4 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[32rem] h-[32rem] bg-brand/10 rounded-full blur-3xl pointer-events-none" />
      <div className="absolute bottom-1/4 left-1/3 w-80 h-80 bg-secondaryAccent/10 rounded-full blur-3xl pointer-events-none" />

      <div className="relative w-full max-w-md bg-card rounded-2xl p-8 border border-border-card shadow-card space-y-6">
        {/* Header */}
        <div className="text-center space-y-2">
          <div className="inline-flex w-12 h-12 rounded-2xl bg-brand text-on-brand items-center justify-center shadow-sm mb-2">
            <Sparkles className="w-6 h-6" />
          </div>
          <h1 className="text-2xl font-bold text-primary tracking-tight">ASTRA QA Cockpit</h1>
          <p className="text-xs text-secondary">
            {isRegister ? 'Enroll your credentials to manage software pipelines' : 'Authenticate to access the autonomous quality cockpit'}
          </p>
        </div>

        {/* Tab Toggle */}
        <div className="grid grid-cols-2 p-1 bg-field rounded-xl border border-border-card text-xs font-semibold">
          <button
            type="button"
            onClick={() => { setIsRegister(false); setError(null); }}
            className={`py-2 rounded-lg transition-all ${!isRegister ? 'bg-brand text-on-brand shadow-sm' : 'text-secondary hover:text-primary'}`}
          >
            Sign In
          </button>
          <button
            type="button"
            onClick={() => { setIsRegister(true); setError(null); }}
            className={`py-2 rounded-lg transition-all ${isRegister ? 'bg-brand text-on-brand shadow-sm' : 'text-secondary hover:text-primary'}`}
          >
            Register
          </button>
        </div>

        {/* Quick Test Credential Presets */}
        {!isRegister && (
          <div className="p-3 rounded-xl bg-field border border-border-card space-y-2">
            <p className="text-[10px] font-bold uppercase tracking-wider text-muted">Quick Test Presets</p>
            <div className="flex flex-wrap gap-1.5">
              <button
                type="button"
                onClick={() => { setEmail('admin@astra.local'); setPassword('Admin123!'); }}
                className="px-2.5 py-1 rounded-lg bg-status-failed-bg text-status-failed border border-status-failed/30 text-[11px] font-semibold hover:opacity-85 transition-opacity"
              >
                Admin
              </button>
              <button
                type="button"
                onClick={() => { setEmail('dev@astra.local'); setPassword('Password123!'); }}
                className="px-2.5 py-1 rounded-lg bg-brand/10 text-brand border border-brand/30 text-[11px] font-semibold hover:bg-brand/20 transition-colors"
              >
                Developer
              </button>
              <button
                type="button"
                onClick={() => { setEmail('tester@astra.local'); setPassword('Password123!'); }}
                className="px-2.5 py-1 rounded-lg bg-status-flaky-bg text-status-flaky border border-status-flaky/30 text-[11px] font-semibold hover:opacity-85 transition-opacity"
              >
                Tester
              </button>
              <button
                type="button"
                onClick={() => { setEmail('viewer@astra.local'); setPassword('Password123!'); }}
                className="px-2.5 py-1 rounded-lg bg-card text-secondary border border-border-field text-[11px] font-semibold hover:text-primary transition-colors"
              >
                Viewer
              </button>
            </div>
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
                  <option value="DEVELOPER">Developer (Create & Manage Projects)</option>
                  <option value="TESTER">QA Tester (Trigger & Run Tests)</option>
                  <option value="VIEWER">Viewer (Read Only Access)</option>
                </select>
              </div>
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
