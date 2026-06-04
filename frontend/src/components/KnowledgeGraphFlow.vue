<template>
  <div class="knowledge-flow-shell">
    <div v-if="!nodes.length" class="network-empty">
      <Sparkles :size="18" />
      <strong>还没有知识网络</strong>
      <span>保存或上传第一条笔记后，AI 会生成课程和知识点图谱。</span>
    </div>

    <template v-else>
      <div class="knowledge-flow-toolbar">
        <div>
          <small>RADIAL MAP</small>
          <strong>知识网络</strong>
          <span>{{ nodes.length }} 个节点 · {{ links.length }} 条关系</span>
        </div>
        <div class="knowledge-flow-actions">
          <button type="button" class="knowledge-flow-tool" title="自动排布" @click="resetLayout">
            <GitBranch :size="15" />
          </button>
          <button type="button" class="knowledge-flow-tool" title="聚焦全图" @click="fitGraph">
            <Crosshair :size="15" />
          </button>
        </div>
      </div>

      <VueFlow
        v-model:nodes="flowNodes"
        v-model:edges="flowEdges"
        :default-viewport="{ x: 0, y: 0, zoom: 0.86 }"
        :min-zoom="0.25"
        :max-zoom="2.1"
        :nodes-draggable="true"
        :nodes-connectable="false"
        :elements-selectable="true"
        fit-view-on-init
        class="knowledge-flow-canvas"
        @node-click="handleNodeClick"
        @node-drag-start="handleNodeDragStart"
        @node-drag="handleNodeDrag"
        @node-drag-stop="handleNodeDragStop"
      >
        <Background pattern-color="rgba(47, 111, 104, 0.1)" :gap="28" />

        <template #node-knowledge="{ data, selected }">
          <div class="knowledge-flow-node" :class="[data.kind, { selected, active: data.active, dragging: data.dragging }]">
            <span class="knowledge-flow-dot" aria-hidden="true">
              <Handle type="target" :position="Position.Top" />
              <Handle type="source" :position="Position.Bottom" />
            </span>
            <strong :title="data.title">{{ data.title }}</strong>
          </div>
        </template>
      </VueFlow>
    </template>
  </div>
</template>

<script setup lang="ts">
import { Background } from "@vue-flow/background";
import { Handle, Position, VueFlow, useVueFlow } from "@vue-flow/core";
import "@vue-flow/core/dist/style.css";
import "@vue-flow/core/dist/theme-default.css";
import { forceCenter, forceCollide, forceLink, forceManyBody, forceSimulation, forceX, forceY, type Simulation } from "d3-force";
import { Crosshair, GitBranch, Sparkles } from "@lucide/vue";
import { nextTick, onMounted, onUnmounted, ref, watch } from "vue";

type KnowledgeFlowNode = {
  id: string;
  type: "course" | "node";
  title: string;
  short: string;
  meta: string;
  depth: number;
  courseId: number;
  nodeId?: number | null;
};

type KnowledgeFlowLink = {
  id: string;
  from: KnowledgeFlowNode;
  to: KnowledgeFlowNode;
};

const props = defineProps<{
  nodes: KnowledgeFlowNode[];
  links: KnowledgeFlowLink[];
  activeId: string;
}>();

const emit = defineEmits<{
  select: [node: KnowledgeFlowNode];
}>();

const { fitView } = useVueFlow();
const flowNodes = ref<any[]>([]);
const flowEdges = ref<any[]>([]);
const basePositions = ref<Map<string, { x: number; y: number }>>(new Map());
const draggingIds = new Set<string>();
let simulation: Simulation<ForceGraphNode, ForceGraphLink> | null = null;
let demoDragTimeout: number | undefined;
let demoDragFrame: number | undefined;

type ForceGraphNode = {
  id: string;
  x: number;
  y: number;
  fx?: number | null;
  fy?: number | null;
};

