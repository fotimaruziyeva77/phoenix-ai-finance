/// <reference types="vite/client" />

interface ImportMetaEnv {
  readonly VITE_PUBLIC_WIDGET_KEY?: string;
  readonly VITE_API_BASE_URL?: string;
}

declare module "*.css?inline" {
  const css: string;
  export default css;
}
