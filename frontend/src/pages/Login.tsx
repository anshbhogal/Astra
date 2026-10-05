import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Terminal, Lock, Mail, User as UserIcon, Shield, ArrowRight } from 'lucide-react';
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
    <div className="min-h-screen bg-slate-950 flex items-center justify-center p-4 selection:bg-indigo-500 selection:text-white">
      {/* Background glowing gradients */}
      <div className="absolute top-1/4 left-1/2 -translate-x-1/2 -translate-y-1/2 w-96 h-96 bg-indigo-600/20 rounded-full blur-3xl pointer-events-none" />
      <div className="absolute bottom-1/4 left-1/3 w-80 h-80 bg-blue-600/15 rounded-full blur-3xl pointer-events-none" />

      <div className="relative w-full max-w-md glass-card rounded-2xl p-8 border border-slate-800 shadow-2xl space-y-6">
        {/* Header */}
        <div className="text-center space-y-2">
          <div className="inline-flex w-12 h-12 rounded-2xl bg-gradient-to-tr from-blue-600 to-indigo-600 items-center justify-center shadow-lg shadow-indigo-500/30 mb-2">
            <Terminal className="w-6 h-6 text-white" />
          </div>
          <h1 className="text-2xl font-extrabold text-white tracking-tight">ASTRA Quality Platform</h1>
          <p className="text-xs text-slate-400">
            {isRegister ? 'Create an account to start managing projects' : 'Sign in to access your testing workspace'}
          </p>
        </div>

        {/* Tab Toggle */}
        <div className="grid grid-cols-2 p-1 bg-slate-900/90 rounded-xl border border-slate-800 text-xs font-semibold">
          <button
            type="button"
            onClick={() => { setIsRegister(false); setError(null); }}
            className={`py-2 rounded-lg transition-all ${!isRegister ? 'bg-indigo-600 text-white shadow' : 'text-slate-400 hover:text-slate-200'}`}
          >
            Sign In
          </button>
          <button
            type="button"
            onClick={() => { setIsRegister(true); setError(null); }}
            className={`py-2 rounded-lg transition-all ${isRegister ? 'bg-indigo-600 text-white shadow' : 'text-slate-400 hover:text-slate-200'}`}
          >
            Register
          </button>
        </div>

        {/* Quick Test Credential Presets */}
        {!isRegister && (
          <div className="p-3 rounded-xl bg-slate-900/90 border border-slate-800 space-y-2">
            <p className="text-[10px] font-bold uppercase tracking-wider text-slate-400">Quick Test Credentials</p>
            <div className="flex flex-wrap gap-1.5">
              <button
                type="button"
                onClick={() => { setEmail('admin@astra.local'); setPassword('Password123!'); }}
                className="px-2.5 py-1 rounded-lg bg-rose-500/10 text-rose-400 border border-rose-500/20 text-[11px] font-semibold hover:bg-rose-500/20 transition-colors"
              >
                Admin
              </button>
              <button
                type="button"
                onClick={() => { setEmail('dev@astra.local'); setPassword('Password123!'); }}
                className="px-2.5 py-1 rounded-lg bg-indigo-500/10 text-indigo-400 border border-indigo-500/20 text-[11px] font-semibold hover:bg-indigo-500/20 transition-colors"
              >
                Developer
              </button>
              <button
                type="button"
                onClick={() => { setEmail('tester@astra.local'); setPassword('Password123!'); }}
                className="px-2.5 py-1 rounded-lg bg-amber-500/10 text-amber-400 border border-amber-500/20 text-[11px] font-semibold hover:bg-amber-500/20 transition-colors"
              >
                Tester
              </button>
              <button
                type="button"
                onClick={() => { setEmail('viewer@astra.local'); setPassword('Password123!'); }}
                className="px-2.5 py-1 rounded-lg bg-slate-500/10 text-slate-400 border border-slate-500/20 text-[11px] font-semibold hover:bg-slate-500/20 transition-colors"
              >
                Viewer
              </button>
            </div>
          </div>
        )}

        {/* Error Notification */}
        {error && (
          <div className="p-3 rounded-xl bg-rose-500/10 border border-rose-500/20 text-rose-400 text-xs font-medium">
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
              <label className="block text-xs font-semibold uppercase tracking-wider text-slate-400">
                Workspace Role
              </label>
              <div className="relative">
                <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none text-slate-500">
                  <Shield className="w-4 h-4" />
                </div>
                <select
                  value={role}
                  onChange={(e) => setRole(e.target.value as UserRole)}
                  className="w-full bg-slate-900/80 text-slate-100 text-sm rounded-lg border border-slate-800 hover:border-slate-700 focus:ring-2 focus:ring-indigo-500 pl-10 pr-3.5 py-2.5 outline-none"
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
            className="w-full py-3"
            isLoading={loading}
            rightIcon={<ArrowRight className="w-4 h-4" />}
          >
            {isRegister ? 'Create Account' : 'Authenticate'}
          </Button>
        </form>

        <div className="text-center text-[11px] text-slate-500">
          ASTRA Automated Software Quality Engine &copy; 2026
        </div>
      </div>
    </div>
  );
};
