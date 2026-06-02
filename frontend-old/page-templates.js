window.NoteWeaveTemplates = window.NoteWeaveTemplates || {};

window.NoteWeaveTemplates.landing = `
<main class="landing-shell">
  <header class="top">
    <a class="brand" href="#landing" data-route="landing" aria-label="NoteWeave 首页">
      <span class="brand-mark" aria-hidden="true">NW</span>
      <div>
        <h1>NoteWeave</h1>
        <p>课程知识协作平台</p>
      </div>
    </a>
    <nav class="top-actions" aria-label="主导航">
      <a class="text-link" href="#features">功能</a>
      <a class="text-link" href="#experience">体验路径</a>
      <a class="text-link" href="#tech-stack">技术与交付</a>
      <a class="text-link" href="../docs/架构文档.md">架构文档</a>
      <a class="btn btn-ghost" href="#workspace" data-route="workspace">进入工作台</a>
    </nav>
  </header>

  <section class="hero" aria-labelledby="hero-title">
    <div>
      <p class="eyebrow">课程协作 • 知识资产化</p>
      <h2 id="hero-title">让课程知识流动起来：从“输入笔记”到“资产复用”都在一个闭环内</h2>
      <p>
        NoteWeave 采用“课程 - 章节 - 知识点”的树状结构，聚焦课程场景下的学习沉淀。
        前端采用 Vue 3 构建，前端轻量运行在浏览器，先以 API 交互打稳课程协作核心流程。
      </p>
      <div class="hero-chips" aria-label="核心卖点">
        <span class="chip">内容优先 + 少即是多的布局</span>
        <span class="chip">课程 / 知识点 / 个人与共享资产</span>
        <span class="chip">协作讨论与补充闭环</span>
        <span class="chip">AI 仅增强，不阻塞主流程</span>
      </div>
      <div class="hero-actions">
        <a class="btn" href="#workspace" data-route="workspace">进入工作台</a>
        <a class="btn btn-soft" href="#features">查看功能</a>
        <a class="btn btn-soft" href="#experience">体验路径</a>
      </div>
    </div>
    <aside class="hero-side" aria-label="项目速览">
      <p class="hero-side-title">项目速览</p>
      <div class="hero-side-row">
        <span>交付形态</span>
        <strong>纯静态前端 + FastAPI</strong>
      </div>
      <div class="hero-side-row">
        <span>MVP 范围</span>
        <strong>课程与节点 / 笔记 / 错题 / 复习 / 协作</strong>
      </div>
      <div class="hero-side-row">
        <span>技术取向</span>
        <strong>低依赖、可部署、可扩展</strong>
      </div>
      <div class="hero-side-row">
        <span>适用场景</span>
        <strong>课程小组、作业复盘、考试复习</strong>
      </div>
      <div class="hero-mockup" aria-label="界面布局示意">
        <p>工作台结构（示意）</p>
        <div class="hero-mockup-bars">
          <span>左栏：课程与知识树</span>
          <span>中栏：工作区（笔记/错题/检索）</span>
          <span>右栏：协作与建议</span>
        </div>
      </div>
    </aside>
  </section>

  <section class="section section-badge" id="position">
    <span class="section-badge">产品定位</span>
    <div class="section-head">
      <h3>高端、简洁、可交付的课程工作台思路</h3>
      <p>参考 Obsidian / Notion 的信息密度控制，目标是“输入快、查找快、协作快”。</p>
    </div>
    <div class="feature-grid">
      <article class="feature-card">
        <span class="feature-icon" aria-hidden="true">⚙</span>
        <h4>三段式信息结构</h4>
        <p>左侧稳定展示课程与知识结构，中区承接编辑/检索，右侧聚焦协作与建议，减少上下文切换。</p>
      </article>
      <article class="feature-card">
        <span class="feature-icon" aria-hidden="true">✦</span>
        <h4>内容先行</h4>
        <p>课程、章节、知识点优先建立组织关系，再承载笔记与错题，天然支持长期复用。</p>
      </article>
      <article class="feature-card">
        <span class="feature-icon" aria-hidden="true">⟶</span>
        <h4>闭环流程</h4>
        <p>录入 → 归档 → 讨论 → 修订 → 复习，每一步都有明确页面和角色边界。</p>
      </article>
    </div>
  </section>

  <section class="section" id="features">
    <div class="section-head">
      <h3>功能概览</h3>
      <p>覆盖课程协作闭环中的核心动作，支持课程管理到复习输出。</p>
    </div>
    <div class="feature-grid">
      <article class="feature-card">
        <span class="feature-icon" aria-hidden="true">①</span>
        <h4>课程与知识树</h4>
        <p>课程-章节-知识点链路化管理，支持树状搜索与节点上下文操作。</p>
      </article>
      <article class="feature-card">
        <span class="feature-icon" aria-hidden="true">②</span>
        <h4>内容写作与归档</h4>
        <p>笔记与错题归属知识点，可设置标签、图片、状态与可见性。</p>
      </article>
      <article class="feature-card">
        <span class="feature-icon" aria-hidden="true">③</span>
        <h4>协作与建议</h4>
        <p>补充、纠错、评论与审核流程，记录可追溯协作状态和处理结果。</p>
      </article>
      <article class="feature-card">
        <span class="feature-icon" aria-hidden="true">④</span>
        <h4>复习与错题闭环</h4>
        <p>题型标签与掌握状态联动，支持高频复盘与学习节奏调整。</p>
      </article>
      <article class="feature-card">
        <span class="feature-icon" aria-hidden="true">⑤</span>
        <h4>检索与跳转</h4>
        <p>按关键词、标签、作者、内容类型过滤，返回可跳转到内容上下文。</p>
      </article>
      <article class="feature-card">
        <span class="feature-icon" aria-hidden="true">⑥</span>
        <h4>AI 可选增强</h4>
        <p>摘要、标签建议可用后处理；模型失败时不影响主流程继续使用。</p>
      </article>
    </div>
  </section>

  <section class="section split-block" id="experience">
    <div class="workflow-card">
      <h4>典型使用路径（5 分钟）</h4>
      <ol class="step-list">
        <li>建立课程并邀请成员，完成课程树初始结构。</li>
        <li>按章节/知识点录入笔记与错题，补齐课程资产。</li>
        <li>基于协作建议改进内容，保留更新痕迹和处理状态。</li>
        <li>按错题标签与掌握状态生成复习列表，持续迭代。</li>
        <li>按知识点快速检索到相关内容，回到学习目标闭环。</li>
      </ol>
    </div>
    <aside class="insight-card" id="tech-stack">
      <h4>工程约束与技术取向</h4>
      <p>当前优先保证可运行与可演示，核心使用纯前端静态页面与 FastAPI API；后续可平滑迁移到组件化框架。</p>
      <a class="btn btn-soft" href="../docs/需求文档.md">查看需求文档</a>
      <a class="btn btn-soft" href="../docs/架构文档.md">查看架构文档</a>
      <a class="btn btn-soft" href="../docs/项目规范文档.md">查看项目规范</a>
    </aside>
  </section>

  <section class="section" id="design-language">
    <div class="section-head">
      <h3>交互语言（高端/简洁）</h3>
      <p>低冗余、高信息密度；强调结构层级和动作区域的清晰边界。</p>
    </div>
    <div class="feature-grid">
      <article class="feature-card">
        <span class="feature-icon" aria-hidden="true">◎</span>
        <h4>静态前端先行</h4>
        <p>不引入复杂前端框架，降低首版部署成本，保留后续迁移能力。</p>
      </article>
      <article class="feature-card">
        <span class="feature-icon" aria-hidden="true">◎</span>
        <h4>高对比信息区</h4>
        <p>课程树、列表、讨论面板分区独立，快速定位当前动作与对象。</p>
      </article>
      <article class="feature-card">
        <span class="feature-icon" aria-hidden="true">◎</span>
        <h4>轻量渐进增强</h4>
        <p>先做“能用、可演示、可扩展”，后续逐步补齐高级编辑与分析能力。</p>
      </article>
    </div>
  </section>

  <section class="section">
    <div class="section-head">
      <h3>功能矩阵（MVP）</h3>
      <p>按模块边界拆分，便于验收与分阶段上线。</p>
    </div>
    <div class="feature-matrix">
      <div class="feature-matrix-row"><span>课程体系</span><span>课程创建、加入、角色与成员管理。</span></div>
      <div class="feature-matrix-row"><span>知识组织</span><span>树节点 CRUD、搜索过滤、层级归档。</span></div>
      <div class="feature-matrix-row"><span>知识沉淀</span><span>笔记/错题归属节点，支持草稿、发布与收藏。</span></div>
      <div class="feature-matrix-row"><span>协作治理</span><span>评论、点赞、建议与处理状态闭环。</span></div>
      <div class="feature-matrix-row"><span>复习支撑</span><span>高频复盘列表、题型标签与掌握状态流转。</span></div>
      <div class="feature-matrix-row"><span>可演进能力</span><span>思维导图展示、向量检索、教学分析等后续迭代。</span></div>
    </div>
  </section>

  <section class="cta-bar">
    <div>
      <strong>从“散碎笔记”升级为“课程知识资产”。</strong>
      <p>启动后端服务后直接打开工作台，体验课程协作的完整闭环。</p>
    </div>
    <a class="btn" href="#workspace" data-route="workspace">打开工作台</a>
  </section>

  <footer>
    NoteWeave 工作台采用 Vue 3 渲染，前端保持轻量化。
  </footer>
</main>
`;

