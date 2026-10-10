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
  Flame,
  Copy,
  Check,
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
  source: string; // "source depends on / calls target"
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

type ViewMode = 'map' | 'detailed' | 'table';
type FilterableType = 'MODULE' | 'ENDPOINT' | 'FUNCTION';
type Role = 'none' | 'selected' | 'affected' | 'uses';
type EdgeKind = 'affected' | 'uses' | 'hover' | 'all';

interface LayoutNode extends GraphNodeData {
  x: number; // centre
  y: number;
  w: number;
  h: number;
  inDegree: number; // how many things use this
  outDegree: number; // how many things this uses
  title: string;
  subtitle: string;
  heat: 0 | 1 | 2; // 2 = high impact, 1 = medium
}

interface GroupBox {
  key: string;
  x: number; // top-left
  y: number;
  w: number;
  h: number;
  count: number;
}

type Rect = { x: number; y: number; w: number; h: number };
type Bounds = { minX: number; minY: number; maxX: number; maxY: number };

/* ───────────────────────────── Constants ──────────────────────────── */

const MIN_ZOOM = 0.15;
const MAX_ZOOM = 2.5;
const NODE_W = 190;
const NODE_H = 48;
const GAP = 14;
const PAD = 16;
const HEAD = 30;
const GROUP_GAP = 28;
const TABLE_ROW_LIMIT = 500;
const ENDPOINT_GROUP = 'API endpoints';
const PROJECT_GROUP = 'Project';

const AMBER = '#fbbf24';
const CYAN = '#0891b2';

const clamp = (v: number, lo: number, hi: number) => Math.min(hi, Math.max(lo, v));
const truncate = (s: string, max: number) => (s.length > max ? `${s.slice(0, max - 2)}..` : s);
const plural = (n: number, word: string) => `${n} ${word}${n === 1 ? '' : 's'}`;

const NODE_STYLE: Record<string, { border: string; badge: string; Icon: LucideIcon; label: string }> = {
  PROJECT: { border: '#5b3df5', badge: 'text-brand border-brand/30 bg-brand/10', Icon: Box, label: 'Project' },
  MODULE: { border: '#0891b2', badge: 'text-secondaryAccent border-secondaryAccent/30 bg-secondaryAccent/10', Icon: FileCode, label: 'Module' },
  ENDPOINT: { border: '#10b981', badge: 'text-status-passed border-status-passed/30 bg-status-passed-bg', Icon: Globe, label: 'API endpoint' },
  FUNCTION: { border: '#8b5cf6', badge: 'text-brand border-brand/30 bg-brand/10', Icon: Cpu, label: 'Function' },
};
const styleOf = (type: string) => NODE_STYLE[type] ?? NODE_STYLE.FUNCTION;

const EDGE_STYLE: Record<EdgeKind, { color: string; width: number; opacity: number }> = {
  affected: { color: AMBER, width: 2, opacity: 0.95 },
  uses: { color: CYAN, width: 2, opacity: 0.95 },
  hover: { color: '#5b3df5', width: 2, opacity: 0.95 },
  all: { color: '#8690b4', width: 1, opacity: 0.4 },
};
const MARKER_COLORS = Array.from(new Set(Object.values(EDGE_STYLE).map((s) => s.color)));

const FILTERS: { type: FilterableType; label: string }[] = [
  { type: 'MODULE', label: 'Modules' },
  { type: 'ENDPOINT', label: 'API endpoints' },
  { type: 'FUNCTION', label: 'Functions' },
];

/* ──────────────────────── Pure graph helpers ──────────────────────── */

const relOf = (e: GraphEdgeData) => (e.relationship || e.type || '').toUpperCase();
const folderOf = (label: string) => (label.includes('/') ? label.slice(0, label.lastIndexOf('/')) : 'root');

/** Which module owns each function/endpoint (via DEFINES edges, falling back to "kind:path:name" ids). */
function mapSymbolsToModules(nodes: GraphNodeData[], edges: GraphEdgeData[]) {
  const moduleIds = new Set(nodes.filter((n) => n.type === 'MODULE').map((n) => n.id));
  const map = new Map<string, string>();
  for (const e of edges) {
    if (relOf(e) === 'DEFINES' && moduleIds.has(e.source)) map.set(e.target, e.source);
  }
  for (const n of nodes) {
    if (n.type === 'MODULE' || map.has(n.id)) continue;
    const parts = n.id.split(':');
    if (parts.length >= 3) {
      const modId = `module:${parts[1].replace(/\\/g, '/')}`;
      if (moduleIds.has(modId)) map.set(n.id, modId);
    }
  }
  return map;
}

/** Project map: modules + API endpoints, with function-level calls rolled up to module level. */
function buildMapGraph(nodes: GraphNodeData[], edges: GraphEdgeData[], symbolToModule: Map<string, string>) {
  const kept = nodes.filter((n) => n.type === 'MODULE' || n.type === 'ENDPOINT');
  const moduleIds = new Set(kept.filter((n) => n.type === 'MODULE').map((n) => n.id));
  const endpointIds = new Set(kept.filter((n) => n.type === 'ENDPOINT').map((n) => n.id));
  const moduleOf = (id: string) => (moduleIds.has(id) ? id : symbolToModule.get(id));

  const out = new Map<string, GraphEdgeData>();
  const add = (s: string | undefined, t: string | undefined, rel: string, confidence: number) => {
    if (!s || !t || s === t) return;
    const key = `${s}->${t}`;
    if (!out.has(key)) out.set(key, { source: s, target: t, relationship: rel, confidence });
  };

  for (const e of edges) {
    const rel = relOf(e);
    const sEnd = endpointIds.has(e.source);
    const tEnd = endpointIds.has(e.target);
    if (sEnd || tEnd) {
      // An endpoint "depends on" the module that handles it, whichever way the edge was stored.
      add(sEnd ? e.source : e.target, moduleOf(sEnd ? e.target : e.source), 'HANDLED_BY', 1);
    } else if (moduleIds.has(e.source) && moduleIds.has(e.target)) {
      add(e.source, e.target, !rel || rel === 'CONTAINS' ? 'DEPENDS_ON' : rel, e.confidence ?? 1);
    } else if (rel === 'CALLS') {
      add(moduleOf(e.source), moduleOf(e.target), 'DEPENDS_ON', 0.9);
    }
  }
  return { nodes: kept, edges: Array.from(out.values()) };
}

