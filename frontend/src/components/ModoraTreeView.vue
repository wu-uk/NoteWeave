<template>
  <div class="modora-flow-shell">
    <div v-if="!tree" class="modora-flow-empty">
      <strong>还没有 MoDora 解析树</strong>
      <span>上传 PDF、DOC/DOCX 或 Markdown 后会生成 CCTree。</span>
    </div>

    <template v-else>
      <div class="modora-flow-head">
        <div>
          <small>MoDora CCTree</small>
          <strong>{{ rootMetadata || "Document topology" }}</strong>
        </div>
        <button type="button" class="modora-flow-tool" title="重置视图" @click="focusRoot">
          <Crosshair :size="15" />
        </button>
      </div>

      <VueFlow
        v-model="elements"
        :default-viewport="{ zoom: 1 }"
        :min-zoom="0.25"
        :max-zoom="2.5"
        :nodes-connectable="false"
        class="modora-flow-canvas"
      >
        <Background pattern-color="rgba(148, 163, 184, 0.22)" :gap="20" />
        <Controls position="bottom-left" />

        <template #node-custom="{ label, data, selected }">
          <div class="modora-node-wrap" @dblclick.stop="jumpToMarkdown(label, data)">
            <div class="modora-node-card" :class="[nodeClass(data.type), { selected }]">
              <div class="modora-node-meta">
                <span>{{ data.type || "NODE" }}</span>
                <Info v-if="data.summary" :size="12" />
              </div>
              <strong :title="String(label)">{{ label }}</strong>
            </div>

            <div v-if="data.summary" class="modora-node-tooltip">
              <div>
                <Sparkles :size="13" />
                <span>Summary Tags</span>
              </div>
              <p>{{ data.summary }}</p>
            </div>
          </div>

          <Handle type="target" :position="Position.Top" />
          <Handle type="source" :position="Position.Bottom" />
        </template>
      </VueFlow>
    </template>
  </div>
</template>

<script setup lang="ts">
import { Background } from "@vue-flow/background";
import { Controls } from "@vue-flow/controls";
import "@vue-flow/controls/dist/style.css";
import { Handle, Position, VueFlow, useVueFlow } from "@vue-flow/core";
import "@vue-flow/core/dist/style.css";
import "@vue-flow/core/dist/theme-default.css";
import dagre from "@dagrejs/dagre";
import { Crosshair, Info, Sparkles } from "@lucide/vue";
import { computed, nextTick, ref, watch } from "vue";

type ModoraTreeNode = {
  type?: string;
  metadata?: unknown;
  data?: unknown;
  children?: Record<string, unknown>;
  impact?: unknown;
  keyword_cnt?: unknown;
};

const props = defineProps<{
  tree: unknown;
}>();

const emit = defineEmits<{
  jump: [payload: { title: string; summary: string; data: string }];
}>();

const { setCenter } = useVueFlow();
const elements = ref<any[]>([]);

const rootMetadata = computed(() => {
  if (!isTreeNode(props.tree)) return "";
  return typeof props.tree.metadata === "string" ? props.tree.metadata : "";
});

watch(
  () => props.tree,
  async () => {
    elements.value = layout(toFlowElements(props.tree));
    await nextTick();
    window.setTimeout(() => void focusRoot(), 120);
  },
  { immediate: true }
);

function isTreeNode(value: unknown): value is ModoraTreeNode {
  return Boolean(value && typeof value === "object" && "children" in value);
}

function toFlowElements(tree: unknown): any[] {
  if (!isTreeNode(tree)) return [];
  const nodes: any[] = [];
  const edges: any[] = [];
  let counter = 0;

  function visit(node: ModoraTreeNode, label: string, parentId: string | null, depth: number): string {
    const id = `modora-${counter}`;
    counter += 1;
    const title = depth === 0 ? "Document Root" : label;
    const data = typeof node.data === "string" ? node.data : "";
    const summary = extractSummaryTags(node, data);
    nodes.push({
      id,
      type: "custom",
      label: title,
      position: { x: 0, y: 0 },
      data: {
        type: String(node.type || (depth === 0 ? "root" : "text")),
        summary,
        data,
        impact: Number(node.impact || 0),
        keywordCount: Number(node.keyword_cnt || 0)
      }
    });

    if (parentId) {
      edges.push({
        id: `${parentId}-${id}`,
        source: parentId,
        target: id,
        animated: true,
        style: { stroke: "rgba(148, 163, 184, 0.72)", strokeWidth: 1.5 }
      });
    }

    const children = node.children || {};
    for (const [childLabel, child] of Object.entries(children)) {
      if (isTreeNode(child)) visit(child, childLabel, id, depth + 1);
    }
    return id;
  }

  visit(tree, "Document Root", null, 0);
  return [...nodes, ...edges];
}

