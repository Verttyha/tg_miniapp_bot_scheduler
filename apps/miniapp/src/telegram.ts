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
  if (!window.Telegram?.WebApp) {
    return "";
  }

  try {
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
  } catch (error) {
    console.warn("Telegram SDK unavailable outside Telegram environment", error);
  }

  window.Telegram.WebApp.ready();
  window.Telegram.WebApp.expand();
  return window.Telegram.WebApp.initData ?? "";
}
