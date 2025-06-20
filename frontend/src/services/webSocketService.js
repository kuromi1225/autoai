import React, { useState, useEffect, useRef } from 'react'
import { io } from 'socket.io-client'

class WebSocketService {
  constructor() {
    this.socket = null
    this.isConnected = false
    this.reconnectAttempts = 0
    this.maxReconnectAttempts = 5
    this.reconnectDelay = 1000
    this.eventListeners = new Map()
    this.messageQueue = []
  }

  connect(token, userId) {
    if (this.socket) {
      this.disconnect()
    }

    const socketUrl = process.env.NODE_ENV === 'production' 
      ? window.location.origin 
      : 'http://localhost:5000'

    this.socket = io(socketUrl, {
      auth: {
        token: token,
        user_id: userId
      },
      transports: ['websocket', 'polling'],
      timeout: 20000,
      forceNew: true
    })

    this.setupEventHandlers()
  }

  setupEventHandlers() {
    if (!this.socket) return

    this.socket.on('connect', () => {
      console.log('WebSocket connected')
      this.isConnected = true
      this.reconnectAttempts = 0
      
      // キューに溜まったメッセージを送信
      this.flushMessageQueue()
      
      // 接続イベントを通知
      this.emit('connection_status', { connected: true })
    })

    this.socket.on('disconnect', (reason) => {
      console.log('WebSocket disconnected:', reason)
      this.isConnected = false
      this.emit('connection_status', { connected: false, reason })
      
      // 自動再接続を試行
      if (reason === 'io server disconnect') {
        // サーバーが切断した場合は手動で再接続
        this.attemptReconnect()
      }
    })

    this.socket.on('connect_error', (error) => {
      console.error('WebSocket connection error:', error)
      this.isConnected = false
      this.emit('connection_error', { error: error.message })
      this.attemptReconnect()
    })

    this.socket.on('connection_established', (data) => {
      console.log('Connection established:', data)
      this.emit('connection_established', data)
    })

    // チャット関連イベント
    this.socket.on('chat_response_chunk', (data) => {
      this.emit('chat_response_chunk', data)
    })

    // 実行関連イベント
    this.socket.on('execution_progress', (data) => {
      this.emit('execution_progress', data)
    })

    this.socket.on('execution_log', (data) => {
      this.emit('execution_log', data)
    })

    this.socket.on('tool_output', (data) => {
      this.emit('tool_output', data)
    })

    this.socket.on('stream_started', (data) => {
      this.emit('stream_started', data)
    })

    this.socket.on('stream_ended', (data) => {
      this.emit('stream_ended', data)
    })

    // 通知関連イベント
    this.socket.on('notification', (data) => {
      this.emit('notification', data)
    })

    this.socket.on('system_message', (data) => {
      this.emit('system_message', data)
    })

    // Ping/Pong for keepalive
    this.socket.on('pong', (data) => {
      console.log('Received pong:', data)
    })

    // エラーハンドリング
    this.socket.on('error', (error) => {
      console.error('WebSocket error:', error)
      this.emit('error', { error })
    })
  }

  attemptReconnect() {
    if (this.reconnectAttempts >= this.maxReconnectAttempts) {
      console.log('Max reconnection attempts reached')
      this.emit('reconnect_failed', { attempts: this.reconnectAttempts })
      return
    }

    this.reconnectAttempts++
    const delay = this.reconnectDelay * Math.pow(2, this.reconnectAttempts - 1)
    
    console.log(`Attempting to reconnect (${this.reconnectAttempts}/${this.maxReconnectAttempts}) in ${delay}ms`)
    
    setTimeout(() => {
      if (this.socket && !this.isConnected) {
        this.socket.connect()
      }
    }, delay)
  }

  disconnect() {
    if (this.socket) {
      this.socket.disconnect()
      this.socket = null
    }
    this.isConnected = false
    this.reconnectAttempts = 0
  }

