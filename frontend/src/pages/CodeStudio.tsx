import React, { useState, useEffect, useRef, useCallback } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import Editor from '@monaco-editor/react';
import {
  Folder,
  FolderOpen,
  FileCode,
  FileText,
  FileJson,
  File,
  Save,
  Play,
  RefreshCw,
  Plus,
  Trash2,
  ChevronRight,
  ChevronDown,
  X,
  Bug,
  Files,
  Terminal,
  CheckCircle2,
  AlertTriangle,
  Clock,
  ArrowLeft,
  Search,
  Maximize2,
  Minimize2,
  Send,
  Sparkles,
} from 'lucide-react';
import { api } from '../services/api';
import { useAuthStore } from '../store/authStore';
import { Button } from '../components/common/Button';

interface FileNode {
  name: string;
  path: string;
  type: 'file' | 'directory';
  size?: number;
  children?: FileNode[];
}

interface OpenTab {
  path: string;
  name: string;
  content: string;
  originalContent: string;
  language: string;
  isDirty: boolean;
}

interface DefectItem {
  id: string;
  summary: string;
  category: string;
  status: string;
  failing_file?: string;
  failing_line?: number;
  error_message: string;
}

export const CodeStudio: React.FC = () => {
  const { id: projectIdParam } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const { user } = useAuthStore();

  const [projectId, setProjectId] = useState<string>(projectIdParam || '');
  const [projectsList, setProjectsList] = useState<{ id: string; name: string }[]>([]);
  const [projectName, setProjectName] = useState<string>('Workspace');
  const [defaultBranch, setDefaultBranch] = useState<string>('main');

  // File tree & tabs
  const [fileTree, setFileTree] = useState<FileNode[]>([]);
  const [expandedFolders, setExpandedFolders] = useState<Set<string>>(new Set());
  const [openTabs, setOpenTabs] = useState<OpenTab[]>([]);
  const [activeTabPath, setActiveTabPath] = useState<string | null>(null);
  const [searchFilter, setSearchFilter] = useState('');

  // Sidebar views: 'files' | 'defects'
  const [activeSidebarView, setActiveSidebarView] = useState<'files' | 'defects'>('files');

  // Defects
  const [defects, setDefects] = useState<DefectItem[]>([]);
  const [selectedDefect, setSelectedDefect] = useState<DefectItem | null>(null);
  const [defectComment, setDefectComment] = useState('');
  const [postingComment, setPostingComment] = useState(false);

  // Bottom panel: 'testRunner' | 'terminal'
  const [bottomPanelOpen, setBottomPanelOpen] = useState(true);
  const [bottomTab, setBottomTab] = useState<'testRunner' | 'terminal'>('testRunner');
  const [testOutput, setTestOutput] = useState<string>('Test runner idle. Click "Run Tests & Verify Fix" to execute test suite.');
  const [testStatus, setTestStatus] = useState<string | null>(null);
  const [runningTests, setRunningTests] = useState(false);

  // Editor cursor pos
  const [cursorPos, setCursorPos] = useState({ line: 1, col: 1 });
  const [editorTheme, setEditorTheme] = useState<'vs-dark' | 'light'>('vs-dark');
  const [savingFile, setSavingFile] = useState(false);

  // Fullscreen state
  const [isFullscreen, setIsFullscreen] = useState(false);
  const containerRef = useRef<HTMLDivElement>(null);
  const editorRef = useRef<any>(null);

  // New file creation state
  const [isCreatingFile, setIsCreatingFile] = useState(false);
  const [newFileName, setNewFileName] = useState('');
  const [newFileParent, setNewFileParent] = useState('');

  // Load user's accessible projects
  useEffect(() => {
    const fetchProjects = async () => {
      try {
        const res = await api.get('/projects/');
        const items = res.data.items || [];
        setProjectsList(items.map((p: any) => ({ id: p.id, name: p.name })));
        if (!projectId && items.length > 0) {
          setProjectId(items[0].id);
        }
      } catch (err) {
        console.error('Failed to load projects list', err);
      }
    };
    fetchProjects();
  }, [projectId]);

  // Load repository tree & defects whenever selected project changes
  const loadTreeAndDefects = useCallback(async () => {
    if (!projectId) return;
    try {
      const [treeRes, defectsRes] = await Promise.all([
        api.get(`/projects/${projectId}/code/tree`),
        api.get(`/projects/${projectId}/code/defects`),
      ]);
      setFileTree(treeRes.data.tree || []);
      setProjectName(treeRes.data.project_name || 'Workspace');
      setDefaultBranch(treeRes.data.default_branch || 'main');
      setDefects(defectsRes.data || []);

      // Auto-expand root folders
      const rootFolders = new Set<string>();
      (treeRes.data.tree || []).forEach((node: FileNode) => {
        if (node.type === 'directory') rootFolders.add(node.path);
      });
      setExpandedFolders(rootFolders);
    } catch (err) {
      console.error('Failed to load file tree', err);
    }
  }, [projectId]);

  useEffect(() => {
    loadTreeAndDefects();
  }, [loadTreeAndDefects]);

  // Handle open file
  const handleOpenFile = async (filePath: string, lineTarget?: number) => {
    const existing = openTabs.find((t) => t.path === filePath);
    if (existing) {
      setActiveTabPath(filePath);
      if (lineTarget && editorRef.current) {
        editorRef.current.revealLineInCenter(lineTarget);
        editorRef.current.setPosition({ lineNumber: lineTarget, column: 1 });
      }
      return;
    }

    try {
      const res = await api.get(`/projects/${projectId}/code/file?path=${encodeURIComponent(filePath)}`);
      const newTab: OpenTab = {
        path: res.data.path,
        name: res.data.path.split('/').pop() || res.data.path,
        content: res.data.content,
        originalContent: res.data.content,
        language: res.data.language,
        isDirty: false,
      };

      setOpenTabs((prev) => [...prev, newTab]);
      setActiveTabPath(res.data.path);

      if (lineTarget && editorRef.current) {
        setTimeout(() => {
          editorRef.current?.revealLineInCenter(lineTarget);
          editorRef.current?.setPosition({ lineNumber: lineTarget, column: 1 });
        }, 150);
      }
    } catch (err) {
      console.error('Failed to open file', err);
    }
  };

  const handleCloseTab = (path: string, e: React.MouseEvent) => {
    e.stopPropagation();
    const tabToClose = openTabs.find((t) => t.path === path);
    if (tabToClose?.isDirty && !window.confirm(`File '${tabToClose.name}' has unsaved changes. Close anyway?`)) {
      return;
    }
    const remaining = openTabs.filter((t) => t.path !== path);
    setOpenTabs(remaining);
    if (activeTabPath === path) {
      setActiveTabPath(remaining.length > 0 ? remaining[remaining.length - 1].path : null);
    }
  };

  const activeTab = openTabs.find((t) => t.path === activeTabPath);

  // Editor content changes
  const handleEditorChange = (value: string | undefined) => {
    if (!activeTab || value === undefined) return;
    setOpenTabs((prev) =>
      prev.map((t) => {
        if (t.path === activeTab.path) {
          return {
            ...t,
            content: value,
            isDirty: value !== t.originalContent,
          };
        }
        return t;
      })
    );
  };

  // Save current active file
  const handleSaveFile = async () => {
    if (!activeTab || !projectId) return;
    setSavingFile(true);
    try {
      await api.put(`/projects/${projectId}/code/file`, {
        path: activeTab.path,
        content: activeTab.content,
      });

      setOpenTabs((prev) =>
        prev.map((t) => (t.path === activeTab.path ? { ...t, originalContent: t.content, isDirty: false } : t))
      );
    } catch (err: any) {
      alert(err.response?.data?.detail || 'Failed to save file.');
    } finally {
      setSavingFile(false);
    }
  };

  // Fullscreen toggle logic
  const toggleFullscreen = () => {
    if (!isFullscreen) {
      const elem = containerRef.current || document.documentElement;
      if (elem.requestFullscreen) {
        elem.requestFullscreen().catch(() => {});
      }
      setIsFullscreen(true);
    } else {
      if (document.fullscreenElement && document.exitFullscreen) {
        document.exitFullscreen().catch(() => {});
      }
      setIsFullscreen(false);
    }
  };

  useEffect(() => {
    const onFullscreenChange = () => {
      setIsFullscreen(Boolean(document.fullscreenElement));
    };
    document.addEventListener('fullscreenchange', onFullscreenChange);
    return () => document.removeEventListener('fullscreenchange', onFullscreenChange);
  }, []);

  // Keyboard shortcuts (Ctrl+S for Save, F11 for Full Screen)
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if ((e.ctrlKey || e.metaKey) && e.key === 's') {
        e.preventDefault();
        handleSaveFile();
      } else if (e.key === 'F11') {
        e.preventDefault();
        toggleFullscreen();
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  });

  // Run tests on working tree
  const handleRunTests = async () => {
    if (!projectId) return;
    setRunningTests(true);
    setBottomPanelOpen(true);
    setBottomTab('testRunner');
    setTestOutput('Executing automated test suite against modified working files...\n');
    try {
      const res = await api.post(`/projects/${projectId}/code/run-tests`);
      setTestStatus(res.data.status);
      setTestOutput(res.data.output);
    } catch (err: any) {
      setTestStatus('ERROR');
      setTestOutput(err.response?.data?.detail || 'Error launching test execution.');
    } finally {
      setRunningTests(false);
    }
  };

  // Create new file
  const handleCreateNewFile = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newFileName.trim()) return;
    const fullPath = newFileParent ? `${newFileParent}/${newFileName.trim()}` : newFileName.trim();
    try {
      await api.post(`/projects/${projectId}/code/file`, {
        path: fullPath,
        is_directory: false,
        content: '',
      });
      setIsCreatingFile(false);
      setNewFileName('');
      loadTreeAndDefects();
      handleOpenFile(fullPath);
    } catch (err: any) {
      alert(err.response?.data?.detail || 'Failed to create file.');
    }
  };

  // Post defect fix comment
  const handlePostDefectComment = async (defectId: string) => {
    if (!defectComment.trim()) return;
    setPostingComment(true);
    try {
      await api.post(`/projects/${projectId}/defects/${defectId}/comments`, {
        message: defectComment,
        status_change: 'FIXED',
      });
      setDefectComment('');
      loadTreeAndDefects();
      alert('Fix comment posted and status updated to FIXED!');
    } catch (err: any) {
      alert(err.response?.data?.detail || 'Failed to post comment.');
    } finally {
      setPostingComment(false);
    }
  };

  const toggleFolder = (path: string) => {
    setExpandedFolders((prev) => {
      const next = new Set(prev);
      if (next.has(path)) next.delete(path);
      else next.add(path);
      return next;
    });
  };

  const getFileIcon = (fileName: string) => {
    const ext = fileName.split('.').pop()?.toLowerCase();
    switch (ext) {
      case 'py':
        return <FileCode className="w-4 h-4 text-emerald-400 shrink-0" />;
      case 'ts':
      case 'tsx':
        return <FileCode className="w-4 h-4 text-sky-400 shrink-0" />;
      case 'js':
      case 'jsx':
        return <FileCode className="w-4 h-4 text-amber-400 shrink-0" />;
      case 'json':
        return <FileJson className="w-4 h-4 text-yellow-500 shrink-0" />;
      case 'md':
        return <FileText className="w-4 h-4 text-purple-400 shrink-0" />;
      default:
        return <File className="w-4 h-4 text-secondary shrink-0" />;
    }
  };

  // Render tree node
  const renderTreeNode = (node: FileNode, depth = 0) => {
    const isExpanded = expandedFolders.has(node.path);
    const isMatchingSearch = !searchFilter || node.name.toLowerCase().includes(searchFilter.toLowerCase());

    if (node.type === 'directory') {
      return (
        <div key={node.path} className="select-none">
          <div
            onClick={() => toggleFolder(node.path)}
            className="flex items-center gap-1.5 px-2 py-1 rounded hover:bg-white/5 cursor-pointer text-xs text-secondary hover:text-primary transition-colors"
            style={{ paddingLeft: `${depth * 12 + 8}px` }}
          >
            {isExpanded ? (
              <ChevronDown className="w-3.5 h-3.5 text-muted shrink-0" />
            ) : (
              <ChevronRight className="w-3.5 h-3.5 text-muted shrink-0" />
            )}
            {isExpanded ? (
              <FolderOpen className="w-4 h-4 text-amber-400 shrink-0" />
            ) : (
              <Folder className="w-4 h-4 text-amber-400 shrink-0" />
            )}
            <span className="truncate">{node.name}</span>
          </div>
          {isExpanded && node.children && (
            <div>
              {node.children.map((child) => renderTreeNode(child, depth + 1))}
            </div>
          )}
        </div>
      );
    }

    if (!isMatchingSearch) return null;

    const isCurrentActive = activeTabPath === node.path;
    return (
      <div
        key={node.path}
        onClick={() => handleOpenFile(node.path)}
        className={`flex items-center gap-2 px-2 py-1 rounded cursor-pointer text-xs transition-colors group ${
          isCurrentActive
            ? 'bg-brand/15 text-brand font-medium'
            : 'text-secondary hover:text-primary hover:bg-white/5'
        }`}
        style={{ paddingLeft: `${depth * 12 + 22}px` }}
      >
        {getFileIcon(node.name)}
        <span className="truncate flex-1">{node.name}</span>
      </div>
    );
  };

  return (
    <div
      ref={containerRef}
      className={`flex flex-col bg-[#1e1e1e] text-[#cccccc] font-sans overflow-hidden transition-all duration-200 ${
        isFullscreen
          ? 'fixed inset-0 z-50 w-screen h-screen rounded-none border-0'
          : 'h-[calc(100vh-4.5rem)] border border-border-card rounded-2xl shadow-glass-elevated'
      }`}
    >
      {/* VS Code Top Menu Bar */}
      <div className="h-10 bg-[#252526] border-b border-[#333333] flex items-center justify-between px-3 text-xs select-none">
        <div className="flex items-center gap-3">
          <button
            onClick={() => navigate('/projects/' + projectId)}
            className="flex items-center gap-1.5 text-secondary hover:text-primary transition-colors py-1 px-2 rounded hover:bg-white/5"
            title="Return to Project Overview"
          >
            <ArrowLeft className="w-3.5 h-3.5" />
            <span className="hidden sm:inline">Back</span>
          </button>

          <span className="text-[#555555]">|</span>

          {/* Project Switcher */}
          <div className="flex items-center gap-2 font-mono">
            <span className="text-secondary">Project:</span>
            <select
              value={projectId}
              onChange={(e) => {
                setProjectId(e.target.value);
                setOpenTabs([]);
                setActiveTabPath(null);
              }}
              className="bg-[#1e1e1e] border border-[#3c3c3c] rounded px-2 py-0.5 text-xs text-primary focus:outline-none focus:border-brand"
            >
              {projectsList.map((p) => (
                <option key={p.id} value={p.id}>
                  {p.name}
                </option>
              ))}
            </select>
          </div>

          <span className="px-2 py-0.5 rounded text-[10px] bg-[#333333] text-[#9cdcfe] font-mono">
            branch: {defaultBranch}
          </span>
        </div>

        {/* Action Controls */}
        <div className="flex items-center gap-2">
          <Button
            variant="secondary"
            size="sm"
            onClick={handleSaveFile}
            disabled={!activeTab || !activeTab.isDirty || savingFile}
            isLoading={savingFile}
            leftIcon={<Save className="w-3.5 h-3.5" />}
          >
            Save File
          </Button>

          <Button
            variant="primary"
            size="sm"
            onClick={handleRunTests}
            isLoading={runningTests}
            leftIcon={<Play className="w-3.5 h-3.5" />}
          >
            Run Tests & Verify Fix
          </Button>

          <button
            onClick={toggleFullscreen}
            className="px-3 py-1.5 rounded-lg bg-sky-500/20 hover:bg-sky-500/30 text-sky-200 hover:text-white border border-sky-400/50 hover:border-sky-300 transition-all shadow-sm flex items-center gap-1.5 text-xs font-semibold"
            title={isFullscreen ? "Exit Full Screen (Esc / F11)" : "Enter Full Screen (F11)"}
          >
            {isFullscreen ? (
              <Minimize2 className="w-3.5 h-3.5 text-sky-300 stroke-[2.5]" />
            ) : (
              <Maximize2 className="w-3.5 h-3.5 text-sky-300 stroke-[2.5]" />
            )}
            <span>{isFullscreen ? 'Exit Full Screen' : 'Full Screen'}</span>
          </button>
        </div>
      </div>

      {/* Main Workspace Area (Activity Bar + Sidebar + Editor) */}
      <div className="flex flex-1 overflow-hidden">
        {/* Activity Bar (VS Code leftmost icons) */}
        <div className="w-12 bg-[#333333] flex flex-col items-center py-3 gap-3 border-r border-[#252526] select-none shrink-0">
          <button
            onClick={() => setActiveSidebarView('files')}
            className={`p-2.5 rounded-lg transition-colors relative ${
              activeSidebarView === 'files'
                ? 'text-white bg-[#252526]'
                : 'text-[#bbbbbb] hover:text-white'
            }`}
            title="File Explorer (Ctrl+Shift+E)"
          >
            <Files className="w-5 h-5" />
            {activeSidebarView === 'files' && (
              <div className="absolute left-0 top-1.5 bottom-1.5 w-0.5 bg-brand" />
            )}
          </button>

          <button
            onClick={() => setActiveSidebarView('defects')}
            className={`p-2.5 rounded-lg transition-colors relative ${
              activeSidebarView === 'defects'
                ? 'text-white bg-[#252526]'
                : 'text-[#bbbbbb] hover:text-white'
            }`}
            title="Tester Defects & Collaboration"
          >
            <Bug className="w-5 h-5" />
            {defects.length > 0 && (
              <span className="absolute top-1 right-1 w-4 h-4 rounded-full bg-status-failed text-[9px] font-bold text-white flex items-center justify-center">
                {defects.length}
              </span>
            )}
            {activeSidebarView === 'defects' && (
              <div className="absolute left-0 top-1.5 bottom-1.5 w-0.5 bg-brand" />
            )}
          </button>

          <div className="flex-1" />

          <button
            onClick={() => setBottomPanelOpen(!bottomPanelOpen)}
            className={`p-2.5 rounded-lg transition-colors ${
              bottomPanelOpen
                ? 'text-brand bg-brand/15 border border-brand/30'
                : 'text-[#bbbbbb] hover:text-white hover:bg-white/10'
            }`}
            title="Toggle Test Runner / Output Terminal"
          >
            <Terminal className="w-5 h-5" />
          </button>
        </div>

        {/* Primary Sidebar (Explorer or Defect Triage) */}
        <div className="w-64 bg-[#252526] border-r border-[#333333] flex flex-col overflow-hidden shrink-0">
          {activeSidebarView === 'files' ? (
            <div className="flex flex-col h-full">
              {/* Explorer Header */}
              <div className="p-3 border-b border-[#333333] flex items-center justify-between">
                <span className="text-[11px] font-bold uppercase tracking-wider text-[#bbbbbb]">
                  Explorer: {projectName}
                </span>
                <div className="flex items-center gap-1">
                  <button
                    onClick={() => setIsCreatingFile(true)}
                    className="p-1 hover:bg-white/10 rounded text-secondary hover:text-primary transition-colors"
                    title="New File"
                  >
                    <Plus className="w-3.5 h-3.5" />
                  </button>
                  <button
                    onClick={loadTreeAndDefects}
                    className="p-1 hover:bg-white/10 rounded text-secondary hover:text-primary transition-colors"
                    title="Refresh Explorer"
                  >
                    <RefreshCw className="w-3.5 h-3.5" />
                  </button>
                </div>
              </div>

              {/* Quick Search */}
              <div className="p-2 border-b border-[#333333]">
                <div className="relative">
                  <Search className="w-3.5 h-3.5 text-muted absolute left-2.5 top-2" />
                  <input
                    type="text"
                    placeholder="Search files..."
                    value={searchFilter}
                    onChange={(e) => setSearchFilter(e.target.value)}
                    className="w-full h-7 bg-[#1e1e1e] border border-[#3c3c3c] rounded pl-8 pr-2 text-xs text-primary focus:outline-none focus:border-brand"
                  />
                </div>
              </div>

              {/* New File Inline Prompt */}
              {isCreatingFile && (
                <form onSubmit={handleCreateNewFile} className="p-2 bg-[#1e1e1e] border-b border-[#333333] space-y-1">
                  <input
                    type="text"
                    placeholder="filename.py"
                    value={newFileName}
                    onChange={(e) => setNewFileName(e.target.value)}
                    autoFocus
                    className="w-full h-7 bg-[#252526] border border-brand rounded px-2 text-xs text-primary focus:outline-none"
                  />
                  <div className="flex justify-end gap-1">
                    <button
                      type="button"
                      onClick={() => setIsCreatingFile(false)}
                      className="px-2 py-0.5 text-[10px] text-muted hover:text-primary"
                    >
                      Cancel
                    </button>
                    <button
                      type="submit"
                      className="px-2 py-0.5 text-[10px] bg-brand text-on-brand rounded"
                    >
                      Create
                    </button>
                  </div>
                </form>
              )}

              {/* File Tree List */}
              <div className="flex-1 overflow-y-auto p-1 py-2 space-y-0.5 font-mono">
                {fileTree.length === 0 ? (
                  <div className="p-4 text-center text-xs text-muted">
                    No files found in workspace.
                  </div>
                ) : (
                  fileTree.map((node) => renderTreeNode(node))
                )}
              </div>
            </div>
          ) : (
            /* Defect Triage View */
            <div className="flex flex-col h-full">
              <div className="p-3 border-b border-[#333333] flex items-center justify-between">
                <span className="text-[11px] font-bold uppercase tracking-wider text-[#bbbbbb] flex items-center gap-1.5">
                  <Bug className="w-3.5 h-3.5 text-status-failed" />
                  Tester Defect Queue ({defects.length})
                </span>
              </div>

              <div className="flex-1 overflow-y-auto p-2 space-y-2">
                {defects.length === 0 ? (
                  <div className="p-8 text-center space-y-2">
                    <CheckCircle2 className="w-8 h-8 text-emerald-400 mx-auto" />
                    <p className="text-xs font-semibold text-primary">Zero Open Defects!</p>
                    <p className="text-[11px] text-muted">All tests are currently passing in this repository.</p>
                  </div>
                ) : (
                  defects.map((d) => (
                    <div
                      key={d.id}
                      onClick={() => {
                        setSelectedDefect(d);
                        if (d.failing_file) {
                          handleOpenFile(d.failing_file, d.failing_line);
                        }
                      }}
                      className={`p-2.5 rounded-lg border text-xs cursor-pointer transition-all space-y-1.5 ${
                        selectedDefect?.id === d.id
                          ? 'bg-status-failed/10 border-status-failed/40 text-primary'
                          : 'bg-[#1e1e1e] border-[#333333] hover:border-[#555555] text-secondary'
                      }`}
                    >
                      <div className="flex items-center justify-between">
                        <span className="px-1.5 py-0.5 rounded text-[9px] font-bold bg-status-failed/20 text-status-failed uppercase font-mono">
                          {d.category}
                        </span>
                        <span className="text-[10px] text-muted font-mono">{d.status}</span>
                      </div>
                      <p className="font-semibold text-primary line-clamp-2 leading-tight">{d.summary}</p>
                      {d.failing_file && (
                        <div className="text-[10px] font-mono text-sky-400 truncate flex items-center gap-1">
                          <FileCode className="w-3 h-3 shrink-0" />
                          <span>{d.failing_file}:{d.failing_line || 1}</span>
                        </div>
                      )}
                    </div>
                  ))
                )}
              </div>

              {/* Defect Quick Action Panel */}
              {selectedDefect && (
                <div className="p-3 border-t border-[#333333] bg-[#1e1e1e] space-y-2">
                  <p className="text-[11px] font-semibold text-primary truncate">Fix Notes for Tester:</p>
                  <textarea
                    value={defectComment}
                    onChange={(e) => setDefectComment(e.target.value)}
                    placeholder="e.g., Patched boundary exception on line 42, added fallback..."
                    rows={2}
                    className="w-full bg-[#252526] border border-[#3c3c3c] rounded p-2 text-xs text-primary focus:outline-none focus:border-brand resize-none"
                  />
                  <Button
                    variant="primary"
                    size="sm"
                    className="w-full"
                    onClick={() => handlePostDefectComment(selectedDefect.id)}
                    isLoading={postingComment}
                    leftIcon={<Send className="w-3.5 h-3.5" />}
                  >
                    Mark as FIXED
                  </Button>
                </div>
              )}
            </div>
          )}
        </div>

        {/* Editor Main Canvas */}
        <div className="flex-1 flex flex-col bg-[#1e1e1e] overflow-hidden">
          {/* Tabs Bar */}
          <div className="h-9 bg-[#252526] border-b border-[#333333] flex items-center overflow-x-auto select-none no-scrollbar">
            {openTabs.length === 0 ? (
              <span className="text-xs text-muted px-4 italic">No files open. Select a file from the Explorer to begin coding.</span>
            ) : (
              openTabs.map((tab) => {
                const isActive = activeTabPath === tab.path;
                return (
                  <div
                    key={tab.path}
                    onClick={() => setActiveTabPath(tab.path)}
                    className={`h-full flex items-center gap-2 px-3 text-xs border-r border-[#333333] cursor-pointer transition-colors max-w-xs group ${
                      isActive
                        ? 'bg-[#1e1e1e] text-primary border-t-2 border-t-brand font-medium'
                        : 'bg-[#2d2d2d] text-secondary hover:text-primary hover:bg-[#282828]'
                    }`}
                  >
                    {getFileIcon(tab.name)}
                    <span className="truncate">{tab.name}</span>
                    {tab.isDirty && (
                      <span className="w-2 h-2 rounded-full bg-amber-400 shrink-0" title="Unsaved changes" />
                    )}
                    <button
                      onClick={(e) => handleCloseTab(tab.path, e)}
                      className="p-0.5 rounded hover:bg-white/10 text-muted hover:text-primary opacity-0 group-hover:opacity-100 transition-opacity"
                    >
                      <X className="w-3 h-3" />
                    </button>
                  </div>
                );
              })
            )}
          </div>

          {/* Monaco Editor Component */}
          <div className="flex-1 relative overflow-hidden">
            {activeTab ? (
              <Editor
                height="100%"
                language={activeTab.language}
                value={activeTab.content}
                theme={editorTheme}
                onChange={handleEditorChange}
                onMount={(editor) => {
                  editorRef.current = editor;
                  editor.onDidChangeCursorPosition((e) => {
                    setCursorPos({
                      line: e.position.lineNumber,
                      col: e.position.column,
                    });
                  });
                }}
                options={{
                  fontSize: 13,
                  fontFamily: "'JetBrains Mono', 'Fira Code', Consolas, 'Courier New', monospace",
                  minimap: { enabled: true },
                  scrollBeyondLastLine: false,
                  wordWrap: 'on',
                  automaticLayout: true,
                  renderWhitespace: 'selection',
                  tabSize: 4,
                  bracketPairColorization: { enabled: true },
                }}
              />
            ) : (
              <div className="h-full flex flex-col items-center justify-center text-center p-8 space-y-4 text-muted">
                <FileCode className="w-16 h-16 opacity-30" />
                <div className="space-y-1">
                  <h3 className="text-base font-bold text-primary">Astra Code Studio</h3>
                  <p className="text-xs max-w-md mx-auto">
                    Open a file from the explorer on the left or select a Tester Defect to inspect the failing code and implement fixes.
                  </p>
                </div>
                <div className="flex items-center gap-3 text-xs font-mono">
                  <span className="px-2 py-1 rounded bg-field border border-border-card">Ctrl+S : Save</span>
                  <span className="px-2 py-1 rounded bg-field border border-border-card">Alt+Click : Multi-cursor</span>
                </div>
              </div>
            )}
          </div>

          {/* Bottom Panel (Integrated Test Runner & Terminal) */}
          {bottomPanelOpen && (
            <div className="h-56 bg-[#181818] border-t border-[#333333] flex flex-col shrink-0 select-none">
              {/* Bottom Panel Header */}
              <div className="h-8 bg-[#252526] border-b border-[#333333] flex items-center justify-between px-3 text-xs">
                <div className="flex items-center gap-3">
                  <button
                    onClick={() => setBottomTab('testRunner')}
                    className={`h-full flex items-center gap-1.5 px-2 font-semibold uppercase tracking-wider text-[10px] transition-colors ${
                      bottomTab === 'testRunner'
                        ? 'text-brand border-b-2 border-b-brand'
                        : 'text-muted hover:text-primary'
                    }`}
                  >
                    <Play className="w-3 h-3" /> Test Runner & Verifier
                  </button>

                  <button
                    onClick={() => setBottomTab('terminal')}
                    className={`h-full flex items-center gap-1.5 px-2 font-semibold uppercase tracking-wider text-[10px] transition-colors ${
                      bottomTab === 'terminal'
                        ? 'text-brand border-b-2 border-b-brand'
                        : 'text-muted hover:text-primary'
                    }`}
                  >
                    <Terminal className="w-3 h-3" /> Output Console
                  </button>
                </div>

                <div className="flex items-center gap-2">
                  {testStatus && (
                    <span
                      className={`px-2 py-0.5 rounded text-[10px] font-bold font-mono ${
                        testStatus === 'PASSED'
                          ? 'bg-emerald-500/15 text-emerald-400 border border-emerald-500/30'
                          : 'bg-status-failed/15 text-status-failed border border-status-failed/30'
                      }`}
                    >
                      {testStatus}
                    </span>
                  )}
                  <button
                    onClick={() => setBottomPanelOpen(false)}
                    className="p-1 text-muted hover:text-primary rounded hover:bg-white/10"
                    title="Close Panel"
                  >
                    <X className="w-3.5 h-3.5" />
                  </button>
                </div>
              </div>

              {/* Bottom Output Console Area */}
              <div className="flex-1 p-3 overflow-y-auto font-mono text-xs text-[#d4d4d4] leading-relaxed whitespace-pre-wrap select-text">
                {testOutput}
              </div>
            </div>
          )}

          {/* Status Bar (VS Code bottom strip) */}
          <div className="h-6 bg-[#007acc] text-white flex items-center justify-between px-3 text-[11px] font-mono select-none">
            <div className="flex items-center gap-4">
              <span className="flex items-center gap-1">
                <Sparkles className="w-3 h-3" /> Astra Studio
              </span>
              <span>{defaultBranch}</span>
              {activeTab && (
                <span>
                  Ln {cursorPos.line}, Col {cursorPos.col}
                </span>
              )}
            </div>

            <div className="flex items-center gap-4">
              {activeTab && (
                <>
                  <span>UTF-8</span>
                  <span className="capitalize">{activeTab.language}</span>
                  <span>{activeTab.isDirty ? '● Unsaved' : 'Saved'}</span>
                </>
              )}
              <span className="opacity-80">Developer Mode</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
