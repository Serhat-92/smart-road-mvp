import { useEffect, useState } from "react";

export function useAsyncResource(loader, deps = [], options = {}) {
  const refreshIntervalMs = options.refreshIntervalMs || 0;
  const [state, setState] = useState({
    data: null,
    error: null,
    isLoading: true,
    isRefreshing: false,
    lastUpdatedAt: null,
  });

  useEffect(() => {
    let isActive = true;
    let refreshTimer = null;

    async function loadResource({ isInitialLoad = false } = {}) {
      setState((currentState) => ({
        data: isInitialLoad ? null : currentState.data,
        error: null,
        isLoading: isInitialLoad,
        isRefreshing: !isInitialLoad && Boolean(currentState.data),
        lastUpdatedAt: currentState.lastUpdatedAt,
      }));

      try {
        const data = await loader();
        if (!isActive) {
          return;
        }

        setState({
          data,
          error: null,
          isLoading: false,
          isRefreshing: false,
          lastUpdatedAt: new Date().toISOString(),
        });
      } catch (error) {
        if (!isActive) {
          return;
        }

        setState((currentState) => ({
          data: currentState.data,
          error,
          isLoading: false,
          isRefreshing: false,
          lastUpdatedAt: currentState.lastUpdatedAt,
        }));
      }
    }

    loadResource({ isInitialLoad: true });

    if (refreshIntervalMs > 0) {
      refreshTimer = window.setInterval(() => {
        loadResource();
      }, refreshIntervalMs);
    }

    return () => {
      isActive = false;
      if (refreshTimer) {
        window.clearInterval(refreshTimer);
      }
    };
  }, [...deps, refreshIntervalMs]);

  return state;
}
