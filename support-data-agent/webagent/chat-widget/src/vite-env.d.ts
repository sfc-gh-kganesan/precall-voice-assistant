/// <reference types="vite/client" />

interface ImportMetaEnv {
  readonly VITE_OTEL_SERVICE_NAME?: string
  readonly VITE_APP_VERSION?: string
  readonly VITE_OTEL_EXPORTER_OTLP_ENDPOINT?: string
}

interface ImportMeta {
  readonly env: ImportMetaEnv
}