type ForceGraphLink = {
  source: string | ForceGraphNode;
  target: string | ForceGraphNode;
};

watch(
  () => [props.nodes, props.links, props.activeId] as const,
  async () => {
    const hadBasePositions = basePositions.value.size > 0;
    const laidOut = layoutNodes(props.nodes, props.links);
    const nextBase = new Map<string, { x: number; y: number }>();
    flowNodes.value = laidOut.map((node) => {
      const base = basePositions.value.get(node.id) || node.position;
      nextBase.set(node.id, base);
      return {
        ...node,
        position: base,
        data: { ...node.data, active: node.id === props.activeId, dragging: draggingIds.has(node.id) }
      };
    });
    basePositions.value = nextBase;
    flowEdges.value = toFlowEdges(props.links);
    await nextTick();
    if (!hadBasePositions) window.setTimeout(() => void fitGraph(), 80);
    scheduleDemoDrag();
  },
  { immediate: true, deep: true }
);

onMounted(() => {
  scheduleDemoDrag();
});

onUnmounted(() => {
  stopSimulation();
  clearDemoDrag();
});

function layoutNodes(nodes: KnowledgeFlowNode[], links: KnowledgeFlowLink[]): any[] {
  const positions = compactForcePositions(nodes, links);

  return nodes.map((node) => {
    const pos = positions.get(node.id) || { x: 0, y: 0 };
    return {
      id: node.id,
      type: "knowledge",
      label: node.title,
      position: {
        x: pos.x - (node.type === "course" ? 112 : 125),
        y: pos.y - 42
      },
      data: {
        source: node,
        kind: node.type,
        title: node.title,
        short: node.short,
        meta: node.meta,
        active: node.id === props.activeId
      }
    };
  });
}

function compactForcePositions(nodes: KnowledgeFlowNode[], links: KnowledgeFlowLink[]): Map<string, { x: number; y: number }> {
  const byId = new Map(nodes.map((node) => [node.id, node]));
  const roots = nodes.filter((node) => node.type === "course");
  const rootAnchors = new Map<number, { x: number; y: number }>();
  const children = new Map<string, KnowledgeFlowNode[]>();
  for (const link of links) {
    const list = children.get(link.from.id) || [];
    list.push(link.to);
    children.set(link.from.id, list);
  }
  for (const list of children.values()) {
    list.sort((a, b) => a.title.localeCompare(b.title, "zh-CN"));
  }
  const rootRadius = roots.length <= 1 ? 0 : Math.min(420, Math.max(230, roots.length * 52));

  roots.forEach((root, index) => {
    const angle = roots.length <= 1 ? 0 : -Math.PI / 2 + (Math.PI * 2 * index) / roots.length;
    rootAnchors.set(root.courseId, {
      x: Math.cos(angle) * rootRadius,
      y: Math.sin(angle) * rootRadius
    });
  });

  const initialPositions = new Map<string, { x: number; y: number }>();
  roots.forEach((root, rootIndex) => {
    const anchor = rootAnchors.get(root.courseId) || { x: 0, y: 0 };
    const direction = roots.length <= 1 ? -Math.PI / 2 : -Math.PI / 2 + (Math.PI * 2 * rootIndex) / roots.length;
    const sector = roots.length <= 1 ? Math.PI * 2 : (Math.PI * 2) / roots.length;
    initialPositions.set(root.id, anchor);
    placeInitialBranch(root, anchor, direction, sector * 0.82, children, initialPositions);
  });

  nodes.forEach((node, index) => {
    if (initialPositions.has(node.id)) return;
    const angle = -Math.PI / 2 + (Math.PI * 2 * index) / Math.max(1, nodes.length);
    initialPositions.set(node.id, { x: Math.cos(angle) * 260, y: Math.sin(angle) * 260 });
  });

  const forceNodes: ForceGraphNode[] = nodes.map((node) => {
    const initial = initialPositions.get(node.id) || rootAnchors.get(node.courseId) || { x: 0, y: 0 };
    return {
      id: node.id,
      x: initial.x,
      y: initial.y
    };
  });
  const forceLinks: ForceGraphLink[] = links.map((link) => ({ source: link.from.id, target: link.to.id }));

  const initialSimulation = forceSimulation<ForceGraphNode>(forceNodes)
    .force("link", forceLink<ForceGraphNode, ForceGraphLink>(forceLinks).id((node) => node.id).distance(compactLinkDistance).strength(0.48))
    .force("charge", forceManyBody<ForceGraphNode>().strength((node) => {
      const source = byId.get(node.id);
      return source?.type === "course" ? -190 : -105;
    }))
    .force("collide", forceCollide<ForceGraphNode>().radius((node) => {
      const source = byId.get(node.id);
      return source?.type === "course" ? 62 : 43;
    }).strength(0.9))
    .force("center", forceCenter<ForceGraphNode>(0, 0))
    .force("x", forceX<ForceGraphNode>((node) => {
      const source = byId.get(node.id);
      return source ? rootAnchors.get(source.courseId)?.x ?? 0 : 0;
    }).strength((node) => (byId.get(node.id)?.type === "course" ? 0.28 : 0.028)))
    .force("y", forceY<ForceGraphNode>((node) => {
      const source = byId.get(node.id);
      return source ? rootAnchors.get(source.courseId)?.y ?? 0 : 0;
    }).strength((node) => (byId.get(node.id)?.type === "course" ? 0.28 : 0.028)))
    .alpha(0.82)
    .alphaDecay(0.045)
    .velocityDecay(0.54)
    .stop();

  for (let i = 0; i < 220; i += 1) initialSimulation.tick();

  return new Map(forceNodes.map((node) => [node.id, { x: node.x, y: node.y }]));
}

