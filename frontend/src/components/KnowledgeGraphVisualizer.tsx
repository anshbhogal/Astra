import React, { memo, useCallback, useEffect, useId, useMemo, useRef, useState } from 'react';
import {
  Network,
  Layers,
  FileCode,
  Cpu,
  Box,
  Globe,
  Search,
  ZoomIn,
  ZoomOut,
  Maximize2,
  List,
  Download,
  ChevronRight,
  X,
  type LucideIcon,
} from 'lucide-react';

/* ────────────────────────────── Types ────────────────────────────── */

export interface NodeProperties {
  language?: string;
  lines?: number;
  method?: string;
  [key: string]: unknown;
}

export interface GraphNodeData {
  id: string;
  label: string;
  type: string;
  properties?: NodeProperties;
}

export interface GraphEdgeData {
  source: string;
  target: string;
  type?: string;
  relationship?: string;
  confidence?: number;
  properties?: NodeProperties;
}

interface KnowledgeGraphVisualizerProps {
  graph: { nodes: GraphNodeData[]; edges: GraphEdgeData[] };
  projectName?: string;
  onSelectNode?: (nodeId: string) => void;
}

type ViewMode = 'modules' | 'full' | 'table';
type FilterableType = 'MODULE' | 'ENDPOINT' | 'FUNCTION';

interface LayoutNode extends GraphNodeData {
  x: number;
  y: number;
  w: number;
  h: number;
  inDegree: number;
  outDegree: number;
  title: string;
  subtitle: string;
}

interface Overrides {
  owner: LayoutNode[]; // overrides are only valid for the layout they were made on
  pos: Record<string, { x: number; y: number }>;
}

type DragState =
  | { kind: 'pan'; pointerId: number; sx: number; sy: number; ox: number; oy: number; moved: boolean }
  | { kind: 'node'; pointerId: number; id: string; dx: number; dy: number };

/* ───────────────────────────── Constants ──────────────────────────── */

const MIN_ZOOM = 0.2;
const MAX_ZOOM = 2.5;
const NODE_H = 48;
const TABLE_ROW_LIMIT = 500;

const clamp = (v: number, lo: number, hi: number) => Math.min(hi, Math.max(lo, v));

const NODE_STYLE: Record<
  string,
  { border: string; badge: string; Icon: LucideIcon }
> = {
  PROJECT: { border: '#fbbf24', badge: 'text-amber-400 border-amber-400/30 bg-amber-400/10', Icon: Box },
  MODULE: { border: '#22d3ee', badge: 'text-cyan-400 border-cyan-400/30 bg-cyan-400/10', Icon: FileCode },
  ENDPOINT: { border: '#34d399', badge: 'text-emerald-400 border-emerald-400/30 bg-emerald-400/10', Icon: Globe },
  FUNCTION: { border: '#818cf8', badge: 'text-indigo-400 border-indigo-400/30 bg-indigo-400/10', Icon: Cpu },
};
const styleOf = (type: string) => NODE_STYLE[type] ?? NODE_STYLE.FUNCTION;

const EDGE_COLORS: Record<string, string> = {
  DEPENDS_ON: '#22d3ee',
  IMPORTS: '#22d3ee',
  HANDLED_BY: '#34d399',
  EXPOSES: '#34d399',
  CALLS: '#818cf8',
  DEFINES: '#a78bfa',
  CONTAINS: '#fbbf24',
};
const EDGE_FALLBACK = '#64748b';
const edgeColor = (rel: string) => EDGE_COLORS[rel] ?? EDGE_FALLBACK;
const ALL_EDGE_COLORS = Array.from(new Set([...Object.values(EDGE_COLORS), EDGE_FALLBACK]));

const FILTERS: { type: FilterableType; label: string; text: string }[] = [
  { type: 'MODULE', label: 'Modules', text: 'text-cyan-400' },
  { type: 'ENDPOINT', label: 'Endpoints', text: 'text-emerald-400' },
  { type: 'FUNCTION', label: 'Functions', text: 'text-indigo-400' },
];

/* ──────────────────────── Pure graph helpers ──────────────────────── */

const relOf = (e: GraphEdgeData) => (e.relationship || e.type || '').toUpperCase();

/** Collapse symbol-level edges into module → module dependencies. */
function buildModuleGraph(rawNodes: GraphNodeData[], rawEdges: GraphEdgeData[]) {
  const moduleNodes = rawNodes.filter((n) => n.type === 'MODULE');
  const moduleIds = new Set(moduleNodes.map((n) => n.id));

  const symbolToModule = new Map<string, string>();
  for (const e of rawEdges) {
    if (relOf(e) === 'DEFINES' && moduleIds.has(e.source)) symbolToModule.set(e.target, e.source);
  }
  // Fallback: function ids look like "function:<relative/path>:<name>"
  for (const n of rawNodes) {
    if (n.type !== 'FUNCTION' || symbolToModule.has(n.id)) continue;
    const parts = n.id.split(':');
    if (parts.length >= 3) {
      const modId = `module:${parts[1].replace(/\\/g, '/')}`;
      if (moduleIds.has(modId)) symbolToModule.set(n.id, modId);
    }
  }

  const edgeMap = new Map<string, GraphEdgeData>();
  for (const e of rawEdges) {
    const rel = relOf(e);
    if (moduleIds.has(e.source) && moduleIds.has(e.target)) {
      if (e.source === e.target) continue;
      edgeMap.set(`${e.source}->${e.target}`, {
        source: e.source,
        target: e.target,
        relationship: rel === 'CONTAINS' || !rel ? 'DEPENDS_ON' : rel,
        confidence: e.confidence ?? 1,
      });
    } else if (rel === 'CALLS') {
      const s = symbolToModule.get(e.source);
      const t = symbolToModule.get(e.target);
      const key = s && t ? `${s}->${t}` : '';
      if (s && t && s !== t && !edgeMap.has(key)) {
        edgeMap.set(key, { source: s, target: t, relationship: 'DEPENDS_ON', confidence: 0.9 });
      }
    }
  }

  // No real dependencies found: chain modules that share a directory so the view isn't empty.
  if (edgeMap.size === 0 && moduleNodes.length > 1) {
    const dirs = new Map<string, string[]>();
    for (const m of moduleNodes) {
      const parts = (m.label || m.id).split('/');
      const dir = parts.length > 1 ? parts.slice(0, -1).join('/') : 'root';
      dirs.set(dir, [...(dirs.get(dir) ?? []), m.id]);
    }
    dirs.forEach((ids) => {
      for (let i = 0; i < ids.length - 1; i++) {
        edgeMap.set(`${ids[i]}->${ids[i + 1]}`, {
          source: ids[i],
          target: ids[i + 1],
          relationship: 'CO_LOCATED',
          confidence: 0.7,
        });
      }
    });
  }

  return { nodes: moduleNodes, edges: Array.from(edgeMap.values()) };
}