const groupSort = (a: string, b: string) => {
  const rank = (k: string) => (k === ENDPOINT_GROUP ? 0 : k === PROJECT_GROUP ? 1 : k === 'Other' ? 3 : 2);
  return rank(a) - rank(b) || a.localeCompare(b);
};

/** Deterministic "folder box" layout: one box per folder, cards in a grid, boxes shelf-packed. */
function computeLayout(nodes: GraphNodeData[], edges: GraphEdgeData[], groupOf: (n: GraphNodeData) => string) {
  const inDeg = new Map<string, number>();
  const outDeg = new Map<string, number>();
  for (const e of edges) {
    outDeg.set(e.source, (outDeg.get(e.source) ?? 0) + 1);
    inDeg.set(e.target, (inDeg.get(e.target) ?? 0) + 1);
  }

  // "Heat": top slice of most-used items = high impact. Endpoints are entry points, so they're excluded.
  const used = nodes.filter((n) => n.type !== 'ENDPOINT').map((n) => inDeg.get(n.id) ?? 0).sort((a, b) => b - a);
  const highCut = Math.max(3, used[Math.floor(used.length * 0.1)] ?? 0);
  const medCut = Math.max(2, used[Math.floor(used.length * 0.3)] ?? 0);

  const buckets = new Map<string, GraphNodeData[]>();
  for (const n of nodes) {
    const k = groupOf(n);
    const list = buckets.get(k);
    if (list) list.push(n);
    else buckets.set(k, [n]);
  }

  const maxRowW = clamp(Math.sqrt(nodes.length) * 300, 900, 2600);
  const laidOut: LayoutNode[] = [];
  const groups: GroupBox[] = [];
  let cx = 0, cy = 0, rowH = 0;

  for (const key of Array.from(buckets.keys()).sort(groupSort)) {
    const items = buckets
      .get(key)!
      .sort((a, b) => (inDeg.get(b.id) ?? 0) - (inDeg.get(a.id) ?? 0) || a.label.localeCompare(b.label));
    const cols = clamp(Math.ceil(Math.sqrt(items.length)), 1, 4);
    const rows = Math.ceil(items.length / cols);
    const gw = cols * NODE_W + (cols - 1) * GAP + PAD * 2;
    const gh = HEAD + rows * NODE_H + (rows - 1) * GAP + PAD * 2;
    if (cx > 0 && cx + gw > maxRowW) {
      cx = 0;
      cy += rowH + GROUP_GAP;
      rowH = 0;
    }
    groups.push({ key, x: cx, y: cy, w: gw, h: gh, count: items.length });

    items.forEach((n, i) => {
      const col = i % cols;
      const row = Math.floor(i / cols);
      const iD = inDeg.get(n.id) ?? 0;
      const oD = outDeg.get(n.id) ?? 0;
      const label = n.label || n.id;
      const method = typeof n.properties?.method === 'string' ? n.properties.method : '';
      laidOut.push({
        ...n,
        x: cx + PAD + col * (NODE_W + GAP) + NODE_W / 2,
        y: cy + HEAD + PAD + row * (NODE_H + GAP) + NODE_H / 2,
        w: NODE_W,
        h: NODE_H,
        inDegree: iD,
        outDegree: oD,
        title: truncate(label.split('/').pop() || label, 22),
        subtitle:
          n.type === 'ENDPOINT' ? method || 'API endpoint' : n.type === 'PROJECT' ? 'Project' : `Used by ${iD} · Uses ${oD}`,
        heat: n.type === 'ENDPOINT' ? 0 : iD >= highCut ? 2 : iD >= medCut ? 1 : 0,
      });
    });

    cx += gw + GROUP_GAP;
    rowH = Math.max(rowH, gh);
  }
  return { nodes: laidOut, groups };
}

/** Everything reachable from `start` by following `adj` (excluding start). */
function reach(start: string, adj: Map<string, string[]>) {
  const seen = new Set<string>();
  const stack = [start];
  while (stack.length) {
    for (const next of adj.get(stack.pop()!) ?? []) {
      if (next !== start && !seen.has(next)) {
        seen.add(next);
        stack.push(next);
      }
    }
  }
  return seen;
}

function clipToRect(cx: number, cy: number, hw: number, hh: number, dx: number, dy: number, gap: number) {
  const len = Math.hypot(dx, dy);
  if (len === 0) return { x: cx, y: cy };
  const k = 1 / Math.max(Math.abs(dx) / hw, Math.abs(dy) / hh);
  return { x: cx + dx * k + (dx / len) * gap, y: cy + dy * k + (dy / len) * gap };
}

function edgePath(s: Rect, t: Rect) {
  const dx = t.x - s.x;
  const dy = t.y - s.y;
  const cx = (s.x + t.x) / 2 - dy * 0.15;
  const cy = (s.y + t.y) / 2 + dx * 0.15;
  const a = clipToRect(s.x, s.y, s.w / 2, s.h / 2, cx - s.x, cy - s.y, 2);
  const b = clipToRect(t.x, t.y, t.w / 2, t.h / 2, cx - t.x, cy - t.y, 4);
  return `M ${a.x} ${a.y} Q ${cx} ${cy} ${b.x} ${b.y}`;
}

function boundsOf(rects: Rect[]): Bounds {
  if (rects.length === 0) return { minX: 0, minY: 0, maxX: 900, maxY: 560 };
  const b = { minX: Infinity, minY: Infinity, maxX: -Infinity, maxY: -Infinity };
  for (const r of rects) {
    b.minX = Math.min(b.minX, r.x - r.w / 2);
    b.maxX = Math.max(b.maxX, r.x + r.w / 2);
    b.minY = Math.min(b.minY, r.y - r.h / 2);
    b.maxY = Math.max(b.maxY, r.y + r.h / 2);
  }
  return b;
}

/* ──────────────────────── Memoised SVG parts ──────────────────────── */

interface EdgeViewProps {
  s: Rect;
  t: Rect;
  kind: EdgeKind;
  rel: string;
  markerPrefix: string;
}

