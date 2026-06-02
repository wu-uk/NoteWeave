(() => {
  if (typeof Vue === "undefined") {
    throw new Error("Vue runtime is not loaded");
  }

  const { createApp, nextTick } = Vue;

  const script = document.currentScript;
  const mountTo = script && script.dataset.mount ? String(script.dataset.mount).trim() : "#noteweave-app";
  const explicitRoute = script && script.dataset.page ? String(script.dataset.page).trim().toLowerCase() : "";

  const appContainer = document.querySelector(mountTo);
  if (!appContainer) {
    throw new Error(`Mount node is missing: ${mountTo}`);
  }

  const LandingPage = {
    name: "LandingPage",
    template: window.NoteWeaveTemplates ? window.NoteWeaveTemplates.landing : ""
  };

  const WorkspacePage = {
    name: "WorkspacePage",
    template: window.NoteWeaveTemplates ? window.NoteWeaveTemplates.workspace : ""
  };

  const routeConfig = {
    landing: {
      name: "landing",
      title: "NoteWeave · 课程知识协作",
      bodyClass: "landing-page",
      component: LandingPage
    },
    workspace: {
      name: "workspace",
      title: "NoteWeave 工作台",
      bodyClass: "noteweave-app",
      component: WorkspacePage
    }
  };

  function normalizeRoute(value) {
    const candidate = String(value || "").replace(/^#/, "").trim().toLowerCase();
    return Object.prototype.hasOwnProperty.call(routeConfig, candidate) ? candidate : "";
  }

  function routeFromLocation() {
    const hashRoute = normalizeRoute(window.location.hash);
    if (hashRoute) {
      return hashRoute;
    }

    if (normalizeRoute(explicitRoute)) {
      return normalizeRoute(explicitRoute);
    }

    return "landing";
  }

  const app = {
    data() {
      return {
        route: routeFromLocation(),
        active: true,
        bootRequestId: 0
      };
    },
    components: {
      LandingPage,
      WorkspacePage
    },
    computed: {
      routeState() {
        return routeConfig[this.route] || routeConfig.landing;
      }
    },
    template: `<component :is="routeState.component" :key="routeState.name"></component>`,
    methods: {
      normalizeRoute,
      syncRouteFromUrl() {
        const next = routeFromLocation();
        if (next !== this.route) {
          this.route = next;
        }
      },
      setRoute(nextRoute) {
        const next = normalizeRoute(nextRoute);
        if (!next || next === this.route) {
          return;
        }

        this.route = next;
      },
      applyBodyClass() {
        document.body.classList.remove("landing-page", "noteweave-app");
        const cls = this.routeState.bodyClass;
        if (cls) {
          document.body.classList.add(cls);
        }
      },
      applyPageTitle() {
        if (this.routeState && this.routeState.title) {
          document.title = this.routeState.title;
        }
      },
      bootWorkspace() {
        if (this.route !== "workspace") {
          return;
        }

        const requestId = this.bootRequestId + 1;
        this.bootRequestId = requestId;

        nextTick(() => {
          if (this.route !== "workspace" || requestId !== this.bootRequestId) {
            return;
          }
          if (typeof window.NoteWeaveBoot === "function") {
            window.NoteWeaveBoot();
          }
        });
      },
      onRouteLinkClick(event) {
        const anchor = event.target.closest("[data-route]");
        if (!anchor || !this.$el.contains(anchor)) {
          return;
        }

        const target = normalizeRoute(anchor.getAttribute("data-route"));
        if (!target) {
          return;
        }

        event.preventDefault();
        this.setRoute(target);
      }
    },
    watch: {
      route: {
        immediate: true,
        handler() {
          if (!this.active) {
            return;
          }
          this.applyBodyClass();
          this.applyPageTitle();
          window.location.hash = `#${this.route}`;
          if (this.route === "workspace") {
            this.bootWorkspace();
          }
        }
      }
    },
    mounted() {
      this.applyBodyClass();
      this.applyPageTitle();
      window.location.hash = `#${this.route}`;
      this._hashHandler = this.syncRouteFromUrl.bind(this);
      this._routeClickHandler = this.onRouteLinkClick.bind(this);
      window.addEventListener("hashchange", this._hashHandler);
      appContainer.addEventListener("click", this._routeClickHandler);
    },
    beforeUnmount() {
      window.removeEventListener("hashchange", this._hashHandler);
      appContainer.removeEventListener("click", this._routeClickHandler);
    },
    unmounted() {
      this.active = false;
    }
  };

  createApp(app).mount(mountTo);
})();
