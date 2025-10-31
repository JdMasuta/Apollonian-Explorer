/**
 * Tests for WebSocket service.
 *
 * Reference: IMPLEMENTATION_PLAN.md Phase 2 Day 5 Task 2
 */

import { describe, it, expect, beforeEach, vi, afterEach } from 'vitest';
import websocketService, {
  type ProgressMessage,
  type CompleteMessage,
  type ErrorMessage,
} from './websocketService';

/**
 * Mock WebSocket class for testing.
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

  constructor(url: string) {
    this.url = url;
    // Simulate async connection
    setTimeout(() => {
      this.readyState = MockWebSocket.OPEN;
      if (this.onopen) {
        this.onopen(new Event('open'));
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
    this.readyState = MockWebSocket.CLOSED;
    if (this.onclose) {
      this.onclose(new CloseEvent('close', { code: 1000, reason: 'Normal closure' }));
    }
  }

  // Helper method to simulate receiving a message
  simulateMessage(data: any): void {
    if (this.onmessage) {
      const event = new MessageEvent('message', {
        data: JSON.stringify(data),
      });
      this.onmessage(event);
    }
  }

  // Helper method to simulate connection error
  simulateError(): void {
    if (this.onerror) {
      this.onerror(new Event('error'));
    }
  }
}

describe('WebSocketService', () => {
  let mockWebSocket: MockWebSocket;

  beforeEach(() => {
    // Mock global WebSocket
    mockWebSocket = null as any;
    (global as any).WebSocket = function (this: any, url: string) {
      mockWebSocket = new MockWebSocket(url) as any;
      return mockWebSocket as any;
    };

    // Reset service state by disconnecting
    websocketService.disconnect();
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  describe('connect()', () => {
    it('should connect to WebSocket server', async () => {
      await websocketService.connect();

      expect(mockWebSocket).toBeTruthy();
      expect(mockWebSocket.url).toBe('ws://localhost:8000/ws/gasket/generate');
      expect(websocketService.isConnected()).toBe(true);
    });

    it('should resolve immediately if already connected', async () => {
      await websocketService.connect();
      const firstWebSocket = mockWebSocket;

      await websocketService.connect();
      const secondWebSocket = mockWebSocket;

      // Should be the same WebSocket instance
      expect(firstWebSocket).toBe(secondWebSocket);
    });

    it('should reject if connection fails', async () => {
      // Override mock to simulate connection failure
      (global as any).WebSocket = function (this: any, url: string) {
        mockWebSocket = new MockWebSocket(url) as any;
        setTimeout(() => {
          mockWebSocket.simulateError();
        }, 0);
        return mockWebSocket as any;
      };

      await expect(websocketService.connect()).rejects.toThrow();
    });
  });

  describe('generateGasket()', () => {
    it('should send generate request with correct format', async () => {
      await websocketService.connect();

      const callbacks = {
        onProgress: vi.fn(),
        onComplete: vi.fn(),
        onError: vi.fn(),
      };

      websocketService.generateGasket(['1', '1', '1'], 5, callbacks);

      expect(mockWebSocket.sentMessages).toHaveLength(1);
      const message = JSON.parse(mockWebSocket.sentMessages[0]);
      expect(message).toEqual({
        action: 'start',
        curvatures: ['1', '1', '1'],
        max_depth: 5,
      });
    });

    it('should call onError if not connected', async () => {
      const callbacks = {
        onProgress: vi.fn(),
        onComplete: vi.fn(),
        onError: vi.fn(),
      };

      websocketService.generateGasket(['1', '1', '1'], 5, callbacks);

      expect(callbacks.onError).toHaveBeenCalledWith({
        type: 'error',
        message: expect.stringContaining('not connected'),
      });
    });
  });

  describe('Message routing', () => {
    it('should route progress messages to onProgress callback', async () => {
      await websocketService.connect();

      const callbacks = {
        onProgress: vi.fn(),
        onComplete: vi.fn(),
        onError: vi.fn(),
      };

      websocketService.generateGasket(['1', '1', '1'], 2, callbacks);

      const progressMessage: ProgressMessage = {
        type: 'progress',
        generation: 0,
        circles_count: 3,
        circles: [
          {
            curvature: '1',
            center: { x: '0', y: '0' },
            radius: '1',
            generation: 0,
            parent_ids: [],
            tangent_ids: [],
          },
        ],
      };

      mockWebSocket.simulateMessage(progressMessage);

      expect(callbacks.onProgress).toHaveBeenCalledWith(progressMessage);
      expect(callbacks.onComplete).not.toHaveBeenCalled();
      expect(callbacks.onError).not.toHaveBeenCalled();
    });

    it('should route complete messages to onComplete callback', async () => {
      await websocketService.connect();

      const callbacks = {
        onProgress: vi.fn(),
        onComplete: vi.fn(),
        onError: vi.fn(),
      };

      websocketService.generateGasket(['1', '1', '1'], 2, callbacks);

      const completeMessage: CompleteMessage = {
        type: 'complete',
        gasket_id: null,
        total_circles: 14,
      };

      mockWebSocket.simulateMessage(completeMessage);

      expect(callbacks.onComplete).toHaveBeenCalledWith(completeMessage);
      expect(callbacks.onProgress).not.toHaveBeenCalled();
      expect(callbacks.onError).not.toHaveBeenCalled();
    });

    it('should route error messages to onError callback', async () => {
      await websocketService.connect();

      const callbacks = {
        onProgress: vi.fn(),
        onComplete: vi.fn(),
        onError: vi.fn(),
      };

      websocketService.generateGasket(['1', '1', '1'], 2, callbacks);

      const errorMessage: ErrorMessage = {
        type: 'error',
        message: 'Invalid curvatures',
      };

      mockWebSocket.simulateMessage(errorMessage);

      expect(callbacks.onError).toHaveBeenCalledWith(errorMessage);
      expect(callbacks.onProgress).not.toHaveBeenCalled();
      expect(callbacks.onComplete).not.toHaveBeenCalled();
    });

    it('should handle multiple progress messages', async () => {
      await websocketService.connect();

      const callbacks = {
        onProgress: vi.fn(),
        onComplete: vi.fn(),
        onError: vi.fn(),
      };

      websocketService.generateGasket(['1', '1', '1'], 3, callbacks);

      // Simulate multiple progress messages
      for (let i = 0; i < 5; i++) {
        mockWebSocket.simulateMessage({
          type: 'progress',
          generation: i,
          circles_count: 2,
          circles: [],
        });
      }

      expect(callbacks.onProgress).toHaveBeenCalledTimes(5);
    });
  });

  describe('disconnect()', () => {
    it('should close WebSocket connection', async () => {
      await websocketService.connect();
      expect(websocketService.isConnected()).toBe(true);

      websocketService.disconnect();

      expect(mockWebSocket.readyState).toBe(MockWebSocket.CLOSED);
      expect(websocketService.isConnected()).toBe(false);
    });

    it('should handle disconnect when not connected', () => {
      // Should not throw
      expect(() => websocketService.disconnect()).not.toThrow();
    });
  });

  describe('isConnected()', () => {
    it('should return true when connected', async () => {
      await websocketService.connect();
      expect(websocketService.isConnected()).toBe(true);
    });

    it('should return false when not connected', () => {
      expect(websocketService.isConnected()).toBe(false);
    });

    it('should return false after disconnect', async () => {
      await websocketService.connect();
      websocketService.disconnect();
      expect(websocketService.isConnected()).toBe(false);
    });
  });

  describe('getReadyState()', () => {
    it('should return ready state when connected', async () => {
      await websocketService.connect();
      expect(websocketService.getReadyState()).toBe(MockWebSocket.OPEN);
    });

    it('should return null when not connected', () => {
      expect(websocketService.getReadyState()).toBe(null);
    });
  });

  describe('Error handling', () => {
    it('should handle invalid JSON in messages', async () => {
      await websocketService.connect();

      const callbacks = {
        onProgress: vi.fn(),
        onComplete: vi.fn(),
        onError: vi.fn(),
      };

      websocketService.generateGasket(['1', '1', '1'], 2, callbacks);

      // Simulate invalid JSON
      if (mockWebSocket.onmessage) {
        const event = new MessageEvent('message', {
          data: 'invalid json {{{',
        });
        mockWebSocket.onmessage(event);
      }

      expect(callbacks.onError).toHaveBeenCalledWith({
        type: 'error',
        message: expect.stringContaining('parse'),
      });
    });
  });
});