/** Force-directed layout on typed arrays. Iterations scale down as the graph grows. */
function computeLayout(
  nodes: GraphNodeData[],
  edges: GraphEdgeData[],
  width = 900,
  height = 560
): LayoutNode[] {
  const n = nodes.length;
  if (n === 0) return [];

  const idx = new Map(nodes.map((nd, i) => [nd.id, i]));
  const inDeg = new Int32Array(n);
  const outDeg = new Int32Array(n);
  const links: [number, number][] = [];
  for (const e of edges) {
    const a = idx.get(e.source);
    const b = idx.get(e.target);
    if (a === undefined || b === undefined) continue;
    links.push([a, b]);
    outDeg[a]++;
    inDeg[b]++;
  }

  const cx = width / 2;
  const cy = height / 2;
  const ring = Math.min(width, height) * 0.38 * Math.max(1, Math.sqrt(n / 12));
  const x = new Float64Array(n);
  const y = new Float64Array(n);
  const vx = new Float64Array(n);
  const vy = new Float64Array(n);
  for (let i = 0; i < n; i++) {
    const a = (i / n) * 2 * Math.PI;
    const r = ring * (i % 2 === 0 ? 1 : 0.85);
    x[i] = cx + r * Math.cos(a);
    y[i] = cy + r * Math.sin(a);
  }

  const kRepel = 12000;
  const kSpring = 0.04;
  const targetDist = 180;
  const iterations = clamp(Math.floor(6e6 / (n * n)), 25, 120);

  for (let it = 0; it < iterations; it++) {
    const cool = 1 - (it / iterations) * 0.7;
    for (let i = 0; i < n; i++) {
      for (let j = i + 1; j < n; j++) {
        const dx = x[j] - x[i];
        const dy = y[j] - y[i];
        const distSq = dx * dx + dy * dy + 100;
        const dist = Math.sqrt(distSq);
        const f = kRepel / distSq;
        const fx = (dx / dist) * f;
        const fy = (dy / dist) * f;
        vx[i] -= fx;
        vy[i] -= fy;
        vx[j] += fx;
        vy[j] += fy;
      }
    }
    for (const [a, b] of links) {
      const dx = x[b] - x[a];
      const dy = y[b] - y[a];
      const dist = Math.sqrt(dx * dx + dy * dy) || 1;
      const f = (dist - targetDist) * kSpring;
      const fx = (dx / dist) * f;
      const fy = (dy / dist) * f;
      vx[a] += fx;
      vy[a] += fy;
      vx[b] -= fx;
      vy[b] -= fy;
    }
    for (let i = 0; i < n; i++) {
      vx[i] += (cx - x[i]) * 0.01;
      vy[i] += (cy - y[i]) * 0.01;
      x[i] += vx[i] * 0.15 * cool;
      y[i] += vy[i] * 0.15 * cool;
      vx[i] *= 0.75;
      vy[i] *= 0.75;
    }
  }

  return nodes.map((nd, i) => {
    const label = nd.label || nd.id;
    const title = label.split('/').pop() || label;
    const dir = label.includes('/') ? label.slice(0, label.lastIndexOf('/')) : '';
    const subtitle = nd.type === 'MODULE' ? (dir ? `${dir}/` : 'root module') : nd.type;
    const shownTitle = truncate(title, 24);
    const shownSub = truncate(subtitle, 26);
    const w = clamp(Math.max(shownTitle.length * 6.6, shownSub.length * 5.2) + 52, 110, 220);
    return {
      ...nd,
      x: x[i],
      y: y[i],
      w,
      h: NODE_H,
      inDegree: inDeg[i],
      outDegree: outDeg[i],
      title: shownTitle,
      subtitle: shownSub,
    };
  });
}

function truncate(s: string, max: number) {
  return s.length > max ? `${s.slice(0, max - 2)}..` : s;
}

/** Point where a ray from the rect's centre toward (dx, dy) leaves the rect, pushed out by `gap`. */
function clipToRect(cx: number, cy: number, hw: number, hh: number, dx: number, dy: number, gap: number) {
  const len = Math.hypot(dx, dy);
  if (len === 0) return { x: cx, y: cy };
  const k = 1 / Math.max(Math.abs(dx) / hw, Math.abs(dy) / hh);
  return { x: cx + dx * k + (dx / len) * gap, y: cy + dy * k + (dy / len) * gap };
}