const EdgeView = memo(function EdgeView({ s, t, kind, rel, markerPrefix }: EdgeViewProps) {
  const st = EDGE_STYLE[kind];
  return (
    <path
      d={edgePath(s, t)}
      fill="none"
      stroke={st.color}
      strokeWidth={st.width}
      strokeOpacity={st.opacity}
      markerEnd={`url(#${markerPrefix}-${st.color.slice(1)})`}
    >
      <title>{rel.replace(/_/g, ' ').toLowerCase()}</title>
    </path>
  );
});

interface NodeViewProps {
  node: LayoutNode;
  role: Role;
  hovered: boolean;
  dimmed: boolean;
  showText: boolean;
  onSelect: (id: string) => void;
  onHover: (id: string | null) => void;
}

const HEAT_STYLE = { 1: { text: 'MED', fill: AMBER }, 2: { text: 'HIGH', fill: '#f87171' } } as const;

const NodeView = memo(function NodeView({ node, role, hovered, dimmed, showText, onSelect, onHover }: NodeViewProps) {
  const { border, Icon, label: typeLabel } = styleOf(node.type);
  const stroke = role === 'selected' ? 'var(--brand)' : role === 'affected' ? AMBER : role === 'uses' ? CYAN : border;
  const fill =
    role === 'selected'
      ? 'var(--bg-hover)'
      : role === 'affected'
      ? 'var(--status-flaky-bg)'
      : role === 'uses'
      ? 'var(--status-running-bg)'
      : hovered
      ? 'var(--bg-hover)'
      : 'var(--bg-card)';
  const hw = node.w / 2;
  const hh = node.h / 2;
  const heat = node.heat ? HEAT_STYLE[node.heat] : null;

  return (
    <g
      transform={`translate(${node.x}, ${node.y})`}
      style={{ opacity: dimmed ? 0.25 : 1, cursor: 'pointer' }}
      role="button"
      tabIndex={0}
      aria-pressed={role === 'selected'}
      aria-label={`${typeLabel} ${node.label}. Used by ${node.inDegree}, uses ${node.outDegree}.`}
      onPointerDown={(e) => e.stopPropagation()}
      onClick={() => onSelect(node.id)}
      onPointerEnter={() => onHover(node.id)}
      onPointerLeave={() => onHover(null)}
      onFocus={() => onHover(node.id)}
      onBlur={() => onHover(null)}
      onKeyDown={(e) => {
        if (e.key === 'Enter' || e.key === ' ') {
          e.preventDefault();
          onSelect(node.id);
        }
      }}
    >
      <title>{`${node.label} (${typeLabel})`}</title>
      <rect
        x={-hw} y={-hh} width={node.w} height={node.h} rx={12}
        fill={fill} stroke={stroke} strokeWidth={role === 'none' ? (hovered ? 1.8 : 1.2) : 2.2}
      />
      <circle cx={-hw + 22} cy={0} r={12} fill={border} fillOpacity={0.15} stroke={border} style={{ pointerEvents: 'none' }} />
      <Icon x={-hw + 15} y={-7} size={14} color={border} style={{ pointerEvents: 'none' }} />
      {showText && (
        <>
          <text x={-hw + 42} y={-3} fill="var(--text-primary)" fontSize={11} fontWeight={600} fontFamily="Inter, system-ui, sans-serif" style={{ pointerEvents: 'none', userSelect: 'none' }}>
            {node.title}
          </text>
          <text x={-hw + 42} y={11} fill="var(--text-muted)" fontSize={9} fontFamily="Inter, system-ui, sans-serif" style={{ pointerEvents: 'none', userSelect: 'none' }}>
            {node.subtitle}
          </text>
        </>
      )}
      {heat && (
        <g transform={`translate(${hw - 34}, ${-hh - 7})`} style={{ pointerEvents: 'none' }}>
          <rect width={heat.text === 'HIGH' ? 34 : 28} height={14} rx={7} fill={heat.fill} />
          <text x={heat.text === 'HIGH' ? 17 : 14} y={10} fill="#ffffff" fontSize={8} fontWeight="bold" fontFamily="Inter, system-ui, sans-serif" textAnchor="middle">
            {heat.text}
          </text>
        </g>
      )}
    </g>
  );
});

/* ─────────────────────────── Small UI parts ───────────────────────── */

const TypeBadge: React.FC<{ type: string }> = ({ type }) => (
  <span className={`px-2 py-0.5 rounded font-bold border text-[10px] font-mono uppercase tracking-wider ${styleOf(type).badge}`}>
    {styleOf(type).label}
  </span>
);

const Stat: React.FC<{ label: string; value: number; tone: string }> = ({ label, value, tone }) => (
  <div className="rounded-xl bg-field border border-border-card px-4 py-2.5 min-w-[110px]">
    <div className={`text-xl font-bold font-mono leading-none ${tone}`}>{value}</div>
    <div className="text-[11px] text-muted mt-1">{label}</div>
  </div>
);

const NodeLink: React.FC<{ node: LayoutNode; onClick: (id: string) => void }> = ({ node, onClick }) => {
  const { Icon, border } = styleOf(node.type);
  return (
    <button
      onClick={() => onClick(node.id)}
      className="w-full px-2.5 py-1.5 rounded-lg bg-field hover:bg-hover border border-border-card text-left text-xs flex items-center gap-2 transition-colors"
    >
      <Icon size={13} color={border} className="shrink-0" />
      <span className="truncate text-primary font-medium">{node.label.split('/').pop()}</span>
      {node.type === 'ENDPOINT' && typeof node.properties?.method === 'string' && (
        <span className="ml-auto text-[9px] text-status-passed font-bold">{node.properties.method}</span>
      )}
    </button>
  );
};

const Section: React.FC<{ title: React.ReactNode; defaultOpen?: boolean; children: React.ReactNode }> = ({ title, defaultOpen, children }) => (
  <details open={defaultOpen} className="group rounded-xl bg-field border border-border-card p-3">
    <summary className="cursor-pointer list-none flex items-center justify-between text-xs font-bold text-primary">
      {title}
      <ChevronRight className="w-3.5 h-3.5 text-muted transition-transform group-open:rotate-90" />
    </summary>
    <div className="mt-3 space-y-1.5">{children}</div>
  </details>
);

/* ───────────────────────────── Component ──────────────────────────── */

