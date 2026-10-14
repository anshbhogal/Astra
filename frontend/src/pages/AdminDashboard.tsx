import React, { useEffect, useState } from 'react';
import {
  Shield,
  Users,
  UserPlus,
  CheckCircle,
  XCircle,
  FolderGit2,
  AlertCircle,
  Clock,
  Trash2,
  Check,
  Search,
  Filter,
  RefreshCw,
  Terminal,
  KeyRound,
  Eye,
  Code2,
  FlaskConical,
} from 'lucide-react';
import { api } from '../services/api';
import { Button } from '../components/common/Button';
import { Input } from '../components/common/Input';
import { Modal } from '../components/common/Modal';

interface UserItem {
  id: string;
  email: string;
  full_name: string;
  role: 'ADMIN' | 'DEVELOPER' | 'TESTER' | 'VIEWER';
  is_active: boolean;
  is_approved: boolean;
  assigned_project_count: number;
  assigned_projects: Array<{ id: string; name: string; role: string }>;
  created_at: string;
}

interface ProjectSummary {
  id: string;
  name: string;
  repository_url: string;
  language_framework: string;
}

export const AdminDashboard: React.FC = () => {
  const [users, setUsers] = useState<UserItem[]>([]);
  const [projects, setProjects] = useState<ProjectSummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [activeTab, setActiveTab] = useState<'users' | 'approvals' | 'teams'>('users');
  const [search, setSearch] = useState('');
  const [roleFilter, setRoleFilter] = useState<string>('ALL');

  // Modal State: Generate User
  const [isGenerateModalOpen, setIsGenerateModalOpen] = useState(false);
  const [genFullName, setGenFullName] = useState('');
  const [genEmail, setGenEmail] = useState('');
  const [genPassword, setGenPassword] = useState('');
  const [genRole, setGenRole] = useState<'DEVELOPER' | 'TESTER' | 'VIEWER'>('TESTER');
  const [genSelectedProjects, setGenSelectedProjects] = useState<string[]>([]);
  const [submittingUser, setSubmittingUser] = useState(false);
  const [modalError, setModalError] = useState<string | null>(null);

  // Modal State: Assign Team to Project
  const [isAssignModalOpen, setIsAssignModalOpen] = useState(false);
  const [selectedProject, setSelectedProject] = useState<ProjectSummary | null>(null);
  const [teamMembers, setTeamMembers] = useState<Array<{ user_id: string; role: 'DEVELOPER' | 'TESTER' | 'VIEWER' }>>([]);
  const [submittingTeam, setSubmittingTeam] = useState(false);

  useEffect(() => {
    fetchData();
  }, []);

  const fetchData = async () => {
    setLoading(true);
    try {
      const [usersRes, projsRes] = await Promise.all([
        api.get('/admin/users'),
        api.get('/projects/?limit=100'),
      ]);
      setUsers(usersRes.data || []);
      setProjects(projsRes.data.items || []);
    } catch (err) {
      console.error('Failed to fetch admin data', err);
    } finally {
      setLoading(false);
    }
  };

  const handleGenerateUser = async (e: React.FormEvent) => {
    e.preventDefault();
    setSubmittingUser(true);
    setModalError(null);
    try {
      await api.post('/admin/users', {
        full_name: genFullName,
        email: genEmail,
        password: genPassword,
        role: genRole,
        project_ids: genSelectedProjects,
      });
      setIsGenerateModalOpen(false);
      setGenFullName('');
      setGenEmail('');
      setGenPassword('');
      setGenRole('TESTER');
      setGenSelectedProjects([]);
      fetchData();
    } catch (err: any) {
      setModalError(err.response?.data?.detail || 'Failed to provision user account.');
    } finally {
      setSubmittingUser(false);
    }
  };

  const handleApproveUser = async (userId: string, targetRole: 'DEVELOPER' | 'TESTER' | 'VIEWER') => {
    try {
      await api.post(`/admin/users/${userId}/approve`, { role: targetRole });
      fetchData();
    } catch (err) {
      console.error('Failed to approve user', err);
    }
  };

  const handleRejectUser = async (userId: string) => {
    if (!window.confirm('Are you sure you want to reject and delete this registration?')) return;
    try {
      await api.post(`/admin/users/${userId}/reject`);
      fetchData();
    } catch (err) {
      console.error('Failed to reject user', err);
    }
  };

  const handleDeleteUser = async (userId: string) => {
    if (!window.confirm('Are you sure you want to permanently delete this user?')) return;
    try {
      await api.delete(`/admin/users/${userId}`);
      fetchData();
    } catch (err) {
      console.error('Failed to delete user', err);
    }
  };

  const openAssignModal = async (project: ProjectSummary) => {
    setSelectedProject(project);
    try {
      const res = await api.get(`/projects/${project.id}/members`);
      setTeamMembers(
        (res.data || []).map((m: any) => ({
          user_id: m.user_id,
          role: m.role,
        }))
      );
    } catch {
      setTeamMembers([]);
    }
    setIsAssignModalOpen(true);
  };

  const handleSaveTeam = async () => {
    if (!selectedProject) return;
    setSubmittingTeam(true);
    try {
      await api.put(`/projects/${selectedProject.id}/members`, {
        members: teamMembers,
      });
      setIsAssignModalOpen(false);
      fetchData();
    } catch (err) {
      console.error('Failed to update project team', err);
    } finally {
      setSubmittingTeam(false);
    }
  };

  const toggleUserInTeam = (userId: string, role: 'DEVELOPER' | 'TESTER' | 'VIEWER') => {
    const existingIndex = teamMembers.findIndex((m) => m.user_id === userId);
    if (existingIndex > -1) {
      if (teamMembers[existingIndex].role === role) {
        // Remove if clicking same role
        setTeamMembers(teamMembers.filter((m) => m.user_id !== userId));
      } else {
        // Change role
        const updated = [...teamMembers];
        updated[existingIndex].role = role;
        setTeamMembers(updated);
      }
    } else {
      // Add with role
      setTeamMembers([...teamMembers, { user_id: userId, role }]);
    }
  };

  const pendingUsers = users.filter((u) => !u.is_approved && u.role !== 'ADMIN');
  const filteredUsers = users.filter((u) => {
    const matchSearch =
      u.full_name.toLowerCase().includes(search.toLowerCase()) ||
      u.email.toLowerCase().includes(search.toLowerCase());
    const matchRole = roleFilter === 'ALL' || u.role === roleFilter;
    return matchSearch && matchRole;
  });

  const getRoleBadge = (role: string) => {
    switch (role) {
      case 'ADMIN':
        return (
          <span className="px-2.5 py-0.5 rounded-full text-xs font-bold bg-purple-500/15 text-purple-400 border border-purple-500/30 flex items-center gap-1.5 w-fit">
            <Shield className="w-3 h-3" /> Admin
          </span>
        );
      case 'TESTER':
        return (
          <span className="px-2.5 py-0.5 rounded-full text-xs font-bold bg-emerald-500/15 text-emerald-400 border border-emerald-500/30 flex items-center gap-1.5 w-fit">
            <FlaskConical className="w-3 h-3" /> Tester
          </span>
        );
      case 'DEVELOPER':
        return (
          <span className="px-2.5 py-0.5 rounded-full text-xs font-bold bg-sky-500/15 text-sky-400 border border-sky-500/30 flex items-center gap-1.5 w-fit">
            <Code2 className="w-3 h-3" /> Developer
          </span>
        );
      case 'VIEWER':
        return (
          <span className="px-2.5 py-0.5 rounded-full text-xs font-bold bg-amber-500/15 text-amber-700 dark:text-amber-400 border border-amber-500/30 flex items-center gap-1.5 w-fit">
            <Eye className="w-3 h-3" /> Viewer
          </span>
        );
      default:
        return <span className="text-xs text-muted">{role}</span>;
    }
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-3">
            <div className="w-9 h-9 rounded-xl bg-purple-500/15 border border-purple-500/30 flex items-center justify-center text-purple-400">
              <Shield className="w-5 h-5" />
            </div>
            <h1 className="text-2xl font-bold text-primary tracking-tight">Admin Governance Cockpit</h1>
          </div>
          <p className="text-xs text-secondary mt-1">
            Provision user credentials, approve self-registered engineers, and orchestrate repository groups for Testers, Developers, and Viewers.
          </p>
        </div>

        <div className="flex items-center gap-3">
          <Button
            variant="secondary"
            onClick={fetchData}
            isLoading={loading}
            leftIcon={<RefreshCw className="w-4 h-4" />}
          >
            Refresh
          </Button>
          <Button
            variant="primary"
            onClick={() => setIsGenerateModalOpen(true)}
            leftIcon={<UserPlus className="w-4 h-4" />}
          >
            Generate User ID
          </Button>
        </div>
      </div>

      {/* KPI Overview Chips */}
      <div className="grid grid-cols-2 md:grid-cols-5 gap-3">
        <div className="p-4 rounded-xl bg-card border border-border-card shadow-card space-y-1">
          <span className="text-[10px] font-semibold text-muted uppercase tracking-wider">Total Users</span>
          <div className="text-xl font-bold font-mono text-primary">{users.length}</div>
        </div>
        <div className="p-4 rounded-xl bg-card border border-border-card shadow-card space-y-1">
          <span className="text-[10px] font-semibold text-muted uppercase tracking-wider">Pending Approvals</span>
          <div className={`text-xl font-bold font-mono ${pendingUsers.length > 0 ? 'text-amber-600 dark:text-amber-400' : 'text-emerald-500'}`}>
            {pendingUsers.length}
          </div>
        </div>
        <div className="p-4 rounded-xl bg-card border border-border-card shadow-card space-y-1">
          <span className="text-[10px] font-semibold text-muted uppercase tracking-wider">Testers</span>
          <div className="text-xl font-bold font-mono text-emerald-400">
            {users.filter((u) => u.role === 'TESTER').length}
          </div>
        </div>
        <div className="p-4 rounded-xl bg-card border border-border-card shadow-card space-y-1">
          <span className="text-[10px] font-semibold text-muted uppercase tracking-wider">Developers</span>
          <div className="text-xl font-bold font-mono text-sky-400">
            {users.filter((u) => u.role === 'DEVELOPER').length}
          </div>
        </div>
        <div className="p-4 rounded-xl bg-card border border-border-card shadow-card space-y-1">
          <span className="text-[10px] font-semibold text-muted uppercase tracking-wider">Repositories</span>
          <div className="text-xl font-bold font-mono text-primary">{projects.length}</div>
        </div>
      </div>

      {/* Pending Approvals Alert Banner */}
      {pendingUsers.length > 0 && activeTab !== 'approvals' && (
        <div className="p-3.5 px-4 rounded-xl bg-amber-500/10 dark:bg-amber-950/30 border border-amber-500/30 dark:border-amber-700/50 flex items-center justify-between gap-4">
          <div className="flex items-center gap-3">
            <Clock className="w-5 h-5 text-amber-600 dark:text-amber-400 shrink-0" />
            <p className="text-sm font-semibold text-amber-900 dark:text-amber-200">
              {pendingUsers.length} New Self-Registered Account(s) Awaiting Approval
            </p>
          </div>
          <Button
            variant="secondary"
            size="sm"
            onClick={() => setActiveTab('approvals')}
          >
            Review Pending ({pendingUsers.length})
          </Button>
        </div>
      )}

      {/* Tab Navigation */}
      <div className="flex border-b border-border-card">
        <button
          onClick={() => setActiveTab('users')}
          className={`px-5 py-3 text-sm font-semibold border-b-2 flex items-center gap-2 transition-colors ${
            activeTab === 'users'
              ? 'border-brand text-brand'
              : 'border-transparent text-secondary hover:text-primary'
          }`}
        >
          <Users className="w-4 h-4" />
          User Directory ({users.length})
        </button>
        <button
          onClick={() => setActiveTab('approvals')}
          className={`px-5 py-3 text-sm font-semibold border-b-2 flex items-center gap-2 transition-colors ${
            activeTab === 'approvals'
              ? 'border-amber-400 text-amber-400'
              : 'border-transparent text-secondary hover:text-primary'
          }`}
        >
          <Clock className="w-4 h-4" />
          Pending Approvals
          {pendingUsers.length > 0 && (
            <span className="px-2 py-0.5 rounded-full text-[10px] font-bold bg-amber-500/20 text-amber-400">
              {pendingUsers.length}
            </span>
          )}
        </button>
        <button
          onClick={() => setActiveTab('teams')}
          className={`px-5 py-3 text-sm font-semibold border-b-2 flex items-center gap-2 transition-colors ${
            activeTab === 'teams'
              ? 'border-brand text-brand'
              : 'border-transparent text-secondary hover:text-primary'
          }`}
        >
          <FolderGit2 className="w-4 h-4" />
          Repository Teams & Assignments ({projects.length})
        </button>
      </div>

      {/* TAB 1: User Directory */}
      {activeTab === 'users' && (
        <div className="space-y-4">
          <div className="flex flex-col sm:flex-row items-center gap-3">
            <div className="relative flex-1 w-full">
              <Search className="w-4 h-4 absolute left-3.5 top-1/2 -translate-y-1/2 text-muted pointer-events-none" />
              <input
                type="text"
                placeholder="Search user by name or email..."
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                className="w-full bg-field border border-border-card rounded-xl pl-10 pr-4 py-2 text-sm text-primary placeholder-muted focus:outline-none focus:border-brand"
              />
            </div>
            <div className="flex items-center gap-2 w-full sm:w-auto">
              <Filter className="w-4 h-4 text-muted shrink-0" />
              <select
                value={roleFilter}
                onChange={(e) => setRoleFilter(e.target.value)}
                className="bg-field border border-border-card rounded-xl px-3 py-2 text-xs text-primary focus:outline-none focus:border-brand"
              >
                <option value="ALL">All Roles</option>
                <option value="ADMIN">Admin</option>
                <option value="TESTER">Tester</option>
                <option value="DEVELOPER">Developer</option>
                <option value="VIEWER">Viewer</option>
              </select>
            </div>
          </div>

          <div className="bg-card rounded-2xl border border-border-card shadow-card overflow-hidden">
            <div className="overflow-x-auto">
              <table className="w-full text-left text-xs">
                <thead>
                  <tr className="bg-field/50 border-b border-border-card text-muted uppercase font-mono text-[10px] tracking-wider">
                    <th className="py-3.5 px-4 font-semibold">User</th>
                    <th className="py-3.5 px-4 font-semibold">Role</th>
                    <th className="py-3.5 px-4 font-semibold">Status</th>
                    <th className="py-3.5 px-4 font-semibold">Assigned Repositories</th>
                    <th className="py-3.5 px-4 font-semibold">Registered</th>
                    <th className="py-3.5 px-4 font-semibold text-right">Actions</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-border-card">
                  {filteredUsers.length === 0 ? (
                    <tr>
                      <td colSpan={6} className="py-8 text-center text-muted">
                        No users match the search criteria.
                      </td>
                    </tr>
                  ) : (
                    filteredUsers.map((u) => (
                      <tr key={u.id} className="hover:bg-field/30 transition-colors">
                        <td className="py-3 px-4">
                          <div className="font-semibold text-primary">{u.full_name}</div>
                          <div className="text-[11px] text-muted font-mono">{u.email}</div>
                        </td>
                        <td className="py-3 px-4">{getRoleBadge(u.role)}</td>
                        <td className="py-3 px-4">
                          {u.is_approved ? (
                            <span className="px-2 py-0.5 rounded-full text-[10px] font-bold bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 border border-emerald-500/20">
                              Active & Approved
                            </span>
                          ) : (
                            <span className="px-2 py-0.5 rounded-full text-[10px] font-bold bg-amber-500/10 text-amber-700 dark:text-amber-400 border border-amber-500/20">
                              Pending Approval
                            </span>
                          )}
                        </td>
                        <td className="py-3 px-4">
                          {u.role === 'ADMIN' ? (
                            <span className="text-purple-400 font-semibold text-[11px]">All Repositories (Superadmin)</span>
                          ) : u.assigned_project_count === 0 ? (
                            <span className="text-muted italic">None assigned</span>
                          ) : (
                            <div className="flex flex-wrap gap-1">
                              {u.assigned_projects.map((p) => (
                                <span
                                  key={p.id}
                                  className="px-2 py-0.5 rounded bg-brand/10 text-brand text-[10px] font-mono border border-brand/20"
                                >
                                  {p.name}
                                </span>
                              ))}
                            </div>
                          )}
                        </td>
                        <td className="py-3 px-4 text-muted font-mono text-[11px]">
                          {new Date(u.created_at).toLocaleDateString()}
                        </td>
                        <td className="py-3 px-4 text-right">
                          {u.role !== 'ADMIN' && u.email !== 'admin@astra.local' && (
                            <button
                              onClick={() => handleDeleteUser(u.id)}
                              className="p-1.5 rounded-lg text-muted hover:text-rose-400 hover:bg-rose-500/10 transition-colors"
                              title="Delete user account"
                            >
                              <Trash2 className="w-4 h-4" />
                            </button>
                          )}
                        </td>
                      </tr>
                    ))
                  )}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      )}

      {/* TAB 2: Pending Approvals Queue */}
      {activeTab === 'approvals' && (
        <div className="space-y-4">
          {pendingUsers.length === 0 ? (
            <div className="p-12 text-center rounded-2xl bg-card border border-border-card shadow-card space-y-3">
              <CheckCircle className="w-10 h-10 text-emerald-400 mx-auto" />
              <h3 className="text-base font-bold text-primary">All Caught Up!</h3>
              <p className="text-xs text-secondary max-w-md mx-auto">
                There are no self-registered accounts pending administrator approval.
              </p>
            </div>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {pendingUsers.map((u) => (
                <div
                  key={u.id}
                  className="p-5 rounded-2xl bg-card border border-amber-500/30 shadow-card space-y-4"
                >
                  <div className="flex items-start justify-between">
                    <div>
                      <h3 className="text-base font-bold text-primary">{u.full_name}</h3>
                      <p className="text-xs font-mono text-muted">{u.email}</p>
                    </div>
                    <span className="px-2.5 py-1 rounded-full text-xs font-semibold bg-amber-500/15 text-amber-700 dark:text-amber-400 border border-amber-500/30">
                      Requested: {u.role}
                    </span>
                  </div>

                  <p className="text-xs text-secondary">
                    Registered on {new Date(u.created_at).toLocaleString()}. Select the approved role to grant platform access:
                  </p>

                  <div className="flex flex-wrap items-center gap-2 pt-2 border-t border-border-card">
                    <Button
                      variant="primary"
                      size="sm"
                      onClick={() => handleApproveUser(u.id, 'TESTER')}
                      leftIcon={<FlaskConical className="w-3.5 h-3.5" />}
                    >
                      Approve as Tester
                    </Button>
                    <Button
                      variant="secondary"
                      size="sm"
                      onClick={() => handleApproveUser(u.id, 'DEVELOPER')}
                      leftIcon={<Code2 className="w-3.5 h-3.5" />}
                    >
                      Approve as Developer
                    </Button>
                    <Button
                      variant="secondary"
                      size="sm"
                      onClick={() => handleApproveUser(u.id, 'VIEWER')}
                      leftIcon={<Eye className="w-3.5 h-3.5" />}
                    >
                      Approve as Viewer
                    </Button>
                    <button
                      onClick={() => handleRejectUser(u.id)}
                      className="px-3 py-1.5 rounded-lg text-xs font-semibold text-rose-400 hover:bg-rose-500/10 transition-colors ml-auto"
                    >
                      Reject
                    </button>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* TAB 3: Repository Teams & Assignments */}
      {activeTab === 'teams' && (
        <div className="space-y-4">
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {projects.map((p) => {
              // Find assigned members for this project
              const assignedMembers = users.filter((u) =>
                u.assigned_projects.some((ap) => ap.id === p.id)
              );
              const testers = assignedMembers.filter((u) => u.role === 'TESTER');
              const developers = assignedMembers.filter((u) => u.role === 'DEVELOPER');
              const viewers = assignedMembers.filter((u) => u.role === 'VIEWER');

              return (
                <div
                  key={p.id}
                  className="p-5 rounded-2xl bg-card border border-border-card shadow-card flex flex-col justify-between space-y-4"
                >
                  <div className="space-y-2">
                    <div className="flex items-center justify-between">
                      <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-brand/10 text-brand font-bold">
                        {p.language_framework}
                      </span>
                      <span className="text-xs text-muted font-mono">{assignedMembers.length} Members</span>
                    </div>
                    <h3 className="text-base font-bold text-primary truncate">{p.name}</h3>
                    <p className="text-xs text-secondary truncate font-mono">{p.repository_url}</p>
                  </div>

                  {/* Team Members Breakdown */}
                  <div className="space-y-2 pt-3 border-t border-border-card text-xs">
                    <div>
                      <span className="text-[10px] font-bold uppercase tracking-wider text-emerald-400 flex items-center gap-1">
                        <FlaskConical className="w-3 h-3" /> Testers ({testers.length}):
                      </span>
                      <p className="text-primary truncate mt-0.5">
                        {testers.length > 0 ? testers.map((t) => t.full_name).join(', ') : <span className="text-muted italic">None</span>}
                      </p>
                    </div>

                    <div>
                      <span className="text-[10px] font-bold uppercase tracking-wider text-sky-400 flex items-center gap-1">
                        <Code2 className="w-3 h-3" /> Developers ({developers.length}):
                      </span>
                      <p className="text-primary truncate mt-0.5">
                        {developers.length > 0 ? developers.map((d) => d.full_name).join(', ') : <span className="text-muted italic">None</span>}
                      </p>
                    </div>

                    <div>
                      <span className="text-[10px] font-bold uppercase tracking-wider text-amber-400 flex items-center gap-1">
                        <Eye className="w-3 h-3" /> Viewers ({viewers.length}):
                      </span>
                      <p className="text-primary truncate mt-0.5">
                        {viewers.length > 0 ? viewers.map((v) => v.full_name).join(', ') : <span className="text-muted italic">None</span>}
                      </p>
                    </div>
                  </div>

                  <Button
                    variant="secondary"
                    size="sm"
                    className="w-full mt-2"
                    onClick={() => openAssignModal(p)}
                  >
                    Configure Team
                  </Button>
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* MODAL 1: Generate User ID Directly */}
      <Modal
        isOpen={isGenerateModalOpen}
        onClose={() => setIsGenerateModalOpen(false)}
        title="Provision New User Account"
      >
        <form onSubmit={handleGenerateUser} className="space-y-4">
          <p className="text-xs text-secondary">
            Generate credentials directly for a Tester, Developer, or Viewer. This account is immediately activated.
          </p>

          {modalError && (
            <div className="p-3 rounded-xl bg-status-failed-bg text-status-failed border border-status-failed/30 text-xs">
              {modalError}
            </div>
          )}

          <Input
            label="Full Name"
            placeholder="e.g. Jane Doe"
            value={genFullName}
            onChange={(e) => setGenFullName(e.target.value)}
            required
          />

          <Input
            label="Email Address (Login ID)"
            type="email"
            placeholder="jane@company.com"
            value={genEmail}
            onChange={(e) => setGenEmail(e.target.value)}
            required
          />

          <Input
            label="Password"
            type="password"
            placeholder="Min. 6 characters"
            value={genPassword}
            onChange={(e) => setGenPassword(e.target.value)}
            required
          />

          <div>
            <label className="block text-xs font-medium text-secondary mb-1">Assigned Role</label>
            <div className="grid grid-cols-3 gap-2">
              <button
                type="button"
                onClick={() => setGenRole('TESTER')}
                className={`p-2.5 rounded-xl border text-xs font-bold transition-all ${
                  genRole === 'TESTER'
                    ? 'bg-emerald-500/20 border-emerald-500 text-emerald-400'
                    : 'bg-field border-border-card text-muted hover:text-primary'
                }`}
              >
                🧪 Tester
              </button>
              <button
                type="button"
                onClick={() => setGenRole('DEVELOPER')}
                className={`p-2.5 rounded-xl border text-xs font-bold transition-all ${
                  genRole === 'DEVELOPER'
                    ? 'bg-sky-500/20 border-sky-500 text-sky-400'
                    : 'bg-field border-border-card text-muted hover:text-primary'
                }`}
              >
                💻 Developer
              </button>
              <button
                type="button"
                onClick={() => setGenRole('VIEWER')}
                className={`p-2.5 rounded-xl border text-xs font-bold transition-all ${
                  genRole === 'VIEWER'
                    ? 'bg-amber-500/20 border-amber-500 text-amber-400'
                    : 'bg-field border-border-card text-muted hover:text-primary'
                }`}
              >
                👁️ Viewer
              </button>
            </div>
          </div>

          <div>
            <label className="block text-xs font-medium text-secondary mb-1">
              Initial Repository Assignments (Optional)
            </label>
            <div className="max-h-36 overflow-y-auto space-y-1 bg-field p-2 rounded-xl border border-border-card">
              {projects.map((p) => {
                const isSelected = genSelectedProjects.includes(p.id);
                return (
                  <label
                    key={p.id}
                    className="flex items-center gap-2 p-1.5 rounded-lg hover:bg-card cursor-pointer text-xs"
                  >
                    <input
                      type="checkbox"
                      checked={isSelected}
                      onChange={() => {
                        if (isSelected) {
                          setGenSelectedProjects(genSelectedProjects.filter((id) => id !== p.id));
                        } else {
                          setGenSelectedProjects([...genSelectedProjects, p.id]);
                        }
                      }}
                      className="rounded border-border-card text-brand focus:ring-brand"
                    />
                    <span className="text-primary font-medium truncate">{p.name}</span>
                  </label>
                );
              })}
            </div>
          </div>

          <div className="flex justify-end gap-3 pt-3 border-t border-border-card">
            <Button variant="secondary" type="button" onClick={() => setIsGenerateModalOpen(false)}>
              Cancel
            </Button>
            <Button variant="primary" type="submit" isLoading={submittingUser}>
              Provision User
            </Button>
          </div>
        </form>
      </Modal>

      {/* MODAL 2: Configure Repository Team */}
      <Modal
        isOpen={isAssignModalOpen}
        onClose={() => setIsAssignModalOpen(false)}
        title={`Assign Team for "${selectedProject?.name}"`}
      >
        <div className="space-y-4">
          <p className="text-xs text-secondary">
            Assign the dedicated group of Testers, Developers, and Viewers for this repository. Non-admin users only have access to repositories assigned to them.
          </p>

          <div className="max-h-80 overflow-y-auto divide-y divide-border-card bg-field rounded-2xl border border-border-card">
            {users
              .filter((u) => u.role !== 'ADMIN' && u.is_approved)
              .map((u) => {
                const currentAssignment = teamMembers.find((m) => m.user_id === u.id);
                const assignedRole = currentAssignment?.role;

                return (
                  <div key={u.id} className="p-3 flex items-center justify-between gap-3">
                    <div className="min-w-0">
                      <div className="font-semibold text-xs text-primary truncate">{u.full_name}</div>
                      <div className="text-[11px] text-muted font-mono truncate">{u.email}</div>
                    </div>

                    <div className="flex items-center gap-1.5 shrink-0">
                      <button
                        type="button"
                        onClick={() => toggleUserInTeam(u.id, 'TESTER')}
                        className={`px-2 py-1 rounded-lg text-xs font-semibold transition-all ${
                          assignedRole === 'TESTER'
                            ? 'bg-emerald-500 text-white shadow-sm'
                            : 'bg-card text-muted hover:text-emerald-400 border border-border-card'
                        }`}
                      >
                        Tester
                      </button>
                      <button
                        type="button"
                        onClick={() => toggleUserInTeam(u.id, 'DEVELOPER')}
                        className={`px-2 py-1 rounded-lg text-xs font-semibold transition-all ${
                          assignedRole === 'DEVELOPER'
                            ? 'bg-sky-500 text-white shadow-sm'
                            : 'bg-card text-muted hover:text-sky-400 border border-border-card'
                        }`}
                      >
                        Developer
                      </button>
                      <button
                        type="button"
                        onClick={() => toggleUserInTeam(u.id, 'VIEWER')}
                        className={`px-2 py-1 rounded-lg text-xs font-semibold transition-all ${
                          assignedRole === 'VIEWER'
                            ? 'bg-amber-500 text-white shadow-sm'
                            : 'bg-card text-muted hover:text-amber-400 border border-border-card'
                        }`}
                      >
                        Viewer
                      </button>
                    </div>
                  </div>
                );
              })}
          </div>

          <div className="flex justify-between items-center pt-3 border-t border-border-card">
            <span className="text-xs text-muted">
              {teamMembers.length} Team member(s) assigned
            </span>
            <div className="flex gap-2">
              <Button variant="secondary" onClick={() => setIsAssignModalOpen(false)}>
                Cancel
              </Button>
              <Button variant="primary" onClick={handleSaveTeam} isLoading={submittingTeam}>
                Save Team
              </Button>
            </div>
          </div>
        </div>
      </Modal>
    </div>
  );
};