function edgeGeometry(
  sx: number, sy: number, sw: number, sh: number,
  tx: number, ty: number, tw: number, th: number
) {
  const dx = tx - sx;
  const dy = ty - sy;
  const cx = (sx + tx) / 2 - dy * 0.18;
  const cy = (sy + ty) / 2 + dx * 0.18;
  const a = clipToRect(sx, sy, sw / 2, sh / 2, cx - sx, cy - sy, 2);
  const b = clipToRect(tx, ty, tw / 2, th / 2, cx - tx, cy - ty, 4);
  return {
    d: `M ${a.x} ${a.y} Q ${cx} ${cy} ${b.x} ${b.y}`,
    lx: 0.25 * a.x + 0.5 * cx + 0.25 * b.x,
    ly: 0.25 * a.y + 0.5 * cy + 0.25 * b.y,
  };
}

function boundsOf(items: { x: number; y: number; w: number; h: number }[]) {
  if (items.length === 0) return { minX: 0, minY: 0, maxX: 900, maxY: 560 };
  let minX = Infinity, minY = Infinity, maxX = -Infinity, maxY = -Infinity;
  for (const i of items) {
    minX = Math.min(minX, i.x - i.w / 2);
    maxX = Math.max(maxX, i.x + i.w / 2);
    minY = Math.min(minY, i.y - i.h / 2);
    maxY = Math.max(maxY, i.y + i.h / 2);
  }
  return { minX, minY, maxX, maxY };
}

/* ──────────────────────── Memoised SVG parts ──────────────────────── */

interface EdgeViewProps {
  sx: number; sy: number; sw: number; sh: number;
  tx: number; ty: number; tw: number; th: number;
  rel: string;
  confidence: number;
  highlighted: boolean;
  dimmed: boolean;
  markerPrefix: string;
}

const EdgeView = memo(function EdgeView(p: EdgeViewProps) {
  const color = edgeColor(p.rel);
  const { d, lx, ly } = edgeGeometry(p.sx, p.sy, p.sw, p.sh, p.tx, p.ty, p.tw, p.th);
  const opacity = p.dimmed ? 0.12 : p.highlighted ? 1 : 0.3 + 0.3 * p.confidence;
  return (
    <g>
      <path
        d={d}
        fill="none"
        stroke={color}
        strokeWidth={p.highlighted ? 2.5 : 1.2}
        strokeDasharray={p.rel === 'CO_LOCATED' ? '4 4' : undefined}
        strokeOpacity={opacity}
        markerEnd={`url(#${p.markerPrefix}-${color.slice(1)})`}
      >
        <title>{`${p.rel} (${Math.round(p.confidence * 100)}% confidence)`}</title>
      </path>
      {p.highlighted && (
        <text
          x={lx}
          y={ly - 6}
          fill={color}
          fontSize={9}
          fontFamily="monospace"
          fontWeight="bold"
          textAnchor="middle"
          stroke="#020617"
          strokeWidth={3}
          paintOrder="stroke"
          style={{ pointerEvents: 'none', userSelect: 'none' }}
        >
          {p.rel}
        </text>
      )}
    </g>
  );
});

interface NodeViewProps {
  node: LayoutNode;
  x: number;
  y: number;
  selected: boolean;
  hovered: boolean;
  dimmed: boolean;
  showText: boolean;
  onPointerDown: (id: string, e: React.PointerEvent<SVGGElement>) => void;
  onHover: (id: string | null) => void;
  onActivate: (id: string) => void;
}

const NodeView = memo(function NodeView({
  node, x, y, selected, hovered, dimmed, showText, onPointerDown, onHover, onActivate,
}: NodeViewProps) {
  const { border, Icon } = styleOf(node.type);
  const hw = node.w / 2;
  const hh = node.h / 2;
  const degree = node.inDegree + node.outDegree;

  return (
    <g
      transform={`translate(${x}, ${y})`}
      style={{ opacity: dimmed ? 0.22 : 1, cursor: 'pointer' }}
      role="button"
      tabIndex={0}
      aria-label={`${node.type} ${node.label}, ${degree} connections`}
      aria-pressed={selected}
      onPointerDown={(e) => onPointerDown(node.id, e)}
      onPointerEnter={() => onHover(node.id)}
      onPointerLeave={() => onHover(null)}
      onFocus={() => onHover(node.id)}
      onBlur={() => onHover(null)}
      onKeyDown={(e) => {
        if (e.key === 'Enter' || e.key === ' ') {
          e.preventDefault();
          onActivate(node.id);
        }
      }}
    >
      {selected && (
        <rect
          x={-hw - 6} y={-hh - 6} width={node.w + 12} height={node.h + 12} rx={18}
          fill="none" stroke={border} strokeWidth={1.5} strokeDasharray="4 3" opacity={0.9}
          style={{ pointerEvents: 'none' }}
        />
      )}
      <rect
        x={-hw} y={-hh} width={node.w} height={node.h} rx={14}
        fill={selected ? '#1e293b' : hovered ? '#0f172a' : '#0b1120'}
        stroke={selected ? '#ffffff' : border}
        strokeWidth={selected ? 2.2 : hovered ? 1.8 : 1.2}
      />
      <circle cx={-hw + 20} cy={0} r={12} fill={border} fillOpacity={0.15} stroke={border} style={{ pointerEvents: 'none' }} />
      <Icon x={-hw + 13} y={-7} size={14} color={border} style={{ pointerEvents: 'none' }} />
      {showText && (
        <>
          <text
            x={-hw + 40} y={-3}
            fill={hovered ? '#38bdf8' : '#f8fafc'}
            fontSize={11} fontWeight={700} fontFamily="monospace"
            style={{ pointerEvents: 'none', userSelect: 'none' }}
          >
            {node.title}
          </text>
          <text
            x={-hw + 40} y={11}
            fill="#64748b" fontSize={8.5} fontFamily="monospace"
            style={{ pointerEvents: 'none', userSelect: 'none' }}
          >
            {node.subtitle}
          </text>
        </>
      )}
      <g transform={`translate(${hw}, ${-hh})`} style={{ pointerEvents: 'none' }}>
        <rect x={-12} y={-7} width={24} height={14} rx={7} fill="#1e293b" stroke={border} />
        <text x={0} y={3} fill={border} fontSize={8} fontWeight="bold" fontFamily="monospace" textAnchor="middle">
          {degree}
        </text>
      </g>
    </g>
  );
});

