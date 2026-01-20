/**
 * SSE Client for Deployment Narration Stream
 *
 * Connects to /api/deploy/stream to receive narration events
 * describing deployment progress. The actual deployment is
 * executed externally via Claude Code with MCP.
 */

class DeploymentStream {
  /**
   * Create a DeploymentStream instance.
   * @param {string} url - SSE endpoint URL
   * @param {Object} options - Event handlers
   * @param {Function} options.onStart - Handler for start events
   * @param {Function} options.onTable - Handler for table events
   * @param {Function} options.onRelationship - Handler for relationship events
   * @param {Function} options.onMeasure - Handler for measure events
   * @param {Function} options.onComplete - Handler for complete events
   * @param {Function} options.onError - Handler for error events
   * @param {Function} options.onHeartbeat - Handler for heartbeat events
   */
  constructor(url, options = {}) {
    this.url = url;
    this.onStart = options.onStart || (() => {});
    this.onTable = options.onTable || (() => {});
    this.onRelationship = options.onRelationship || (() => {});
    this.onMeasure = options.onMeasure || (() => {});
    this.onComplete = options.onComplete || (() => {});
    this.onError = options.onError || (() => {});
    this.onHeartbeat = options.onHeartbeat || (() => {});
    this.source = null;
    this.isConnected = false;
    this.reconnectAttempts = 0;
    this.maxReconnectAttempts = 3;
  }

  /**
   * Connect to the SSE stream.
   * Opens EventSource connection and sets up event listeners.
   */
  connect() {
    if (this.source) {
      this.close();
    }

    try {
      this.source = new EventSource(this.url);
      this.isConnected = true;
      this.reconnectAttempts = 0;

      // Start event - deployment beginning
      this.source.addEventListener('start', (e) => {
        try {
          const data = JSON.parse(e.data);
          this.onStart(data);
        } catch (err) {
          console.error('Error parsing start event:', err);
        }
      });

      // Table event - table being deployed
      this.source.addEventListener('table', (e) => {
        try {
          const data = JSON.parse(e.data);
          this.onTable(data);
        } catch (err) {
          console.error('Error parsing table event:', err);
        }
      });

      // Relationship event - relationship being created
      this.source.addEventListener('relationship', (e) => {
        try {
          const data = JSON.parse(e.data);
          this.onRelationship(data);
        } catch (err) {
          console.error('Error parsing relationship event:', err);
        }
      });

      // Measure event - measure being created
      this.source.addEventListener('measure', (e) => {
        try {
          const data = JSON.parse(e.data);
          this.onMeasure(data);
        } catch (err) {
          console.error('Error parsing measure event:', err);
        }
      });

      // Complete event - deployment finished
      this.source.addEventListener('complete', (e) => {
        try {
          const data = JSON.parse(e.data);
          this.onComplete(data);
          // Close connection after completion
          this.close();
        } catch (err) {
          console.error('Error parsing complete event:', err);
        }
      });

      // Error event from server
      this.source.addEventListener('error', (e) => {
        try {
          const data = e.data ? JSON.parse(e.data) : { message: 'Unknown error' };
          this.onError(data);
        } catch (err) {
          // May be a connection error, not a data error
          console.error('SSE error event:', err);
        }
      });

      // Heartbeat event - keep-alive
      this.source.addEventListener('heartbeat', (e) => {
        try {
          const data = JSON.parse(e.data);
          this.onHeartbeat(data);
        } catch (err) {
          console.error('Error parsing heartbeat event:', err);
        }
      });

      // Handle connection errors
      this.source.onerror = (err) => {
        console.error('SSE connection error:', err);
        this.isConnected = false;

        // EventSource auto-reconnects, but we track attempts
        this.reconnectAttempts++;

        if (this.reconnectAttempts >= this.maxReconnectAttempts) {
          this.close();
          this.onError({ message: 'Connection lost after multiple attempts' });
        }
      };

      // Handle connection open
      this.source.onopen = () => {
        console.log('SSE connection established');
        this.isConnected = true;
        this.reconnectAttempts = 0;
      };

    } catch (err) {
      console.error('Failed to create EventSource:', err);
      this.onError({ message: 'Failed to connect to server' });
    }
  }

  /**
   * Close the SSE connection.
   */
  close() {
    if (this.source) {
      this.source.close();
      this.source = null;
      this.isConnected = false;
    }
  }

  /**
   * Check if stream is connected.
   * @returns {boolean}
   */
  connected() {
    return this.isConnected && this.source && this.source.readyState === EventSource.OPEN;
  }
}

// Export for use in main.js
window.DeploymentStream = DeploymentStream;
