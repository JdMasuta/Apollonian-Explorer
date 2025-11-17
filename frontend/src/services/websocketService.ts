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
  private isConnecting: boolean = false;

  /**
   * Initialize WebSocket service with URL.
   *
   * In development mode, uses Vite proxy (ws://localhost:5173/ws/gasket/generate).
   * In production, connects directly to backend (ws://localhost:8000/ws/gasket/generate).
   *
   * @param url - Optional WebSocket URL override
   */
  constructor(url?: string) {
    // Determine WebSocket URL based on environment
    if (url) {
      this.url = url;
    } else if (import.meta.env.DEV) {
      // Development: Use Vite proxy on same host as frontend
      const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
      this.url = `${protocol}//${window.location.host}/ws/gasket/generate`;
    } else {
      // Production: Connect directly to backend
      this.url = 'ws://localhost:8000/ws/gasket/generate';
    }
  }

  /**
   * Connect to WebSocket server.
   *
   * @returns Promise that resolves when connection is established
   * @throws Error if connection fails
   */
  connect(): Promise<void> {
    return new Promise((resolve, reject) => {
      // Prevent multiple simultaneous connection attempts
      if (this.isConnecting) {
        reject(new Error('Connection already in progress'));
        return;
      }

      // Already connected
      if (this.ws && this.ws.readyState === WebSocket.OPEN) {
        resolve();
        return;
      }

      this.isConnecting = true;

      try {
        this.ws = new WebSocket(this.url);

        this.ws.onopen = () => {
          this.isConnecting = false;
          console.log('[WebSocket] Connected to', this.url);
          resolve();
        };

        this.ws.onerror = (event) => {
          this.isConnecting = false;
          console.error('[WebSocket] Connection error:', event);
          reject(new Error('WebSocket connection failed'));
        };

        this.ws.onclose = (event) => {
          this.isConnecting = false;
          console.log('[WebSocket] Connection closed:', event.code, event.reason);
          this.ws = null;
          this.callbacks = null;
        };

        this.ws.onmessage = (event) => {
          this.handleMessage(event);
        };
      } catch (error) {
        this.isConnecting = false;
        reject(error);
      }
    });
  }

  /**
   * Generate an Apollonian gasket with real-time streaming.
   *
   * @param curvatures - Initial curvatures (3 or 4 values as strings)
   * @param maxDepth - Maximum recursion depth (1-15)
   * @param callbacks - Callback functions for progress, complete, and error
   */
  generateGasket(
    curvatures: string[],
    maxDepth: number,
    callbacks: WebSocketCallbacks
  ): void {
    if (!this.ws || this.ws.readyState !== WebSocket.OPEN) {
      callbacks.onError({
        type: 'error',
        message: 'WebSocket is not connected. Call connect() first.',
      });
      return;
    }

    // Store callbacks for message routing
    this.callbacks = callbacks;

    // Send start message
    const message = {
      action: 'start',
      curvatures,
      max_depth: maxDepth,
    };

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
   */
  disconnect(): void {
    if (this.ws) {
      console.log('[WebSocket] Disconnecting...');
      this.ws.close();
      this.ws = null;
      this.callbacks = null;
    }
  }

  /**
   * Handle incoming WebSocket message.
   *
   * @param event - WebSocket message event
   */
  private handleMessage(event: MessageEvent): void {
    try {
      const data: WebSocketMessage = JSON.parse(event.data);

      console.log('[WebSocket] Received message:', data.type);

      if (!this.callbacks) {
        console.warn('[WebSocket] Received message but no callbacks registered');
        return;
      }

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
          console.warn('[WebSocket] Unknown message type:', (data as any).type);
      }
    } catch (error) {
      console.error('[WebSocket] Failed to parse message:', error);
      if (this.callbacks) {
        this.callbacks.onError({
          type: 'error',
          message: `Failed to parse message: ${error}`,
        });
      }
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
