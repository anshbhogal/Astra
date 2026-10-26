import React from 'react';
import { Link, useNavigate } from 'react-router-dom';
import {
  ArrowLeft,
  ExternalLink,
  GitBranch,
  Shield,
  Layers,
  FileCode,
  Users,
  FlaskConical,
  Code2,
  Eye,
  Play,
  Sliders,
} from 'lucide-react';
import { Button } from '../common/Button';
import {
  Project,
  Analysis,
  ProjectMember,
  DiscoveredEndpoint,
  formatFrameworkName,
} from './types';

interface ProjectHeaderBannerProps {
  project: Project;
  analysis: Analysis | null;
  endpoints: DiscoveredEndpoint[];
  members: ProjectMember[];
  canRunTests: boolean;
  analyzing: boolean;
  isAdmin: boolean;
  onTriggerAnalysis: () => void;
  onOpenAdvancedDrawer: () => void;
}

export const ProjectHeaderBanner: React.FC<ProjectHeaderBannerProps> = ({
  project,
  analysis,
  endpoints,
  members,
  canRunTests,
  analyzing,
  isAdmin,
  onTriggerAnalysis,
  onOpenAdvancedDrawer,
}) => {
  const navigate = useNavigate();
  const isRunning = analyzing || analysis?.status === 'RUNNING' || analysis?.status === 'QUEUED';
  const isCompleted = analysis?.status === 'COMPLETED' || analysis?.status === 'COMPLETED_WITH_WARNINGS';

  return (
    <div className="space-y-6">
      {/* Top Breadcrumb Header */}
      <div className="flex items-center gap-2 text-xs text-muted">
        <Link to="/projects" className="hover:text-primary transition-colors flex items-center gap-1 font-medium">
          <ArrowLeft className="w-3.5 h-3.5" /> Projects
        </Link>
        <span>/</span>
        <span className="text-primary font-semibold">{project.name}</span>
      </div>

      {/* Project Banner Card */}
      <div className="glass-card border-t-4 border-t-brand rounded-2xl p-6 shadow-glass space-y-5">
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
          <div className="space-y-1">
            <div className="flex items-center gap-2.5 flex-wrap">
              <h1 className="text-2xl font-bold text-primary tracking-tight">{project.name}</h1>
              <span className="text-xs font-semibold px-2.5 py-0.5 rounded-full bg-brand/10 text-brand border border-brand/20">
                {formatFrameworkName(project.language_framework)}
              </span>
            </div>
            <p className="text-xs text-secondary">{project.description || 'No description provided.'}</p>
          </div>

          <div className="flex items-center gap-3 flex-wrap">
            <Button
              variant="primary"
              size="md"
              onClick={onTriggerAnalysis}
              disabled={!canRunTests || isRunning}
              isLoading={isRunning}
              leftIcon={<Play className="w-3.5 h-3.5 fill-current" />}
              title={!canRunTests ? 'Only Testers and Admins can trigger repository analysis' : undefined}
            >
              {isRunning
                ? `Analyzing (${analysis?.progress_percent ?? 0}%)`
                : isCompleted
                ? 'Re-run Analysis'
                : 'Analyze Repository'}
            </Button>

            <Button
              variant="secondary"
              size="md"
              onClick={() => navigate(`/projects/${project.id}/ide`)}
              leftIcon={<Code2 className="w-3.5 h-3.5 text-sky-400" />}
              className="border-sky-500/30 text-sky-400 hover:border-sky-500"
            >
              Open in Code Studio (IDE)
            </Button>

            <Button
              variant="secondary"
              size="md"
              onClick={onOpenAdvancedDrawer}
              disabled={!canRunTests || !analysis || endpoints.length === 0}
              leftIcon={<Sliders className="w-3.5 h-3.5 text-brand" />}
              title={!canRunTests ? 'Only Testers and Admins can generate synthetic suites' : undefined}
            >
              Advanced Suite Generator
            </Button>

            <a
              href={project.repository_url}
              target="_blank"
              rel="noopener noreferrer"
              className="inline-flex items-center gap-1.5 px-3.5 h-10 rounded-lg bg-card border border-border-field hover:bg-hover text-xs font-semibold text-primary transition-colors shrink-0"
            >
              <ExternalLink className="w-3.5 h-3.5 text-brand" /> View Repository
            </a>
          </div>
        </div>

        {/* Metadata Strip */}
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 pt-4 border-t border-border-card text-xs">
          <div className="flex items-center gap-3">
            <div className="w-8 h-8 rounded-lg bg-brand/10 border border-brand/20 flex items-center justify-center text-brand shrink-0">
              <GitBranch className="w-4 h-4" />
            </div>
            <div className="min-w-0">
              <span className="text-muted block text-[10px] uppercase font-semibold">Default Branch</span>
              <span className="text-primary font-semibold truncate block mt-0.5">{project.default_branch}</span>
            </div>
          </div>

          <div className="flex items-center gap-3">
            <div className="w-8 h-8 rounded-lg bg-secondaryAccent/10 border border-secondaryAccent/20 flex items-center justify-center text-secondaryAccent shrink-0">
              <Shield className="w-4 h-4" />
            </div>
            <div className="min-w-0">
              <span className="text-muted block text-[10px] uppercase font-semibold">Project Owner</span>
              <span className="text-primary font-semibold truncate block mt-0.5">
                {project.owner?.full_name || 'System Admin'}
              </span>
            </div>
          </div>

          <div className="flex items-center gap-3">
            <div className="w-8 h-8 rounded-lg bg-brand/10 border border-brand/20 flex items-center justify-center text-brand shrink-0">
              <FileCode className="w-4 h-4" />
            </div>
            <div className="min-w-0">
              <span className="text-muted block text-[10px] uppercase font-semibold">Latest Analysis SHA</span>
              <span className="text-primary font-mono text-[11px] font-semibold truncate block mt-0.5">
                {analysis?.commit_sha ? analysis.commit_sha.substring(0, 8) : 'Not Analyzed'}
              </span>
            </div>
          </div>

          <div className="flex items-center gap-3">
            <div className="w-8 h-8 rounded-lg bg-secondaryAccent/10 border border-secondaryAccent/20 flex items-center justify-center text-secondaryAccent shrink-0">
              <Layers className="w-4 h-4" />
            </div>
            <div className="min-w-0">
              <span className="text-muted block text-[10px] uppercase font-semibold">Detected Stack</span>
              <span className="text-primary font-semibold truncate block mt-0.5">
                {formatFrameworkName(analysis?.detected_framework)}
              </span>
            </div>
          </div>
        </div>
      </div>

      {/* Repository Team Governance Strip */}
      <div className="glass-card rounded-2xl p-4 shadow-card border border-border-card flex flex-col md:flex-row items-start md:items-center justify-between gap-4">
        <div className="flex flex-col sm:flex-row sm:items-center gap-5">
          <div className="flex items-center gap-2.5">
            <div className="w-8 h-8 rounded-lg bg-purple-500/15 border border-purple-500/30 flex items-center justify-center text-purple-400">
              <Users className="w-4 h-4" />
            </div>
            <div>
              <span className="text-[10px] font-bold uppercase tracking-wider text-muted">Assigned Team</span>
              <span className="text-xs font-semibold text-primary block">{members.length} Member(s)</span>
            </div>
          </div>

          <div className="flex items-center gap-3 text-xs flex-wrap">
            <div className="flex items-center gap-1.5">
              <span className="px-2 py-0.5 rounded-full text-[10px] font-bold bg-emerald-500/15 text-emerald-400 border border-emerald-500/30 flex items-center gap-1">
                <FlaskConical className="w-3 h-3" /> Testers ({members.filter((m) => m.role === 'TESTER').length})
              </span>
              <span className="text-secondary font-medium">
                {members.filter((m) => m.role === 'TESTER').map((m) => m.user?.full_name).join(', ') || (
                  <span className="text-muted italic">None</span>
                )}
              </span>
            </div>

            <div className="flex items-center gap-1.5">
              <span className="px-2 py-0.5 rounded-full text-[10px] font-bold bg-sky-500/15 text-sky-400 border border-sky-500/30 flex items-center gap-1">
                <Code2 className="w-3 h-3" /> Developers ({members.filter((m) => m.role === 'DEVELOPER').length})
              </span>
              <span className="text-secondary font-medium">
                {members.filter((m) => m.role === 'DEVELOPER').map((m) => m.user?.full_name).join(', ') || (
                  <span className="text-muted italic">None</span>
                )}
              </span>
            </div>

            <div className="flex items-center gap-1.5">
              <span className="px-2 py-0.5 rounded-full text-[10px] font-bold bg-amber-500/15 text-amber-400 border border-amber-500/30 flex items-center gap-1">
                <Eye className="w-3 h-3" /> Viewers ({members.filter((m) => m.role === 'VIEWER').length})
              </span>
              <span className="text-secondary font-medium">
                {members.filter((m) => m.role === 'VIEWER').map((m) => m.user?.full_name).join(', ') || (
                  <span className="text-muted italic">None</span>
                )}
              </span>
            </div>
          </div>
        </div>

        {isAdmin && (
          <Button
            variant="secondary"
            size="sm"
            onClick={() => navigate('/admin')}
            leftIcon={<Shield className="w-3.5 h-3.5 text-purple-400" />}
          >
            Manage Team
          </Button>
        )}
      </div>
    </div>
  );
};
