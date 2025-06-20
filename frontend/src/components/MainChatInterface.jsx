import React, { useRef, useEffect } from 'react'
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
  Play,
  Pause,
  Square
} from 'lucide-react'
import { useAppStore } from '../store/appStore'

const MainChatInterface = () => {
  const messagesEndRef = useRef(null)
  
  const {
    messages = [],
    inputMessage = '',
    isTyping = false,
    currentPlan = null,
    showPlanDialog = false,
    planExecutionStatus = 'idle',
    executionLogs = [],
    setInputMessage,
    setIsTyping,
    sendMessage,
    setCurrentPlan,
    setShowPlanDialog,
    setPlanExecutionStatus,
    addExecutionLog,
    clearExecutionLogs,
    executePlan,
    logout
  } = useAppStore()

  // メッセージが追加されたら自動スクロール
  useEffect(() => {
    if (messagesEndRef.current) {
      messagesEndRef.current.scrollIntoView({ behavior: 'smooth' })
    }
  }, [messages])

  const handleSendMessage = () => {
    const trimmedMessage = inputMessage?.trim()
    if (!trimmedMessage) return
    
    sendMessage(trimmedMessage)
  }

  const handleInputChange = (e) => {
    const value = e.target.value
    if (inputMessage !== value) {
      setInputMessage(value)
    }
  }

  const handleKeyPress = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSendMessage()
    }
  }

  const handleLogout = () => {
    if (typeof logout === 'function') {
      logout()
    }
  }

  return (
    <div className="flex h-screen bg-gray-50">
      {/* メインチャットエリア */}
      <div className="flex-1 flex flex-col">
        {/* ヘッダー */}
        <div className="bg-white border-b px-6 py-4 flex justify-between items-center">
          <div>
            <h1 className="text-xl font-semibold text-gray-900">Devin AI Clone</h1>
            <p className="text-sm text-gray-500">自律型AIエージェント</p>
          </div>
          <div className="flex items-center space-x-2">
            {/* 設定ボタン */}
            <Button variant="outline" size="sm">
              <Settings className="h-4 w-4" />
            </Button>
            {/* ログアウトボタン */}
            <Button variant="outline" size="sm" onClick={handleLogout}>
              ログアウト
            </Button>
          </div>
        </div>

        {/* チャットメッセージエリア */}
        <ScrollArea className="flex-1 p-6">
          <div className="space-y-4">
            {messages.map((message, index) => (
              <div
                key={index}
                className={`flex ${
                  message.type === 'user' ? 'justify-end' : 'justify-start'
                }`}
              >
                <div
                  className={`max-w-[70%] rounded-lg px-4 py-2 ${
                    message.type === 'user'
                      ? 'bg-blue-500 text-white'
                      : 'bg-white border shadow-sm'
                  }`}
                >
                  <div className="flex items-start space-x-2">
                    {message.type === 'assistant' && (
                      <Bot className="h-5 w-5 mt-0.5 text-gray-500" />
                    )}
                    {message.type === 'user' && (
                      <User className="h-5 w-5 mt-0.5 text-white" />
                    )}
                    <div className="flex-1">
                      <p className="text-sm">{message.content}</p>
                      <span className="text-xs text-gray-500">
                        {new Date(message.timestamp).toLocaleTimeString()}
                      </span>
                    </div>
                  </div>
                </div>
              </div>
            ))}
            
            {/* タイピングインジケーター */}
            {isTyping && (
              <div className="flex justify-start">
                <div className="bg-white border shadow-sm rounded-lg px-4 py-2">
                  <div className="flex items-center space-x-2">
                    <Bot className="h-5 w-5 text-gray-500" />
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
        <div className="bg-white border-t p-4">
          <div className="flex space-x-2">
            <div className="flex-1">
              <Input
                value={inputMessage || ''}
                onChange={handleInputChange}
                onKeyPress={handleKeyPress}
                placeholder="メッセージを入力..."
                disabled={isTyping}
              />
            </div>
            <Button 
              onClick={handleSendMessage}
              disabled={!inputMessage?.trim() || isTyping}
            >
              <Send className="h-4 w-4" />
            </Button>
          </div>
        </div>
      </div>

      {/* サイドパネル（計画実行状況） */}
      <div className="w-80 bg-white border-l">
        <div className="p-4">
          <h2 className="text-lg font-semibold mb-4">実行状況</h2>
          
          {currentPlan && (
            <Card className="mb-4">
              <CardHeader>
                <CardTitle className="text-sm">現在の計画</CardTitle>
              </CardHeader>
              <CardContent>
                <p className="text-sm text-gray-600">{currentPlan}</p>
                <div className="flex items-center space-x-2 mt-2">
                  <Badge variant={planExecutionStatus === 'running' ? 'default' : 'secondary'}>
                    {planExecutionStatus}
                  </Badge>
                  {planExecutionStatus === 'running' && (
                    <Button size="sm" variant="outline">
                      <Pause className="h-3 w-3" />
                    </Button>
                  )}
                </div>
              </CardContent>
            </Card>
          )}

          {/* 実行ログ */}
          <div>
            <h3 className="text-sm font-medium mb-2">実行ログ</h3>
            <ScrollArea className="h-64 border rounded p-2">
              <div className="space-y-1">
                {executionLogs.map((log, index) => (
                  <div key={index} className="text-xs text-gray-600">
                    <span className="text-gray-400">{log.timestamp}</span> {log.message}
                  </div>
                ))}
              </div>
            </ScrollArea>
          </div>
        </div>
      </div>
    </div>
  )
}

export default MainChatInterface