function layout(els: any[]): any[] {
  const graph = new dagre.graphlib.Graph();
  graph.setDefaultEdgeLabel(() => ({}));
  graph.setGraph({ rankdir: "TB", nodesep: 42, ranksep: 62, marginx: 32, marginy: 28 });

  for (const el of els) {
    if ("position" in el) {
      graph.setNode(el.id, { width: 192, height: 86 });
    } else {
      graph.setEdge(el.source, el.target);
    }
  }

  dagre.layout(graph);

  return els.map((el) => {
    if (!("position" in el)) return el;
    const pos = graph.node(el.id);
    return {
      ...el,
      position: {
        x: pos.x - 96,
        y: pos.y - 43
      }
    };
  });
}

async function focusRoot(): Promise<void> {
  const root = elements.value.find((item) => "position" in item);
  if (!root) return;
  await nextTick();
  setCenter(root.position.x + 96, root.position.y + 43, { zoom: 0.9, duration: 650 });
}

function nodeClass(type: string): string {
  if (type === "root") return "root";
  if (type === "table") return "table";
  if (type === "image" || type === "chart") return "media";
  if (type === "text") return "text";
  return "default";
}

function jumpToMarkdown(label: unknown, data: { summary?: unknown; data?: unknown }): void {
  emit("jump", {
    title: String(label || ""),
    summary: typeof data.summary === "string" ? data.summary : "",
    data: typeof data.data === "string" ? data.data : ""
  });
}

function extractSummaryTags(node: ModoraTreeNode, rawData: string): string {
  const metadata = node.metadata;
  const candidates: string[] = [];
  if (typeof metadata === "string") {
    candidates.push(metadata);
  } else if (metadata && typeof metadata === "object") {
    const record = metadata as Record<string, unknown>;
    for (const key of ["summary", "summary_tags", "tags", "keywords", "metadata"]) {
      const value = record[key];
      if (Array.isArray(value)) candidates.push(value.map(String).join("; "));
      if (typeof value === "string") candidates.push(value);
    }
  }

  const normalizedData = normalizeText(rawData);
  for (const candidate of candidates) {
    const cleaned = candidate.replace(/\s+/g, " ").trim();
    if (!cleaned) continue;
    if (normalizeText(cleaned) === normalizedData) continue;
    if (cleaned.length > 220 && !cleaned.includes(";")) continue;
    return cleaned.length > 260 ? `${cleaned.slice(0, 260)}...` : cleaned;
  }
  return "";
}

function normalizeText(value: string): string {
  return value.replace(/\s+/g, " ").trim().toLowerCase();
}
</script>

<style>
.modora-flow-shell {
  position: relative;
  display: grid;
  grid-template-rows: auto minmax(0, 1fr);
  height: 100%;
  min-height: 0;
  overflow: hidden;
  border-radius: 8px;
  background: radial-gradient(circle at top, rgba(43, 54, 70, 0.9), rgba(14, 18, 24, 0.96) 46%);
}

.modora-flow-head {
  position: relative;
  z-index: 2;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  padding: 14px 16px;
  border-bottom: 1px solid rgba(255, 255, 255, 0.1);
  background: rgba(15, 20, 28, 0.72);
  backdrop-filter: blur(12px);
}

.modora-flow-head div {
  display: grid;
  gap: 4px;
  min-width: 0;
}

.modora-flow-head small {
  color: #91a0b7;
  font-size: 11px;
  font-weight: 800;
  letter-spacing: 0;
  text-transform: uppercase;
}

