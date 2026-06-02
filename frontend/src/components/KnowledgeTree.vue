<template>
  <div class="tree-node-list">
    <div v-for="node in nodes" :key="node.id" class="tree-row-wrap">
      <button
        type="button"
        class="tree-row"
        :class="{ active: selectedId === node.id }"
        :style="{ paddingLeft: `${Math.max(node.depth - 1, 0) * 14 + 10}px` }"
        @click="$emit('select', node)"
      >
        <ChevronRight v-if="node.children.length" :size="14" />
        <CircleDot v-else :size="12" />
        <span>{{ node.title }}</span>
        <small>{{ node.note_count || 0 }}/{{ node.mistake_count || 0 }}</small>
      </button>
      <KnowledgeTree
        v-if="node.children.length"
        :nodes="node.children"
        :selected-id="selectedId"
        @select="$emit('select', $event)"
      />
    </div>
  </div>
</template>

<script setup lang="ts">
import { ChevronRight, CircleDot } from "@lucide/vue";

import type { KnowledgeNode } from "@/types";

defineProps<{
  nodes: KnowledgeNode[];
  selectedId: number | null;
}>();

defineEmits<{
  select: [node: KnowledgeNode];
}>();
</script>
