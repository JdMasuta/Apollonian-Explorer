/**
 * WebSocket service for real-time gasket generation.
 *
 * This service provides a singleton WebSocket client for connecting to the
 * backend gasket generation endpoint and receiving real-time circle data
 * as the gasket is being generated.
 *
 * Reference: IMPLEMENTATION_PLAN.md Phase 2 Day 5 Task 2
 */

/**
 * Circle data structure received from backend.
 */
export interface CircleData {
  id?: number;
  curvature: string;
  center: {
    x: string;
    y: string;
  };
  radius: string;
  generation: number;
  parent_ids: number[];
  tangent_ids: number[];
}

/**
 * Progress message from backend during generation.
 */
export interface ProgressMessage {
  type: 'progress';
  generation: number;
  circles_count: number;
  circles: CircleData[];
}

/**
 * Completion message from backend after generation finishes.
 */
export interface CompleteMessage {
  type: 'complete';
  gasket_id: number | null;
  total_circles: number;
}

/**
 * Error message from backend if something goes wrong.
 */
export interface ErrorMessage {
  type: 'error';
  message: string;
}

/**
 * Union type of all possible WebSocket messages.
 */
export type WebSocketMessage = ProgressMessage | CompleteMessage | ErrorMessage;

/**
 * Callback functions for handling WebSocket messages.
 */
export interface WebSocketCallbacks {
  onProgress: (data: ProgressMessage) => void;
  onComplete: (data: CompleteMessage) => void;
  onError: (data: ErrorMessage) => void;
}

/**
 * WebSocket service class for gasket generation.
 *
 * Usage:
 * ```typescript
 * import websocketService from './services/websocketService';
 *
 * await websocketService.connect();
 * websocketService.generateGasket(
 *   ['1', '1', '1'],
 *   5,
 *   {
 *     onProgress: (data) => console.log('Progress:', data),
 *     onComplete: (data) => console.log('Complete:', data),
 *     onError: (data) => console.error('Error:', data)
 *   }
 * );
 * ```
 */
class WebSocketService {
  private ws: WebSocket | null = null;
  private url: string;
  private callbacks: WebSocketCallbacks | null = null;
  private connectPromise: Promise<void> | null = null;

  /**
   * Initialize WebSocket service with URL.
   *
   * The URL is derived from the page origin in all modes:
   * - Development: the Vite dev server proxies /ws to the backend
   *   (see vite.config.ts).
   * - Production: the frontend build is served from the backend itself
   *   (static mount), so same-origin is the backend.
   * `VITE_WS_URL` overrides this for split deployments.
   *
   * @param url - Optional WebSocket URL override
   */
  constructor(url?: string) {
    if (url) {
      this.url = url;
    } else if (import.meta.env.VITE_WS_URL) {
      this.url = import.meta.env.VITE_WS_URL;
    } else {
      const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
      this.url = `${protocol}//${window.location.host}/ws/gasket/generate`;
    }
  }

  /**
   * Connect to WebSocket server.
   *
   * Idempotent: while a connection attempt is in flight, subsequent calls
   * return the same promise instead of rejecting. This matters under React
   * StrictMode, whose dev-mode mount/unmount/mount cycle calls
   * connect() / disconnect() / connect() in quick succession.
   *
   * @returns Promise that resolves when connection is established
   * @throws Error if connection fails
   */
  connect(): Promise<void> {
    // Already connected
    if (this.ws && this.ws.readyState === WebSocket.OPEN) {
      return Promise.resolve();
    }

    // Connection attempt already in flight: share it
    if (this.connectPromise) {
      return this.connectPromise;
    }

    this.connectPromise = new Promise((resolve, reject) => {
      try {
        const ws = new WebSocket(this.url);
        this.ws = ws;

        ws.onopen = () => {
          this.connectPromise = null;
          console.log('[WebSocket] Connected to', this.url);
          resolve();
        };

        ws.onerror = (event) => {
          this.connectPromise = null;
          console.error('[WebSocket] Connection error:', event);
          reject(new Error('WebSocket connection failed'));
        };

        ws.onclose = (event) => {
          this.connectPromise = null;
          console.log('[WebSocket] Connection closed:', event.code, event.reason);
          // Reject connect() callers if the socket closed before opening
          // (e.g. disconnect() during StrictMode's first mount cycle).
          reject(new Error('WebSocket closed before the connection was established'));
          if (this.ws === ws) {
            this.ws = null;
            this.callbacks = null;
          }
        };

        ws.onmessage = (event) => {
          this.handleMessage(event);
        };
      } catch (error) {
        this.connectPromise = null;
        reject(error);
      }
    });
    return this.connectPromise;
  }

