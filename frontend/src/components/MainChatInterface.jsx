import React, { useEffect, useRef } from 'react'
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
import PlanReviewDialog from '@/components/PlanReviewDialog'

const MainChatInterface = () => {
  const messagesEndRef = useRef(null)
  const inputRef = useRef(null)
  
  const {
    user,
    messages,
    inputMessage,
    isTyping,
    currentPlan,
    showPlanDialog,
    planExecutionStatus,
    executionLogs,
    systemStatus,
    actions
  } = useAppStore(state => ({
    user: state.user,
    messages: state.messages,
    inputMessage: state.inputMessage,
    isTyping: state.isTyping,
    currentPlan: state.currentPlan,
    showPlanDialog: state.showPlanDialog,
    planExecutionStatus: state.planExecutionStatus,
    executionLogs: state.executionLogs,
    systemStatus: state.systemStatus,
    actions: state.actions
  }))
  
  // メッセージが追加されたら自動スクロール
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, isTyping])
  
  // 入力フィールドにフォーカス
  useEffect(() => {
    inputRef.current?.focus()
  }, [])
  
  const handleSendMessage = async (e) => {
    e.preventDefault()
    
    if (!(inputMessage || '').trim()) return
    
    const message = (inputMessage || '').trim()
    actions.setInputMessage('')
    
    await actions.sendMessage(message)
  }
  
  const handleKeyPress = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSendMessage(e)
    }
  }
  
  const getMessageIcon = (type) => {
    switch (type) {
      case 'user':
        return <User className="w-4 h-4" />
      case 'assistant':
        return <Bot className="w-4 h-4" />
      case 'system':
        return <AlertCircle className="w-4 h-4" />
      default:
        return <Bot className="w-4 h-4" />
    }
  }
  
  const getMessageBgColor = (type) => {
    switch (type) {
      case 'user':
        return 'bg-blue-50 border-blue-200'
      case 'assistant':
        return 'bg-green-50 border-green-200'
      case 'system':
        return 'bg-yellow-50 border-yellow-200'
      default:
        return 'bg-gray-50 border-gray-200'
    }
  }
  
  const getExecutionStatusBadge = () => {
    switch (planExecutionStatus) {
      case 'running':
        return <Badge variant="default" className="bg-blue-500"><Clock className="w-3 h-3 mr-1" />実行中</Badge>
      case 'completed':
        return <Badge variant="default" className="bg-green-500"><CheckCircle className="w-3 h-3 mr-1" />完了</Badge>
      case 'error':
        return <Badge variant="destructive"><AlertCircle className="w-3 h-3 mr-1" />エラー</Badge>
      default:
        return null
    }
  }
  
  return (
    <div className="flex flex-col h-screen bg-gray-50">
      {/* ヘッダー */}
      <header className="bg-white border-b border-gray-200 px-4 py-3">
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-3">
            <div className="w-8 h-8 bg-blue-600 rounded-lg flex items-center justify-center">
              <Bot className="w-5 h-5 text-white" />
            </div>
            <div>
              <h1 className="text-lg font-semibold text-gray-900">Devin AI Clone</h1>
              <p className="text-sm text-gray-500">自律型AIエージェント</p>
            </div>
          </div>
          
          <div className="flex items-center space-x-3">
            {/* システム状態インジケーター */}
            <div className="flex items-center space-x-2">
              {systemStatus.backend_connected ? (
                <Wifi className="w-4 h-4 text-green-500" title="バックエンド接続中" />
              ) : (
                <WifiOff className="w-4 h-4 text-red-500" title="バックエンド未接続" />
              )}
            </div>
            
            {/* 実行ステータス */}
            {getExecutionStatusBadge()}
            
            {/* ユーザー情報 */}
            <div className="flex items-center space-x-2 text-sm text-gray-600">
              <User className="w-4 h-4" />
              <span>{user?.username}</span>
              <Badge variant="outline">{user?.role}</Badge>
            </div>
            
            {/* 設定ボタン */}
            <Button
              variant="outline"
              size="sm"
              onClick={() => actions.setCurrentView('settings')}
            >
              <Settings className="w-4 h-4 mr-2" />
              設定
            </Button>
            
            {/* ログアウトボタン */}
            <Button
              variant="outline"
              size="sm"
              onClick={actions.logout}
            >
              <LogOut className="w-4 h-4 mr-2" />
              ログアウト
            </Button>
          </div>
        </div>
      </header>
      
      {/* メインコンテンツ */}
      <div className="flex-1 flex overflow-hidden">
        {/* チャットエリア */}
        <div className="flex-1 flex flex-col">
          {/* メッセージ一覧 */}
          <ScrollArea className="flex-1 p-4">
            <div className="space-y-4 max-w-4xl mx-auto">
              {messages.map((message) => (
                <div
                  key={message.id}
                  className={`flex items-start space-x-3 p-4 rounded-lg border ${getMessageBgColor(message.type)}`}
                >
                  <div className="flex-shrink-0 w-8 h-8 rounded-full bg-white border flex items-center justify-center">
                    {getMessageIcon(message.type)}
                  </div>
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center space-x-2 mb-1">
                      <span className="text-sm font-medium text-gray-900">
                        {message.type === 'user' ? user?.username : 
                         message.type === 'assistant' ? 'Devin AI' : 'システム'}
                      </span>
                      <span className="text-xs text-gray-500">
                        {message.timestamp.toLocaleTimeString()}
                      </span>
                    </div>
                    <div className="text-gray-700 whitespace-pre-wrap">
                      {message.content}
                    </div>
                  </div>
                </div>
              ))}
              
              {/* タイピングインジケーター */}
              {isTyping && (
                <div className="flex items-start space-x-3 p-4 rounded-lg border bg-green-50 border-green-200">
                  <div className="flex-shrink-0 w-8 h-8 rounded-full bg-white border flex items-center justify-center">
                    <Bot className="w-4 h-4" />
                  </div>
                  <div className="flex-1">
                    <div className="flex items-center space-x-2 mb-1">
                      <span className="text-sm font-medium text-gray-900">Devin AI</span>
                    </div>
                    <div className="flex space-x-1">
                      <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce"></div>
                      <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '0.1s' }}></div>
                      <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '0.2s' }}></div>
                    </div>
                  </div>
                </div>
              )}
              
              <div ref={messagesEndRef} />
            </div>
          </ScrollArea>
          
          {/* 入力エリア */}
          <div className="border-t border-gray-200 bg-white p-4">
            <form onSubmit={handleSendMessage} className="max-w-4xl mx-auto">
              <div className="flex space-x-3">
                <Input
                  ref={inputRef}
                  value={inputMessage}
                  onChange={(e) => actions.setInputMessage(e.target.value)}
                  onKeyPress={handleKeyPress}
                  placeholder="メッセージを入力してください..."
                  disabled={isTyping}
                  className="flex-1"
                />
                <Button 
                  type="submit" 
                  disabled={!inputMessage.trim() || isTyping}
                  size="sm"
                >
                  <Send className="w-4 h-4" />
                </Button>
              </div>
            </form>
          </div>
        </div>
        
        {/* サイドパネル（実行ログ） */}
        {(planExecutionStatus !== 'idle' || executionLogs.length > 0) && (
          <>
            <Separator orientation="vertical" />
            <div className="w-80 bg-white border-l border-gray-200">
              <Card className="h-full rounded-none border-0">
                <CardHeader className="pb-3">
                  <CardTitle className="text-sm flex items-center space-x-2">
                    <Clock className="w-4 h-4" />
                    <span>実行ログ</span>
                    {getExecutionStatusBadge()}
                  </CardTitle>
                </CardHeader>
                <CardContent className="pt-0">
                  <ScrollArea className="h-96">
                    <div className="space-y-2">
                      {executionLogs.map((log, index) => (
                        <div key={index} className="text-xs text-gray-600 font-mono bg-gray-50 p-2 rounded">
                          {log}
                        </div>
                      ))}
                      {executionLogs.length === 0 && (
                        <div className="text-xs text-gray-400 text-center py-4">
                          実行ログはありません
                        </div>
                      )}
                    </div>
                  </ScrollArea>
                </CardContent>
              </Card>
            </div>
          </>
        )}
      </div>
      
      {/* 計画レビューダイアログ */}
      <PlanReviewDialog
        open={showPlanDialog}
        onOpenChange={actions.setShowPlanDialog}
        plan={currentPlan}
        onApprove={async () => {
          if (currentPlan) {
            const success = await actions.executePlan(currentPlan.plan_id)
            if (success) {
              actions.setShowPlanDialog(false)
              actions.addMessage({
                type: 'system',
                content: '計画が承認されました。実行を開始します。'
              })
            }
          }
        }}
        onReject={() => {
          actions.setShowPlanDialog(false)
          actions.setCurrentPlan(null)
          actions.addMessage({
            type: 'system',
            content: '計画が拒否されました。'
          })
        }}
      />
    </div>
  )
}

export default MainChatInterface

