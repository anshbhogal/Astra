import React, { useState, useEffect, useRef, useMemo } from 'react';
import {
  Network,
  Layers,
  FileCode,
  Cpu,
  Search,
  ZoomIn,
  ZoomOut,
  Maximize2,
  List,
  Download,
  ChevronRight,
  X
} from 'lucide-react';

export interface GraphNodeData {
  id: string;
  label: string;
  type: string;
  properties?: any;
}

export interface GraphEdgeData {
  source: string;
  target: string;
  type?: string;
  relationship?: string;
  confidence?: number;
  properties?: any;
}

interface KnowledgeGraphVisualizerProps {
  graph: {
    nodes: GraphNodeData[];
    edges: GraphEdgeData[];
  };
  projectName?: string;
  onSelectNode?: (nodeId: string) => void;
}

interface SimulatedNode extends GraphNodeData {
  x: number;
  y: number;
  vx: number;
  vy: number;
  inDegree: number;
  outDegree: number;
  radius: number;
}

interface SimulatedEdge extends GraphEdgeData {
  sourceNode: SimulatedNode;
  targetNode: SimulatedNode;
}

export const KnowledgeGraphVisualizer: React.FC<KnowledgeGraphVisualizerProps> = ({
  graph,
  projectName = 'Repository',
  onSelectNode,
}) => {
  // View states
  const [viewMode, setViewMode] = useState<'modules' | 'full' | 'table'>('modules');
  const [searchQuery, setSearchQuery] = useState<string>('');
  const [selectedNodeId, setSelectedNodeId] = useState<string | null>(null);
  const [hoveredNodeId, setHoveredNodeId] = useState<string | null>(null);
  
  // Type toggles for Full Graph mode
  const [showModules, setShowModules] = useState<boolean>(true);
  const [showEndpoints, setShowEndpoints] = useState<boolean>(true);
  const [showFunctions, setShowFunctions] = useState<boolean>(false);

  // Canvas pan & zoom states
  const [zoom, setZoom] = useState<number>(1);
  const [pan, setPan] = useState<{ x: number; y: number }>({ x: 0, y: 0 });
  const [isPanning, setIsPanning] = useState<boolean>(false);
  const [dragStart, setDragStart] = useState<{ x: number; y: number }>({ x: 0, y: 0 });

  // Node drag state
  const [draggedNodeId, setDraggedNodeId] = useState<string | null>(null);

  const svgRef = useRef<SVGSVGElement | null>(null);
  const containerRef = useRef<HTMLDivElement | null>(null);

  // 1. Process and derive Module-to-Module dependencies
  const processedGraph = useMemo(() => {
    const rawNodes = graph?.nodes || [];
    const rawEdges = graph?.edges || [];

    if (viewMode === 'modules') {
      const moduleNodes = rawNodes.filter((n) => n.type === 'MODULE');
      const moduleIds = new Set(moduleNodes.map((n) => n.id));

      const funcToModule = new Map<string, string>();
      rawEdges.forEach((e) => {
        const rel = (e.relationship || e.type || '').toUpperCase();
        if (rel === 'DEFINES' && moduleIds.has(e.source)) {
          funcToModule.set(e.target, e.source);
        }
      });

      rawNodes.forEach((n) => {
        if (n.type === 'FUNCTION') {
          const parts = n.id.split(':');
          if (parts.length >= 3) {
            const relPath = parts[1].replace(/\\/g, '/');
            const modId = `module:${relPath}`;
            if (moduleIds.has(modId)) {
              funcToModule.set(n.id, modId);
            }
          }
        }
      });

      const moduleEdgeMap = new Map<string, GraphEdgeData>();

      rawEdges.forEach((e) => {
        const rel = (e.relationship || e.type || '').toUpperCase();
        
        if (moduleIds.has(e.source) && moduleIds.has(e.target) && e.source !== e.target) {
          const key = `${e.source}->${e.target}`;
          moduleEdgeMap.set(key, {
            source: e.source,
            target: e.target,
            relationship: rel === 'CONTAINS' ? 'DEPENDS_ON' : rel,
            confidence: e.confidence || 1.0,
          });
          return;
        }

        if (rel === 'CALLS') {
          const modSource = funcToModule.get(e.source);
          const modTarget = funcToModule.get(e.target);
          if (modSource && modTarget && modSource !== modTarget) {
            const key = `${modSource}->${modTarget}`;
            if (!moduleEdgeMap.has(key)) {
              moduleEdgeMap.set(key, {
                source: modSource,
                target: modTarget,
                relationship: 'DEPENDS_ON',
                confidence: 0.9,
              });
            }
          }
        }
      });

      if (moduleEdgeMap.size === 0 && moduleNodes.length > 1) {
        const dirGroups = new Map<string, string[]>();
        moduleNodes.forEach((m) => {
          const label = m.label || m.id;
          const parts = label.split('/');
          const dir = parts.length > 1 ? parts.slice(0, -1).join('/') : 'root';
          if (!dirGroups.has(dir)) dirGroups.set(dir, []);
          dirGroups.get(dir)!.push(m.id);
        });

        dirGroups.forEach((ids) => {
          for (let i = 0; i < ids.length - 1; i++) {
            const key = `${ids[i]}->${ids[i + 1]}`;
            moduleEdgeMap.set(key, {
              source: ids[i],
              target: ids[i + 1],
              relationship: 'CO_LOCATED',
              confidence: 0.7,
            });
          }
        });
      }

      return {
        nodes: moduleNodes,
        edges: Array.from(moduleEdgeMap.values()),
      };
    } else {
      const allowedTypes = new Set<string>();
      allowedTypes.add('PROJECT');
      if (showModules) allowedTypes.add('MODULE');
      if (showEndpoints) allowedTypes.add('ENDPOINT');
      if (showFunctions) allowedTypes.add('FUNCTION');

      const filteredNodes = rawNodes.filter((n) => allowedTypes.has(n.type));
      const allowedNodeIds = new Set(filteredNodes.map((n) => n.id));

      const filteredEdges = rawEdges.filter(
        (e) => allowedNodeIds.has(e.source) && allowedNodeIds.has(e.target)
      );

      return {
        nodes: filteredNodes,
        edges: filteredEdges,
      };
    }
  }, [graph, viewMode, showModules, showEndpoints, showFunctions]);

  // 2. Node Simulation Layout
  const [simulatedNodes, setSimulatedNodes] = useState<SimulatedNode[]>([]);

  useEffect(() => {
    const { nodes, edges } = processedGraph;
    if (nodes.length === 0) {
      setSimulatedNodes([]);
      return;
    }

    const width = 900;
    const height = 560;
    const cx = width / 2;
    const cy = height / 2;

    const inDeg = new Map<string, number>();
    const outDeg = new Map<string, number>();
    edges.forEach((e) => {
      outDeg.set(e.source, (outDeg.get(e.source) || 0) + 1);
      inDeg.set(e.target, (inDeg.get(e.target) || 0) + 1);
    });

    const radius = Math.min(width, height) * 0.38;
    const total = nodes.length;

    let initNodes: SimulatedNode[] = nodes.map((n, idx) => {
      const angle = (idx / Math.max(1, total)) * 2 * Math.PI;
      const jitter = (idx % 2 === 0 ? 1 : 0.85);
      const r = radius * jitter;
      const x = cx + r * Math.cos(angle);
      const y = cy + r * Math.sin(angle);

      let nodeRadius = 36;
      if (n.type === 'PROJECT') nodeRadius = 42;
      else if (n.type === 'MODULE') nodeRadius = 38;
      else if (n.type === 'ENDPOINT') nodeRadius = 32;
      else if (n.type === 'FUNCTION') nodeRadius = 26;

      return {
        ...n,
        x,
        y,
        vx: 0,
        vy: 0,
        inDegree: inDeg.get(n.id) || 0,
        outDegree: outDeg.get(n.id) || 0,
        radius: nodeRadius,
      };
    });

    const nodeMap = new Map<string, SimulatedNode>();
    initNodes.forEach((n) => nodeMap.set(n.id, n));

    const iterations = Math.min(80, Math.max(30, total * 3));
    const kRepel = 7000;
    const kSpring = 0.04;
    const targetDist = 140;

    for (let iter = 0; iter < iterations; iter++) {
      for (let i = 0; i < initNodes.length; i++) {
        for (let j = i + 1; j < initNodes.length; j++) {
          const a = initNodes[i];
          const b = initNodes[j];
          const dx = b.x - a.x;
          const dy = b.y - a.y;
          const distSq = dx * dx + dy * dy + 100;
          const dist = Math.sqrt(distSq);
          const force = kRepel / distSq;
          const fx = (dx / dist) * force;
          const fy = (dy / dist) * force;
          a.vx -= fx;
          a.vy -= fy;
          b.vx += fx;
          b.vy += fy;
        }
      }

      edges.forEach((e) => {
        const a = nodeMap.get(e.source);
        const b = nodeMap.get(e.target);
        if (a && b) {
          const dx = b.x - a.x;
          const dy = b.y - a.y;
          const dist = Math.sqrt(dx * dx + dy * dy) || 1;
          const force = (dist - targetDist) * kSpring;
          const fx = (dx / dist) * force;
          const fy = (dy / dist) * force;
          a.vx += fx;
          a.vy += fy;
          b.vx += fx;
          b.vy += fy;
        }
      });

      const damping = 0.75;
      initNodes.forEach((n) => {
        n.vx += (cx - n.x) * 0.01;
        n.vy += (cy - n.y) * 0.01;
        n.x += n.vx * 0.15;
        n.y += n.vy * 0.15;
        n.vx *= damping;
        n.vy *= damping;
      });
    }

    setSimulatedNodes(initNodes);
  }, [processedGraph]);

  const simulatedNodeMap = useMemo(() => {
    const map = new Map<string, SimulatedNode>();
    simulatedNodes.forEach((n) => map.set(n.id, n));
    return map;
  }, [simulatedNodes]);

  const simulatedEdges = useMemo<SimulatedEdge[]>(() => {
    const result: SimulatedEdge[] = [];
    processedGraph.edges.forEach((e) => {
      const sourceNode = simulatedNodeMap.get(e.source);
      const targetNode = simulatedNodeMap.get(e.target);
      if (sourceNode && targetNode) {
        result.push({
          ...e,
          sourceNode,
          targetNode,
        });
      }
    });
    return result;
  }, [processedGraph.edges, simulatedNodeMap]);

  const selectedNode = useMemo(() => {
    if (!selectedNodeId) return null;
    return simulatedNodeMap.get(selectedNodeId) || null;
  }, [selectedNodeId, simulatedNodeMap]);

  const neighborNodeIds = useMemo(() => {
    if (!selectedNodeId) return new Set<string>();
    const neighbors = new Set<string>();
    neighbors.add(selectedNodeId);
    simulatedEdges.forEach((e) => {
      if (e.source === selectedNodeId) neighbors.add(e.target);
      if (e.target === selectedNodeId) neighbors.add(e.source);
    });
    return neighbors;
  }, [selectedNodeId, simulatedEdges]);

  const searchMatchedIds = useMemo(() => {
    if (!searchQuery.trim()) return null;
    const q = searchQuery.toLowerCase();
    const set = new Set<string>();
    simulatedNodes.forEach((n) => {
      if (n.label.toLowerCase().includes(q) || n.id.toLowerCase().includes(q)) {
        set.add(n.id);
      }
    });
    return set;
  }, [searchQuery, simulatedNodes]);

  const handleNodeMouseDown = (nodeId: string, e: React.MouseEvent) => {
    e.stopPropagation();
    setDraggedNodeId(nodeId);
    setSelectedNodeId(nodeId);
    if (onSelectNode) onSelectNode(nodeId);
  };

  const handleCanvasMouseMove = (e: React.MouseEvent) => {
    if (draggedNodeId) {
      const svg = svgRef.current;
      if (!svg) return;
      const rect = svg.getBoundingClientRect();
      const clientX = e.clientX - rect.left;
      const clientY = e.clientY - rect.top;
      const svgX = (clientX - pan.x) / zoom;
      const svgY = (clientY - pan.y) / zoom;

      setSimulatedNodes((prev) =>
        prev.map((n) => (n.id === draggedNodeId ? { ...n, x: svgX, y: svgY } : n))
      );
    } else if (isPanning) {
      setPan({
        x: e.clientX - dragStart.x,
        y: e.clientY - dragStart.y,
      });
    }
  };

  const handleCanvasMouseUp = () => {
    setDraggedNodeId(null);
    setIsPanning(false);
  };

  const handleCanvasMouseDown = (e: React.MouseEvent) => {
    if (e.target === svgRef.current || (e.target as HTMLElement).tagName === 'svg' || (e.target as HTMLElement).tagName === 'rect') {
      setIsPanning(true);
      setDragStart({ x: e.clientX - pan.x, y: e.clientY - pan.y });
    }
  };

  const handleWheel = (e: React.WheelEvent) => {
    e.preventDefault();
    const zoomFactor = e.deltaY < 0 ? 1.1 : 0.9;
    setZoom((prev) => Math.min(2.5, Math.max(0.3, prev * zoomFactor)));
  };

  const resetView = () => {
    setZoom(1);
    setPan({ x: 0, y: 0 });
    setSelectedNodeId(null);
  };

  const centerOnNode = (node: SimulatedNode) => {
    const width = containerRef.current?.clientWidth || 900;
    const height = containerRef.current?.clientHeight || 560;
    setPan({
      x: width / 2 - node.x * zoom,
      y: height / 2 - node.y * zoom,
    });
    setSelectedNodeId(node.id);
  };

  const getNodeColor = (type: string) => {
    switch (type) {
      case 'PROJECT':
        return {
          fill: '#f59e0b',
          bg: 'rgba(245, 158, 11, 0.15)',
          border: '#fbbf24',
          text: 'text-amber-400',
        };
      case 'MODULE':
        return {
          fill: '#06b6d4',
          bg: 'rgba(6, 182, 212, 0.15)',
          border: '#22d3ee',
          text: 'text-cyan-400',
        };
      case 'ENDPOINT':
        return {
          fill: '#10b981',
          bg: 'rgba(16, 185, 129, 0.15)',
          border: '#34d399',
          text: 'text-emerald-400',
        };
      case 'FUNCTION':
      default:
        return {
          fill: '#6366f1',
          bg: 'rgba(99, 102, 241, 0.15)',
          border: '#818cf8',
          text: 'text-indigo-400',
        };
    }
  };

  const getEdgeColor = (rel?: string) => {
    const r = (rel || '').toUpperCase();
    if (r === 'DEPENDS_ON' || r === 'IMPORTS') return '#22d3ee';
    if (r === 'HANDLED_BY' || r === 'EXPOSES') return '#34d399';
    if (r === 'CALLS') return '#818cf8';
    if (r === 'DEFINES') return '#a78bfa';
    if (r === 'CONTAINS') return '#fbbf24';
    return '#64748b';
  };

  const handleExportSvg = () => {
    if (!svgRef.current) return;
    const svgData = new XMLSerializer().serializeToString(svgRef.current);
    const blob = new Blob([svgData], { type: 'image/svg+xml;charset=utf-8' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = `${projectName.toLowerCase().replace(/[^a-z0-9]/g, '_')}_knowledge_graph.svg`;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(url);
  };

  return (
    <div className="space-y-4">
      {/* Top Interactive Graph Controls Bar */}
      <div className="glass-card rounded-2xl p-4 border border-slate-800 flex flex-col lg:flex-row items-stretch lg:items-center justify-between gap-4">
        {/* Left: View Mode Tabs & Stats */}
        <div className="flex flex-wrap items-center gap-3">
          <div className="flex items-center bg-slate-950 border border-slate-800 rounded-xl p-1 text-xs">
            <button
              onClick={() => setViewMode('modules')}
              className={`px-3 py-1.5 rounded-lg font-bold flex items-center gap-1.5 transition-all ${
                viewMode === 'modules'
                  ? 'bg-indigo-600 text-white shadow-md shadow-indigo-600/30'
                  : 'text-slate-400 hover:text-slate-200'
              }`}
            >
              <Layers className="w-3.5 h-3.5" /> Module Architecture ({processedGraph.nodes.filter(n => n.type === 'MODULE').length})
            </button>
            <button
              onClick={() => setViewMode('full')}
              className={`px-3 py-1.5 rounded-lg font-bold flex items-center gap-1.5 transition-all ${
                viewMode === 'full'
                  ? 'bg-indigo-600 text-white shadow-md shadow-indigo-600/30'
                  : 'text-slate-400 hover:text-slate-200'
              }`}
            >
              <Network className="w-3.5 h-3.5" /> Full Knowledge Graph ({graph?.nodes?.length || 0})
            </button>
            <button
              onClick={() => setViewMode('table')}
              className={`px-3 py-1.5 rounded-lg font-bold flex items-center gap-1.5 transition-all ${
                viewMode === 'table'
                  ? 'bg-indigo-600 text-white shadow-md shadow-indigo-600/30'
                  : 'text-slate-400 hover:text-slate-200'
              }`}
            >
              <List className="w-3.5 h-3.5" /> Table List
            </button>
          </div>

          <div className="hidden sm:flex items-center gap-2 px-3 py-1.5 rounded-xl bg-slate-900/60 border border-slate-800 text-[11px] font-mono text-slate-400">
            <span>Nodes: <strong className="text-white">{processedGraph.nodes.length}</strong></span>
            <span>•</span>
            <span>Connections: <strong className="text-indigo-400">{processedGraph.edges.length}</strong></span>
          </div>
        </div>

        {/* Right: Search, Filter Checks & Export */}
        <div className="flex flex-wrap items-center gap-3">
          <div className="relative flex-1 sm:w-60">
            <Search className="w-3.5 h-3.5 text-slate-500 absolute left-3 top-1/2 -translate-y-1/2" />
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="Search module or symbol..."
              className="w-full bg-slate-950 border border-slate-800 rounded-xl pl-8 pr-3 py-1.5 text-xs text-white placeholder-slate-500 focus:outline-none focus:border-indigo-500/50"
            />
            {searchQuery && (
              <button
                onClick={() => setSearchQuery('')}
                className="absolute right-2.5 top-1/2 -translate-y-1/2 text-slate-500 hover:text-slate-300 text-xs"
              >
                ×
              </button>
            )}
          </div>

          {viewMode === 'full' && (
            <div className="flex items-center gap-2 text-[11px] font-semibold text-slate-300">
              <label className="flex items-center gap-1 cursor-pointer">
                <input
                  type="checkbox"
                  checked={showModules}
                  onChange={(e) => setShowModules(e.target.checked)}
                  className="rounded bg-slate-900 border-slate-700 text-cyan-500 focus:ring-0"
                />
                <span className="text-cyan-400">Modules</span>
              </label>
              <label className="flex items-center gap-1 cursor-pointer">
                <input
                  type="checkbox"
                  checked={showEndpoints}
                  onChange={(e) => setShowEndpoints(e.target.checked)}
                  className="rounded bg-slate-900 border-slate-700 text-emerald-500 focus:ring-0"
                />
                <span className="text-emerald-400">Endpoints</span>
              </label>
              <label className="flex items-center gap-1 cursor-pointer">
                <input
                  type="checkbox"
                  checked={showFunctions}
                  onChange={(e) => setShowFunctions(e.target.checked)}
                  className="rounded bg-slate-900 border-slate-700 text-indigo-500 focus:ring-0"
                />
                <span className="text-indigo-400">Functions</span>
              </label>
            </div>
          )}

          <button
            onClick={handleExportSvg}
            className="p-2 rounded-xl bg-slate-900 hover:bg-slate-800 border border-slate-800 text-slate-400 hover:text-slate-200 transition-colors"
            title="Export Architecture Diagram (SVG)"
          >
            <Download className="w-4 h-4" />
          </button>
        </div>
      </div>

      {/* Main Graph Visualization Stage */}
      {viewMode !== 'table' ? (
        <div
          ref={containerRef}
          className="relative w-full h-[580px] bg-slate-950/90 rounded-2xl border border-slate-800 overflow-hidden shadow-2xl select-none"
        >
          <div className="absolute top-4 left-4 z-10 pointer-events-none flex items-center gap-2">
            <span className="px-2.5 py-1 rounded-lg bg-slate-900/90 border border-slate-800 text-[11px] font-mono text-slate-400 backdrop-blur-md">
              {viewMode === 'modules' ? 'Module Dependency Architecture' : 'Semantic Knowledge Graph'} • Drag nodes to organize • Click to inspect
            </span>
          </div>

          <div className="absolute bottom-4 right-4 z-10 flex items-center gap-1.5 bg-slate-900/90 border border-slate-800 rounded-xl p-1 shadow-xl backdrop-blur-md">
            <button
              onClick={() => setZoom((z) => Math.min(2.5, z + 0.15))}
              className="p-1.5 rounded-lg text-slate-400 hover:text-white hover:bg-slate-800 transition-colors"
              title="Zoom In"
            >
              <ZoomIn className="w-4 h-4" />
            </button>
            <button
              onClick={() => setZoom((z) => Math.max(0.3, z - 0.15))}
              className="p-1.5 rounded-lg text-slate-400 hover:text-white hover:bg-slate-800 transition-colors"
              title="Zoom Out"
            >
              <ZoomOut className="w-4 h-4" />
            </button>
            <button
              onClick={resetView}
              className="p-1.5 rounded-lg text-slate-400 hover:text-white hover:bg-slate-800 transition-colors"
              title="Reset View"
            >
              <Maximize2 className="w-4 h-4" />
            </button>
          </div>

          <svg
            ref={svgRef}
            className="w-full h-full cursor-grab active:cursor-grabbing"
            onMouseDown={handleCanvasMouseDown}
            onMouseMove={handleCanvasMouseMove}
            onMouseUp={handleCanvasMouseUp}
            onWheel={handleWheel}
          >
            <defs>
              <pattern id="graph-grid" width="30" height="30" patternUnits="userSpaceOnUse">
                <circle cx="2" cy="2" r="1" fill="#1e293b" opacity="0.6" />
              </pattern>

              {['#22d3ee', '#34d399', '#818cf8', '#a78bfa', '#fbbf24', '#64748b'].map((color) => (
                <marker
                  key={color}
                  id={`arrow-${color.replace('#', '')}`}
                  viewBox="0 0 10 10"
                  refX="22"
                  refY="5"
                  markerWidth="6"
                  markerHeight="6"
                  orient="auto-start-reverse"
                >
                  <path d="M 0 1 L 10 5 L 0 9 z" fill={color} />
                </marker>
              ))}
            </defs>

            <rect width="100%" height="100%" fill="url(#graph-grid)" />

            <g transform={`translate(${pan.x}, ${pan.y}) scale(${zoom})`}>
              {/* Layer 1: Edges */}
              <g className="edges-layer">
                {simulatedEdges.map((edge, idx) => {
                  const s = edge.sourceNode;
                  const t = edge.targetNode;
                  const isHighlighted =
                    selectedNodeId && (edge.source === selectedNodeId || edge.target === selectedNodeId);
                  const isDimmed =
                    selectedNodeId && !isHighlighted;
                  const edgeColor = getEdgeColor(edge.relationship);

                  const dx = t.x - s.x;
                  const dy = t.y - s.y;
                  const dr = Math.sqrt(dx * dx + dy * dy);
                  const pathData = `M ${s.x} ${s.y} A ${dr * 1.2} ${dr * 1.2} 0 0,1 ${t.x} ${t.y}`;

                  return (
                    <g key={`edge-${idx}`} className="transition-opacity duration-300">
                      <path
                        d={pathData}
                        fill="none"
                        stroke={edgeColor}
                        strokeWidth={isHighlighted ? 2.5 : 1.2}
                        strokeDasharray={edge.relationship === 'CO_LOCATED' ? '4 4' : undefined}
                        strokeOpacity={isDimmed ? 0.15 : isHighlighted ? 1 : 0.45}
                        markerEnd={`url(#arrow-${edgeColor.replace('#', '')})`}
                      />
                      {isHighlighted && (
                        <text
                          x={(s.x + t.x) / 2}
                          y={(s.y + t.y) / 2 - 8}
                          fill={edgeColor}
                          fontSize="9"
                          fontFamily="monospace"
                          fontWeight="bold"
                          textAnchor="middle"
                          className="pointer-events-none select-none bg-slate-900 px-1"
                        >
                          {edge.relationship}
                        </text>
                      )}
                    </g>
                  );
                })}
              </g>

              {/* Layer 2: Nodes */}
              <g className="nodes-layer">
                {simulatedNodes.map((node) => {
                  const isSelected = selectedNodeId === node.id;
                  const isNeighbor = neighborNodeIds.has(node.id);
                  const isSearchMatch = searchMatchedIds ? searchMatchedIds.has(node.id) : true;
                  const isDimmed = (selectedNodeId && !isNeighbor) || (searchMatchedIds && !isSearchMatch);
                  const isHovered = hoveredNodeId === node.id;
                  const colors = getNodeColor(node.type);

                  const displayLabel = node.label.split('/').pop() || node.label;
                  const dirPath = node.label.includes('/')
                    ? node.label.substring(0, node.label.lastIndexOf('/'))
                    : '';

                  return (
                    <g
                      key={node.id}
                      transform={`translate(${node.x}, ${node.y})`}
                      className={`cursor-pointer transition-transform duration-150 ${
                        isHovered || isSelected ? 'scale-105' : ''
                      }`}
                      style={{ opacity: isDimmed ? 0.22 : 1 }}
                      onMouseDown={(e) => handleNodeMouseDown(node.id, e)}
                      onMouseEnter={() => setHoveredNodeId(node.id)}
                      onMouseLeave={() => setHoveredNodeId(null)}
                    >
                      {(isSelected || isHovered) && (
                        <circle
                          r={node.radius + 8}
                          fill="none"
                          stroke={colors.border}
                          strokeWidth="2"
                          strokeDasharray="4 3"
                          opacity="0.8"
                        />
                      )}

                      <rect
                        x={-node.radius - 14}
                        y={-node.radius + 6}
                        width={(node.radius + 14) * 2}
                        height={node.radius * 1.5}
                        rx="14"
                        fill="#0b1120"
                        stroke={isSelected ? '#ffffff' : colors.border}
                        strokeWidth={isSelected ? 2 : 1.2}
                      />

                      <circle
                        cx="0"
                        cy={-node.radius + 18}
                        r="9"
                        fill={colors.bg}
                        stroke={colors.border}
                        strokeWidth="1"
                      />

                      <text
                        x="0"
                        y={node.radius * 0.15}
                        fill="#f8fafc"
                        fontSize="11"
                        fontWeight="700"
                        fontFamily="monospace"
                        textAnchor="middle"
                        className="pointer-events-none select-none"
                      >
                        {displayLabel.length > 16 ? displayLabel.substring(0, 14) + '..' : displayLabel}
                      </text>

                      <text
                        x="0"
                        y={node.radius * 0.42}
                        fill="#64748b"
                        fontSize="8.5"
                        fontFamily="monospace"
                        textAnchor="middle"
                        className="pointer-events-none select-none"
                      >
                        {node.type === 'MODULE'
                          ? dirPath ? `${dirPath}/` : 'root module'
                          : node.type}
                      </text>

                      <g transform={`translate(${node.radius + 4}, ${-node.radius + 10})`}>
                        <rect
                          x="-10"
                          y="-7"
                          width="20"
                          height="14"
                          rx="7"
                          fill="#1e293b"
                          stroke={colors.border}
                          strokeWidth="1"
                        />
                        <text
                          x="0"
                          y="3"
                          fill={colors.border}
                          fontSize="8"
                          fontWeight="bold"
                          fontFamily="monospace"
                          textAnchor="middle"
                          className="pointer-events-none select-none"
                        >
                          {node.inDegree + node.outDegree}
                        </text>
                      </g>
                    </g>
                  );
                })}
              </g>
            </g>
          </svg>

          {/* Node Inspector Drawer */}
          {selectedNode && (
            <div className="absolute top-4 right-4 bottom-4 w-84 bg-slate-900/95 border border-slate-800 rounded-2xl p-5 shadow-2xl backdrop-blur-xl flex flex-col justify-between z-20 space-y-4">
              <div className="space-y-4 overflow-y-auto pr-1">
                <div className="flex items-start justify-between border-b border-slate-800 pb-3">
                  <div className="space-y-1">
                    <span
                      className={`px-2 py-0.5 rounded text-[10px] font-bold font-mono uppercase tracking-wider border ${
                        getNodeColor(selectedNode.type).text
                      } border-current/20 bg-current/10`}
                    >
                      {selectedNode.type}
                    </span>
                    <h3 className="text-sm font-extrabold text-white font-mono break-all leading-tight">
                      {selectedNode.label}
                    </h3>
                  </div>
                  <button
                    onClick={() => setSelectedNodeId(null)}
                    className="p-1 rounded-lg text-slate-400 hover:text-white hover:bg-slate-800"
                  >
                    <X className="w-4 h-4" />
                  </button>
                </div>

                <div className="bg-slate-950/80 border border-slate-800/80 rounded-xl p-3 space-y-2 text-xs font-mono">
                  <div className="flex items-center justify-between text-slate-400">
                    <span>Node ID:</span>
                    <span className="text-slate-300 truncate max-w-[150px]" title={selectedNode.id}>
                      {selectedNode.id}
                    </span>
                  </div>
                  {selectedNode.properties?.language && (
                    <div className="flex items-center justify-between text-slate-400">
                      <span>Language:</span>
                      <span className="text-cyan-400 font-bold">{selectedNode.properties.language}</span>
                    </div>
                  )}
                  {selectedNode.properties?.lines !== undefined && (
                    <div className="flex items-center justify-between text-slate-400">
                      <span>Lines of Code:</span>
                      <span className="text-white font-bold">{selectedNode.properties.lines}</span>
                    </div>
                  )}
                  {selectedNode.properties?.method && (
                    <div className="flex items-center justify-between text-slate-400">
                      <span>HTTP Method:</span>
                      <span className="text-emerald-400 font-bold">{selectedNode.properties.method}</span>
                    </div>
                  )}
                  <div className="flex items-center justify-between text-slate-400">
                    <span>Dependencies:</span>
                    <span className="text-indigo-400 font-bold">{selectedNode.outDegree} outgoing</span>
                  </div>
                  <div className="flex items-center justify-between text-slate-400">
                    <span>Dependents:</span>
                    <span className="text-indigo-400 font-bold">{selectedNode.inDegree} incoming</span>
                  </div>
                </div>

                <div className="space-y-2">
                  <h4 className="text-[11px] uppercase font-bold text-slate-400 flex items-center justify-between">
                    <span>Inbound Connections ({selectedNode.inDegree})</span>
                  </h4>
                  <div className="space-y-1.5 max-h-36 overflow-y-auto pr-1">
                    {simulatedEdges
                      .filter((e) => e.target === selectedNode.id)
                      .map((e, idx) => (
                        <button
                          key={idx}
                          onClick={() => {
                            setSelectedNodeId(e.source);
                            centerOnNode(e.sourceNode);
                          }}
                          className="w-full p-2 rounded-lg bg-slate-950/60 hover:bg-slate-800/80 border border-slate-800/60 text-left text-xs font-mono flex items-center justify-between group transition-colors"
                        >
                          <div className="truncate max-w-[180px]">
                            <span className="text-slate-300 group-hover:text-cyan-400 transition-colors">
                              {e.sourceNode.label.split('/').pop()}
                            </span>
                            <span className="text-[9px] text-slate-500 block truncate">{e.sourceNode.id}</span>
                          </div>
                          <span className="text-[9px] px-1.5 py-0.5 rounded bg-slate-800 text-slate-400 border border-slate-700">
                            {e.relationship}
                          </span>
                        </button>
                      ))}
                    {selectedNode.inDegree === 0 && (
                      <p className="text-[11px] text-slate-500 italic">No inbound dependencies.</p>
                    )}
                  </div>
                </div>

                <div className="space-y-2">
                  <h4 className="text-[11px] uppercase font-bold text-slate-400 flex items-center justify-between">
                    <span>Outbound Connections ({selectedNode.outDegree})</span>
                  </h4>
                  <div className="space-y-1.5 max-h-36 overflow-y-auto pr-1">
                    {simulatedEdges
                      .filter((e) => e.source === selectedNode.id)
                      .map((e, idx) => (
                        <button
                          key={idx}
                          onClick={() => {
                            setSelectedNodeId(e.target);
                            centerOnNode(e.targetNode);
                          }}
                          className="w-full p-2 rounded-lg bg-slate-950/60 hover:bg-slate-800/80 border border-slate-800/60 text-left text-xs font-mono flex items-center justify-between group transition-colors"
                        >
                          <div className="truncate max-w-[180px]">
                            <span className="text-slate-300 group-hover:text-indigo-400 transition-colors">
                              {e.targetNode.label.split('/').pop()}
                            </span>
                            <span className="text-[9px] text-slate-500 block truncate">{e.targetNode.id}</span>
                          </div>
                          <span className="text-[9px] px-1.5 py-0.5 rounded bg-slate-800 text-slate-400 border border-slate-700">
                            {e.relationship}
                          </span>
                        </button>
                      ))}
                    {selectedNode.outDegree === 0 && (
                      <p className="text-[11px] text-slate-500 italic">No outbound dependencies.</p>
                    )}
                  </div>
                </div>
              </div>

              <div className="pt-2 border-t border-slate-800/80 flex items-center gap-2">
                <button
                  onClick={() => centerOnNode(selectedNode)}
                  className="w-full py-2 rounded-xl bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-bold transition-all shadow-md shadow-indigo-600/30 flex items-center justify-center gap-1.5"
                >
                  <Maximize2 className="w-3.5 h-3.5" /> Center on Node
                </button>
              </div>
            </div>
          )}
        </div>
      ) : (
        <div className="glass-card rounded-2xl border border-slate-800 overflow-hidden shadow-xl">
          <div className="p-4 border-b border-slate-800 bg-slate-900/60 flex items-center justify-between">
            <h4 className="text-xs font-bold uppercase tracking-wider text-slate-400">
              Knowledge Graph Index Registry ({processedGraph.nodes.length} Elements)
            </h4>
            <span className="text-xs font-mono text-indigo-400">{processedGraph.edges.length} total edges</span>
          </div>

          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs font-mono">
              <thead className="bg-slate-950/80 text-slate-400 border-b border-slate-800 uppercase text-[10px]">
                <tr>
                  <th className="px-4 py-3">Type</th>
                  <th className="px-4 py-3">Label / Name</th>
                  <th className="px-4 py-3">Identifier</th>
                  <th className="px-4 py-3">Properties / Metadata</th>
                  <th className="px-4 py-3 text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800/60 text-slate-300">
                {processedGraph.nodes
                  .filter((n) =>
                    searchQuery
                      ? n.label.toLowerCase().includes(searchQuery.toLowerCase()) ||
                        n.id.toLowerCase().includes(searchQuery.toLowerCase())
                      : true
                  )
                  .map((node) => {
                    const colors = getNodeColor(node.type);
                    return (
                      <tr key={node.id} className="hover:bg-slate-800/40 transition-colors">
                        <td className="px-4 py-3">
                          <span
                            className={`px-2 py-0.5 rounded font-bold border text-[10px] ${colors.text} border-current/20 bg-current/10`}
                          >
                            {node.type}
                          </span>
                        </td>
                        <td className="px-4 py-3 text-white font-bold max-w-[240px] truncate">
                          {node.label}
                        </td>
                        <td className="px-4 py-3 text-slate-500 text-[11px] max-w-[200px] truncate">
                          {node.id}
                        </td>
                        <td className="px-4 py-3 text-slate-400 text-[11px]">
                          {node.properties?.language && (
                            <span className="mr-2 text-cyan-400">{node.properties.language}</span>
                          )}
                          {node.properties?.lines !== undefined && (
                            <span>{node.properties.lines} LOC</span>
                          )}
                          {node.properties?.method && (
                            <span className="text-emerald-400 font-bold">{node.properties.method}</span>
                          )}
                        </td>
                        <td className="px-4 py-3 text-right">
                          <button
                            onClick={() => {
                              setViewMode('modules');
                              setSelectedNodeId(node.id);
                            }}
                            className="px-2.5 py-1 rounded-lg bg-indigo-600/20 hover:bg-indigo-600/30 border border-indigo-500/30 text-indigo-300 text-[11px] font-semibold transition-colors inline-flex items-center gap-1"
                          >
                            View in Graph <ChevronRight className="w-3 h-3" />
                          </button>
                        </td>
                      </tr>
                    );
                  })}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
};
