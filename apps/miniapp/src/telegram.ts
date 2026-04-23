import {
  bindMiniAppCssVars,
  bindThemeParamsCssVars,
  bindViewportCssVars,
  init,
  mountMiniAppSync,
  mountThemeParamsSync,
  mountViewport,
  retrieveRawInitData
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
  try {
    init();
    if (mountMiniAppSync.isAvailable()) {
      mountMiniAppSync();
    }
    if (bindMiniAppCssVars.isAvailable()) {
      bindMiniAppCssVars();
    }
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

  window.Telegram?.WebApp?.ready();
  window.Telegram?.WebApp?.expand();

  try {
    return retrieveRawInitData();
  } catch {
    return window.Telegram?.WebApp?.initData ?? "";
  }
}
