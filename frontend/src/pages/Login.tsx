import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Terminal, Lock, Mail, User as UserIcon, Shield, ArrowRight, Zap } from 'lucide-react';
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
    <div className="min-h-screen bg-base flex items-center justify-center p-4 selection:bg-brand selection:text-white relative overflow-hidden transition-colors duration-200">
      {/* Background glowing gradients */}
      <div className="absolute top-1/4 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[32rem] h-[32rem] bg-brand/15 rounded-full blur-3xl pointer-events-none" />
      <div className="absolute bottom-1/4 left-1/3 w-80 h-80 bg-accent/10 rounded-full blur-3xl pointer-events-none" />

      <div className="relative w-full max-w-md glass-card rounded-2xl p-8 border border-border shadow-2xl space-y-6">
        {/* Header */}
        <div className="text-center space-y-2">
          <div className="inline-flex w-12 h-12 rounded-2xl bg-brand/15 border border-brand/30 text-brand items-center justify-center shadow-brand-glow mb-2">
            <Zap className="w-6 h-6 text-accent" />
          </div>
          <h1 className="text-2xl font-extrabold text-primary tracking-tight">ASTRA Mission Control</h1>
          <p className="text-xs text-secondary">
            {isRegister ? 'Enroll your credentials to manage software pipelines' : 'Authenticate to access the autonomous quality cockpit'}
          </p>
        </div>

        {/* Tab Toggle */}
        <div className="grid grid-cols-2 p-1 bg-surface rounded-xl border border-border text-xs font-semibold">
          <button
            type="button"
            onClick={() => { setIsRegister(false); setError(null); }}
            className={`py-2 rounded-lg transition-all ${!isRegister ? 'bg-brand text-white shadow-brand-glow' : 'text-secondary hover:text-primary'}`}
          >
            Sign In
          </button>
          <button
            type="button"
            onClick={() => { setIsRegister(true); setError(null); }}
            className={`py-2 rounded-lg transition-all ${isRegister ? 'bg-brand text-white shadow-brand-glow' : 'text-secondary hover:text-primary'}`}
          >
            Register
          </button>
        </div>

        {/* Quick Test Credential Presets */}
        {!isRegister && (
          <div className="p-3 rounded-xl bg-surface border border-border space-y-2">
            <p className="text-[10px] font-bold uppercase tracking-wider text-muted">Quick Test Presets</p>
            <div className="flex flex-wrap gap-1.5">
              <button
                type="button"
                onClick={() => { setEmail('admin@astra.local'); setPassword('Admin123!'); }}
                className="px-2.5 py-1 rounded-lg bg-status-failed-bg text-status-failed border border-status-failed-border text-[11px] font-semibold hover:opacity-80 transition-colors"
              >
                Admin
              </button>
              <button
                type="button"
                onClick={() => { setEmail('dev@astra.local'); setPassword('Password123!'); }}
                className="px-2.5 py-1 rounded-lg bg-brand/10 text-brand border border-brand/20 text-[11px] font-semibold hover:bg-brand/20 transition-colors"
              >
                Developer
              </button>
              <button
                type="button"
                onClick={() => { setEmail('tester@astra.local'); setPassword('Password123!'); }}
                className="px-2.5 py-1 rounded-lg bg-status-flaky-bg text-status-flaky border border-status-flaky-border text-[11px] font-semibold hover:opacity-80 transition-colors"
              >
                Tester
              </button>
              <button
                type="button"
                onClick={() => { setEmail('viewer@astra.local'); setPassword('Password123!'); }}
                className="px-2.5 py-1 rounded-lg bg-raised text-muted border border-border text-[11px] font-semibold hover:text-primary transition-colors"
              >
                Viewer
              </button>
            </div>
          </div>
        )}

        {/* Error Notification */}
        {error && (
          <div className="p-3 rounded-xl bg-status-failed-bg border border-status-failed-border text-status-failed text-xs font-medium">
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
              <label className="block text-xs font-semibold uppercase tracking-wider text-secondary">
                Workspace Role
              </label>
              <div className="relative">
                <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none text-muted">
                  <Shield className="w-4 h-4" />
                </div>
                <select
                  value={role}
                  onChange={(e) => setRole(e.target.value as UserRole)}
                  className="w-full bg-surface text-primary text-sm rounded-lg border border-border hover:border-brand/40 focus:ring-2 focus:ring-brand pl-10 pr-3.5 py-2.5 outline-none transition-colors"
                >
                  <option value="DEVELOPER">Developer (Create & Manage Projects)</option>
                  <option value="TESTER">QA Tester (Trigger & Run Tests)</option>
                  <option value="VIEWER">Viewer (Read Only Access)</option>
                </select>
              </div>
            </div>
          )}

          {/* Single Volt Lime Highlight CTA on this page */}
          <Button
            type="submit"
            variant="accent"
            className="w-full py-3"
            isLoading={loading}
            rightIcon={<ArrowRight className="w-4 h-4" />}
          >
            {isRegister ? 'Create Account' : 'Authenticate Console'}
          </Button>
        </form>

        <div className="text-center text-[11px] text-muted font-mono">
          ASTRA Automated Software Quality Engine &copy; 2026
        </div>
      </div>
    </div>
  );
};