  // イベントリスナー管理
  on(event, callback) {
    if (!this.eventListeners.has(event)) {
      this.eventListeners.set(event, [])
    }
    this.eventListeners.get(event).push(callback)
  }

  off(event, callback) {
    if (this.eventListeners.has(event)) {
      const listeners = this.eventListeners.get(event)
      const index = listeners.indexOf(callback)
      if (index > -1) {
        listeners.splice(index, 1)
      }
    }
  }

  emit(event, data) {
    if (this.eventListeners.has(event)) {
      this.eventListeners.get(event).forEach(callback => {
        try {
          callback(data)
        } catch (error) {
          console.error(`Error in event listener for ${event}:`, error)
        }
      })
    }
  }

  // メッセージ送信
  send(event, data) {
    if (this.isConnected && this.socket) {
      this.socket.emit(event, data)
    } else {
      // 接続されていない場合はキューに追加
      this.messageQueue.push({ event, data })
    }
  }

  flushMessageQueue() {
    while (this.messageQueue.length > 0) {
      const { event, data } = this.messageQueue.shift()
      this.socket.emit(event, data)
    }
  }

  // 実行セッション管理
  joinExecutionRoom(executionId) {
    this.send('join_execution_room', { execution_id: executionId })
  }

  leaveExecutionRoom(executionId) {
    this.send('leave_execution_room', { execution_id: executionId })
  }

  // Keepalive
  startPing() {
    this.pingInterval = setInterval(() => {
      if (this.isConnected) {
        this.send('ping', { timestamp: new Date().toISOString() })
      }
    }, 30000) // 30秒間隔
  }

  stopPing() {
    if (this.pingInterval) {
      clearInterval(this.pingInterval)
      this.pingInterval = null
    }
  }

  // 接続状態取得
  getConnectionStatus() {
    return {
      connected: this.isConnected,
      reconnectAttempts: this.reconnectAttempts,
      queuedMessages: this.messageQueue.length
    }
  }
}

// シングルトンインスタンス
const webSocketService = new WebSocketService()

// React Hook for WebSocket
export const useWebSocket = () => {
  const [connectionStatus, setConnectionStatus] = useState({
    connected: false,
    reconnectAttempts: 0,
    queuedMessages: 0
  })
  const [notifications, setNotifications] = useState([])
  const [executionLogs, setExecutionLogs] = useState([])
  const [executionProgress, setExecutionProgress] = useState({})
  const [chatResponseChunks, setChatResponseChunks] = useState([])

  useEffect(() => {
    // 接続状態の監視
    const handleConnectionStatus = (status) => {
      setConnectionStatus(prev => ({ ...prev, ...status }))
    }

    const handleNotification = (notification) => {
      setNotifications(prev => [...prev, {
        ...notification,
        id: Date.now() + Math.random()
      }])
    }

    const handleExecutionLog = (logData) => {
      setExecutionLogs(prev => [...prev, {
        ...logData.log,
        execution_id: logData.execution_id,
        id: Date.now() + Math.random()
      }])
    }

    const handleExecutionProgress = (progressData) => {
      setExecutionProgress(prev => ({
        ...prev,
        [progressData.execution_id]: progressData.progress
      }))
    }

    const handleChatResponseChunk = (chunkData) => {
      setChatResponseChunks(prev => [...prev, chunkData])
    }

    // イベントリスナーを登録
    webSocketService.on('connection_status', handleConnectionStatus)
    webSocketService.on('notification', handleNotification)
    webSocketService.on('execution_log', handleExecutionLog)
    webSocketService.on('execution_progress', handleExecutionProgress)
    webSocketService.on('chat_response_chunk', handleChatResponseChunk)

    // クリーンアップ
    return () => {
      webSocketService.off('connection_status', handleConnectionStatus)
      webSocketService.off('notification', handleNotification)
      webSocketService.off('execution_log', handleExecutionLog)
      webSocketService.off('execution_progress', handleExecutionProgress)
      webSocketService.off('chat_response_chunk', handleChatResponseChunk)
    }
  }, [])

  const connect = (token, userId) => {
    webSocketService.connect(token, userId)
    webSocketService.startPing()
  }

  const disconnect = () => {
    webSocketService.stopPing()
    webSocketService.disconnect()
  }

  const joinExecutionRoom = (executionId) => {
    webSocketService.joinExecutionRoom(executionId)
  }

  const leaveExecutionRoom = (executionId) => {
    webSocketService.leaveExecutionRoom(executionId)
  }

  const clearNotifications = () => {
    setNotifications([])
  }

  const clearExecutionLogs = () => {
    setExecutionLogs([])
  }

  const clearChatResponseChunks = () => {
    setChatResponseChunks([])
  }

  return {
    connectionStatus,
    notifications,
    executionLogs,
    executionProgress,
    chatResponseChunks,
    connect,
    disconnect,
    joinExecutionRoom,
    leaveExecutionRoom,
    clearNotifications,
    clearExecutionLogs,
    clearChatResponseChunks,
    webSocketService
  }
}

