import React, { useEffect, useRef, useMemo } from 'react'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { ScrollArea } from '@/components/ui/scroll-area'
import { Badge } from '@/components/ui/badge'
import { Separator } from '@/components/ui/separator'
import { 
  Settings, 
  Send, 
  User, 
  Bot, 
  AlertCircle,
  CheckCircle,
  Clock,
  LogOut,
  Wifi,
  WifiOff
} from 'lucide-react'
import { useAppStore } from '@/store/appStore'

const MainChatInterface = () => {
  const messagesEndRef = useRef(null)
  const inputRef = useRef(null)
  
  // Zustandストアから必要な状態を取得（useMemoでキャッシュ）
  const storeData = useMemo(() => {
    return useAppStore.getState()
  }, [])
  
  const {
    user,
    messages = [],
    inputMessage = '',
    isTyping = false,
    currentPlan = null,
    showPlanDialog = false,
    planExecutionStatus = 'idle',
    executionLogs = [],
    systemStatus = { backend_connected: false },
    actions
  } = storeData

  // メッセージが更新されたときに最下部にスクロール
  useEffect(() => {
    if (messagesEndRef.current) {
      messagesEndRef.current.scrollIntoView({ behavior: 'smooth' })
    }
  }, [messages])

  // バックエンドヘルスチェック
  useEffect(() => {
    const checkHealth = async () => {
      if (actions?.checkBackendHealth) {
        await actions.checkBackendHealth()
      }
    }
    
    checkHealth()
    const interval = setInterval(checkHealth, 30000) // 30秒ごと
    
    return () => clearInterval(interval)
  }, [actions])

  const handleSendMessage = async () => {
    if (!inputMessage?.trim() || isTyping) return

    const message = inputMessage.trim()
    
    // メッセージをクリア
    if (actions?.setInputMessage) {
      actions.setInputMessage('')
    }

    // ユーザーメッセージを追加
    if (actions?.addMessage) {
      actions.addMessage({
        id: Date.now(),
        type: 'user',
        content: message,
        timestamp: new Date().toISOString()
      })
    }

    // タイピング状態を開始
    if (actions?.setIsTyping) {
      actions.setIsTyping(true)
    }

    try {
      // ここでバックエンドAPIを呼び出す
      // 現在はモック応答
      setTimeout(() => {
        if (actions?.addMessage) {
          actions.addMessage({
            id: Date.now() + 1,
            type: 'assistant',
            content: `受信したメッセージ: "${message}"\n\n現在、AIエージェント機能は開発中です。近日中に完全な機能を提供予定です。`,
            timestamp: new Date().toISOString()
          })
        }
        
        if (actions?.setIsTyping) {
          actions.setIsTyping(false)
        }
      }, 1500)
    } catch (error) {
      console.error('メッセージ送信エラー:', error)
      if (actions?.setIsTyping) {
        actions.setIsTyping(false)
      }
    }
  }

  const handleKeyPress = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSendMessage()
    }
  }

  const handleLogout = () => {
    if (actions?.setAuthenticated) {
      actions.setAuthenticated(false)
    }
  }

  const getStatusColor = (status) => {
    switch (status) {
      case 'running': return 'bg-green-500'
      case 'error': return 'bg-red-500'
      case 'warning': return 'bg-yellow-500'
      default: return 'bg-gray-500'
    }
  }

  const formatTimestamp = (timestamp) => {
    try {
      return new Date(timestamp).toLocaleTimeString('ja-JP', {
        hour: '2-digit',
        minute: '2-digit'
      })
    } catch {
      return ''
    }
  }

  return (
    <div className="flex h-screen bg-gray-50">
      {/* サイドバー */}
      <div className="w-80 bg-white border-r border-gray-200 flex flex-col">
        {/* ヘッダー */}
        <div className="p-4 border-b border-gray-200">
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-3">
              <div className="w-8 h-8 bg-blue-600 rounded-lg flex items-center justify-center">
                <Bot className="w-5 h-5 text-white" />
              </div>
              <div>
                <h1 className="font-semibold text-gray-900">Devin AI Clone</h1>
                <p className="text-sm text-gray-500">自律型AIエージェント</p>
              </div>
            </div>
            <Button
              variant="ghost"
              size="sm"
              onClick={handleLogout}
              className="text-gray-500 hover:text-gray-700"
            >
              <LogOut className="w-4 h-4" />
            </Button>
          </div>
        </div>

        {/* ユーザー情報 */}
        <div className="p-4 border-b border-gray-200">
          <div className="flex items-center space-x-3">
            <div className="w-10 h-10 bg-gray-200 rounded-full flex items-center justify-center">
              <User className="w-5 h-5 text-gray-600" />
            </div>
            <div>
              <p className="font-medium text-gray-900">{user?.username || 'ユーザー'}</p>
              <p className="text-sm text-gray-500">{user?.role || 'ゲスト'}</p>
            </div>
          </div>
        </div>

        {/* システム状態 */}
        <div className="p-4 border-b border-gray-200">
          <h3 className="text-sm font-medium text-gray-900 mb-3">システム状態</h3>
          <div className="space-y-2">
            <div className="flex items-center justify-between">
              <div className="flex items-center space-x-2">
                {systemStatus?.backend_connected ? (
                  <Wifi className="w-4 h-4 text-green-500" />
                ) : (
                  <WifiOff className="w-4 h-4 text-red-500" />
                )}
                <span className="text-sm text-gray-600">バックエンド</span>
              </div>
              <Badge variant={systemStatus?.backend_connected ? "default" : "destructive"}>
                {systemStatus?.backend_connected ? '接続中' : '切断'}
              </Badge>
            </div>
          </div>
        </div>

        {/* プラン実行状態 */}
        {currentPlan && (
          <div className="p-4 border-b border-gray-200">
            <h3 className="text-sm font-medium text-gray-900 mb-3">実行中のプラン</h3>
            <Card>
              <CardHeader className="pb-2">
                <CardTitle className="text-sm">{currentPlan.title}</CardTitle>
              </CardHeader>
              <CardContent className="pt-0">
                <div className="flex items-center space-x-2">
                  <div className={`w-2 h-2 rounded-full ${getStatusColor(planExecutionStatus)}`}></div>
                  <span className="text-xs text-gray-600 capitalize">{planExecutionStatus}</span>
                </div>
              </CardContent>
            </Card>
          </div>
        )}

        {/* 実行ログ */}
        {executionLogs.length > 0 && (
          <div className="flex-1 p-4">
            <h3 className="text-sm font-medium text-gray-900 mb-3">実行ログ</h3>
            <ScrollArea className="h-32">
              <div className="space-y-1">
                {executionLogs.slice(-10).map((log, index) => (
                  <div key={index} className="text-xs text-gray-600 p-2 bg-gray-50 rounded">
                    <span className="text-gray-400">{formatTimestamp(log.timestamp)}</span>
                    <span className="ml-2">{log.message}</span>
                  </div>
                ))}
              </div>
            </ScrollArea>
          </div>
        )}
      </div>

      {/* メインチャットエリア */}
      <div className="flex-1 flex flex-col">
        {/* チャットヘッダー */}
        <div className="p-4 bg-white border-b border-gray-200">
          <div className="flex items-center justify-between">
            <h2 className="text-lg font-semibold text-gray-900">チャット</h2>
            <div className="flex items-center space-x-2">
              <Button variant="ghost" size="sm">
                <Settings className="w-4 h-4" />
              </Button>
            </div>
          </div>
        </div>

        {/* メッセージエリア */}
        <ScrollArea className="flex-1 p-4">
          <div className="space-y-4">
            {messages.length === 0 ? (
              <div className="text-center py-12">
                <Bot className="w-12 h-12 text-gray-400 mx-auto mb-4" />
                <h3 className="text-lg font-medium text-gray-900 mb-2">
                  Devin AI Cloneへようこそ
                </h3>
                <p className="text-gray-500 max-w-md mx-auto">
                  自律型AIエージェントとして、プログラミング、問題解決、タスク実行をサポートします。
                  何でもお気軽にお聞きください。
                </p>
              </div>
            ) : (
              messages.map((message) => (
                <div
                  key={message.id}
                  className={`flex ${message.type === 'user' ? 'justify-end' : 'justify-start'}`}
                >
                  <div
                    className={`max-w-xs lg:max-w-md px-4 py-2 rounded-lg ${
                      message.type === 'user'
                        ? 'bg-blue-600 text-white'
                        : 'bg-white border border-gray-200 text-gray-900'
                    }`}
                  >
                    <div className="flex items-start space-x-2">
                      {message.type === 'assistant' && (
                        <Bot className="w-4 h-4 mt-0.5 text-gray-500" />
                      )}
                      <div className="flex-1">
                        <p className="text-sm whitespace-pre-wrap">{message.content}</p>
                        <p className={`text-xs mt-1 ${
                          message.type === 'user' ? 'text-blue-100' : 'text-gray-500'
                        }`}>
                          {formatTimestamp(message.timestamp)}
                        </p>
                      </div>
                    </div>
                  </div>
                </div>
              ))
            )}
            
            {/* タイピングインジケーター */}
            {isTyping && (
              <div className="flex justify-start">
                <div className="max-w-xs lg:max-w-md px-4 py-2 rounded-lg bg-white border border-gray-200">
                  <div className="flex items-center space-x-2">
                    <Bot className="w-4 h-4 text-gray-500" />
                    <div className="flex space-x-1">
                      <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce"></div>
                      <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{animationDelay: '0.1s'}}></div>
                      <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{animationDelay: '0.2s'}}></div>
                    </div>
                  </div>
                </div>
              </div>
            )}
            
            <div ref={messagesEndRef} />
          </div>
        </ScrollArea>

        {/* 入力エリア */}
        <div className="p-4 bg-white border-t border-gray-200">
          <div className="flex space-x-2">
            <Input
              ref={inputRef}
              value={inputMessage}
              onChange={(e) => actions?.setInputMessage?.(e.target.value)}
              onKeyPress={handleKeyPress}
              placeholder="メッセージを入力..."
              disabled={isTyping}
              className="flex-1"
            />
            <Button
              onClick={handleSendMessage}
              disabled={!inputMessage?.trim() || isTyping}
              size="sm"
            >
              <Send className="w-4 h-4" />
            </Button>
          </div>
        </div>
      </div>
    </div>
  )
}

export default MainChatInterface