.modora-flow-head strong {
  overflow: hidden;
  color: #f8fafc;
  font-size: 15px;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.modora-flow-tool {
  display: grid;
  width: 34px;
  height: 34px;
  place-items: center;
  border: 1px solid rgba(255, 255, 255, 0.12);
  border-radius: 8px;
  color: #b9c4d3;
  background: rgba(255, 255, 255, 0.055);
  cursor: pointer;
}

.modora-flow-tool:hover {
  color: #ffffff;
  background: rgba(255, 255, 255, 0.1);
}

.modora-flow-canvas {
  min-height: 0;
}

.modora-flow-empty {
  display: grid;
  place-items: center;
  align-content: center;
  gap: 8px;
  min-height: 320px;
  color: #aab5c4;
  text-align: center;
}

.modora-flow-empty strong {
  color: #f8fafc;
}

.modora-node-wrap {
  position: relative;
}

.modora-node-card {
  display: grid;
  width: 192px;
  gap: 7px;
  padding: 10px 12px;
  border: 1px solid rgba(226, 232, 240, 0.16);
  border-radius: 12px;
  color: #e8eef7;
  background: rgba(29, 37, 49, 0.86);
  box-shadow: 0 16px 38px rgba(0, 0, 0, 0.28);
  cursor: pointer;
  backdrop-filter: blur(14px);
  transition: border-color 0.18s ease, box-shadow 0.18s ease, transform 0.18s ease;
}

.modora-node-card:hover,
.modora-node-card.selected {
  border-color: rgba(129, 140, 248, 0.95);
  box-shadow: 0 0 0 3px rgba(99, 102, 241, 0.18), 0 20px 46px rgba(0, 0, 0, 0.35);
  transform: translateY(-1px);
}

.modora-node-card.root {
  border-color: rgba(129, 140, 248, 0.9);
  background: rgba(49, 46, 129, 0.72);
}

.modora-node-card.table {
  border-color: rgba(45, 212, 191, 0.5);
}

.modora-node-card.media {
  border-color: rgba(251, 191, 36, 0.46);
}

.modora-node-card.text {
  border-color: rgba(148, 163, 184, 0.2);
}

.modora-node-meta {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  color: #9fb0c5;
}

.modora-node-meta span {
  overflow: hidden;
  max-width: 130px;
  padding: 2px 6px;
  border-radius: 6px;
  color: #a9b8cc;
  background: rgba(226, 232, 240, 0.08);
  font-size: 9px;
  font-weight: 900;
  text-overflow: ellipsis;
  text-transform: uppercase;
  white-space: nowrap;
}

.modora-node-card strong {
  display: -webkit-box;
  overflow: hidden;
  color: #f8fafc;
  font-size: 12px;
  line-height: 1.35;
  -webkit-box-orient: vertical;
  -webkit-line-clamp: 2;
}

.modora-node-tooltip {
  position: absolute;
  bottom: calc(100% + 10px);
  left: 50%;
  z-index: 50;
  width: 260px;
  padding: 11px 12px;
  border: 1px solid rgba(148, 163, 184, 0.28);
  border-radius: 10px;
  color: #dbe4ef;
  background: rgba(15, 23, 42, 0.96);
  box-shadow: 0 20px 50px rgba(0, 0, 0, 0.35);
  opacity: 0;
  pointer-events: none;
  transform: translate(-50%, 8px);
  transition: opacity 0.16s ease, transform 0.16s ease;
}

.modora-node-wrap:hover .modora-node-tooltip {
  opacity: 1;
  transform: translate(-50%, 0);
}

.modora-node-tooltip div {
  display: flex;
  align-items: center;
  gap: 6px;
  margin-bottom: 7px;
  padding-bottom: 7px;
  border-bottom: 1px solid rgba(148, 163, 184, 0.22);
  color: #fde68a;
  font-size: 11px;
  font-weight: 800;
}

.modora-node-tooltip p {
  margin: 0;
  color: #c8d3e1;
  font-size: 12px;
  line-height: 1.55;
}

.modora-flow-shell .vue-flow__handle {
  width: 8px;
  height: 8px;
  border: 2px solid #17202b;
  background-color: #94a3b8;
}

.modora-flow-shell .vue-flow__edge-path {
  stroke-dasharray: 6 10;
  animation: modora-edge-flow 1.6s linear infinite;
}

.modora-flow-shell .vue-flow__controls {
  overflow: hidden;
  border: 1px solid rgba(148, 163, 184, 0.2);
  border-radius: 8px;
  background: rgba(15, 23, 42, 0.72);
}

.modora-flow-shell .vue-flow__controls-button {
  border-bottom-color: rgba(148, 163, 184, 0.18);
  color: #dbe4ef;
  background: transparent;
}

.modora-flow-shell .vue-flow__controls-button:hover {
  background: rgba(255, 255, 255, 0.08);
}

.theme-light .modora-flow-shell {
  background:
    linear-gradient(135deg, rgba(255, 255, 255, 0.92), rgba(244, 247, 248, 0.8)),
    #f8fafc;
}

.theme-light .modora-flow-head {
  border-bottom-color: rgba(25, 31, 40, 0.1);
  background: rgba(255, 255, 255, 0.74);
}

.theme-light .modora-flow-head small {
  color: #667085;
}

.theme-light .modora-flow-head strong {
  color: #17202b;
}

.theme-light .modora-flow-tool {
  border-color: rgba(25, 31, 40, 0.12);
  color: #2f3744;
  background: #ffffff;
}

.theme-light .modora-flow-tool:hover {
  color: var(--brand-dark);
  background: #eef7f4;
}

.theme-light .modora-flow-empty {
  color: #667085;
}

.theme-light .modora-flow-empty strong {
  color: #17202b;
}

.theme-light .modora-node-card {
  border-color: rgba(25, 31, 40, 0.12);
  color: #24303d;
  background: rgba(255, 255, 255, 0.86);
  box-shadow: 0 16px 38px rgba(30, 35, 41, 0.12);
}

.theme-light .modora-node-card:hover,
.theme-light .modora-node-card.selected {
  border-color: rgba(47, 111, 104, 0.48);
  box-shadow: 0 0 0 3px rgba(47, 111, 104, 0.12), 0 20px 46px rgba(30, 35, 41, 0.16);
}

.theme-light .modora-node-card.root {
  border-color: rgba(47, 111, 104, 0.44);
  background: rgba(238, 247, 244, 0.92);
}

.theme-light .modora-node-card.table {
  border-color: rgba(20, 125, 100, 0.34);
}

.theme-light .modora-node-card.media {
  border-color: rgba(183, 121, 31, 0.34);
}

.theme-light .modora-node-meta {
  color: #667085;
}

.theme-light .modora-node-meta span {
  color: #55616f;
  background: rgba(47, 111, 104, 0.08);
}

.theme-light .modora-node-card strong {
  color: #17202b;
}

.theme-light .modora-node-tooltip {
  border-color: rgba(25, 31, 40, 0.12);
  color: #344054;
  background: rgba(255, 255, 255, 0.96);
  box-shadow: 0 20px 50px rgba(30, 35, 41, 0.16);
}

.theme-light .modora-node-tooltip div {
  border-bottom-color: rgba(25, 31, 40, 0.1);
  color: var(--brand-dark);
}

.theme-light .modora-node-tooltip p {
  color: #425066;
}

.theme-light .modora-flow-shell .vue-flow__handle {
  border-color: #ffffff;
  background-color: var(--brand);
}

.theme-light .modora-flow-shell .vue-flow__edge-path {
  stroke: rgba(47, 111, 104, 0.5);
}

.theme-light .modora-flow-shell .vue-flow__controls {
  border-color: rgba(25, 31, 40, 0.12);
  background: rgba(255, 255, 255, 0.78);
}

.theme-light .modora-flow-shell .vue-flow__controls-button {
  border-bottom-color: rgba(25, 31, 40, 0.1);
  color: #2f3744;
}

.theme-light .modora-flow-shell .vue-flow__controls-button:hover {
  background: #eef7f4;
}

@keyframes modora-edge-flow {
  to {
    stroke-dashoffset: -32;
  }
}
</style>
