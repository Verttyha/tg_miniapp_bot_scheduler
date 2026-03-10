import {
  bindThemeParamsCssVars,
  bindViewportCssVars,
  init,
  mountThemeParamsSync,
  mountViewport
} from "@telegram-apps/sdk";

declare global {
  interface Window {
    Telegram?: {
      WebApp?: {
        initData: string;
        ready: () => void;
        expand: () => void;
      };
    };
  }
}

export async function initTelegramApp(): Promise<string> {
  init();
  if (mountThemeParamsSync.isAvailable()) {
    mountThemeParamsSync();
  }
  if (bindThemeParamsCssVars.isAvailable()) {
    bindThemeParamsCssVars();
  }
  if (mountViewport.isAvailable()) {
    await mountViewport();
  }
  if (bindViewportCssVars.isAvailable()) {
    bindViewportCssVars();
  }
  window.Telegram?.WebApp?.ready();
  window.Telegram?.WebApp?.expand();
  return window.Telegram?.WebApp?.initData ?? "";
}