function placeInitialBranch(
  parent: KnowledgeFlowNode,
  parentPosition: { x: number; y: number },
  direction: number,
  sector: number,
  children: Map<string, KnowledgeFlowNode[]>,
  positions: Map<string, { x: number; y: number }>
): void {
  const childNodes = children.get(parent.id) || [];
  if (!childNodes.length) return;

  childNodes.forEach((child, index) => {
    const ratio = childNodes.length === 1 ? 0 : index / (childNodes.length - 1) - 0.5;
    const angle = direction + ratio * sector;
    const depthGap = Math.max(1, child.depth - parent.depth);
    const distance = parent.type === "course" ? 138 : 116 + Math.min(2, depthGap) * 18;
    const position = {
      x: parentPosition.x + Math.cos(angle) * distance,
      y: parentPosition.y + Math.sin(angle) * distance
    };
    positions.set(child.id, position);
    placeInitialBranch(child, position, angle, Math.max(0.42, sector * 0.58), children, positions);
  });
}

function toFlowEdges(links: KnowledgeFlowLink[]): any[] {
  return links.map((link) => ({
    id: link.id,
    source: link.from.id,
    target: link.to.id,
    type: "straight",
    animated: false,
    style: { stroke: "rgba(184, 234, 219, 0.42)", strokeWidth: 1.6 }
  }));
}

function handleNodeClick(event: { node?: { data?: { source?: KnowledgeFlowNode } } }): void {
  const source = event.node?.data?.source;
  if (source) emit("select", source);
}

function handleNodeDragStart(event: { node?: { id?: string; position?: { x: number; y: number } } }): void {
  const id = event.node?.id;
  if (!id) return;
  clearDemoDrag();
  draggingIds.add(id);
  if (event.node?.position) basePositions.value.set(id, event.node.position);
  setNodeDragging(id, true);
  startSimulation(id, event.node?.position);
}