window.NoteWeaveTemplates.workspace = `
<div class="shell">
  <aside class="sidebar">
    <div class="brand">
      <div class="brand-mark">N</div>
      <div>
        <h1>NoteWeave</h1>
        <p>课程笔记协作系统</p>
      </div>
    </div>

    <section class="auth-panel" id="auth-panel">
      <div class="section-title">账号</div>
      <div class="user-bar hidden" id="user-bar">
        <div>
          <strong id="current-user-name"></strong>
          <span id="current-user-role"></span>
        </div>
        <button class="icon-button" id="edit-profile-button" title="编辑昵称">编辑</button>
        <button class="icon-button" id="change-password-button" title="修改密码">安全</button>
        <button class="icon-button" id="logout-button" title="退出">退出</button>
      </div>
      <form class="auth-form" id="auth-form">
        <input id="auth-username" name="username" autocomplete="username" placeholder="用户名" />
        <input id="auth-password" name="password" type="password" autocomplete="current-password" placeholder="密码" />
        <input id="auth-display-name" name="displayName" placeholder="昵称（注册时可填）" />
        <div class="button-row">
          <button type="button" id="login-button">登录</button>
          <button type="button" class="secondary" id="register-button">注册</button>
        </div>
      </form>
    </section>

    <section>
      <div class="section-title">课程</div>
      <div class="course-actions">
        <input id="course-name" placeholder="新课程名称" />
        <input id="course-semester" placeholder="学期" />
        <button id="create-course-button">新建课程</button>
      </div>
      <div class="join-row">
        <input id="invite-code" placeholder="邀请码" />
        <button id="join-course-button" class="secondary">加入</button>
      </div>
      <div class="join-row">
        <input id="course-search-query" placeholder="搜索课程名称、学期或标签" />
        <button id="course-search-button" class="secondary">搜索</button>
      </div>
      <div class="course-list compact" id="course-search-results"></div>
      <div class="course-list" id="course-list"></div>
    </section>
  </aside>

  <main class="workspace">
    <header class="topbar">
      <div>
        <div class="eyebrow" id="course-role">未选择课程</div>
        <h2 id="course-title">课程工作台</h2>
      </div>
      <div class="status" id="status-line">
        <span>后端 API: <span id="api-base-label"></span></span>
        <a class="status-link" href="#landing" data-route="landing">功能介绍</a>
        <a class="status-link" href="../docs/需求文档.md">需求文档</a>
        <a class="status-link" href="../docs/架构文档.md">架构说明</a>
      </div>
    </header>

    <nav class="tabs" id="tabs">
      <button class="active" data-view="overview">总览</button>
      <button data-view="notes">笔记</button>
      <button data-view="mistakes">错题</button>
      <button data-view="review">复习</button>
      <button data-view="search">检索</button>
      <button data-view="collab">协作</button>
      <button data-view="settings">设置</button>
    </nav>

    <section class="view active" id="view-overview">
      <div class="grid two-columns">
        <section class="panel">
          <div class="panel-header">
            <div>
              <h3>知识树</h3>
              <p id="tree-meta">选择课程后加载章节和知识点</p>
            </div>
            <button id="refresh-tree-button" class="secondary">刷新</button>
          </div>
          <div class="tree-tools">
            <input id="tree-search" placeholder="搜索章节或知识点" />
            <button id="expand-tree-button" type="button" class="secondary">展开</button>
            <button id="collapse-tree-button" type="button" class="secondary">折叠</button>
          </div>
          <div class="tree" id="knowledge-tree"></div>
        </section>

        <section class="panel">
          <div class="panel-header">
            <div>
              <h3>节点详情</h3>
              <p id="selected-node-path">未选择节点</p>
            </div>
          </div>
          <div class="node-summary" id="node-summary"></div>
          <form class="stack-form" id="node-form">
            <div class="row">
              <select id="node-type">
                <option value="chapter">章节</option>
                <option value="knowledge_point">知识点</option>
              </select>
              <input id="node-title" placeholder="节点标题" />
            </div>
            <textarea id="node-description" placeholder="节点说明"></textarea>
            <button type="submit">在当前节点下新增</button>
          </form>
        </section>
      </div>
    </section>

    <section class="view" id="view-notes">
      <div class="grid two-columns">
        <section class="panel">
          <div class="panel-header">
            <div>
              <h3>创建笔记</h3>
              <p>笔记会归档到当前选中的知识节点</p>
            </div>
          </div>
          <form class="stack-form" id="note-form">
            <input id="note-title" placeholder="标题" />
            <textarea id="note-content" class="large" placeholder="正文，支持 Markdown / 公式 / 代码文本"></textarea>
            <div class="upload-row">
              <input id="note-image" type="file" accept="image/*" />
              <button id="note-image-button" type="button" class="secondary">插入图片</button>
              <button id="note-mindmap-button" type="button" class="secondary">插入思维导图</button>
            </div>
            <div id="note-image-preview" class="image-preview hidden"></div>
            <input id="note-tags" placeholder="标签，用逗号分隔" />
            <div class="row">
              <select id="note-visibility">
                <option value="private">个人可见</option>
                <option value="shared">课程共享</option>
              </select>
              <select id="note-status">
                <option value="draft">草稿</option>
                <option value="published">发布</option>
              </select>
            </div>
            <button type="submit">保存笔记</button>
          </form>
        </section>

        <section class="panel">
          <div class="panel-header">
            <div>
              <h3>笔记列表</h3>
              <p id="note-count">0 条</p>
            </div>
            <button id="refresh-notes-button" class="secondary">刷新</button>
          </div>
          <div class="item-list" id="note-list"></div>
          <div class="load-more-row">
            <button id="load-more-notes-button" type="button" class="secondary hidden">加载更多</button>
          </div>
        </section>
      </div>
    </section>

    <section class="view" id="view-mistakes">
      <div class="grid two-columns">
        <section class="panel">
          <div class="panel-header">
            <div>
              <h3>录入错题</h3>
              <p>题目会关联当前知识节点</p>
            </div>
          </div>
          <form class="stack-form" id="mistake-form">
            <textarea id="mistake-question" placeholder="题目内容"></textarea>
            <div class="upload-row">
              <input id="mistake-image" type="file" accept="image/*" />
              <button id="mistake-image-button" type="button" class="secondary">插入图片</button>
              <button id="mistake-mindmap-button" type="button" class="secondary">插入思维导图</button>
            </div>
            <div id="mistake-image-preview" class="image-preview hidden"></div>
            <input id="mistake-correct" placeholder="正确答案" />
            <input id="mistake-wrong" placeholder="错误答案" />
            <textarea id="mistake-reason" placeholder="错误原因"></textarea>
            <textarea id="mistake-solution" placeholder="解题思路"></textarea>
            <div class="row">
              <input id="mistake-type" placeholder="题型" />
              <select id="mistake-mastery">
                <option value="todo">待复习</option>
                <option value="retry">需再练</option>
                <option value="mastered">已掌握</option>
              </select>
            </div>
            <input id="mistake-tags" placeholder="标签，用逗号分隔" />
            <button type="submit">保存错题</button>
          </form>
        </section>

        <section class="panel">
          <div class="panel-header">
            <div>
              <h3>错题复习</h3>
              <p id="mistake-count">0 条</p>
            </div>
            <button id="refresh-mistakes-button" class="secondary">刷新</button>
          </div>
          <div class="filters">
            <input id="mistake-filter-tag" placeholder="标签筛选" />
            <select id="mistake-filter-mastery">
              <option value="">全部状态</option>
              <option value="todo">待复习</option>
              <option value="retry">需再练</option>
              <option value="mastered">已掌握</option>
            </select>
          </div>
          <div class="item-list" id="mistake-list"></div>
          <div class="load-more-row">
            <button id="load-more-mistakes-button" type="button" class="secondary hidden">加载更多</button>
          </div>
        </section>
      </div>
    </section>

    <section class="view" id="view-search">
      <section class="panel">
        <div class="panel-header">
          <div>
            <h3>课程检索</h3>
            <p>返回笔记、错题、知识节点路径和匹配字段</p>
          </div>
        </div>
        <form class="search-form" id="search-form">
          <input id="search-query" placeholder="关键词" />
          <input id="search-tag" placeholder="标签" />
          <input id="search-author" type="number" min="1" placeholder="作者 ID" />
          <select id="search-type">
            <option value="">全部内容</option>
            <option value="note">笔记</option>
            <option value="mistake">错题</option>
          </select>
          <label class="check-line">
            <input id="search-current-node" type="checkbox" />
            <span>当前节点</span>
          </label>
          <button type="submit">检索</button>
        </form>
        <div class="item-list search-results" id="search-results"></div>
      </section>
    </section>

    <section class="view" id="view-review">
      <section class="panel">
        <div class="panel-header">
          <div>
            <h3>复习资料</h3>
            <p>按章节、标签、题型和收藏拉取笔记与错题</p>
          </div>
          <button id="refresh-review-button" class="secondary">刷新</button>
        </div>
        <form class="search-form" id="review-form">
          <select id="review-mode">
            <option value="all">全部资料</option>
            <option value="favorites">我的收藏</option>
            <option value="recent">最近更新</option>
            <option value="viewed">最近浏览</option>
            <option value="top">高赞笔记</option>
          </select>
          <input id="review-tag" placeholder="标签" />
          <input id="review-question-type" placeholder="题型" />
          <label class="check-line">
            <input id="review-current-node" type="checkbox" />
            <span>当前节点</span>
          </label>
          <button type="submit">筛选</button>
        </form>
        <div class="item-list" id="review-list"></div>
        <div class="load-more-row">
          <button id="load-more-review-button" type="button" class="secondary hidden">加载更多</button>
        </div>
      </section>
    </section>

    <section class="view" id="view-collab">
      <div class="grid two-columns">
        <section class="panel">
          <div class="panel-header">
            <div>
              <h3>共享笔记</h3>
              <p>点赞、评论和 AI 结果采纳</p>
            </div>
          </div>
          <div class="filters">
            <select id="shared-note-sort">
              <option value="updated">最近更新</option>
              <option value="likes">点赞最多</option>
              <option value="comments">评论最多</option>
            </select>
            <button id="refresh-shared-notes-button" class="secondary">刷新共享</button>
          </div>
          <div class="item-list" id="shared-note-list"></div>
          <div class="load-more-row">
            <button id="load-more-shared-notes-button" type="button" class="secondary hidden">加载更多</button>
          </div>
        </section>

        <section class="panel">
          <div class="panel-header">
            <div>
              <h3>补充与纠错</h3>
              <p>面向当前选中的笔记或节点</p>
            </div>
          </div>
          <form class="stack-form" id="suggestion-form">
            <select id="suggestion-target-type">
              <option value="note">笔记</option>
              <option value="knowledge_node">知识节点</option>
            </select>
            <input id="suggestion-target-id" placeholder="目标 ID" />
            <select id="suggestion-type">
              <option value="supplement">补充</option>
              <option value="correction">纠错</option>
            </select>
            <textarea id="suggestion-content" placeholder="建议内容"></textarea>
            <button type="submit">提交建议</button>
          </form>
          <div class="item-list" id="suggestion-list"></div>
        </section>
      </div>
    </section>

    <section class="view" id="view-settings">
      <div class="grid two-columns">
        <section class="panel">
          <div class="panel-header">
            <div>
              <h3>课程信息</h3>
              <p>维护者可编辑课程基础资料</p>
            </div>
            <button type="button" id="leave-course-button" class="secondary">退出课程</button>
          </div>
          <form class="stack-form" id="course-settings-form">
            <input id="settings-course-name" placeholder="课程名称" />
            <input id="settings-course-semester" placeholder="学期" />
            <textarea id="settings-course-description" placeholder="课程简介"></textarea>
            <input id="settings-course-tags" placeholder="课程标签，用逗号分隔" />
            <button type="submit">保存课程信息</button>
          </form>
        </section>

        <section class="panel">
          <div class="panel-header">
            <div>
              <h3>成员权限</h3>
              <p>维护者可调整课程内角色</p>
            </div>
          </div>
          <div class="item-list" id="member-list"></div>
        </section>

        <section class="panel full-width">
          <div class="panel-header">
            <div>
              <h3>AI 配置状态</h3>
              <p>显示远程模型配置和本地降级能力</p>
            </div>
          </div>
          <div class="item-list" id="ai-status-panel"></div>
        </section>

        <section class="panel full-width">
          <div class="panel-header">
            <div>
              <h3>审计日志</h3>
              <p>记录发布、采纳、删除和权限变更</p>
            </div>
          </div>
          <div class="item-list" id="audit-log-list"></div>
        </section>
      </div>
    </section>
  </main>
</div>

<section class="discussion-drawer hidden" id="discussion-drawer" aria-hidden="true">
  <div class="discussion-card">
    <header class="discussion-header">
      <div>
        <h3 id="discussion-title">讨论</h3>
        <p id="discussion-subtitle">选择要讨论的内容</p>
      </div>
      <div class="discussion-controls">
        <button id="discussion-refresh" class="secondary" type="button">刷新</button>
        <button id="discussion-close" class="icon-button" type="button">关闭</button>
      </div>
    </header>
    <div class="discussion-body" id="discussion-list"></div>
    <div class="load-more-row">
      <button id="discussion-load-more" class="secondary hidden" type="button">加载更多评论</button>
    </div>
    <form class="discussion-form" id="discussion-form">
      <textarea id="discussion-content" class="discussion-input" rows="3" placeholder="输入评论..."></textarea>
      <button type="submit">发布评论</button>
    </form>
  </div>
</section>

<div class="toast hidden" id="toast"></div>
`;
