/// <reference types="vite/client" />

declare module "*.vue" {
  import type { DefineComponent } from "vue";

  const component: DefineComponent<Record<string, unknown>, Record<string, unknown>, unknown>;
  export default component;
}

declare module "markdown-it-texmath" {
  import type MarkdownIt from "markdown-it";

  type TexmathOptions = {
    engine: unknown;
    delimiters?: string | string[];
    katexOptions?: Record<string, unknown>;
  };

  const texmath: MarkdownIt.PluginWithOptions<TexmathOptions>;
  export default texmath;
}