/* ─────────────────────────── Small UI parts ───────────────────────── */

const Row: React.FC<{ label: string; value: React.ReactNode; className?: string }> = ({ label, value, className = 'text-white' }) => (
  <div className="flex items-center justify-between text-slate-400">
    <span>{label}</span>
    <span className={`font-bold truncate max-w-[150px] ${className}`}>{value}</span>
  </div>
);

const TypeBadge: React.FC<{ type: string }> = ({ type }) => (
  <span className={`px-2 py-0.5 rounded font-bold border text-[10px] font-mono uppercase tracking-wider ${styleOf(type).badge}`}>
    {type}
  </span>
);

/* ───────────────────────────── Component ──────────────────────────── */

export const KnowledgeGraphVisualizer: React.FC<KnowledgeGraphVisualizerProps> = ({
  graph,
  projectName = 'Repository',
  onSelectNode,
}) => {
  const [viewMode, setViewMode] = useState<ViewMode>('modules');
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedNodeId, setSelectedNodeId] = useState<string | null>(null);
  const [hoveredNodeId, setHoveredNodeId] = useState<string | null>(null);
  const [show, setShow] = useState<Record<FilterableType, boolean>>({ MODULE: true, ENDPOINT: true, FUNCTION: false });
  const [view, setView] = useState({ k: 1, x: 0, y: 0 });
  const [size, setSize] = useState({ w: 0, h: 0 });
  const [overrides, setOverrides] = useState<Overrides>({ owner: [], pos: {} });

  const svgRef = useRef<SVGSVGElement | null>(null);
  const containerRef = useRef<HTMLDivElement | null>(null);
  const dragRef = useRef<DragState | null>(null);
  const pendingFocus = useRef<string | null>(null);
  const markerPrefix = `kg${useId().replace(/:/g, '')}`;

  const showCanvas = viewMode !== 'table';

  /* 1. Derive the graph for the current view */
  const { rawNodes, rawEdges } = useMemo(
    () => ({
      rawNodes: graph?.nodes ?? [],
      rawEdges: (graph?.edges ?? []).map((e) => ({ ...e, relationship: relOf(e) || 'RELATED' })),
    }),
    [graph]
  );

  const moduleCount = useMemo(() => rawNodes.filter((n) => n.type === 'MODULE').length, [rawNodes]);

  const processedGraph = useMemo(() => {
    if (viewMode === 'table') return { nodes: rawNodes, edges: rawEdges };
    if (viewMode === 'modules') return buildModuleGraph(rawNodes, rawEdges);

    const allowed = new Set<string>(['PROJECT']);
    (Object.keys(show) as FilterableType[]).forEach((t) => show[t] && allowed.add(t));
    const nodes = rawNodes.filter((n) => allowed.has(n.type));
    const ids = new Set(nodes.map((n) => n.id));
    const edges = rawEdges.filter((e) => e.source !== e.target && ids.has(e.source) && ids.has(e.target));
    return { nodes, edges };
  }, [rawNodes, rawEdges, viewMode, show]);

  /* 2. Layout (skipped entirely in table mode) */
  const baseNodes = useMemo(
    () => (showCanvas ? computeLayout(processedGraph.nodes, processedGraph.edges) : []),
    [processedGraph, showCanvas]
  );
  const baseNodeMap = useMemo(() => new Map(baseNodes.map((n) => [n.id, n])), [baseNodes]);
  const edges = useMemo(
    () => (showCanvas ? processedGraph.edges.filter((e) => baseNodeMap.has(e.source) && baseNodeMap.has(e.target)) : []),
    [processedGraph.edges, baseNodeMap, showCanvas]
  );

  const activeOverrides = overrides.owner === baseNodes ? overrides.pos : EMPTY_POS;

  // Latest values for stable event handlers (avoids stale closures without re-creating callbacks)
  const live = useRef({ view, size, baseNodes, baseNodeMap, activeOverrides });
  live.current = { view, size, baseNodes, baseNodeMap, activeOverrides };

  /* 3. Selection, neighbours, search */
  const selected = selectedNodeId ? baseNodeMap.get(selectedNodeId) ?? null : null;
  const selectedId = selected?.id ?? null; // ignores a stale id after a view switch, so nothing gets dimmed

  const neighborIds = useMemo(() => {
    const set = new Set<string>();
    if (!selectedId) return set;
    set.add(selectedId);
    for (const e of edges) {
      if (e.source === selectedId) set.add(e.target);
      if (e.target === selectedId) set.add(e.source);
    }
    return set;
  }, [selectedId, edges]);

  const { inbound, outbound } = useMemo(
    () => ({
      inbound: selectedId ? edges.filter((e) => e.target === selectedId) : [],
      outbound: selectedId ? edges.filter((e) => e.source === selectedId) : [],
    }),
    [selectedId, edges]
  );

  const query = searchQuery.trim().toLowerCase();
  const matches = useCallback(
    (n: GraphNodeData) => n.label.toLowerCase().includes(query) || n.id.toLowerCase().includes(query),
    [query]
  );
  const matchedIds = useMemo(
    () => (query ? new Set(baseNodes.filter(matches).map((n) => n.id)) : null),
    [query, baseNodes, matches]
  );

  /* 4. Viewport helpers */
  const zoomAt = useCallback((px: number, py: number, factor: number) => {
    setView((v) => {
      const k = clamp(v.k * factor, MIN_ZOOM, MAX_ZOOM);
      const r = k / v.k;
      return { k, x: px - (px - v.x) * r, y: py - (py - v.y) * r };
    });
  }, []);

  const fitView = useCallback((nodes: LayoutNode[]) => {
    const { w, h } = live.current.size;
    if (!w || !h) return;
    const b = boundsOf(nodes);
    const pad = 70;
    const k = clamp(Math.min(w / (b.maxX - b.minX + pad * 2), h / (b.maxY - b.minY + pad * 2), 1.2), MIN_ZOOM, MAX_ZOOM);
    setView({ k, x: w / 2 - ((b.minX + b.maxX) / 2) * k, y: h / 2 - ((b.minY + b.maxY) / 2) * k });
  }, []);

  const centerOn = useCallback((id: string) => {
    const { baseNodeMap: map, activeOverrides: ov, size: s, view: v } = live.current;
    const n = map.get(id);
    if (!n) return;
    const p = ov[id] ?? n;
    setView({ k: v.k, x: s.w / 2 - p.x * v.k, y: s.h / 2 - p.y * v.k });
  }, []);

  useEffect(() => {
    const el = containerRef.current;
    if (!el) return;
    const ro = new ResizeObserver(([entry]) => {
      const { width, height } = entry.contentRect;
      setSize({ w: width, h: height });
    });
    ro.observe(el);
    return () => ro.disconnect();
  }, [showCanvas]);

  // React's onWheel is passive, so preventDefault only works through a native listener.
  useEffect(() => {
    const svg = svgRef.current;
    if (!svg) return;
    const onWheel = (e: WheelEvent) => {
      e.preventDefault();
      const r = svg.getBoundingClientRect();
      zoomAt(e.clientX - r.left, e.clientY - r.top, e.deltaY < 0 ? 1.1 : 1 / 1.1);
    };
    svg.addEventListener('wheel', onWheel, { passive: false });
    return () => svg.removeEventListener('wheel', onWheel);
  }, [showCanvas, zoomAt]);

  const hasSize = size.w > 0 && size.h > 0;
  useEffect(() => {
    if (!showCanvas || !hasSize) return;
    const target = pendingFocus.current;
    pendingFocus.current = null;
    if (target && baseNodeMap.has(target)) {
      const n = baseNodeMap.get(target)!;
      setView({ k: 1, x: live.current.size.w / 2 - n.x, y: live.current.size.h / 2 - n.y });
    } else {
      fitView(baseNodes);
    }
  }, [baseNodes, baseNodeMap, showCanvas, hasSize, fitView]);

  /* 5. Pointer interaction (mouse + touch + pen) */
  const toWorld = (clientX: number, clientY: number) => {
    const r = svgRef.current!.getBoundingClientRect();
    const v = live.current.view;
    return { x: (clientX - r.left - v.x) / v.k, y: (clientY - r.top - v.y) / v.k };
  };

  const selectNode = useCallback(
    (id: string) => {
      setSelectedNodeId(id);
      onSelectNode?.(id);
    },
    [onSelectNode]
  );

  const handleNodePointerDown = useCallback(
    (id: string, e: React.PointerEvent<SVGGElement>) => {
      e.stopPropagation();
      const svg = svgRef.current;
      const n = live.current.baseNodeMap.get(id);
      if (!svg || !n) return;
      svg.setPointerCapture(e.pointerId);
      const p = live.current.activeOverrides[id] ?? n;
      const w = toWorld(e.clientX, e.clientY);
      dragRef.current = { kind: 'node', pointerId: e.pointerId, id, dx: p.x - w.x, dy: p.y - w.y };
      selectNode(id);
    },
    [selectNode] // eslint-disable-line react-hooks/exhaustive-deps
  );

  const handleCanvasPointerDown = (e: React.PointerEvent<SVGSVGElement>) => {
    e.currentTarget.setPointerCapture(e.pointerId);
    const v = live.current.view;
    dragRef.current = { kind: 'pan', pointerId: e.pointerId, sx: e.clientX, sy: e.clientY, ox: v.x, oy: v.y, moved: false };
  };

  const handlePointerMove = (e: React.PointerEvent<SVGSVGElement>) => {
    const d = dragRef.current;
    if (!d || d.pointerId !== e.pointerId) return;
    if (d.kind === 'pan') {
      const mx = e.clientX - d.sx;
      const my = e.clientY - d.sy;
      if (Math.hypot(mx, my) > 3) d.moved = true;
      setView((v) => ({ ...v, x: d.ox + mx, y: d.oy + my }));
    } else {
      const w = toWorld(e.clientX, e.clientY);
      const owner = live.current.baseNodes;
      setOverrides((prev) => ({
        owner,
        pos: { ...(prev.owner === owner ? prev.pos : {}), [d.id]: { x: w.x + d.dx, y: w.y + d.dy } },
      }));
    }
  };

  const handlePointerEnd = (e: React.PointerEvent<SVGSVGElement>) => {
    const d = dragRef.current;
    if (!d || d.pointerId !== e.pointerId) return;
    if (d.kind === 'pan' && !d.moved) setSelectedNodeId(null); // plain click on empty canvas
    dragRef.current = null;
    if (e.currentTarget.hasPointerCapture(e.pointerId)) e.currentTarget.releasePointerCapture(e.pointerId);
  };

  const zoomBy = (factor: number) => zoomAt(live.current.size.w / 2, live.current.size.h / 2, factor);
  const resetView = () => {
    setSelectedNodeId(null);
    setOverrides({ owner: [], pos: {} });
    fitView(live.current.baseNodes);
  };

  /* 6. Actions */
  const focusFromTable = (node: GraphNodeData) => {
    pendingFocus.current = node.id;
    if (node.type === 'MODULE') {
      setViewMode('modules');
    } else {
      if (node.type in show) setShow((s) => ({ ...s, [node.type as FilterableType]: true }));
      setViewMode('full');
    }
    setSelectedNodeId(node.id);
  };

  const handleSearchKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === 'Enter' && showCanvas) {
      const first = baseNodes.find(matches);
      if (first) {
        selectNode(first.id);
        centerOn(first.id);
      }
    }
  };

  const handleExportSvg = () => {
    const svg = svgRef.current;
    if (!svg) return;
    const positioned = baseNodes.map((n) => activeOverrides[n.id] ? { ...n, ...activeOverrides[n.id] } : n);
    const b = boundsOf(positioned);
    const pad = 40;
    const width = b.maxX - b.minX + pad * 2;
    const height = b.maxY - b.minY + pad * 2;

    const clone = svg.cloneNode(true) as SVGSVGElement;
    clone.setAttribute('xmlns', 'http://www.w3.org/2000/svg');
    clone.setAttribute('viewBox', `${b.minX - pad} ${b.minY - pad} ${width} ${height}`);
    clone.setAttribute('width', String(Math.round(width)));
    clone.setAttribute('height', String(Math.round(height)));
    clone.removeAttribute('class');
    clone.removeAttribute('style');
    clone.querySelector('[data-world]')?.removeAttribute('transform');
    clone.querySelector('[data-grid]')?.remove();
    const bg = document.createElementNS('http://www.w3.org/2000/svg', 'rect');
    for (const [k, v] of Object.entries({ x: b.minX - pad, y: b.minY - pad, width, height, fill: '#020617' })) {
      bg.setAttribute(k, String(v));
    }
    clone.insertBefore(bg, clone.firstChild);

    const url = URL.createObjectURL(new Blob([new XMLSerializer().serializeToString(clone)], { type: 'image/svg+xml;charset=utf-8' }));
    const a = document.createElement('a');
    a.href = url;
    a.download = `${projectName.toLowerCase().replace(/[^a-z0-9]+/g, '_')}_knowledge_graph.svg`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  };

  /* 7. Render */
  const tableRows = useMemo(
    () => (viewMode === 'table' ? processedGraph.nodes.filter((n) => !query || matches(n)) : []),
    [viewMode, processedGraph.nodes, query, matches]
  );

  const tabs: { mode: ViewMode; label: string; Icon: LucideIcon }[] = [
    { mode: 'modules', label: `Module Architecture (${moduleCount})`, Icon: Layers },
    { mode: 'full', label: `Full Knowledge Graph (${rawNodes.length})`, Icon: Network },
    { mode: 'table', label: 'Table List', Icon: List },
  ];

  const tabClass = (active: boolean) =>
    `px-3 py-1.5 rounded-lg font-bold flex items-center gap-1.5 transition-all ${
      active ? 'bg-indigo-600 text-white shadow-md shadow-indigo-600/30' : 'text-slate-400 hover:text-slate-200'
    }`;
  const iconBtn = 'p-1.5 rounded-lg text-slate-400 hover:text-white hover:bg-slate-800 transition-colors';

  return (
    <div className="space-y-4">
      {/* Controls */}
      <div className="glass-card rounded-2xl p-4 border border-slate-800 flex flex-col lg:flex-row items-stretch lg:items-center justify-between gap-4">
        <div className="flex flex-wrap items-center gap-3">
          <div role="tablist" aria-label="Graph view" className="flex flex-wrap items-center bg-slate-950 border border-slate-800 rounded-xl p-1 text-xs">
            {tabs.map(({ mode, label, Icon }) => (
              <button key={mode} role="tab" aria-selected={viewMode === mode} onClick={() => setViewMode(mode)} className={tabClass(viewMode === mode)}>
                <Icon className="w-3.5 h-3.5" /> {label}
              </button>
            ))}
          </div>
          <div className="hidden sm:flex items-center gap-2 px-3 py-1.5 rounded-xl bg-slate-900/60 border border-slate-800 text-[11px] font-mono text-slate-400">
            <span>Nodes: <strong className="text-white">{processedGraph.nodes.length}</strong></span>
            <span aria-hidden>•</span>
            <span>Connections: <strong className="text-indigo-400">{processedGraph.edges.length}</strong></span>
          </div>
        </div>

        <div className="flex flex-wrap items-center gap-3">
          <div className="relative flex-1 sm:w-60">
            <Search className="w-3.5 h-3.5 text-slate-500 absolute left-3 top-1/2 -translate-y-1/2" aria-hidden />
            <input
              type="search"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              onKeyDown={handleSearchKeyDown}
              placeholder="Search module or symbol…  (Enter to jump)"
              aria-label="Search nodes"
              className="w-full bg-slate-950 border border-slate-800 rounded-xl pl-8 pr-8 py-1.5 text-xs text-white placeholder-slate-500 focus:outline-none focus:border-indigo-500/50"
            />
            {searchQuery && (
              <button onClick={() => setSearchQuery('')} aria-label="Clear search" className="absolute right-2.5 top-1/2 -translate-y-1/2 text-slate-500 hover:text-slate-300">
                <X className="w-3 h-3" />
              </button>
            )}
          </div>

          {viewMode === 'full' && (
            <div className="flex items-center gap-2 text-[11px] font-semibold">
              {FILTERS.map(({ type, label, text }) => (
                <label key={type} className="flex items-center gap-1 cursor-pointer">
                  <input
                    type="checkbox"
                    checked={show[type]}
                    onChange={(e) => setShow((s) => ({ ...s, [type]: e.target.checked }))}
                    className="rounded bg-slate-900 border-slate-700 focus:ring-0"
                  />
                  <span className={text}>{label}</span>
                </label>
              ))}
            </div>
          )}

          <button
            onClick={handleExportSvg}
            disabled={!showCanvas || baseNodes.length === 0}
            className="p-2 rounded-xl bg-slate-900 hover:bg-slate-800 border border-slate-800 text-slate-400 hover:text-slate-200 transition-colors disabled:opacity-40 disabled:pointer-events-none"
            title="Export diagram (SVG)"
            aria-label="Export diagram as SVG"
          >
            <Download className="w-4 h-4" />
          </button>
        </div>
      </div>

      {showCanvas ? (
        <div
          ref={containerRef}
          className="relative w-full h-[580px] bg-slate-950/90 rounded-2xl border border-slate-800 overflow-hidden shadow-2xl select-none"
          onKeyDown={(e) => e.key === 'Escape' && setSelectedNodeId(null)}
        >
          <div className="absolute top-4 left-4 z-10 pointer-events-none">
            <span className="px-2.5 py-1 rounded-lg bg-slate-900/90 border border-slate-800 text-[11px] font-mono text-slate-400 backdrop-blur-md">
              {viewMode === 'modules' ? 'Module Dependency Architecture' : 'Semantic Knowledge Graph'} • Drag to move • Click to inspect • Esc to clear
            </span>
          </div>

          <div className="absolute bottom-4 right-4 z-10 flex items-center gap-1.5 bg-slate-900/90 border border-slate-800 rounded-xl p-1 shadow-xl backdrop-blur-md">
            <button onClick={() => zoomBy(1.2)} className={iconBtn} title="Zoom in" aria-label="Zoom in"><ZoomIn className="w-4 h-4" /></button>
            <button onClick={() => zoomBy(1 / 1.2)} className={iconBtn} title="Zoom out" aria-label="Zoom out"><ZoomOut className="w-4 h-4" /></button>
            <button onClick={resetView} className={iconBtn} title="Fit to screen" aria-label="Fit to screen"><Maximize2 className="w-4 h-4" /></button>
          </div>

          {baseNodes.length === 0 && (
            <div className="absolute inset-0 z-10 flex items-center justify-center text-sm text-slate-500 pointer-events-none">
              {viewMode === 'full' ? 'Nothing to show. Enable a node type above.' : 'No modules found in this graph.'}
            </div>
          )}

          <svg
            ref={svgRef}
            role="group"
            aria-label={`${projectName} dependency graph`}
            className="w-full h-full cursor-grab active:cursor-grabbing"
            style={{ touchAction: 'none' }}
            onPointerDown={handleCanvasPointerDown}
            onPointerMove={handlePointerMove}
            onPointerUp={handlePointerEnd}
            onPointerCancel={handlePointerEnd}
          >
            <defs>
              <pattern id={`${markerPrefix}-grid`} width="30" height="30" patternUnits="userSpaceOnUse">
                <circle cx="2" cy="2" r="1" fill="#1e293b" opacity="0.6" />
              </pattern>
              {ALL_EDGE_COLORS.map((c) => (
                <marker
                  key={c}
                  id={`${markerPrefix}-${c.slice(1)}`}
                  viewBox="0 0 10 10"
                  refX="9"
                  refY="5"
                  markerWidth="8"
                  markerHeight="8"
                  markerUnits="userSpaceOnUse"
                  orient="auto"
                >
                  <path d="M 0 1 L 10 5 L 0 9 z" fill={c} />
                </marker>
              ))}
            </defs>

            <rect data-grid width="100%" height="100%" fill={`url(#${markerPrefix}-grid)`} />

            <g data-world transform={`translate(${view.x}, ${view.y}) scale(${view.k})`}>
              <g>
                {edges.map((e) => {
                  const s = baseNodeMap.get(e.source)!;
                  const t = baseNodeMap.get(e.target)!;
                  const sp = activeOverrides[s.id] ?? s;
                  const tp = activeOverrides[t.id] ?? t;
                  const highlighted = !!selectedId && (e.source === selectedId || e.target === selectedId);
                  return (
                    <EdgeView
                      key={`${e.source}->${e.target}:${e.relationship}`}
                      sx={sp.x} sy={sp.y} sw={s.w} sh={s.h}
                      tx={tp.x} ty={tp.y} tw={t.w} th={t.h}
                      rel={e.relationship ?? 'RELATED'}
                      confidence={e.confidence ?? 1}
                      highlighted={highlighted}
                      dimmed={!!selectedId && !highlighted}
                      markerPrefix={markerPrefix}
                    />
                  );
                })}
              </g>
              <g>
                {baseNodes.map((n) => {
                  const p = activeOverrides[n.id] ?? n;
                  const dimmed = (!!selectedId && !neighborIds.has(n.id)) || (!!matchedIds && !matchedIds.has(n.id));
                  return (
                    <NodeView
                      key={n.id}
                      node={n}
                      x={p.x}
                      y={p.y}
                      selected={selectedId === n.id}
                      hovered={hoveredNodeId === n.id}
                      dimmed={dimmed}
                      showText={view.k >= 0.4}
                      onPointerDown={handleNodePointerDown}
                      onHover={setHoveredNodeId}
                      onActivate={selectNode}
                    />
                  );
                })}
              </g>
            </g>
          </svg>

          {/* Inspector */}
          {selected && (
            <aside
              aria-label="Node details"
              className="absolute top-4 right-4 bottom-4 w-80 max-w-[calc(100%-2rem)] bg-slate-900/95 border border-slate-800 rounded-2xl p-5 shadow-2xl backdrop-blur-xl flex flex-col justify-between z-20 gap-4"
            >
              <div className="space-y-4 overflow-y-auto pr-1">
                <div className="flex items-start justify-between border-b border-slate-800 pb-3 gap-2">
                  <div className="space-y-1.5 min-w-0">
                    <TypeBadge type={selected.type} />
                    <h3 className="text-sm font-extrabold text-white font-mono break-all leading-tight">{selected.label}</h3>
                  </div>
                  <button onClick={() => setSelectedNodeId(null)} className={iconBtn} aria-label="Close details"><X className="w-4 h-4" /></button>
                </div>

                <div className="bg-slate-950/80 border border-slate-800/80 rounded-xl p-3 space-y-2 text-xs font-mono">
                  <div className="flex items-center justify-between text-slate-400">
                    <span>Node ID:</span>
                    <span className="text-slate-300 truncate max-w-[150px]" title={selected.id}>{selected.id}</span>
                  </div>
                  {selected.properties?.language && <Row label="Language:" value={selected.properties.language} className="text-cyan-400" />}
                  {selected.properties?.lines !== undefined && <Row label="Lines of code:" value={selected.properties.lines} />}
                  {selected.properties?.method && <Row label="HTTP method:" value={selected.properties.method} className="text-emerald-400" />}
                  <Row label="Dependencies:" value={`${selected.outDegree} outgoing`} className="text-indigo-400" />
                  <Row label="Dependents:" value={`${selected.inDegree} incoming`} className="text-indigo-400" />
                </div>

                {([
                  ['Inbound', inbound, 'source'],
                  ['Outbound', outbound, 'target'],
                ] as const).map(([title, list, end]) => (
                  <div key={title} className="space-y-2">
                    <h4 className="text-[11px] uppercase font-bold text-slate-400">{title} connections ({list.length})</h4>
                    <div className="space-y-1.5 max-h-36 overflow-y-auto pr-1">
                      {list.map((e) => {
                        const other = baseNodeMap.get(e[end])!;
                        return (
                          <button
                            key={`${e.source}->${e.target}:${e.relationship}`}
                            onClick={() => { selectNode(other.id); centerOn(other.id); }}
                            className="w-full p-2 rounded-lg bg-slate-950/60 hover:bg-slate-800/80 border border-slate-800/60 text-left text-xs font-mono flex items-center justify-between gap-2 group transition-colors"
                          >
                            <span className="truncate">
                              <span className="text-slate-300 group-hover:text-cyan-400 transition-colors">{other.label.split('/').pop()}</span>
                              <span className="text-[9px] text-slate-500 block truncate">{other.id}</span>
                            </span>
                            <span className="text-[9px] px-1.5 py-0.5 rounded bg-slate-800 text-slate-400 border border-slate-700 shrink-0">{e.relationship}</span>
                          </button>
                        );
                      })}
                      {list.length === 0 && <p className="text-[11px] text-slate-500 italic">None.</p>}
                    </div>
                  </div>
                ))}
              </div>

              <button
                onClick={() => centerOn(selected.id)}
                className="w-full py-2 rounded-xl bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-bold transition-all shadow-md shadow-indigo-600/30 flex items-center justify-center gap-1.5"
              >
                <Maximize2 className="w-3.5 h-3.5" /> Center on node
              </button>
            </aside>
          )}
        </div>
      ) : (
        <div className="glass-card rounded-2xl border border-slate-800 overflow-hidden shadow-xl">
          <div className="p-4 border-b border-slate-800 bg-slate-900/60 flex items-center justify-between">
            <h4 className="text-xs font-bold uppercase tracking-wider text-slate-400">
              Knowledge graph index ({tableRows.length} of {rawNodes.length} elements)
            </h4>
            <span className="text-xs font-mono text-indigo-400">{rawEdges.length} total edges</span>
          </div>

          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs font-mono">
              <thead className="bg-slate-950/80 text-slate-400 border-b border-slate-800 uppercase text-[10px]">
                <tr>
                  <th scope="col" className="px-4 py-3">Type</th>
                  <th scope="col" className="px-4 py-3">Label / Name</th>
                  <th scope="col" className="px-4 py-3">Identifier</th>
                  <th scope="col" className="px-4 py-3">Properties</th>
                  <th scope="col" className="px-4 py-3 text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800/60 text-slate-300">
                {tableRows.slice(0, TABLE_ROW_LIMIT).map((node) => (
                  <tr key={node.id} className="hover:bg-slate-800/40 transition-colors">
                    <td className="px-4 py-3"><TypeBadge type={node.type} /></td>
                    <td className="px-4 py-3 text-white font-bold max-w-[240px] truncate" title={node.label}>{node.label}</td>
                    <td className="px-4 py-3 text-slate-500 text-[11px] max-w-[200px] truncate" title={node.id}>{node.id}</td>
                    <td className="px-4 py-3 text-slate-400 text-[11px] space-x-2">
                      {node.properties?.language && <span className="text-cyan-400">{node.properties.language}</span>}
                      {node.properties?.lines !== undefined && <span>{node.properties.lines} LOC</span>}
                      {node.properties?.method && <span className="text-emerald-400 font-bold">{node.properties.method}</span>}
                    </td>
                    <td className="px-4 py-3 text-right">
                      <button
                        onClick={() => focusFromTable(node)}
                        className="px-2.5 py-1 rounded-lg bg-indigo-600/20 hover:bg-indigo-600/30 border border-indigo-500/30 text-indigo-300 text-[11px] font-semibold transition-colors inline-flex items-center gap-1"
                      >
                        View in graph <ChevronRight className="w-3 h-3" />
                      </button>
                    </td>
                  </tr>
                ))}
                {tableRows.length === 0 && (
                  <tr><td colSpan={5} className="px-4 py-8 text-center text-slate-500">No matching elements.</td></tr>
                )}
              </tbody>
            </table>
          </div>
          {tableRows.length > TABLE_ROW_LIMIT && (
            <p className="px-4 py-3 text-[11px] text-slate-500 border-t border-slate-800">
              Showing the first {TABLE_ROW_LIMIT} rows. Use search to narrow the list.
            </p>
          )}
        </div>
      )}
    </div>
  );
};

const EMPTY_POS: Overrides['pos'] = {};

export default KnowledgeGraphVisualizer;