// React Component for real-time notifications
export const NotificationCenter = () => {
  const { notifications, clearNotifications } = useWebSocket()
  const [isVisible, setIsVisible] = useState(false)

  useEffect(() => {
    if (notifications.length > 0) {
      setIsVisible(true)
    }
  }, [notifications])

  const getNotificationIcon = (type) => {
    switch (type) {
      case 'success':
        return '✅'
      case 'error':
        return '❌'
      case 'warning':
        return '⚠️'
      case 'info':
      default:
        return 'ℹ️'
    }
  }

  const getNotificationColor = (type) => {
    switch (type) {
      case 'success':
        return 'bg-green-100 border-green-500 text-green-800'
      case 'error':
        return 'bg-red-100 border-red-500 text-red-800'
      case 'warning':
        return 'bg-yellow-100 border-yellow-500 text-yellow-800'
      case 'info':
      default:
        return 'bg-blue-100 border-blue-500 text-blue-800'
    }
  }

  if (!isVisible || notifications.length === 0) {
    return null
  }

  return (
    <div className="fixed top-4 right-4 z-50 space-y-2 max-w-sm">
      {notifications.slice(-5).map((notification) => (
        <div
          key={notification.id}
          className={`p-4 border-l-4 rounded-lg shadow-lg ${getNotificationColor(notification.type)}`}
        >
          <div className="flex items-start">
            <span className="text-lg mr-3">{getNotificationIcon(notification.type)}</span>
            <div className="flex-1">
              <p className="font-medium">{notification.message}</p>
              {notification.data && (
                <p className="text-sm mt-1 opacity-75">
                  {JSON.stringify(notification.data, null, 2)}
                </p>
              )}
              <p className="text-xs mt-2 opacity-60">
                {new Date(notification.timestamp).toLocaleTimeString()}
              </p>
            </div>
            <button
              onClick={() => {
                // 個別の通知を削除する機能は簡略化のため省略
                clearNotifications()
              }}
              className="ml-2 text-lg opacity-60 hover:opacity-100"
            >
              ×
            </button>
          </div>
        </div>
      ))}
      
      {notifications.length > 5 && (
        <div className="text-center">
          <button
            onClick={clearNotifications}
            className="text-sm text-blue-600 hover:text-blue-800"
          >
            すべてクリア ({notifications.length}件)
          </button>
        </div>
      )}
    </div>
  )
}

// React Component for connection status
export const ConnectionStatus = () => {
  const { connectionStatus } = useWebSocket()

  return (
    <div className="flex items-center space-x-2">
      <div className={`w-3 h-3 rounded-full ${
        connectionStatus.connected ? 'bg-green-500' : 'bg-red-500'
      }`} />
      <span className="text-sm text-gray-600">
        {connectionStatus.connected ? '接続中' : '切断中'}
        {connectionStatus.reconnectAttempts > 0 && (
          <span className="ml-1">
            (再接続試行: {connectionStatus.reconnectAttempts})
          </span>
        )}
      </span>
    </div>
  )
}

export default webSocketService

