import React, { useState, useRef, useEffect } from 'react'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { ScrollArea } from '@/components/ui/scroll-area'
import { Badge } from '@/components/ui/badge'
import { Separator } from '@/components/ui/separator'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { Progress } from '@/components/ui/progress'
import { 
  Settings, 
  Send, 
  User, 
  Bot,
  Play,
  Pause,
  Square,
  FileText,
  Code,
  Globe,
  Database,
  Image,
  Mail,
  Terminal,
  Folder,
  Download,
  Upload,
  Eye,
  Edit,
  Trash2,
  Plus,
  Search,
  Filter,
  RefreshCw,
  CheckCircle,
  XCircle,
  Clock,
  AlertCircle
} from 'lucide-react'
import { useAppStore } from '../store/appStore'

const MainChatInterface = () => {
  const messagesEndRef = useRef(null)
  const [activeTab, setActiveTab] = useState('chat')
  const [selectedTool, setSelectedTool] = useState(null)
  const [toolParameters, setToolParameters] = useState({})
  
  const {
    messages = [],
    inputMessage = '',
    isTyping = false,
    currentPlan = null,
    showPlanDialog = false,
    planExecutionStatus = 'idle',
    executionLogs = [],
    availableTools = [],
    workspaceFiles = [],
    executionHistory = [],
    setInputMessage,
    setIsTyping,
    sendMessage,
    setCurrentPlan,
    setShowPlanDialog,
    setPlanExecutionStatus,
    addExecutionLog,
    clearExecutionLogs,
    executePlan,
    executeToolDirectly,
    loadWorkspaceFiles,
    loadExecutionHistory,
    logout
  } = useAppStore()

  // メッセージが追加されたら自動スクロール
  useEffect(() => {
    if (messagesEndRef.current) {
      messagesEndRef.current.scrollIntoView({ behavior: 'smooth' })
    }
  }, [messages])

  // 初期データ読み込み
  useEffect(() => {
    loadWorkspaceFiles()
    loadExecutionHistory()
  }, [])

  const handleSendMessage = () => {
    const trimmedMessage = inputMessage?.trim()
    if (trimmedMessage) {
      sendMessage(trimmedMessage)
      setInputMessage('')
    }
  }

  const handleKeyPress = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSendMessage()
    }
  }

  const handleExecutePlan = () => {
    if (currentPlan) {
      executePlan(currentPlan)
    }
  }

  const handleToolExecution = async () => {
    if (selectedTool) {
      await executeToolDirectly(selectedTool, toolParameters)
      setSelectedTool(null)
      setToolParameters({})
    }
  }

  const getStatusIcon = (status) => {
    switch (status) {
      case 'completed':
        return <CheckCircle className="h-4 w-4 text-green-500" />
      case 'failed':
        return <XCircle className="h-4 w-4 text-red-500" />
      case 'running':
        return <RefreshCw className="h-4 w-4 text-blue-500 animate-spin" />
      case 'pending':
        return <Clock className="h-4 w-4 text-yellow-500" />
      default:
        return <AlertCircle className="h-4 w-4 text-gray-500" />
    }
  }

  const getToolIcon = (category) => {
    switch (category) {
      case 'file':
        return <FileText className="h-4 w-4" />
      case 'code':
        return <Code className="h-4 w-4" />
      case 'browser':
        return <Globe className="h-4 w-4" />
      case 'data':
        return <Database className="h-4 w-4" />
      case 'media':
        return <Image className="h-4 w-4" />
      case 'communication':
        return <Mail className="h-4 w-4" />
      case 'api':
        return <Terminal className="h-4 w-4" />
      default:
        return <Settings className="h-4 w-4" />
    }
  }

  return (
    <div className="flex h-screen bg-gray-50">
      {/* メインコンテンツエリア */}
      <div className="flex-1 flex flex-col">
        {/* ヘッダー */}
        <div className="bg-white border-b border-gray-200 p-4">
          <div className="flex items-center justify-between">
            <h1 className="text-2xl font-bold text-gray-900">AI Agent Dashboard</h1>
            <div className="flex items-center space-x-4">
              <Badge variant={planExecutionStatus === 'running' ? 'default' : 'secondary'}>
                {planExecutionStatus === 'running' ? '実行中' : 'アイドル'}
              </Badge>
              <Button variant="outline" onClick={logout}>
                ログアウト
              </Button>
            </div>
          </div>
        </div>

        {/* タブナビゲーション */}
        <Tabs value={activeTab} onValueChange={setActiveTab} className="flex-1 flex flex-col">
          <TabsList className="grid w-full grid-cols-5 bg-white border-b">
            <TabsTrigger value="chat">チャット</TabsTrigger>
            <TabsTrigger value="tools">ツール</TabsTrigger>
            <TabsTrigger value="files">ファイル</TabsTrigger>
            <TabsTrigger value="execution">実行履歴</TabsTrigger>
            <TabsTrigger value="logs">ログ</TabsTrigger>
          </TabsList>

          {/* チャットタブ */}
          <TabsContent value="chat" className="flex-1 flex flex-col p-4">
            <div className="flex-1 flex space-x-4">
              {/* チャットエリア */}
              <Card className="flex-1 flex flex-col">
                <CardHeader>
                  <CardTitle className="flex items-center space-x-2">
                    <Bot className="h-5 w-5" />
                    <span>AI Assistant</span>
                  </CardTitle>
                </CardHeader>
                <CardContent className="flex-1 flex flex-col">
                  <ScrollArea className="flex-1 pr-4">
                    <div className="space-y-4">
                      {messages.map((message, index) => (
                        <div
                          key={index}
                          className={`flex ${message.sender === 'user' ? 'justify-end' : 'justify-start'}`}
                        >
                          <div
                            className={`max-w-[70%] rounded-lg p-3 ${
                              message.sender === 'user'
                                ? 'bg-blue-500 text-white'
                                : 'bg-gray-100 text-gray-900'
                            }`}
                          >
                            <div className="flex items-start space-x-2">
                              {message.sender === 'user' ? (
                                <User className="h-4 w-4 mt-0.5 flex-shrink-0" />
                              ) : (
                                <Bot className="h-4 w-4 mt-0.5 flex-shrink-0" />
                              )}
                              <div className="flex-1">
                                <p className="text-sm">{message.content}</p>
                                <p className="text-xs opacity-70 mt-1">
                                  {new Date(message.timestamp).toLocaleTimeString()}
                                </p>
                              </div>
                            </div>
                          </div>
                        </div>
                      ))}
                      {isTyping && (
                        <div className="flex justify-start">
                          <div className="bg-gray-100 rounded-lg p-3">
                            <div className="flex items-center space-x-2">
                              <Bot className="h-4 w-4" />
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
                  
                  <Separator className="my-4" />
                  
                  <div className="flex space-x-2">
                    <Input
                      value={inputMessage}
                      onChange={(e) => setInputMessage(e.target.value)}
                      onKeyPress={handleKeyPress}
                      placeholder="メッセージを入力してください..."
                      className="flex-1"
                      disabled={isTyping}
                    />
                    <Button 
                      onClick={handleSendMessage} 
                      disabled={!inputMessage?.trim() || isTyping}
                    >
                      <Send className="h-4 w-4" />
                    </Button>
                  </div>
                </CardContent>
              </Card>

              {/* 実行計画パネル */}
              {currentPlan && (
                <Card className="w-80">
                  <CardHeader>
                    <CardTitle className="flex items-center justify-between">
                      <span>実行計画</span>
                      <Button
                        size="sm"
                        onClick={handleExecutePlan}
                        disabled={planExecutionStatus === 'running'}
                      >
                        {planExecutionStatus === 'running' ? (
                          <Pause className="h-4 w-4" />
                        ) : (
                          <Play className="h-4 w-4" />
                        )}
                      </Button>
                    </CardTitle>
                  </CardHeader>
                  <CardContent>
                    <div className="space-y-3">
                      {currentPlan.tasks?.map((task, index) => (
                        <div key={index} className="flex items-center space-x-2 p-2 border rounded">
                          {getStatusIcon(task.status)}
                          <div className="flex-1">
                            <p className="text-sm font-medium">{task.title}</p>
                            <p className="text-xs text-gray-500">{task.tool_name}</p>
                          </div>
                        </div>
                      ))}
                    </div>
                  </CardContent>
                </Card>
              )}
            </div>
          </TabsContent>

          {/* ツールタブ */}
          <TabsContent value="tools" className="flex-1 p-4">
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
              {/* 利用可能なツール */}
              <Card>
                <CardHeader>
                  <CardTitle>利用可能なツール</CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="grid grid-cols-1 gap-3">
                    {availableTools.map((tool, index) => (
                      <div
                        key={index}
                        className={`p-3 border rounded-lg cursor-pointer transition-colors ${
                          selectedTool === tool.name ? 'border-blue-500 bg-blue-50' : 'hover:bg-gray-50'
                        }`}
                        onClick={() => setSelectedTool(tool.name)}
                      >
                        <div className="flex items-center space-x-3">
                          {getToolIcon(tool.category)}
                          <div className="flex-1">
                            <h3 className="font-medium">{tool.name}</h3>
                            <p className="text-sm text-gray-500">{tool.description}</p>
                            <Badge variant="outline" className="mt-1">
                              {tool.category}
                            </Badge>
                          </div>
                        </div>
                      </div>
                    ))}
                  </div>
                </CardContent>
              </Card>

              {/* ツール実行パネル */}
              {selectedTool && (
                <Card>
                  <CardHeader>
                    <CardTitle>ツール実行: {selectedTool}</CardTitle>
                  </CardHeader>
                  <CardContent>
                    <div className="space-y-4">
                      <div>
                        <label className="text-sm font-medium">パラメータ (JSON)</label>
                        <textarea
                          className="w-full mt-1 p-2 border rounded-md"
                          rows={6}
                          value={JSON.stringify(toolParameters, null, 2)}
                          onChange={(e) => {
                            try {
                              setToolParameters(JSON.parse(e.target.value))
                            } catch (err) {
                              // Invalid JSON, keep the text for editing
                            }
                          }}
                          placeholder='{"action": "example", "parameter": "value"}'
                        />
                      </div>
                      <Button onClick={handleToolExecution} className="w-full">
                        実行
                      </Button>
                    </div>
                  </CardContent>
                </Card>
              )}
            </div>
          </TabsContent>

          {/* ファイルタブ */}
          <TabsContent value="files" className="flex-1 p-4">
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center justify-between">
                  <span>ワークスペースファイル</span>
                  <div className="flex space-x-2">
                    <Button size="sm" variant="outline">
                      <Upload className="h-4 w-4 mr-2" />
                      アップロード
                    </Button>
                    <Button size="sm" variant="outline" onClick={loadWorkspaceFiles}>
                      <RefreshCw className="h-4 w-4 mr-2" />
                      更新
                    </Button>
                  </div>
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className="space-y-2">
                  {workspaceFiles.map((file, index) => (
                    <div key={index} className="flex items-center justify-between p-3 border rounded-lg">
                      <div className="flex items-center space-x-3">
                        <Folder className="h-4 w-4 text-gray-500" />
                        <div>
                          <p className="font-medium">{file.name}</p>
                          <p className="text-sm text-gray-500">
                            {file.type} • {file.size} bytes
                          </p>
                        </div>
                      </div>
                      <div className="flex space-x-2">
                        <Button size="sm" variant="outline">
                          <Eye className="h-4 w-4" />
                        </Button>
                        <Button size="sm" variant="outline">
                          <Edit className="h-4 w-4" />
                        </Button>
                        <Button size="sm" variant="outline">
                          <Download className="h-4 w-4" />
                        </Button>
                        <Button size="sm" variant="outline">
                          <Trash2 className="h-4 w-4" />
                        </Button>
                      </div>
                    </div>
                  ))}
                </div>
              </CardContent>
            </Card>
          </TabsContent>

          {/* 実行履歴タブ */}
          <TabsContent value="execution" className="flex-1 p-4">
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center justify-between">
                  <span>実行履歴</span>
                  <Button size="sm" variant="outline" onClick={loadExecutionHistory}>
                    <RefreshCw className="h-4 w-4 mr-2" />
                    更新
                  </Button>
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className="space-y-3">
                  {executionHistory.map((execution, index) => (
                    <div key={index} className="p-4 border rounded-lg">
                      <div className="flex items-center justify-between mb-2">
                        <div className="flex items-center space-x-2">
                          {getStatusIcon(execution.status)}
                          <span className="font-medium">実行 #{execution.session_id}</span>
                        </div>
                        <span className="text-sm text-gray-500">
                          {new Date(execution.timestamp).toLocaleString()}
                        </span>
                      </div>
                      <p className="text-sm text-gray-600 mb-2">{execution.request}</p>
                      {execution.progress && (
                        <Progress value={execution.progress} className="mb-2" />
                      )}
                      <div className="flex items-center justify-between text-xs text-gray-500">
                        <span>実行時間: {execution.execution_time}秒</span>
                        <span>タスク数: {execution.total_tasks}</span>
                      </div>
                    </div>
                  ))}
                </div>
              </CardContent>
            </Card>
          </TabsContent>

          {/* ログタブ */}
          <TabsContent value="logs" className="flex-1 p-4">
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center justify-between">
                  <span>実行ログ</span>
                  <Button size="sm" variant="outline" onClick={clearExecutionLogs}>
                    クリア
                  </Button>
                </CardTitle>
              </CardHeader>
              <CardContent>
                <ScrollArea className="h-96">
                  <div className="space-y-2">
                    {executionLogs.map((log, index) => (
                      <div key={index} className="p-2 border-l-4 border-gray-300 bg-gray-50">
                        <div className="flex items-center justify-between">
                          <span className="text-sm font-medium">{log.event_type}</span>
                          <span className="text-xs text-gray-500">{log.timestamp}</span>
                        </div>
                        <p className="text-sm text-gray-700">{log.message}</p>
                        {log.data && (
                          <pre className="text-xs text-gray-600 mt-1 overflow-x-auto">
                            {JSON.stringify(log.data, null, 2)}
                          </pre>
                        )}
                      </div>
                    ))}
                  </div>
                </ScrollArea>
              </CardContent>
            </Card>
          </TabsContent>
        </Tabs>
      </div>
    </div>
  )
}

export default MainChatInterface

