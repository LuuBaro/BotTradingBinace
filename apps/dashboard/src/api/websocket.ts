export interface WsStreamMessage {
  type: 'status' | 'decision' | 'position_change' | 'order_change' | 'event' | 'recon'
  timestamp: string
  data: Record<string, any>
}

export interface WsConnectionOptions {
  url: string
  token: string
  onMessage?: (msg: WsStreamMessage) => void
  onConnect?: () => void
  onDisconnect?: () => void
  onError?: (error: Event | Error) => void
}

export class WsClient {
  private ws: WebSocket | null = null
  private url: string
  private token: string
  private onMessage?: (msg: WsStreamMessage) => void
  private onConnect?: () => void
  private onDisconnect?: () => void
  private onError?: (error: Event | Error) => void
  private reconnectAttempts = 0
  private maxReconnectAttempts = 5
  private reconnectDelay = 3000
  private messageQueue: string[] = []
  private isConnecting = false

  constructor(options: WsConnectionOptions) {
    this.url = options.url
    this.token = options.token
    this.onMessage = options.onMessage
    this.onConnect = options.onConnect
    this.onDisconnect = options.onDisconnect
    this.onError = options.onError
  }

  connect(): Promise<void> {
    return new Promise((resolve, reject) => {
      if (this.isConnecting) {
        reject(new Error('Already connecting'))
        return
      }

      this.isConnecting = true

      try {
        const wsUrl = `${this.url}?token=${encodeURIComponent(this.token)}`
        this.ws = new WebSocket(wsUrl)

        this.ws.onopen = () => {
          this.isConnecting = false
          this.reconnectAttempts = 0
          this.flushMessageQueue()
          this.onConnect?.()
          resolve()
        }

        this.ws.onmessage = (event) => {
          try {
            const message = JSON.parse(event.data) as WsStreamMessage
            this.onMessage?.(message)
          } catch (error) {
            console.error('Failed to parse WebSocket message:', error)
          }
        }

        this.ws.onclose = () => {
          this.isConnecting = false
          this.onDisconnect?.()
          this.attemptReconnect()
        }

        this.ws.onerror = (error) => {
          this.isConnecting = false
          this.onError?.(error)
          reject(error)
        }
      } catch (error) {
        this.isConnecting = false
        reject(error)
      }
    })
  }

  private attemptReconnect() {
    if (this.reconnectAttempts >= this.maxReconnectAttempts) {
      console.error('Max WebSocket reconnection attempts reached')
      return
    }

    this.reconnectAttempts++
    console.log(`Attempting WebSocket reconnect (${this.reconnectAttempts}/${this.maxReconnectAttempts})`)

    setTimeout(() => {
      this.connect().catch((error) => {
        console.error('WebSocket reconnection failed:', error)
      })
    }, this.reconnectDelay)
  }

  send(data: Record<string, any>) {
    const message = JSON.stringify(data)

    if (this.ws?.readyState === WebSocket.OPEN) {
      this.ws.send(message)
    } else {
      this.messageQueue.push(message)
    }
  }

  private flushMessageQueue() {
    while (this.messageQueue.length > 0 && this.ws?.readyState === WebSocket.OPEN) {
      const message = this.messageQueue.shift()
      if (message) {
        this.ws.send(message)
      }
    }
  }

  disconnect() {
    this.maxReconnectAttempts = 0 // Disable auto-reconnect
    if (this.ws) {
      this.ws.close()
      this.ws = null
    }
  }

  isConnected(): boolean {
    return this.ws?.readyState === WebSocket.OPEN
  }

  subscribe(streamType: string) {
    this.send({
      action: 'subscribe',
      stream: streamType,
    })
  }

  unsubscribe(streamType: string) {
    this.send({
      action: 'unsubscribe',
      stream: streamType,
    })
  }
}

export const createWsClient = (options: WsConnectionOptions) => {
  return new WsClient(options)
}