function handleNodeDrag(event: { node?: { id?: string; position?: { x: number; y: number } } }): void {
  const id = event.node?.id;
  const position = event.node?.position;
  if (!id || !position || !simulation) return;
  const node = simulation.nodes().find((item) => item.id === id);
  if (!node) return;
  node.fx = position.x;
  node.fy = position.y;
  simulation.alphaTarget(0.24).restart();
}

function handleNodeDragStop(event: { node?: { id?: string; position?: { x: number; y: number } } }): void {
  const id = event.node?.id;
  if (!id) return;
  draggingIds.delete(id);
  if (event.node?.position) basePositions.value.set(id, event.node.position);
  setNodeDragging(id, false);
  const node = simulation?.nodes().find((item) => item.id === id);
  if (node) {
    node.fx = null;
    node.fy = null;
  }
  simulation?.alphaTarget(0).restart();
  scheduleDemoDrag();
}

function setNodeDragging(id: string, dragging: boolean): void {
  flowNodes.value = flowNodes.value.map((node) => {
    if (node.id !== id) return node;
    return { ...node, data: { ...node.data, dragging } };
  });
}

async function fitGraph(): Promise<void> {
  await nextTick();
  fitView({ padding: 0.18, duration: 520, maxZoom: 1.05 });
}

async function resetLayout(): Promise<void> {
  stopSimulation();
  const nextBase = new Map<string, { x: number; y: number }>();
  flowNodes.value = layoutNodes(props.nodes, props.links).map((node) => {
    nextBase.set(node.id, node.position);
    return {
      ...node,
      data: { ...node.data, active: node.id === props.activeId, dragging: false }
    };
  });
  basePositions.value = nextBase;
  await fitGraph();
}

function startSimulation(draggedId: string, draggedPosition?: { x: number; y: number }): void {
  stopSimulation();
  const forceNodes: ForceGraphNode[] = flowNodes.value.map((node) => ({
    id: node.id,
    x: node.position.x,
    y: node.position.y,
    fx: node.id === draggedId ? draggedPosition?.x ?? node.position.x : null,
    fy: node.id === draggedId ? draggedPosition?.y ?? node.position.y : null
  }));
  const forceLinks: ForceGraphLink[] = props.links.map((link) => ({ source: link.from.id, target: link.to.id }));
  simulation = forceSimulation<ForceGraphNode>(forceNodes)
    .force("link", forceLink<ForceGraphNode, ForceGraphLink>(forceLinks).id((node) => node.id).distance(linkDistance).strength(0.12))
    .force("charge", forceManyBody<ForceGraphNode>().strength(-150))
    .force("collide", forceCollide<ForceGraphNode>().radius(62).strength(0.72))
    .force("center", forceCenter<ForceGraphNode>(0, 0))
    .force("x", forceX<ForceGraphNode>((node) => basePositions.value.get(node.id)?.x ?? 0).strength(0.025))
    .force("y", forceY<ForceGraphNode>((node) => basePositions.value.get(node.id)?.y ?? 0).strength(0.025))
    .alpha(0.55)
    .alphaDecay(0.045)
    .velocityDecay(0.42)
    .on("tick", syncForcePositions)
    .on("end", commitForcePositions);
}

function syncForcePositions(): void {
  if (!simulation) return;
  const positions = new Map(simulation.nodes().map((node) => [node.id, { x: node.x, y: node.y }]));
  flowNodes.value = flowNodes.value.map((node) => {
    const position = positions.get(node.id);
    return position ? { ...node, position } : node;
  });
}

function commitForcePositions(): void {
  if (!simulation) return;
  const nextBase = new Map(basePositions.value);
  for (const node of simulation.nodes()) {
    nextBase.set(node.id, { x: node.x, y: node.y });
  }
  basePositions.value = nextBase;
  stopSimulation();
}

function stopSimulation(): void {
  if (!simulation) return;
  simulation.stop();
  simulation.on("tick", null);
  simulation.on("end", null);
  simulation = null;
}

