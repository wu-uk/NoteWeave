<template>
  <main class="landing note-landing">
    <header class="landing-nav">
      <button class="brand-button" type="button" @click="$emit('enter')">
        <span class="brand-mark">N</span>
        <span>
          <strong>NoteWeave</strong>
          <small>AI note workspace</small>
        </span>
      </button>
      <nav>
        <a href="#features">功能</a>
        <a href="#workflow">流程</a>
        <a href="#stack">技术</a>
        <button type="button" class="ghost-button" @click="$emit('enter')">
          <LogIn :size="16" />
          进入 Demo
        </button>
      </nav>
    </header>

    <section class="note-hero">
      <div class="hero-copy">
        <p class="eyebrow">Note-first · MoDora-inspired QA · API model only</p>
        <h1>NoteWeave</h1>
        <p class="hero-lead">
          一个以笔记为核心的学习 Demo。用户只负责记录、共享和讨论，AI 负责解析内容、判断课程归属、生成知识点，并基于笔记回答问题。
        </p>
        <div class="hero-actions">
          <button type="button" class="primary-button" @click="$emit('enter')">
            <PanelRightOpen :size="17" />
            打开笔记工作台
          </button>
          <a class="secondary-link" href="#workflow">查看流程</a>
        </div>
      </div>

      <div class="notebook-shot" aria-label="NoteWeave 笔记工作台预览">
        <div class="shot-note active">
          <small>计算机科学 / Dijkstra</small>
          <strong>Dijkstra 的适用条件</strong>
          <p>非负权图中可用，核心是每次选择当前距离最小的未确定节点。</p>
          <span>AI 已归档</span>
        </div>
        <div class="shot-note">
          <small>笔记问答</small>
          <strong>为什么不能有负权边？</strong>
          <p>因为已确定的最短距离可能被后续负权路径推翻。</p>
          <span>引用 2 条笔记</span>
        </div>
        <div class="shot-thread">
          <span></span>
          <span></span>
          <span></span>
        </div>
      </div>
    </section>

    <section id="features" class="section-band">
      <div class="section-heading">
        <span>核心能力</span>
        <h2>不再先建课程，先把笔记写进去</h2>
      </div>
      <div class="feature-grid">
        <article>
          <NotebookPen :size="20" />
          <h3>笔记摄取</h3>
          <p>普通用户添加笔记、上传内容、共享笔记，保留评论、点赞和后续编辑。</p>
        </article>
        <article>
          <Sparkles :size="20" />
          <h3>AI 自动归类</h3>
          <p>模型根据内容决定课程和知识点；课程是后台分类结果，不是用户工作负担。</p>
        </article>
        <article>
          <MessageSquare :size="20" />
          <h3>讨论反馈</h3>
          <p>共享笔记支持评论和点赞，用最少角色模型支撑 demo 协作。</p>
        </article>
        <article>
          <Search :size="20" />
          <h3>笔记问答</h3>
          <p>借鉴 MoDora 的检索增强问答：先召回笔记片段，再交给 API 模型回答。</p>
        </article>
      </div>
    </section>

    <section id="workflow" class="workflow section-band">
      <div>
        <span>体验路径</span>
        <h2>从记录到问答</h2>
      </div>
      <ol>
        <li>普通用户写入或上传笔记。</li>
        <li>AI 解析摘要、标签、课程和知识点。</li>
        <li>用户共享、评论、点赞优质内容。</li>
        <li>通过笔记检索和问答回到学习上下文。</li>
      </ol>
    </section>

    <section id="stack" class="stack-strip">
      <span>Vue 3</span>
      <span>Vite</span>
      <span>TypeScript</span>
      <span>FastAPI</span>
      <span>SQLite</span>
      <span>uv</span>
      <span>Remote Model API</span>
    </section>
  </main>
</template>

<script setup lang="ts">
import { LogIn, MessageSquare, NotebookPen, PanelRightOpen, Search, Sparkles } from "@lucide/vue";

defineEmits<{ enter: [] }>();
</script>
