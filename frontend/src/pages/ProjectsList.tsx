import React, { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import {
  Plus,
  Search,
  FolderGit2,
  Trash2,
  ExternalLink,
  GitBranch,
  AlertCircle,
  ArrowUpRight,
} from 'lucide-react';
import { api } from '../services/api';
import { useAuthStore } from '../store/authStore';
import { Button } from '../components/common/Button';
import { Input } from '../components/common/Input';
import { Modal } from '../components/common/Modal';

interface Project {
  id: string;
  name: string;
  description: string | null;
  repository_url: string;
  default_branch: string;
  language_framework: string;
  owner_id: string;
  owner?: { full_name: string; email: string };
  created_at: string;
}

export const ProjectsList: React.FC = () => {
  const { user } = useAuthStore();
  const [projects, setProjects] = useState<Project[]>([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState('');

  // Modal State
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [name, setName] = useState('');
  const [description, setDescription] = useState('');
  const [repositoryUrl, setRepositoryUrl] = useState('');
  const [defaultBranch, setDefaultBranch] = useState('main');
  const [framework, setFramework] = useState('PYTHON_FASTAPI');
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const isViewer = user?.role === 'VIEWER';

  useEffect(() => {
    fetchProjects();
  }, []);

  const fetchProjects = async () => {
    setLoading(true);
    try {
      const res = await api.get('/projects/');
      setProjects(res.data.items || []);
    } catch (err) {
      console.error('Failed to fetch projects', err);
    } finally {
      setLoading(false);
    }
  };

  const handleCreateProject = async (e: React.FormEvent) => {
    e.preventDefault();
    setSubmitting(true);
    setError(null);

    try {
      await api.post('/projects/', {
        name,
        description: description || null,
        repository_url: repositoryUrl,
        default_branch: defaultBranch,
        language_framework: framework,
      });

      setIsModalOpen(false);
      setName('');
      setDescription('');
      setRepositoryUrl('');
      fetchProjects();
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to create project.');
    } finally {
      setSubmitting(false);
    }
  };

  const handleDeleteProject = async (id: string, e: React.MouseEvent) => {
    e.stopPropagation();
    if (!window.confirm('Are you sure you want to delete this repository?')) return;

    try {
      await api.delete(`/projects/${id}`);
      fetchProjects();
    } catch (err: any) {
      alert(err.response?.data?.detail || 'Failed to delete project.');
    }
  };

  const filteredProjects = projects.filter((p) =>
    p.name.toLowerCase().includes(search.toLowerCase()) ||
    p.repository_url.toLowerCase().includes(search.toLowerCase()) ||
    p.language_framework.toLowerCase().includes(search.toLowerCase())
  );

  return (
    <div className="space-y-6">
      {/* Page Header */}
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-3">
            <h1 className="text-[28px] font-semibold text-primary tracking-tight">Repositories</h1>
            <span className="px-2.5 py-0.5 rounded-full text-xs font-semibold bg-brand/10 text-brand">
              {projects.length} Total
            </span>
          </div>
          <p className="text-sm text-secondary mt-0.5">
            Target codebases connected for automated AST parsing, test generation, and defect tracking.
          </p>
        </div>

        <Button
          onClick={() => setIsModalOpen(true)}
          disabled={isViewer}
          variant="primary"
          leftIcon={<Plus className="w-4 h-4" />}
          title={isViewer ? 'Viewer role is restricted to read-only access' : 'Register Repository'}
        >
          Register Repository
        </Button>
      </div>

      {isViewer && (
        <div className="p-3.5 rounded-xl bg-status-flaky-bg border border-status-flaky/30 text-status-flaky text-xs flex items-center gap-2">
          <AlertCircle className="w-4 h-4 shrink-0" />
          <span>You have Viewer permissions. Adding or deleting repositories requires Developer or Admin access.</span>
        </div>
      )}

      {/* Search & Filter Bar */}
      <div className="flex items-center gap-4">
        <div className="relative flex-1">
          <Search className="w-4 h-4 absolute left-3.5 top-1/2 -translate-y-1/2 text-muted pointer-events-none" />
          <input
            type="text"
            placeholder="Search repositories by name, language, or URL..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="w-full h-10 bg-field text-primary text-sm rounded-lg border border-border-field pl-10 pr-4 placeholder-muted focus:outline-none focus:ring-2 focus:ring-brand focus:ring-offset-2 focus:ring-offset-app transition-colors"
          />
        </div>
      </div>

      {/* Repositories Grid */}
      {loading ? (
        <div className="text-center py-16 text-muted text-sm flex flex-col items-center gap-2">
          <div className="w-6 h-6 border-2 border-brand border-t-transparent rounded-full animate-spin" />
          <span>Loading workspace repositories...</span>
        </div>
      ) : filteredProjects.length === 0 ? (
        <div className="bg-card rounded-2xl p-12 text-center space-y-3 border border-border-card shadow-card">
          <FolderGit2 className="w-12 h-12 text-muted mx-auto opacity-50" />
          <h3 className="text-base font-semibold text-primary">No Repositories Found</h3>
          <p className="text-xs text-secondary max-w-sm mx-auto">
            {search
              ? 'No repositories match your search query. Try clearing the filter.'
              : 'Enroll your first target Git repository to begin automated AST parsing and test execution.'}
          </p>
          {!search && !isViewer && (
            <Button
              onClick={() => setIsModalOpen(true)}
              variant="primary"
              size="sm"
              leftIcon={<Plus className="w-4 h-4" />}
              className="mt-2"
            >
              Add First Repository
            </Button>
          )}
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
          {filteredProjects.map((project) => (
            <Link
              key={project.id}
              to={`/projects/${project.id}`}
              className="bg-card rounded-xl p-5 border border-border-card shadow-card hover:border-brand/50 transition-all duration-150 flex flex-col justify-between space-y-4 group"
            >
              <div className="space-y-3">
                <div className="flex items-center justify-between">
                  <span className="text-xs font-semibold px-2.5 py-0.5 rounded-full bg-brand/10 text-brand">
                    {project.language_framework}
                  </span>
                  {!isViewer && (
                    <button
                      onClick={(e) => handleDeleteProject(project.id, e)}
                      className="p-1 text-muted hover:text-status-failed rounded-lg transition-colors opacity-0 group-hover:opacity-100"
                      title="Delete Repository"
                    >
                      <Trash2 className="w-4 h-4" />
                    </button>
                  )}
                </div>

                <div className="space-y-1">
                  <h3 className="text-base font-semibold text-primary group-hover:text-brand transition-colors flex items-center justify-between">
                    <span className="truncate">{project.name}</span>
                    <ArrowUpRight className="w-4 h-4 text-muted group-hover:text-brand transition-colors shrink-0 ml-1" />
                  </h3>
                  <p className="text-xs text-secondary line-clamp-2 leading-relaxed">
                    {project.description || 'No description provided.'}
                  </p>
                </div>
              </div>

              <div className="pt-3 border-t border-border-card text-xs text-secondary space-y-1.5">
                <div className="flex items-center gap-1.5 truncate">
                  <ExternalLink className="w-3.5 h-3.5 text-muted shrink-0" />
                  <span className="truncate text-muted font-mono">{project.repository_url}</span>
                </div>
                <div className="flex items-center justify-between text-xs text-muted">
                  <span className="flex items-center gap-1">
                    <GitBranch className="w-3.5 h-3.5" /> <span className="font-mono">{project.default_branch}</span>
                  </span>
                  <span>Owner: {project.owner?.full_name?.split(' ')[0] || 'Admin'}</span>
                </div>
              </div>
            </Link>
          ))}
        </div>
      )}

      {/* Create Project Modal */}
      <Modal isOpen={isModalOpen} onClose={() => setIsModalOpen(false)} title="Register Repository">
        <form onSubmit={handleCreateProject} className="space-y-4">
          {error && (
            <div className="p-3 rounded-lg bg-status-failed-bg border border-status-failed/30 text-status-failed text-xs font-medium">
              {error}
            </div>
          )}

          <Input
            label="Repository Name"
            placeholder="e.g., E-Commerce Checkout API"
            value={name}
            onChange={(e) => setName(e.target.value)}
            required
          />

          <div className="space-y-1.5">
            <label className="block text-xs font-semibold text-secondary">
              Description
            </label>
            <textarea
              rows={2}
              placeholder="Brief description of the service or component"
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              className="w-full bg-field text-primary text-sm rounded-lg border border-border-field hover:border-brand focus:ring-2 focus:ring-brand focus:ring-offset-2 focus:ring-offset-card p-3 outline-none transition-colors placeholder-muted"
            />
          </div>

          <Input
            label="Git Repository URL"
            placeholder="https://github.com/company/repo-name"
            value={repositoryUrl}
            onChange={(e) => setRepositoryUrl(e.target.value)}
            helperText="Supports https://, git@, or file:// paths"
            required
          />

          <div className="grid grid-cols-2 gap-4">
            <Input
              label="Default Branch"
              value={defaultBranch}
              onChange={(e) => setDefaultBranch(e.target.value)}
              required
            />

            <div className="space-y-1.5">
              <label className="block text-xs font-semibold text-secondary">
                Language / Framework
              </label>
              <select
                value={framework}
                onChange={(e) => setFramework(e.target.value)}
                className="w-full h-10 bg-field text-primary text-sm rounded-lg border border-border-field hover:border-brand focus:ring-2 focus:ring-brand focus:ring-offset-2 focus:ring-offset-card px-3 outline-none transition-colors cursor-pointer"
              >
                <option value="PYTHON_FASTAPI">Python FastAPI</option>
                <option value="PYTHON_FLASK">Python Flask</option>
                <option value="NODE_EXPRESS">Node Express</option>
                <option value="JAVA_SPRING">Java Spring Boot</option>
                <option value="OTHER">Other Framework</option>
              </select>
            </div>
          </div>

          <div className="flex justify-end gap-3 pt-4 border-t border-border-card">
            <Button type="button" variant="secondary" onClick={() => setIsModalOpen(false)}>
              Cancel
            </Button>
            <Button type="submit" variant="primary" isLoading={submitting}>
              Save Repository
            </Button>
          </div>
        </form>
      </Modal>
    </div>
  );
};