export const KnowledgeGraphVisualizer: React.FC<KnowledgeGraphVisualizerProps> = ({
  graph,
  projectName = 'Repository',
  onSelectNode,
}) => {
  const [viewMode, setViewMode] = useState<ViewMode>('map');
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedNodeId, setSelectedNodeId] = useState<string | null>(null);
  const [hoveredNodeId, setHoveredNodeId] = useState<string | null>(null);
  const [show, setShow] = useState<Record<FilterableType, boolean>>({ MODULE: true, ENDPOINT: true, FUNCTION: true });
  const [showAllLinks, setShowAllLinks] = useState(false);
  const [view, setView] = useState({ k: 1, x: 0, y: 0 });
  const [size, setSize] = useState({ w: 0, h: 0 });
  const [copied, setCopied] = useState(false);

  const svgRef = useRef<SVGSVGElement | null>(null);
  const containerRef = useRef<HTMLDivElement | null>(null);
  const panRef = useRef<{ pointerId: number; sx: number; sy: number; ox: number; oy: number; moved: boolean } | null>(null);
  const pendingFocus = useRef<string | null>(null);
  const markerPrefix = `kg${useId().replace(/:/g, '')}`;

  const showCanvas = viewMode !== 'table';

  /* 1. Normalise input and derive the graph for the current view */
  const { rawNodes, rawEdges } = useMemo(
    () => ({
      rawNodes: graph?.nodes ?? [],
      rawEdges: (graph?.edges ?? []).map((e) => ({ ...e, relationship: relOf(e) || 'RELATED' })),
    }),
    [graph]
  );
  const symbolToModule = useMemo(() => mapSymbolsToModules(rawNodes, rawEdges), [rawNodes, rawEdges]);
  const rawNodeById = useMemo(() => new Map(rawNodes.map((n) => [n.id, n])), [rawNodes]);

  const totals = useMemo(() => {
    const count = (t: string) => rawNodes.filter((n) => n.type === t).length;
    return { modules: count('MODULE'), endpoints: count('ENDPOINT'), functions: count('FUNCTION'), links: rawEdges.length };
  }, [rawNodes, rawEdges]);

  const processed = useMemo(() => {
    if (viewMode === 'table') return { nodes: rawNodes, edges: rawEdges };
    if (viewMode === 'map') return buildMapGraph(rawNodes, rawEdges, symbolToModule);
    const allowed = new Set<string>(['PROJECT']);
    (Object.keys(show) as FilterableType[]).forEach((t) => show[t] && allowed.add(t));
    const nodes = rawNodes.filter((n) => allowed.has(n.type));
    const ids = new Set(nodes.map((n) => n.id));
    return { nodes, edges: rawEdges.filter((e) => e.source !== e.target && ids.has(e.source) && ids.has(e.target)) };
  }, [rawNodes, rawEdges, symbolToModule, viewMode, show]);

  /* 2. Layout */
  const layout = useMemo(() => {
    if (!showCanvas) return { nodes: [] as LayoutNode[], groups: [] as GroupBox[] };
    const groupOf = (n: GraphNodeData) => {
      if (n.type === 'ENDPOINT') return ENDPOINT_GROUP;
      if (n.type === 'PROJECT') return PROJECT_GROUP;
      const mod = n.type === 'MODULE' ? n : rawNodeById.get(symbolToModule.get(n.id) ?? '');
      return mod ? folderOf(mod.label || mod.id) : 'Other';
    };
    return computeLayout(processed.nodes, processed.edges, groupOf);
  }, [processed, showCanvas, rawNodeById, symbolToModule]);

  const baseNodes = layout.nodes;
  const baseNodeMap = useMemo(() => new Map(baseNodes.map((n) => [n.id, n])), [baseNodes]);
  const edges = useMemo(
    () => (showCanvas ? processed.edges.filter((e) => baseNodeMap.has(e.source) && baseNodeMap.has(e.target)) : []),
    [processed.edges, baseNodeMap, showCanvas]
  );
  const bounds = useMemo(
    () => boundsOf(layout.groups.map((g) => ({ x: g.x + g.w / 2, y: g.y + g.h / 2, w: g.w, h: g.h }))),
    [layout.groups]
  );

  const live = useRef({ view, size, baseNodeMap, bounds });
  live.current = { view, size, baseNodeMap, bounds };

  /* 3. Impact analysis: what is affected if X changes, and what X depends on */
  const { inAdj, outAdj } = useMemo(() => {
    const i = new Map<string, string[]>();
    const o = new Map<string, string[]>();
    for (const e of edges) {
      (o.get(e.source) ?? o.set(e.source, []).get(e.source)!).push(e.target);
      (i.get(e.target) ?? i.set(e.target, []).get(e.target)!).push(e.source);
    }
    return { inAdj: i, outAdj: o };
  }, [edges]);

  const selected = selectedNodeId ? baseNodeMap.get(selectedNodeId) ?? null : null;
  const selectedId = selected?.id ?? null;

  const impact = useMemo(() => {
    if (!selectedId) return null;
    const affected = reach(selectedId, inAdj);
    const uses = reach(selectedId, outAdj);
    const toNodes = (set: Set<string>) =>
      Array.from(set)
        .map((id) => baseNodeMap.get(id))
        .filter((n): n is LayoutNode => !!n)
        .sort((a, b) => Number(b.type === 'ENDPOINT') - Number(a.type === 'ENDPOINT') || b.inDegree - a.inDegree);
    return { affected, uses, affectedNodes: toNodes(affected), usesNodes: toNodes(uses) };
  }, [selectedId, inAdj, outAdj, baseNodeMap]);

  /** Links are hidden by default and revealed on demand, so the map stays readable. */
  const drawnEdges = useMemo(() => {
    const keyOf = (e: GraphEdgeData) => `${e.source}->${e.target}`;
    if (selectedId && impact) {
      const aff = new Set([selectedId, ...impact.affected]);
      const use = new Set([selectedId, ...impact.uses]);
      return edges.flatMap((e) =>
        aff.has(e.source) && aff.has(e.target) ? [{ e, kind: 'affected' as EdgeKind, key: keyOf(e) }]
        : use.has(e.source) && use.has(e.target) ? [{ e, kind: 'uses' as EdgeKind, key: keyOf(e) }]
        : []
      );
    }
    if (hoveredNodeId) {
      return edges
        .filter((e) => e.source === hoveredNodeId || e.target === hoveredNodeId)
        .map((e) => ({ e, kind: 'hover' as EdgeKind, key: keyOf(e) }));
    }
    if (showAllLinks) return edges.map((e) => ({ e, kind: 'all' as EdgeKind, key: keyOf(e) }));
    return [];
  }, [selectedId, impact, hoveredNodeId, showAllLinks, edges]);

  /* 4. Search + sidebar data */
  const query = searchQuery.trim().toLowerCase();
  const matches = useCallback(
    (n: GraphNodeData) => n.label.toLowerCase().includes(query) || n.id.toLowerCase().includes(query),
    [query]
  );
  const matchedIds = useMemo(() => (query ? new Set(baseNodes.filter(matches).map((n) => n.id)) : null), [query, baseNodes, matches]);

  const hotSpots = useMemo(
    () => baseNodes.filter((n) => n.type !== 'ENDPOINT' && n.inDegree > 0).sort((a, b) => b.inDegree - a.inDegree).slice(0, 6),
    [baseNodes]
  );
  const endpointNodes = useMemo(
    () => baseNodes.filter((n) => n.type === 'ENDPOINT').sort((a, b) => a.label.localeCompare(b.label)),
    [baseNodes]
  );
  const unlinkedCount = useMemo(
    () => baseNodes.filter((n) => n.type === 'MODULE' && n.inDegree + n.outDegree === 0).length,
    [baseNodes]
  );

  /* 5. Viewport */
  const zoomAt = useCallback((px: number, py: number, factor: number) => {
    setView((v) => {
      const k = clamp(v.k * factor, MIN_ZOOM, MAX_ZOOM);
      const r = k / v.k;
      return { k, x: px - (px - v.x) * r, y: py - (py - v.y) * r };
    });
  }, []);

  const fitView = useCallback((b: Bounds) => {
    const { w, h } = live.current.size;
    if (!w || !h) return;
    const pad = 40;
    const k = clamp(Math.min(w / (b.maxX - b.minX + pad * 2), h / (b.maxY - b.minY + pad * 2), 1), MIN_ZOOM, MAX_ZOOM);
    setView({ k, x: w / 2 - ((b.minX + b.maxX) / 2) * k, y: h / 2 - ((b.minY + b.maxY) / 2) * k });
  }, []);

  const centerOn = useCallback((id: string) => {
    const { baseNodeMap: map, size: s, view: v } = live.current;
    const n = map.get(id);
    if (!n) return;
    const k = Math.max(v.k, 0.8); // zoom in enough that the text is readable
    setView({ k, x: s.w / 2 - n.x * k, y: s.h / 2 - n.y * k });
  }, []);

  const selectNode = useCallback(
    (id: string) => {
      setSelectedNodeId(id);
      onSelectNode?.(id);
    },
    [onSelectNode]
  );
  const selectAndCenter = useCallback(
    (id: string) => {
      selectNode(id);
      centerOn(id);
    },
    [selectNode, centerOn]
  );

  useEffect(() => {
    const el = containerRef.current;
    if (!el) return;
    const ro = new ResizeObserver(([entry]) => setSize({ w: entry.contentRect.width, h: entry.contentRect.height }));
    ro.observe(el);
    return () => ro.disconnect();
  }, [showCanvas]);

  // React's onWheel is passive, so preventDefault needs a native listener.
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
    const n = target ? baseNodeMap.get(target) : undefined;
    if (n) setView({ k: 1, x: live.current.size.w / 2 - n.x, y: live.current.size.h / 2 - n.y });
    else fitView(bounds);
  }, [baseNodeMap, bounds, showCanvas, hasSize, fitView]);

  /* 6. Pan (mouse, touch, pen) */
  const onCanvasPointerDown = (e: React.PointerEvent<SVGSVGElement>) => {
    e.currentTarget.setPointerCapture(e.pointerId);
    const v = live.current.view;
    panRef.current = { pointerId: e.pointerId, sx: e.clientX, sy: e.clientY, ox: v.x, oy: v.y, moved: false };
  };
  const onCanvasPointerMove = (e: React.PointerEvent<SVGSVGElement>) => {
    const p = panRef.current;
    if (!p || p.pointerId !== e.pointerId) return;
    const mx = e.clientX - p.sx;
    const my = e.clientY - p.sy;
    if (Math.hypot(mx, my) > 3) p.moved = true;
    setView((v) => ({ ...v, x: p.ox + mx, y: p.oy + my }));
  };
  const onCanvasPointerEnd = (e: React.PointerEvent<SVGSVGElement>) => {
    const p = panRef.current;
    if (!p || p.pointerId !== e.pointerId) return;
    if (!p.moved) setSelectedNodeId(null); // click on empty space
    panRef.current = null;
    if (e.currentTarget.hasPointerCapture(e.pointerId)) e.currentTarget.releasePointerCapture(e.pointerId);
  };

  const zoomBy = (f: number) => zoomAt(live.current.size.w / 2, live.current.size.h / 2, f);

  /* 7. Actions */
  const focusFromTable = (node: GraphNodeData) => {
    pendingFocus.current = node.id;
    setViewMode(node.type === 'MODULE' || node.type === 'ENDPOINT' ? 'map' : 'detailed');
    setSelectedNodeId(node.id);
  };

  const onSearchKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key !== 'Enter' || !showCanvas) return;
    const first = baseNodes.find(matches);
    if (first) selectAndCenter(first.id);
  };

  const copyRetestList = () => {
    if (!selected || !impact) return;
    const lines = [`Re-test if "${selected.label}" changes:`, ...impact.affectedNodes.map((n) => `- [${styleOf(n.type).label}] ${n.label}`)];
    navigator.clipboard?.writeText(lines.join('\n')).then(() => {
      setCopied(true);
      window.setTimeout(() => setCopied(false), 1500);
    });
  };

  const exportSvg = () => {
    const svg = svgRef.current;
    if (!svg) return;
    const pad = 40;
    const { minX, minY, maxX, maxY } = bounds;
    const w = maxX - minX + pad * 2;
    const h = maxY - minY + pad * 2;
    const clone = svg.cloneNode(true) as SVGSVGElement;
    clone.setAttribute('xmlns', 'http://www.w3.org/2000/svg');
    clone.setAttribute('viewBox', `${minX - pad} ${minY - pad} ${w} ${h}`);
    clone.setAttribute('width', String(Math.round(w)));
    clone.setAttribute('height', String(Math.round(h)));
    clone.removeAttribute('class');
    clone.removeAttribute('style');
    clone.querySelector('[data-world]')?.removeAttribute('transform');
    clone.querySelector('[data-grid]')?.remove();
    const bg = document.createElementNS('http://www.w3.org/2000/svg', 'rect');
    for (const [k, v] of Object.entries({ x: minX - pad, y: minY - pad, width: w, height: h, fill: '#020617' })) bg.setAttribute(k, String(v));
    clone.insertBefore(bg, clone.firstChild);

    const url = URL.createObjectURL(new Blob([new XMLSerializer().serializeToString(clone)], { type: 'image/svg+xml;charset=utf-8' }));
    const a = document.createElement('a');
    a.href = url;
    a.download = `${projectName.toLowerCase().replace(/[^a-z0-9]+/g, '_')}_project_map.svg`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  };

  /* 8. Table data */
  const rawDegree = useMemo(() => {
    const d = new Map<string, { in: number; out: number }>();
    const get = (id: string) => d.get(id) ?? d.set(id, { in: 0, out: 0 }).get(id)!;
    for (const e of rawEdges) {
      get(e.source).out++;
      get(e.target).in++;
    }
    return d;
  }, [rawEdges]);
  const tableRows = useMemo(
    () => (viewMode === 'table' ? rawNodes.filter((n) => !query || matches(n)) : []),
    [viewMode, rawNodes, query, matches]
  );

  /* 9. Render */
  const tabs: { mode: ViewMode; label: string; Icon: LucideIcon }[] = [
    { mode: 'map', label: 'Project map', Icon: Layers },
    { mode: 'detailed', label: 'Detailed graph', Icon: Network },
    { mode: 'table', label: 'Table', Icon: List },
  ];
  const tabClass = (active: boolean) =>
    `px-3 py-1.5 rounded-lg font-semibold flex items-center gap-1.5 transition-all ${
      active ? 'bg-brand text-on-brand shadow-sm' : 'text-secondary hover:text-primary'
    }`;
  const iconBtn = 'p-1.5 rounded-lg text-secondary hover:text-primary hover:bg-hover transition-colors';
  const maxUsed = hotSpots[0]?.inDegree || 1;

  return (
    <div className="space-y-4">
      {/* Summary: the whole project in one row */}
      <div className="bg-card rounded-2xl p-4 border border-border-card shadow-card flex flex-wrap items-center gap-3">
        <div className="mr-2">
          <h2 className="text-sm font-bold text-primary">{projectName}</h2>
          <p className="text-[11px] text-secondary max-w-[260px]">Click any box to see what it uses and what to re-test if it changes.</p>
        </div>
        <Stat label="Modules" value={totals.modules} tone="text-secondaryAccent" />
        <Stat label="API endpoints" value={totals.endpoints} tone="text-status-passed" />
        <Stat label="Functions" value={totals.functions} tone="text-brand" />
        <Stat label="Dependencies" value={totals.links} tone="text-brand" />
      </div>

      {/* Controls */}
      <div className="bg-card rounded-2xl p-3 border border-border-card shadow-card flex flex-col lg:flex-row items-stretch lg:items-center justify-between gap-3">
        <div role="tablist" aria-label="Graph view" className="flex flex-wrap items-center bg-field border border-border-card rounded-xl p-1 text-xs">
          {tabs.map(({ mode, label, Icon }) => (
            <button key={mode} role="tab" aria-selected={viewMode === mode} onClick={() => setViewMode(mode)} className={tabClass(viewMode === mode)}>
              <Icon className="w-3.5 h-3.5" /> {label}
            </button>
          ))}
        </div>

        <div className="flex flex-wrap items-center gap-3">
          <div className="relative flex-1 sm:w-64">
            <Search className="w-3.5 h-3.5 text-muted absolute left-3 top-1/2 -translate-y-1/2" aria-hidden />
            <input
              type="search"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              onKeyDown={onSearchKeyDown}
              placeholder="Find a module, endpoint or function…"
              aria-label="Search"
              className="w-full bg-field border border-border-field rounded-xl pl-8 pr-8 py-1.5 text-xs text-primary placeholder-muted focus:outline-none focus:ring-2 focus:ring-brand"
            />
            {searchQuery && (
              <button onClick={() => setSearchQuery('')} aria-label="Clear search" className="absolute right-2.5 top-1/2 -translate-y-1/2 text-muted hover:text-primary">
                <X className="w-3 h-3" />
              </button>
            )}
          </div>

          {viewMode === 'detailed' && (
            <div className="flex items-center gap-3 text-[11px] font-semibold text-secondary">
              {FILTERS.map(({ type, label }) => (
                <label key={type} className="flex items-center gap-1 cursor-pointer">
                  <input
                    type="checkbox"
                    checked={show[type]}
                    onChange={(e) => setShow((s) => ({ ...s, [type]: e.target.checked }))}
                    className="rounded bg-field border-border-field text-brand focus:ring-brand"
                  />
                  {label}
                </label>
              ))}
            </div>
          )}

          {showCanvas && (
            <label className="flex items-center gap-1.5 text-[11px] font-semibold text-secondary cursor-pointer">
              <input type="checkbox" checked={showAllLinks} onChange={(e) => setShowAllLinks(e.target.checked)} className="rounded bg-field border-border-field text-brand focus:ring-brand" />
              Show all links
            </label>
          )}

          <button
            onClick={exportSvg}
            disabled={!showCanvas || baseNodes.length === 0}
            className="p-2 rounded-xl bg-field hover:bg-hover border border-border-card text-secondary hover:text-primary transition-colors disabled:opacity-40 disabled:pointer-events-none"
            title="Export as SVG"
            aria-label="Export as SVG"
          >
            <Download className="w-4 h-4" />
          </button>
        </div>
      </div>

      {showCanvas ? (
        <div className="flex flex-col lg:flex-row gap-4">
          {/* Sidebar */}
          <aside className="lg:w-64 shrink-0 space-y-3 lg:max-h-[620px] lg:overflow-y-auto">
            <Section
              defaultOpen
              title={<span className="flex items-center gap-1.5"><Flame className="w-3.5 h-3.5 text-status-failed" /> Test these first</span>}
            >
              <p className="text-[11px] text-muted pb-1">Most-used parts. A bug here reaches the most places.</p>
              {hotSpots.map((n) => (
                <button key={n.id} onClick={() => selectAndCenter(n.id)} className="w-full text-left group">
                  <div className="flex items-center justify-between text-xs font-mono">
                    <span className="truncate text-primary group-hover:text-brand">{n.label.split('/').pop()}</span>
                    <span className="text-secondary ml-2">{n.inDegree}</span>
                  </div>
                  <div className="h-1.5 rounded-full bg-field border border-border-card mt-1 overflow-hidden">
                    <div className="h-full rounded-full" style={{ width: `${(n.inDegree / maxUsed) * 100}%`, background: n.heat === 2 ? 'var(--status-failed)' : n.heat === 1 ? AMBER : 'var(--text-muted)' }} />
                  </div>
                </button>
              ))}
              {hotSpots.length === 0 && <p className="text-[11px] text-muted italic">No dependencies found.</p>}
              {unlinkedCount > 0 && (
                <p className="text-[11px] text-muted pt-1">{plural(unlinkedCount, 'module')} with no links (unused, or only reached at runtime).</p>
              )}
            </Section>

            {endpointNodes.length > 0 && (
              <Section title={`API endpoints (${endpointNodes.length})`}>
                <div className="max-h-56 overflow-y-auto space-y-1.5 pr-1">
                  {endpointNodes.map((n) => <NodeLink key={n.id} node={n} onClick={selectAndCenter} />)}
                </div>
              </Section>
            )}

            <Section title="How to read this">
              <ul className="text-[11px] text-secondary space-y-1.5">
                <li>Each outlined area is a folder.</li>
                <li><span className="text-status-failed font-bold">HIGH</span> / <span className="text-status-flaky font-bold">MED</span> tags mark parts many others rely on.</li>
                <li><span className="text-status-flaky font-bold">Amber</span>: re-test if the selected item changes.</li>
                <li><span className="text-secondaryAccent font-bold">Cyan</span>: what the selected item depends on.</li>
                <li>Arrows point from the caller to the dependency.</li>
              </ul>
            </Section>
          </aside>

          {/* Canvas */}
          <div
            ref={containerRef}
            className="relative flex-1 min-w-0 h-[620px] bg-field rounded-2xl border border-border-card overflow-hidden shadow-card select-none"
            onKeyDown={(e) => e.key === 'Escape' && setSelectedNodeId(null)}
          >
            <div className="absolute bottom-4 right-4 z-10 flex items-center gap-1.5 bg-card/90 border border-border-card rounded-xl p-1 shadow-card backdrop-blur-md">
              <button onClick={() => zoomBy(1.2)} className={iconBtn} title="Zoom in" aria-label="Zoom in"><ZoomIn className="w-4 h-4" /></button>
              <button onClick={() => zoomBy(1 / 1.2)} className={iconBtn} title="Zoom out" aria-label="Zoom out"><ZoomOut className="w-4 h-4" /></button>
              <button onClick={() => { setSelectedNodeId(null); fitView(live.current.bounds); }} className={iconBtn} title="Show whole project" aria-label="Show whole project"><Maximize2 className="w-4 h-4" /></button>
            </div>

            {baseNodes.length === 0 && (
              <div className="absolute inset-0 z-10 flex items-center justify-center text-sm text-muted pointer-events-none">
                {viewMode === 'detailed' ? 'Nothing to show. Turn on a type above.' : 'No modules or endpoints found.'}
              </div>
            )}

            <svg
              ref={svgRef}
              role="group"
              aria-label={`${projectName} project map`}
              className="w-full h-full cursor-grab active:cursor-grabbing"
              style={{ touchAction: 'none' }}
              onPointerDown={onCanvasPointerDown}
              onPointerMove={onCanvasPointerMove}
              onPointerUp={onCanvasPointerEnd}
              onPointerCancel={onCanvasPointerEnd}
            >
              <defs>
                <pattern id={`${markerPrefix}-grid`} width="30" height="30" patternUnits="userSpaceOnUse">
                  <circle cx="2" cy="2" r="1.2" fill="var(--border-card)" opacity="0.9" />
                </pattern>
                {MARKER_COLORS.map((c) => (
                  <marker key={c} id={`${markerPrefix}-${c.slice(1)}`} viewBox="0 0 10 10" refX="9" refY="5" markerWidth="8" markerHeight="8" markerUnits="userSpaceOnUse" orient="auto">
                    <path d="M 0 1 L 10 5 L 0 9 z" fill={c} />
                  </marker>
                ))}
              </defs>
              <rect data-grid width="100%" height="100%" fill={`url(#${markerPrefix}-grid)`} />

              <g data-world transform={`translate(${view.x}, ${view.y}) scale(${view.k})`}>
                {/* Folder boxes */}
                <g>
                  {layout.groups.map((g) => (
                    <g key={g.key} style={{ pointerEvents: 'none' }}>
                      <rect
                        x={g.x} y={g.y} width={g.w} height={g.h} rx={18}
                        fill="var(--bg-card)" fillOpacity={0.65}
                        stroke={g.key === ENDPOINT_GROUP ? 'var(--status-passed)' : 'var(--border-card)'} strokeWidth={1.2}
                      />
                      <text x={g.x + PAD} y={g.y + 21} fill="var(--text-primary)" fontSize={12} fontWeight={700} fontFamily="Inter, sans-serif">
                        {truncate(g.key, 34)}
                        <tspan fill="var(--text-muted)" fontWeight={500}>{`  (${g.count})`}</tspan>
                      </text>
                    </g>
                  ))}
                </g>

                {/* Links (only the relevant ones) */}
                <g>
                  {drawnEdges.map(({ e, kind, key }) => {
                    const s = baseNodeMap.get(e.source)!;
                    const t = baseNodeMap.get(e.target)!;
                    return <EdgeView key={`${key}:${kind}`} s={s} t={t} kind={kind} rel={e.relationship ?? 'RELATED'} markerPrefix={markerPrefix} />;
                  })}
                </g>

                {/* Cards */}
                <g>
                  {baseNodes.map((n) => {
                    const role: Role =
                      selectedId === n.id ? 'selected'
                      : impact?.affected.has(n.id) ? 'affected'
                      : impact?.uses.has(n.id) ? 'uses'
                      : 'none';
                    const dimmed = impact ? role === 'none' : !!matchedIds && !matchedIds.has(n.id);
                    return (
                      <NodeView
                        key={n.id}
                        node={n}
                        role={role}
                        hovered={hoveredNodeId === n.id}
                        dimmed={dimmed}
                        showText={view.k >= 0.35}
                        onSelect={selectNode}
                        onHover={setHoveredNodeId}
                      />
                    );
                  })}
                </g>
              </g>
            </svg>

            {/* Inspector */}
            {selected && impact && (
              <aside
                aria-label="Details"
                className="absolute top-4 right-4 bottom-4 w-72 max-w-[calc(100%-2rem)] bg-card border border-border-card rounded-2xl p-4 shadow-card flex flex-col gap-3 z-20 overflow-y-auto"
              >
                <div className="flex items-start justify-between gap-2 border-b border-border-card pb-3">
                  <div className="space-y-1.5 min-w-0">
                    <TypeBadge type={selected.type} />
                    <h3 className="text-sm font-bold text-primary font-mono break-all leading-tight">{selected.label}</h3>
                    {(selected.properties?.language || selected.properties?.lines !== undefined) && (
                      <p className="text-[11px] text-muted font-mono">
                        {[selected.properties?.language, selected.properties?.lines !== undefined ? `${selected.properties.lines} lines` : null].filter(Boolean).join(' · ')}
                      </p>
                    )}
                  </div>
                  <button onClick={() => setSelectedNodeId(null)} className={iconBtn} aria-label="Close details"><X className="w-4 h-4" /></button>
                </div>

                <p className="text-xs text-secondary leading-relaxed bg-field border border-border-field rounded-xl p-3">
                  {impact.affectedNodes.length === 0
                    ? 'Nothing else depends on this, so a change here stays local.'
                    : `A change here could affect ${plural(impact.affectedNodes.length, 'item')}, including ${plural(impact.affectedNodes.filter((n) => n.type === 'ENDPOINT').length, 'API endpoint')}.`}
                </p>

                <div className="space-y-1.5">
                  <div className="flex items-center justify-between">
                    <h4 className="text-[11px] font-bold text-status-flaky">Re-test if this changes ({impact.affectedNodes.length})</h4>
                    {impact.affectedNodes.length > 0 && (
                      <button onClick={copyRetestList} className="text-[10px] text-secondary hover:text-primary flex items-center gap-1">
                        {copied ? <Check className="w-3 h-3 text-status-passed" /> : <Copy className="w-3 h-3" />} {copied ? 'Copied' : 'Copy list'}
                      </button>
                    )}
                  </div>
                  <div className="space-y-1 max-h-44 overflow-y-auto pr-1">
                    {impact.affectedNodes.map((n) => <NodeLink key={n.id} node={n} onClick={selectAndCenter} />)}
                    {impact.affectedNodes.length === 0 && <p className="text-[11px] text-muted italic">None.</p>}
                  </div>
                </div>

                <div className="space-y-1.5">
                  <h4 className="text-[11px] font-bold text-secondaryAccent">Depends on ({impact.usesNodes.length})</h4>
                  <div className="space-y-1 max-h-44 overflow-y-auto pr-1">
                    {impact.usesNodes.map((n) => <NodeLink key={n.id} node={n} onClick={selectAndCenter} />)}
                    {impact.usesNodes.length === 0 && <p className="text-[11px] text-muted italic">None.</p>}
                  </div>
                </div>
              </aside>
            )}
          </div>
        </div>
      ) : (
        <div className="bg-card rounded-2xl border border-border-card overflow-hidden shadow-card">
          <div className="p-4 border-b border-border-card bg-field flex items-center justify-between">
            <h4 className="text-xs font-semibold text-secondary">
              {tableRows.length} of {rawNodes.length} items
            </h4>
            <span className="text-xs font-mono text-brand font-semibold">{rawEdges.length} dependencies</span>
          </div>
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs font-mono">
              <thead className="bg-field text-secondary border-b border-border-card text-[11px]">
                <tr>
                  <th scope="col" className="px-4 py-3">Type</th>
                  <th scope="col" className="px-4 py-3">Name</th>
                  <th scope="col" className="px-4 py-3">Used by</th>
                  <th scope="col" className="px-4 py-3">Uses</th>
                  <th scope="col" className="px-4 py-3">Details</th>
                  <th scope="col" className="px-4 py-3 text-right"><span className="sr-only">Actions</span></th>
                </tr>
              </thead>
              <tbody className="divide-y divide-border-card text-secondary">
                {tableRows.slice(0, TABLE_ROW_LIMIT).map((node) => {
                  const d = rawDegree.get(node.id);
                  return (
                    <tr key={node.id} className="hover:bg-hover transition-colors">
                      <td className="px-4 py-3"><TypeBadge type={node.type} /></td>
                      <td className="px-4 py-3 text-primary font-bold max-w-[280px] truncate" title={node.id}>{node.label}</td>
                      <td className="px-4 py-3">{d?.in ?? 0}</td>
                      <td className="px-4 py-3">{d?.out ?? 0}</td>
                      <td className="px-4 py-3 text-muted text-[11px] space-x-2">
                        {node.properties?.language && <span className="text-secondaryAccent">{node.properties.language}</span>}
                        {node.properties?.lines !== undefined && <span>{node.properties.lines} lines</span>}
                        {node.properties?.method && <span className="text-status-passed font-bold">{node.properties.method}</span>}
                      </td>
                      <td className="px-4 py-3 text-right">
                        <button
                          onClick={() => focusFromTable(node)}
                          className="px-2.5 py-1 rounded-lg bg-brand/10 hover:bg-brand/20 border border-brand/30 text-brand text-[11px] font-semibold transition-colors inline-flex items-center gap-1"
                        >
                          Show on map <ChevronRight className="w-3 h-3" />
                        </button>
                      </td>
                    </tr>
                  );
                })}
                {tableRows.length === 0 && (
                  <tr><td colSpan={6} className="px-4 py-8 text-center text-muted">No matches.</td></tr>
                )}
              </tbody>
            </table>
          </div>
          {tableRows.length > TABLE_ROW_LIMIT && (
            <p className="px-4 py-3 text-[11px] text-muted border-t border-border-card">
              Showing the first {TABLE_ROW_LIMIT} rows. Search to narrow the list.
            </p>
          )}
        </div>
      )}
    </div>
  );
};

export default KnowledgeGraphVisualizer;
