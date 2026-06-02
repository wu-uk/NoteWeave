<template>
  <LandingPage v-if="route === 'landing'" @enter="goWorkspace" />
  <WorkspacePage v-else @home="goLanding" />
</template>

<script setup lang="ts">
import { onMounted, ref } from "vue";

import LandingPage from "@/components/LandingPage.vue";
import WorkspacePage from "@/components/WorkspacePage.vue";
import type { ViewMode } from "@/types";

const route = ref<ViewMode>("landing");

function routeFromHash(): ViewMode {
  return window.location.hash.replace("#", "") === "workspace" ? "workspace" : "landing";
}

function syncRoute(): void {
  route.value = routeFromHash();
  document.title = route.value === "landing" ? "NoteWeave" : "NoteWeave 工作台";
}

function goWorkspace(): void {
  window.location.hash = "workspace";
  syncRoute();
}

function goLanding(): void {
  window.location.hash = "landing";
  syncRoute();
}

onMounted(() => {
  syncRoute();
  window.addEventListener("hashchange", syncRoute);
});
</script>
