export type BackendLevel = 'info' | 'success' | 'warning' | 'error';

export interface BackendEvent {
  type: string;
  id?: string;
  action?: string;
  source?: string;
  level?: BackendLevel;
  message?: string;
  title?: string;
  value?: number;
  name?: string;
  prompt_id?: string;
  kind?: 'input' | 'confirm';
  is_password?: boolean;
  default?: string;
  buttons?: Array<{ text: string; value: unknown; style?: string }>;
  result?: unknown;
  success?: boolean;
  timestamp?: string;
  [key: string]: unknown;
}

export interface BackendApi {
  runAction: (action: string, payload?: Record<string, unknown>) => Promise<{ id?: string; accepted?: boolean; error?: string } | unknown>;
  cancelAction: () => Promise<{ id?: string; accepted?: boolean; error?: string } | unknown>;
  respondPrompt: (promptId: string, value: unknown) => Promise<boolean | unknown>;
  sendConsoleInput: (value: string) => Promise<boolean | unknown>;
  onBackendEvent: (callback: (event: BackendEvent) => void) => () => void;
  getAppInfo: () => Promise<Record<string, unknown> | unknown>;
  getBackendStatus: () => Promise<Record<string, unknown> | unknown>;
  pingPreload: () => Promise<Record<string, unknown> | unknown>;
  quitApp: () => Promise<Record<string, unknown> | unknown>;
}

declare global {
  interface Window {
    easyDeployBackend?: BackendApi;
    electronAPI?: BackendApi;
    easyDeploy?: BackendApi;
  }
}

export {};
