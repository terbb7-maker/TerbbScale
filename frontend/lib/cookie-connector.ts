export type ConnectorQueueItem = {
  id: string;
  file_name: string;
  account_hint: string;
  cookie_count: number;
  story_status?: "idle" | "publishing" | "published" | "failed";
  story_link?: string | null;
  story_error?: string | null;
  story_published_at?: string | null;
};

export type ConnectorStatus = {
  items: ConnectorQueueItem[];
  active_index: number;
};

export type ConnectorStoryResult = {
  status: ConnectorStatus;
  published_link: string | null;
  published_at: string;
};

type ConnectorResponse<T> = {
  source: "terbb-scale-extension";
  requestId: string;
  ok: boolean;
  data?: T;
  error?: string;
};

export class ConnectorError extends Error {}

export function connectorCommand<T>(
  type: string,
  payload?: unknown,
  timeoutMs = 10_000,
): Promise<T> {
  if (typeof window === "undefined") {
    return Promise.reject(new ConnectorError("O conector só pode ser usado no navegador."));
  }

  const requestId = crypto.randomUUID();
  return new Promise<T>((resolve, reject) => {
    const timeout = window.setTimeout(() => {
      window.removeEventListener("message", onMessage);
      reject(new ConnectorError("A extensão Terbb Cookie Connector não respondeu."));
    }, timeoutMs);

    function onMessage(event: MessageEvent<ConnectorResponse<T>>) {
      if (
        event.source !== window
        || event.data?.source !== "terbb-scale-extension"
        || event.data.requestId !== requestId
      ) return;

      window.clearTimeout(timeout);
      window.removeEventListener("message", onMessage);
      if (!event.data.ok) {
        reject(new ConnectorError(event.data.error ?? "A extensão não concluiu a operação."));
        return;
      }
      resolve(event.data.data as T);
    }

    window.addEventListener("message", onMessage);
    window.postMessage({
      source: "terbb-scale-web",
      version: 1,
      requestId,
      type,
      payload,
    }, window.location.origin);
  });
}
