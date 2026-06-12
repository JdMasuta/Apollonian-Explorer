/**
 * Tests for the WebSocket service (frontend side of the gasket-generation
 * protocol).
 *
 * Covers the full communication lifecycle against a mock socket:
 * - URL derivation (same-origin, proxied by Vite in dev)
 * - connect/disconnect lifecycle, including the React StrictMode
 *   mount/unmount/mount cycle that previously wedged the service
 *   (see ISSUES.md Issue #4 / DEBUG_LOG ERR-011)
 * - request format and message routing (progress / complete / error)
 *
 * The backend side of the same protocol is covered by
 * backend/tests/test_websocket.py, and the message schema contract by
 * backend/tests/test_ws_contract.py (mirrors the TypeScript interfaces in
 * websocketService.ts).
 */

import { describe, it, expect, beforeEach, vi } from 'vitest';
import websocketService, {
  type ProgressMessage,
  type CompleteMessage,
  type ErrorMessage,
} from './websocketService';

/**
 * Mock WebSocket. Opens asynchronously on the macrotask queue, like a real
 * socket; tests use real timers and `flush()` to advance.
 */
class MockWebSocket {
  static CONNECTING = 0;
  static OPEN = 1;
  static CLOSING = 2;
  static CLOSED = 3;

  readyState: number = MockWebSocket.CONNECTING;
  url: string;
  onopen: ((event: Event) => void) | null = null;
  onclose: ((event: CloseEvent) => void) | null = null;
  onerror: ((event: Event) => void) | null = null;
  onmessage: ((event: MessageEvent) => void) | null = null;

  sentMessages: string[] = [];
  /** When true, the socket fires onerror instead of opening. */
  static failNext = false;

  constructor(url: string) {
    this.url = url;
    const shouldFail = MockWebSocket.failNext;
    MockWebSocket.failNext = false;
    setTimeout(() => {
      if (this.readyState !== MockWebSocket.CONNECTING) {
        return; // closed before the connection was established
      }
      if (shouldFail) {
        this.readyState = MockWebSocket.CLOSED;
        this.onerror?.(new Event('error'));
        this.onclose?.(new CloseEvent('close', { code: 1006 }));
      } else {
        this.readyState = MockWebSocket.OPEN;
        this.onopen?.(new Event('open'));
      }
    }, 0);
  }

  send(data: string): void {
    if (this.readyState !== MockWebSocket.OPEN) {
      throw new Error('WebSocket is not open');
    }
    this.sentMessages.push(data);
  }

  close(): void {
    const wasConnecting = this.readyState === MockWebSocket.CONNECTING;
    this.readyState = MockWebSocket.CLOSED;
    // Browsers fire error+close when closing a CONNECTING socket, and just
    // close for an OPEN one.
    if (wasConnecting) {
      this.onerror?.(new Event('error'));
    }
    this.onclose?.(new CloseEvent('close', { code: 1000, reason: 'Normal closure' }));
  }

  simulateMessage(data: unknown): void {
    this.onmessage?.(new MessageEvent('message', { data: JSON.stringify(data) }));
  }

  simulateRawMessage(data: string): void {
    this.onmessage?.(new MessageEvent('message', { data }));
  }
}

let sockets: MockWebSocket[] = [];
const lastSocket = () => sockets[sockets.length - 1];

function makeCallbacks() {
  return {
    onProgress: vi.fn<(data: ProgressMessage) => void>(),
    onComplete: vi.fn<(data: CompleteMessage) => void>(),
    onError: vi.fn<(data: ErrorMessage) => void>(),
  };
}

beforeEach(() => {
  sockets = [];
  MockWebSocket.failNext = false;
  vi.stubGlobal(
    'WebSocket',
    class extends MockWebSocket {
      constructor(url: string) {
        super(url);
        sockets.push(this);
      }
    }
  );
  websocketService.disconnect();
});

