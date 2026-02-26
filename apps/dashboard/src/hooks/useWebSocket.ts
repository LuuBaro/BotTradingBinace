import { useEffect, useRef } from 'react'
import { useAuthStore, useDashboardStore, useEventsStore } from '../store'
import { createWsClient, WsClient, WsStreamMessage } from '../api/websocket'
import { getApiBaseUrl } from '../api/client'

export const useWebSocket = () => {
    const { token } = useAuthStore()
    const { setBotStatus, setPositions, setOrders, setDecisions, updatePosition, updateOrder } = useDashboardStore()
    const { addEvent } = useEventsStore()
    const wsClientRef = useRef<WsClient | null>(null)

    useEffect(() => {
        if (!token) return

        // Convert http(s) to ws(s)
        const baseUrl = getApiBaseUrl()
        const wsUrl = baseUrl.replace(/^http/, 'ws').replace(/\/api\/?$/, '/api/ws/stream')

        console.log('🔌 Connecting to WebSocket:', wsUrl)

        const client = createWsClient({
            url: wsUrl,
            token: token,
            onConnect: () => {
                console.log('✅ WebSocket Connected')
                // Subscribe to all relevant streams
                client.subscribe('status')
                client.subscribe('positions')
                client.subscribe('orders')
                client.subscribe('decision')
                client.subscribe('events')
            },
            onDisconnect: () => {
                console.log('❌ WebSocket Disconnected')
            },
            onMessage: (msg: WsStreamMessage) => {
                console.log('📩 WS Message:', msg.type, msg.data)

                switch (msg.type) {
                    case 'status':
                        setBotStatus(msg.data as any)
                        break
                    case 'position_change':
                        // If it's a single update, we might need a more granular store update
                        // For now, let's assume it might be full list or handled by updatePosition
                        if (Array.isArray(msg.data)) {
                            setPositions(msg.data)
                        } else {
                            updatePosition(msg.data as any)
                        }
                        break
                    case 'order_change':
                        if (Array.isArray(msg.data)) {
                            setOrders(msg.data)
                        } else {
                            updateOrder(msg.data as any)
                        }
                        break
                    case 'decision':
                        // Logic to append to decisions
                        setDecisions(Array.isArray(msg.data) ? msg.data : [msg.data as any])
                        break
                    case 'event':
                        addEvent(msg.data as any)
                        break
                }
            },
            onError: (err) => {
                console.error('⚠️ WebSocket Error:', err)
            }
        })

        client.connect()
        wsClientRef.current = client

        return () => {
            client.disconnect()
            wsClientRef.current = null
        }
    }, [token])

    return wsClientRef.current
}
