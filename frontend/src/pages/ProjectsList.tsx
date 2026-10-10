import React, { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import {
  Plus,
  Search,
  FolderGit2,
  Trash2,
  ExternalLink,
  GitBranch,
  Code2,
  AlertCircle,
  Sparkles,
  Layers,
  ArrowUpRight,
  ShieldCheck,
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
    if (!window.confirm('Are you sure you want to delete this project?')) return;

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
      {/* Header Bar */}
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2">
            <h1 className="text-2xl font-extrabold text-primary tracking-tight">Software Projects</h1>
            <span className="px-2 py-0.5 rounded-full text-xs font-mono font-bold bg-brand/10 text-brand border border-brand/20">
              {projects.length} Repositories
            </span>
          </div>
          <p className="text-xs text-secondary mt-1">
            Target codebases enrolled in automated AST parsing, test suite synthesis, and failure telemetry.
          </p>
        </div>

        {/* The single Volt Lime highlight button on this screen */}
        <Button
          onClick={() => setIsModalOpen(true)}
          disabled={isViewer}
          variant="accent"
          size="md"
          leftIcon={<Plus className="w-4 h-4" />}
          title={isViewer ? 'Viewer role is restricted to read-only access' : 'Register Repository'}
        >
          Register Repository
        </Button>
      </div>

      {isViewer && (
        <div className="p-3 rounded-xl bg-status-flaky-bg border border-status-flaky-border text-status-flaky text-xs flex items-center gap-2">
          <AlertCircle className="w-4 h-4 shrink-0" />
          <span>You have Viewer read-only permissions. Creating or deleting projects requires Developer or Admin access.</span>
        </div>
      )}

      {/* Search & Filter Bar */}
      <div className="flex items-center gap-4">
        <div className="relative flex-1">
          <Search className="w-4 h-4 absolute left-3.5 top-1/2 -translate-y-1/2 text-muted" />
          <input
            type="text"
            placeholder="Search projects by name, language, or repository URL..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="w-full bg-surface text-primary text-sm rounded-xl pl-10 pr-4 py-2.5 border border-border focus:outline-none focus:ring-2 focus:ring-brand placeholder-muted transition-colors"
          />
        </div>
      </div>

      {/* Projects Grid */}
      {loading ? (
        <div className="text-center py-16 text-muted text-sm font-mono flex flex-col items-center gap-2">
          <div className="w-6 h-6 border-2 border-brand border-t-transparent rounded-full animate-spin" />
          <span>Loading workspace repositories...</span>
        </div>
      ) : filteredProjects.length === 0 ? (
        <div className="glass-card rounded-2xl p-12 text-center space-y-3 border border-border">
          <FolderGit2 className="w-12 h-12 text-muted mx-auto opacity-50" />
          <h3 className="text-base font-semibold text-primary">No Projects Found</h3>
          <p className="text-xs text-secondary max-w-sm mx-auto">
            {search
              ? 'No projects match your search query. Try clearing the filter.'
              : 'Get started by adding a target Git repository for ASTRA static code analysis and test execution.'}
          </p>
          {!search && !isViewer && (
            <Button
              onClick={() => setIsModalOpen(true)}
              variant="accent"
              size="sm"
              leftIcon={<Plus className="w-4 h-4" />}
              className="mt-2"
            >
              Add First Project
            </Button>
          )}
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
          {filteredProjects.map((project) => (
            <Link
              key={project.id}
              to={`/projects/${project.id}`}
              className="glass-card rounded-xl p-5 border border-border hover:border-brand/50 hover:shadow-brand-glow transition-all duration-200 flex flex-col justify-between space-y-4 group"
            >
              <div className="space-y-3">
                <div className="flex items-center justify-between">
                  <span className="text-[10px] font-mono font-bold px-2 py-0.5 rounded bg-brand/10 text-brand border border-brand/20">
                    {project.language_framework}
                  </span>
                  {!isViewer && (
                    <button
                      onClick={(e) => handleDeleteProject(project.id, e)}
                      className="p-1 text-muted hover:text-status-failed rounded transition-colors opacity-0 group-hover:opacity-100"
                      title="Delete Project"
                    >
                      <Trash2 className="w-4 h-4" />
                    </button>
                  )}
                </div>

                <div className="space-y-1">
                  <h3 className="text-base font-bold text-primary group-hover:text-brand transition-colors flex items-center justify-between">
                    <span className="truncate">{project.name}</span>
                    <ArrowUpRight className="w-4 h-4 text-muted group-hover:text-brand transition-colors shrink-0 ml-1" />
                  </h3>
                  <p className="text-xs text-secondary line-clamp-2">
                    {project.description || 'No description provided.'}
                  </p>
                </div>
              </div>

              <div className="pt-3 border-t border-border text-xs text-secondary space-y-1.5 font-mono">
                <div className="flex items-center gap-1.5 truncate">
                  <ExternalLink className="w-3.5 h-3.5 text-muted shrink-0" />
                  <span className="truncate text-muted">{project.repository_url}</span>
                </div>
                <div className="flex items-center justify-between text-[11px]">
                  <span className="flex items-center gap-1 text-secondary">
                    <GitBranch className="w-3 h-3 text-muted" /> {project.default_branch}
                  </span>
                  <span className="text-muted">Owner: {project.owner?.full_name?.split(' ')[0] || 'Admin'}</span>
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
            <div className="p-3 rounded-xl bg-status-failed-bg border border-status-failed-border text-status-failed text-xs font-medium">
              {error}
            </div>
          )}

          <Input
            label="Project Name"
            placeholder="E-Commerce Payment API"
            value={name}
            onChange={(e) => setName(e.target.value)}
            required
          />

          <div className="space-y-1.5">
            <label className="block text-xs font-semibold uppercase tracking-wider text-secondary">
              Description
            </label>
            <textarea
              rows={2}
              placeholder="Brief description of the microservice or API"
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              className="w-full bg-surface text-primary text-sm rounded-lg border border-border hover:border-brand/40 focus:ring-2 focus:ring-brand p-3 outline-none transition-colors"
            />
          </div>

          <Input
            label="Repository URL"
            placeholder="https://github.com/company/repo-name"
            value={repositoryUrl}
            onChange={(e) => setRepositoryUrl(e.target.value)}
            helperText="Supports http://, https://, or git@ URLs"
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
              <label className="block text-xs font-semibold uppercase tracking-wider text-secondary">
                Language / Framework
              </label>
              <select
                value={framework}
                onChange={(e) => setFramework(e.target.value)}
                className="w-full bg-surface text-primary text-sm rounded-lg border border-border hover:border-brand/40 focus:ring-2 focus:ring-brand px-3.5 py-2.5 outline-none transition-colors"
              >
                <option value="PYTHON_FASTAPI">Python FastAPI</option>
                <option value="PYTHON_FLASK">Python Flask</option>
                <option value="NODE_EXPRESS">Node Express</option>
                <option value="JAVA_SPRING">Java Spring Boot</option>
                <option value="OTHER">Other Framework</option>
              </select>
            </div>
          </div>

          <div className="flex justify-end gap-3 pt-4 border-t border-border">
            <Button type="button" variant="outline" onClick={() => setIsModalOpen(false)}>
              Cancel
            </Button>
            <Button type="submit" variant="accent" isLoading={submitting}>
              Enroll Project
            </Button>
          </div>
        </form>
      </Modal>
    </div>
  );
};
