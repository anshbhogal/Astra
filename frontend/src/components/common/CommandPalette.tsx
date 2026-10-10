import React, { useState, useEffect, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Search,
  FolderGit2,
  BarChart3,
  FlaskConical,
  Sun,
  Moon,
  Layers,
  ArrowRight,
} from 'lucide-react';
import { api } from '../../services/api';
import { useTheme } from '../../hooks/useTheme';

interface CommandPaletteProps {
  isOpen: boolean;
  onClose: () => void;
}

interface CommandItem {
  id: string;
  title: string;
  subtitle: string;
  category: 'NAVIGATION' | 'PROJECTS' | 'ACTIONS';
  icon: React.ComponentType<{ className?: string }>;
  action: () => void;
}

export const CommandPalette: React.FC<CommandPaletteProps> = ({ isOpen, onClose }) => {
  const [query, setQuery] = useState('');
  const [selectedIndex, setSelectedIndex] = useState(0);
  const [projects, setProjects] = useState<any[]>([]);
  const navigate = useNavigate();
  const { theme, toggleTheme } = useTheme();
  const inputRef = useRef<HTMLInputElement | null>(null);

  useEffect(() => {
    if (isOpen) {
      setQuery('');
      setSelectedIndex(0);
      setTimeout(() => inputRef.current?.focus(), 50);
      fetchProjects();
    }
  }, [isOpen]);

  const fetchProjects = async () => {
    try {
      const res = await api.get('/projects/?page_size=20');
      setProjects(res.data.items || []);
    } catch (e) {
      // ignore
    }
  };

  const baseCommands: CommandItem[] = [
    {
      id: 'nav-overview',
      title: 'Workspace Overview',
      subtitle: 'System dashboard & platform metrics overview',
      category: 'NAVIGATION',
      icon: Layers,
      action: () => {
        navigate('/');
        onClose();
      },
    },
    {
      id: 'nav-projects',
      title: 'Repositories Registry',
      subtitle: 'Browse all connected target repositories',
      category: 'NAVIGATION',
      icon: FolderGit2,
      action: () => {
        navigate('/projects');
        onClose();
      },
    },
    {
      id: 'nav-analytics',
      title: 'Quality Analytics & Reports',
      subtitle: 'Defect clustering & formal audit reports',
      category: 'NAVIGATION',
      icon: BarChart3,
      action: () => {
        navigate('/analytics');
        onClose();
      },
    },
    {
      id: 'nav-benchmarks',
      title: 'Research Benchmarks',
      subtitle: 'Empirical bug-detection accuracy matrix',
      category: 'NAVIGATION',
      icon: FlaskConical,
      action: () => {
        navigate('/benchmarks');
        onClose();
      },
    },
    {
      id: 'action-theme',
      title: 'Toggle theme',
      subtitle: `Switch to ${theme === 'dark' ? 'light' : 'dark'} mode (Shortcut: 't')`,
      category: 'ACTIONS',
      icon: theme === 'dark' ? Sun : Moon,
      action: () => {
        toggleTheme();
        onClose();
      },
    },
  ];

  const projectCommands: CommandItem[] = projects.map((p) => ({
    id: `project-${p.id}`,
    title: p.name,
    subtitle: `${p.language_framework || 'Microservice'} • ${p.repository_url}`,
    category: 'PROJECTS',
    icon: FolderGit2,
    action: () => {
      navigate(`/projects/${p.id}`);
      onClose();
    },
  }));

  const allItems = [...baseCommands, ...projectCommands];

  const filteredItems = allItems.filter(
    (item) =>
      item.title.toLowerCase().includes(query.toLowerCase()) ||
      item.subtitle.toLowerCase().includes(query.toLowerCase())
  );

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'ArrowDown') {
      e.preventDefault();
      setSelectedIndex((prev) => (prev < filteredItems.length - 1 ? prev + 1 : 0));
    } else if (e.key === 'ArrowUp') {
      e.preventDefault();
      setSelectedIndex((prev) => (prev > 0 ? prev - 1 : filteredItems.length - 1));
    } else if (e.key === 'Enter') {
      e.preventDefault();
      if (filteredItems[selectedIndex]) {
        filteredItems[selectedIndex].action();
      }
    } else if (e.key === 'Escape') {
      onClose();
    }
  };

  if (!isOpen) return null;

  return (
    <div
      className="fixed inset-0 z-50 flex items-start justify-center pt-24 p-4 bg-primary/40 backdrop-blur-sm animate-fade-in"
      onClick={onClose}
    >
      <div
        className="w-full max-w-xl bg-card rounded-2xl shadow-xl border border-border-card overflow-hidden flex flex-col max-h-[480px]"
        onClick={(e) => e.stopPropagation()}
        onKeyDown={handleKeyDown}
      >
        {/* Search Header */}
        <div className="flex items-center gap-3 px-4 py-3 border-b border-border-card bg-field">
          <Search className="w-4 h-4 text-muted shrink-0" />
          <input
            ref={inputRef}
            type="text"
            value={query}
            onChange={(e) => {
              setQuery(e.target.value);
              setSelectedIndex(0);
            }}
            placeholder="Type a command, project, or view... (ESC to exit)"
            className="w-full bg-transparent text-primary text-sm placeholder-muted focus:outline-none"
          />
          <kbd className="hidden sm:inline-flex items-center gap-0.5 px-2 py-0.5 rounded bg-card border border-border-field text-[10px] font-mono text-muted">
            ESC
          </kbd>
        </div>

        {/* Command List */}
        <div className="flex-1 overflow-y-auto p-2 space-y-1">
          {filteredItems.length === 0 ? (
            <div className="p-8 text-center text-xs text-muted">
              No matching commands or projects found.
            </div>
          ) : (
            filteredItems.map((item, idx) => {
              const Icon = item.icon;
              const isSelected = selectedIndex === idx;

              return (
                <div
                  key={item.id}
                  onClick={item.action}
                  onMouseEnter={() => setSelectedIndex(idx)}
                  className={`flex items-center justify-between p-3 rounded-lg cursor-pointer transition-all ${
                    isSelected
                      ? 'bg-hover text-primary border border-brand/40 shadow-sm'
                      : 'text-secondary hover:text-primary hover:bg-hover border border-transparent'
                  }`}
                >
                  <div className="flex items-center gap-3 min-w-0">
                    <div
                      className={`p-2 rounded-lg shrink-0 ${
                        isSelected ? 'bg-brand/15 text-brand' : 'bg-field border border-border-card text-muted'
                      }`}
                    >
                      <Icon className="w-4 h-4" />
                    </div>
                    <div className="min-w-0">
                      <p className="text-xs font-semibold text-primary truncate">{item.title}</p>
                      <p className="text-[11px] text-muted truncate">{item.subtitle}</p>
                    </div>
                  </div>

                  <ArrowRight
                    className={`w-3.5 h-3.5 shrink-0 transition-transform ${
                      isSelected ? 'text-brand translate-x-0.5' : 'text-transparent'
                    }`}
                  />
                </div>
              );
            })
          )}
        </div>

        {/* Keyboard Hint Footer */}
        <div className="p-3 bg-field border-t border-border-card flex items-center justify-between text-[11px] text-muted">
          <div className="flex items-center gap-3">
            <span>
              <kbd className="px-1.5 py-0.5 rounded bg-card border border-border-card">↑</kbd>{' '}
              <kbd className="px-1.5 py-0.5 rounded bg-card border border-border-card">↓</kbd> to navigate
            </span>
            <span>
              <kbd className="px-1.5 py-0.5 rounded bg-card border border-border-card">↵</kbd> to select
            </span>
          </div>
          <span className="text-xs font-semibold text-brand">ASTRA Quick Actions</span>
        </div>
      </div>
    </div>
  );
};