describe('WebSocketService', () => {
  describe('URL derivation', () => {
    it('connects same-origin so the Vite dev proxy (or the backend static host) serves it', async () => {
      await websocketService.connect();

      const expectedProtocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
      expect(lastSocket().url).toBe(
        `${expectedProtocol}//${window.location.host}/ws/gasket/generate`
      );
    });
  });

  describe('connect()', () => {
    it('resolves when the socket opens', async () => {
      await websocketService.connect();

      expect(websocketService.isConnected()).toBe(true);
      expect(websocketService.getReadyState()).toBe(MockWebSocket.OPEN);
    });

    it('resolves immediately if already connected, without a second socket', async () => {
      await websocketService.connect();
      await websocketService.connect();

      expect(sockets).toHaveLength(1);
      expect(websocketService.isConnected()).toBe(true);
    });

    it('shares an in-flight connection attempt between concurrent callers', async () => {
      // Two synchronous connect() calls (e.g. two components mounting)
      const first = websocketService.connect();
      const second = websocketService.connect();

      await Promise.all([first, second]);

      expect(sockets).toHaveLength(1);
      expect(websocketService.isConnected()).toBe(true);
    });

    it('rejects if the connection fails', async () => {
      MockWebSocket.failNext = true;

      await expect(websocketService.connect()).rejects.toThrow(
        'WebSocket connection failed'
      );
      expect(websocketService.isConnected()).toBe(false);
    });

    it('survives the React StrictMode mount/unmount/mount cycle', async () => {
      // StrictMode (dev) runs: effect -> cleanup -> effect, i.e.
      // connect(); disconnect(); connect() in quick succession. The first
      // attempt is aborted while CONNECTING; the second must succeed.
      // Regression test for ERR-011 (service wedged with
      // 'Connection already in progress', page showed disconnected).
      const first = websocketService.connect().catch(() => 'aborted');
      websocketService.disconnect();
      const second = websocketService.connect();

      await second;
      expect(await first).toBe('aborted');
      expect(websocketService.isConnected()).toBe(true);
      expect(sockets).toHaveLength(2);
    });

    it('can reconnect after a clean disconnect', async () => {
      await websocketService.connect();
      websocketService.disconnect();
      expect(websocketService.isConnected()).toBe(false);

      await websocketService.connect();
      expect(websocketService.isConnected()).toBe(true);
      expect(sockets).toHaveLength(2);
    });
  });

  describe('generateGasket()', () => {
    it('sends the start request in the protocol format', async () => {
      await websocketService.connect();
      await websocketService.generateGasket(['-1', '2', '2'], 5, makeCallbacks());

      expect(lastSocket().sentMessages).toHaveLength(1);
      expect(JSON.parse(lastSocket().sentMessages[0])).toEqual({
        action: 'start',
        curvatures: ['-1', '2', '2'],
        max_depth: 5,
      });
    });

    it('includes min_radius when provided', async () => {
      await websocketService.generateGasket(['-1', '2', '2'], 8, makeCallbacks(), {
        minRadius: 0.001,
      });

      expect(JSON.parse(lastSocket().sentMessages[0])).toEqual({
        action: 'start',
        curvatures: ['-1', '2', '2'],
        max_depth: 8,
        min_radius: 0.001,
      });
    });

    it('connects on demand when not connected (lazy connection)', async () => {
      expect(websocketService.isConnected()).toBe(false);

      await websocketService.generateGasket(['1', '1', '1'], 3, makeCallbacks());

      expect(websocketService.isConnected()).toBe(true);
      expect(lastSocket().sentMessages).toHaveLength(1);
    });

    it('reconnects after the server closes the socket post-completion', async () => {
      // First generation: backend closes the connection after 'complete'.
      const first = makeCallbacks();
      await websocketService.generateGasket(['-1', '2', '2'], 3, first);
      lastSocket().simulateMessage({ type: 'complete', gasket_id: null, total_circles: 8 });
      lastSocket().close(); // server-side close (code 1000 after complete)
      expect(websocketService.isConnected()).toBe(false);

      // Second generation in the same page must transparently reconnect
      // (regression: 'WebSocket is not connected. Call connect() first.').
      const second = makeCallbacks();
      await websocketService.generateGasket(['-1', '2', '2'], 3, second);

      expect(second.onError).not.toHaveBeenCalled();
      expect(websocketService.isConnected()).toBe(true);
      expect(sockets).toHaveLength(2);
      expect(lastSocket().sentMessages).toHaveLength(1);
    });

    it('reports connection failures through onError', async () => {
      MockWebSocket.failNext = true;
      const callbacks = makeCallbacks();

      await websocketService.generateGasket(['1', '1', '1'], 3, callbacks);

      expect(callbacks.onError).toHaveBeenCalledTimes(1);
      expect(callbacks.onError.mock.calls[0][0].message).toMatch(/connect/i);
    });
  });

  describe('message routing', () => {
    async function connectAndRegister() {
      const callbacks = makeCallbacks();
      await websocketService.generateGasket(['-1', '2', '2'], 2, callbacks);
      return callbacks;
    }

    it('routes progress messages to onProgress', async () => {
      const callbacks = await connectAndRegister();
      const progress: ProgressMessage = {
        type: 'progress',
        generation: 1,
        circles_count: 2,
        circles: [
          {
            curvature: '3/1',
            center: { x: '0/1', y: '2/3' },
            radius: '1/3',
            generation: 1,
            parent_ids: [],
            tangent_ids: [],
          },
        ],
      };

      lastSocket().simulateMessage(progress);

      expect(callbacks.onProgress).toHaveBeenCalledTimes(1);
      expect(callbacks.onProgress.mock.calls[0][0]).toEqual(progress);
      expect(callbacks.onComplete).not.toHaveBeenCalled();
    });

    it('routes complete messages to onComplete', async () => {
      const callbacks = await connectAndRegister();

      lastSocket().simulateMessage({ type: 'complete', gasket_id: null, total_circles: 20 });

      expect(callbacks.onComplete).toHaveBeenCalledTimes(1);
      expect(callbacks.onComplete.mock.calls[0][0].total_circles).toBe(20);
    });

    it('routes error messages to onError', async () => {
      const callbacks = await connectAndRegister();

      lastSocket().simulateMessage({ type: 'error', message: 'boom' });

      expect(callbacks.onError).toHaveBeenCalledTimes(1);
      expect(callbacks.onError.mock.calls[0][0].message).toBe('boom');
    });

    it('handles multiple progress messages in order', async () => {
      const callbacks = await connectAndRegister();

      for (let generation = 1; generation <= 3; generation += 1) {
        lastSocket().simulateMessage({
          type: 'progress',
          generation,
          circles_count: 0,
          circles: [],
        });
      }

      expect(callbacks.onProgress).toHaveBeenCalledTimes(3);
      expect(callbacks.onProgress.mock.calls.map((c) => c[0].generation)).toEqual([1, 2, 3]);
    });

    it('reports malformed JSON through onError', async () => {
      const callbacks = await connectAndRegister();

      lastSocket().simulateRawMessage('invalid json {{{');

      expect(callbacks.onError).toHaveBeenCalledTimes(1);
      expect(callbacks.onError.mock.calls[0][0].message).toMatch(/parse/i);
    });

    it('ignores unknown message types without invoking callbacks', async () => {
      const callbacks = await connectAndRegister();

      lastSocket().simulateMessage({ type: 'mystery' });

      expect(callbacks.onProgress).not.toHaveBeenCalled();
      expect(callbacks.onComplete).not.toHaveBeenCalled();
      expect(callbacks.onError).not.toHaveBeenCalled();
    });

    it('does not misreport callback exceptions as parse failures', async () => {
      // Regression for ERR-013: a React error thrown inside onProgress was
      // surfaced as "Failed to parse message: ...".
      const callbacks = makeCallbacks();
      callbacks.onProgress.mockImplementation(() => {
        throw new Error('Maximum update depth exceeded');
      });
      await websocketService.generateGasket(['-1', '2', '2'], 2, callbacks);

      lastSocket().simulateMessage({
        type: 'progress',
        generation: 1,
        circles_count: 0,
        circles: [],
      });

      expect(callbacks.onError).toHaveBeenCalledTimes(1);
      const message = callbacks.onError.mock.calls[0][0].message;
      expect(message).not.toMatch(/parse/i);
      expect(message).toMatch(/handling 'progress' message/i);
      expect(message).toMatch(/Maximum update depth exceeded/);
    });
  });

  describe('disconnect()', () => {
    it('closes the connection', async () => {
      await websocketService.connect();
      websocketService.disconnect();

      expect(websocketService.isConnected()).toBe(false);
      expect(websocketService.getReadyState()).toBeNull();
    });

    it('is a no-op when not connected', () => {
      expect(() => websocketService.disconnect()).not.toThrow();
      expect(websocketService.isConnected()).toBe(false);
    });
  });

  describe('getReadyState()', () => {
    it('returns null when no socket exists', () => {
      expect(websocketService.getReadyState()).toBeNull();
    });

    it('returns OPEN after connecting', async () => {
      await websocketService.connect();
      expect(websocketService.getReadyState()).toBe(MockWebSocket.OPEN);
    });
  });
});