  /**
   * Generate an Apollonian gasket with real-time streaming.
   *
   * Connects on demand: the backend closes the socket after each completed
   * run (one generation per connection), so this method always ensures a
   * live connection first (connect() is idempotent).
   *
   * @param curvatures - Initial curvatures (3 or 4 values as strings)
   * @param maxDepth - Maximum recursion depth (1-15)
   * @param callbacks - Callback functions for progress, complete, and error
   * @param options - Optional generation parameters:
   *   minRadius — resolution bound in model units; circles smaller than
   *   this are pruned server-side along with their subtrees.
   */
  async generateGasket(
    curvatures: string[],
    maxDepth: number,
    callbacks: WebSocketCallbacks,
    options: { minRadius?: number } = {}
  ): Promise<void> {
    try {
      await this.connect();
    } catch (error) {
      callbacks.onError({
        type: 'error',
        message: `Could not connect to the server: ${error instanceof Error ? error.message : error}`,
      });
      return;
    }

    if (!this.ws || this.ws.readyState !== WebSocket.OPEN) {
      callbacks.onError({
        type: 'error',
        message: 'WebSocket is not connected.',
      });
      return;
    }

    // Store callbacks for message routing
    this.callbacks = callbacks;

    // Send start message
    const message: Record<string, unknown> = {
      action: 'start',
      curvatures,
      max_depth: maxDepth,
    };
    if (options.minRadius !== undefined) {
      message.min_radius = options.minRadius;
    }

    try {
      this.ws.send(JSON.stringify(message));
      console.log('[WebSocket] Sent generate request:', message);
    } catch (error) {
      callbacks.onError({
        type: 'error',
        message: `Failed to send request: ${error}`,
      });
    }
  }

  /**
   * Disconnect from WebSocket server.
   *
   * Safe to call while a connection attempt is in flight: the pending
   * connect() promise is rejected and internal state fully reset, so a
   * subsequent connect() starts cleanly.
   */
  disconnect(): void {
    if (this.ws) {
      console.log('[WebSocket] Disconnecting...');
      this.ws.close();
      this.ws = null;
      this.callbacks = null;
    }
    this.connectPromise = null;
  }

  /**
   * Handle incoming WebSocket message.
   *
   * JSON parsing and callback dispatch have separate error handling so an
   * exception thrown by application code is never misreported as a protocol
   * parse failure (DEBUG_LOG ERR-013).
   *
   * @param event - WebSocket message event
   */
  private handleMessage(event: MessageEvent): void {
    let data: WebSocketMessage;
    try {
      data = JSON.parse(event.data);
    } catch (error) {
      console.error('[WebSocket] Failed to parse message:', error);
      this.callbacks?.onError({
        type: 'error',
        message: `Failed to parse message: ${error}`,
      });
      return;
    }

    if (!this.callbacks) {
      console.warn('[WebSocket] Received message but no callbacks registered');
      return;
    }

    try {
      // Route message to appropriate callback
      switch (data.type) {
        case 'progress':
          this.callbacks.onProgress(data);
          break;

        case 'complete':
          this.callbacks.onComplete(data);
          break;

        case 'error':
          this.callbacks.onError(data);
          break;

        default:
          console.warn(
            '[WebSocket] Unknown message type:',
            (data as { type?: string }).type
          );
      }
    } catch (error) {
      // An error thrown by a callback is an application bug; report it as
      // such (and to the console with its real stack).
      console.error('[WebSocket] Message handler threw:', error);
      this.callbacks?.onError({
        type: 'error',
        message: `Error handling '${data.type}' message: ${error instanceof Error ? error.message : error}`,
      });
    }
  }

  /**
   * Check if WebSocket is currently connected.
   */
  isConnected(): boolean {
    return this.ws !== null && this.ws.readyState === WebSocket.OPEN;
  }

  /**
   * Get current WebSocket ready state.
   */
  getReadyState(): number | null {
    return this.ws ? this.ws.readyState : null;
  }
}

// Export singleton instance
const websocketService = new WebSocketService();
export default websocketService;
