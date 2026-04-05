import { getAuthToken, coalesceRefresh, clearAuthAndRedirect } from "./client";
import type { SSEEvent } from "@/types/assistant";

const BASE_URL = "/api";

// ---------------------------------------------------------------------------
// SSE buffer parser
// ---------------------------------------------------------------------------

interface SSEFrame {
  event?: string;
  data: string;
}

/**
 * Split a raw SSE text buffer into parsed frames.
 *
 * SSE frames are separated by blank lines (`\n\n`). Each frame may contain
 * `event:` and `data:` fields. Returns the successfully parsed frames and
 * any remaining incomplete text that should be prepended to the next chunk.
 */
export function parseSSEBuffer(buffer: string): {
  parsed: SSEFrame[];
  remaining: string;
} {
  const parsed: SSEFrame[] = [];

  // Split on double-newline boundaries
  const parts = buffer.split("\n\n");

  // The last part is potentially incomplete — carry it over
  const remaining = parts.pop() ?? "";

  for (const raw of parts) {
    if (!raw.trim()) continue;

    let event: string | undefined;
    let data = "";

    for (const line of raw.split("\n")) {
      if (line.startsWith("event:")) {
        event = line.slice("event:".length).trim();
      } else if (line.startsWith("data:")) {
        // Concatenate multiple `data:` lines (SSE spec)
        data += (data ? "\n" : "") + line.slice("data:".length).trim();
      }
      // Ignore comments (`:`) and unknown fields
    }

    if (data) {
      parsed.push({ event, data });
    }
  }

  return { parsed, remaining };
}

// ---------------------------------------------------------------------------
// SSE stream consumers
// ---------------------------------------------------------------------------

interface StreamChatBody {
  content: string;
  class_id?: string;
  files?: Array<{ file_id: string; filename: string; mime_type: string }>;
  [key: string]: unknown;
}

/**
 * Send a message and consume the SSE response as an async generator.
 *
 * Uses `fetch` + `ReadableStream` instead of `EventSource` because we need
 * POST with a JSON body and an Authorization header.
 */
export async function* streamChat(
  conversationId: string,
  body: StreamChatBody,
  signal?: AbortSignal,
): AsyncGenerator<SSEEvent> {
  yield* consumeSSE(
    `${BASE_URL}/assistant/conversations/${conversationId}/messages`,
    body,
    signal,
  );
}

/**
 * Answer an `ask_user` question and consume the resumed SSE stream.
 */
export async function* streamAnswer(
  conversationId: string,
  answer: string,
  signal?: AbortSignal,
): AsyncGenerator<SSEEvent> {
  yield* consumeSSE(
    `${BASE_URL}/assistant/conversations/${conversationId}/answer`,
    { answer },
    signal,
  );
}

// ---------------------------------------------------------------------------
// Internal SSE consumer
// ---------------------------------------------------------------------------

function buildHeaders(token: string | null): Record<string, string> {
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
  };
  if (token) {
    headers["Authorization"] = `Bearer ${token}`;
  }
  return headers;
}

async function* consumeSSE(
  url: string,
  body: Record<string, unknown>,
  signal?: AbortSignal,
): AsyncGenerator<SSEEvent> {
  const jsonBody = JSON.stringify(body);

  let response = await fetch(url, {
    method: "POST",
    headers: buildHeaders(getAuthToken()),
    body: jsonBody,
    signal,
  });

  // Handle 401: attempt token refresh then retry once
  if (response.status === 401) {
    let newToken: string;
    try {
      newToken = await coalesceRefresh();
    } catch {
      clearAuthAndRedirect();
      throw new Error("认证已过期");
    }

    response = await fetch(url, {
      method: "POST",
      headers: buildHeaders(newToken),
      body: jsonBody,
      signal,
    });
  }

  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: "请求失败" }));
    throw new Error(
      (error as { detail?: string }).detail ?? `HTTP ${response.status}`,
    );
  }

  const reader = response.body?.getReader();
  if (!reader) {
    throw new Error("响应不支持流式读取");
  }

  const decoder = new TextDecoder();
  let buffer = "";

  try {
    for (;;) {
      const { done, value } = await reader.read();
      if (done) break;

      buffer += decoder.decode(value, { stream: true });

      const { parsed, remaining } = parseSSEBuffer(buffer);
      buffer = remaining;

      for (const frame of parsed) {
        const event = parseSSEEvent(frame);
        if (event) yield event;
      }
    }

    // Flush any trailing data left in the buffer
    if (buffer.trim()) {
      const { parsed } = parseSSEBuffer(buffer + "\n\n");
      for (const frame of parsed) {
        const event = parseSSEEvent(frame);
        if (event) yield event;
      }
    }
  } finally {
    reader.releaseLock();
  }
}

// ---------------------------------------------------------------------------
// SSE frame → typed event
// ---------------------------------------------------------------------------

function parseSSEEvent(frame: SSEFrame): SSEEvent | null {
  try {
    return JSON.parse(frame.data) as SSEEvent;
  } catch {
    return null;
  }
}