function clearDemoDrag(): void {
  if (demoDragTimeout !== undefined) {
    window.clearTimeout(demoDragTimeout);
    demoDragTimeout = undefined;
  }
  if (demoDragFrame !== undefined) {
    window.cancelAnimationFrame(demoDragFrame);
    demoDragFrame = undefined;
  }
}

function scheduleDemoDrag(): void {
  if (!props.nodes.length || flowNodes.value.length < 2) return;
  if (demoDragTimeout !== undefined || demoDragFrame !== undefined) return;
  demoDragTimeout = window.setTimeout(() => {
    demoDragTimeout = undefined;
    runDemoDrag();
  }, 1400 + Math.random() * 1400);
}

function runDemoDrag(): void {
  if (!props.nodes.length || flowNodes.value.length < 2 || simulation || draggingIds.size) {
    scheduleDemoDrag();
    return;
  }

  const candidates = flowNodes.value.filter((node) => node.data?.kind !== "course");
  const node = (candidates.length ? candidates : flowNodes.value)[Math.floor(Math.random() * (candidates.length || flowNodes.value.length))];
  if (!node?.id || !node.position) {
    scheduleDemoDrag();
    return;
  }

  const id = node.id;
  const start = { x: node.position.x, y: node.position.y };
  const angle = Math.random() * Math.PI * 2;
  const distance = 64 + Math.random() * 54;
  const end = {
    x: start.x + Math.cos(angle) * distance,
    y: start.y + Math.sin(angle) * distance
  };
  const control = {
    x: (start.x + end.x) / 2 + Math.sin(angle) * 22,
    y: (start.y + end.y) / 2 - Math.cos(angle) * 22
  };
  const duration = 1550;
  const startedAt = performance.now();

  draggingIds.add(id);
  setNodeDragging(id, true);

  const step = (now: number) => {
    const elapsed = Math.min(1, (now - startedAt) / duration);
    const eased = easeInOutCubic(elapsed);
    const position = quadraticPoint(start, control, end, eased);
    flowNodes.value = flowNodes.value.map((item) => (item.id === id ? { ...item, position } : item));

    if (elapsed < 1) {
      demoDragFrame = window.requestAnimationFrame(step);
      return;
    }

    demoDragFrame = undefined;
    draggingIds.delete(id);
    basePositions.value.set(id, end);
    setNodeDragging(id, false);
    scheduleDemoDrag();
  };

  demoDragFrame = window.requestAnimationFrame(step);
}

function quadraticPoint(
  start: { x: number; y: number },
  control: { x: number; y: number },
  end: { x: number; y: number },
  t: number
): { x: number; y: number } {
  const inv = 1 - t;
  return {
    x: inv * inv * start.x + 2 * inv * t * control.x + t * t * end.x,
    y: inv * inv * start.y + 2 * inv * t * control.y + t * t * end.y
  };
}

function easeInOutCubic(value: number): number {
  return value < 0.5 ? 4 * value * value * value : 1 - Math.pow(-2 * value + 2, 3) / 2;
}

function linkDistance(link: ForceGraphLink): number {
  const sourceId = typeof link.source === "string" ? link.source : link.source.id;
  const targetId = typeof link.target === "string" ? link.target : link.target.id;
  const source = props.nodes.find((node) => node.id === sourceId);
  const target = props.nodes.find((node) => node.id === targetId);
  const gap = Math.abs((target?.depth || 0) - (source?.depth || 0));
  return 82 + gap * 18;
}

function compactLinkDistance(link: ForceGraphLink): number {
  const sourceId = typeof link.source === "string" ? link.source : link.source.id;
  const targetId = typeof link.target === "string" ? link.target : link.target.id;
  const source = props.nodes.find((node) => node.id === sourceId);
  const target = props.nodes.find((node) => node.id === targetId);
  if (source?.type === "course" || target?.type === "course") return 128;
  const gap = Math.abs((target?.depth || 0) - (source?.depth || 0));
  return 96 + gap * 16;
}
</script>
