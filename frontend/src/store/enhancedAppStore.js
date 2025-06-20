import { create } from 'zustand'

const useAppStore = create((set, get) => ({
  // 認証状態
  isAuthenticated: false,
  user: null,
  
  // チャット関連
  messages: [],
  inputMessage: '',
  isTyping: false,
  
  // 計画実行関連
  currentPlan: null,
  showPlanDialog: false,
  planExecutionStatus: 'idle', // idle, running, completed, failed
  executionLogs: [],
  
  // ツール関連
  availableTools: [
    {
      name: 'file_editor',
      description: 'ファイルの読み書き、編集、検索を行う',
      category: 'file',
      schema: {
        type: 'object',
        properties: {
          action: { type: 'string', enum: ['read', 'write', 'append', 'delete', 'list', 'search'] },
          file_path: { type: 'string' },
          content: { type: 'string' },
          directory: { type: 'string' },
          pattern: { type: 'string' }
        }
      }
    },
    {
      name: 'code_executor',
      description: 'Python、JavaScript、Shellコードを実行する',
      category: 'code',
      schema: {
        type: 'object',
        properties: {
          language: { type: 'string', enum: ['python', 'javascript', 'shell'] },
          code: { type: 'string' }
        }
      }
    },
    {
      name: 'browser',
      description: 'ブラウザを自動化してWebページの操作を行う',
      category: 'browser',
      schema: {
        type: 'object',
        properties: {
          action: { type: 'string', enum: ['start', 'navigate', 'click', 'input', 'get_text', 'screenshot', 'stop'] },
          url: { type: 'string' },
          selector: { type: 'string' },
          text: { type: 'string' }
        }
      }
    },
    {
      name: 'data_analysis',
      description: 'データの読み込み、分析、可視化を行う',
      category: 'data',
      schema: {
        type: 'object',
        properties: {
          action: { type: 'string', enum: ['load_csv', 'analyze', 'visualize', 'export'] },
          file_path: { type: 'string' },
          data_id: { type: 'string' },
          chart_type: { type: 'string', enum: ['line', 'bar', 'histogram', 'correlation'] },
          format: { type: 'string', enum: ['csv', 'json', 'excel'] }
        }
      }
    },
    {
      name: 'image_generator',
      description: '画像の生成、編集、変換を行う',
      category: 'media',
      schema: {
        type: 'object',
        properties: {
          action: { type: 'string', enum: ['create', 'add_text', 'resize', 'convert'] },
          width: { type: 'integer' },
          height: { type: 'integer' },
          background_color: { type: 'string' },
          image_path: { type: 'string' },
          text: { type: 'string' },
          position: { type: 'array', items: { type: 'integer' } },
          format: { type: 'string', enum: ['PNG', 'JPEG', 'GIF', 'BMP'] }
        }
      }
    },
    {
      name: 'api_connector',
      description: '外部APIとの連携を行う',
      category: 'api',
      schema: {
        type: 'object',
        properties: {
          action: { type: 'string', enum: ['request', 'openai_chat', 'github_api'] },
          method: { type: 'string', enum: ['GET', 'POST', 'PUT', 'DELETE', 'PATCH'] },
          url: { type: 'string' },
          headers: { type: 'object' },
          data: {},
          messages: { type: 'array' },
          model: { type: 'string' },
          endpoint: { type: 'string' }
        }
      }
    },
    {
      name: 'web_scraping',
      description: 'Webページからデータを抽出する',
      category: 'web',
      schema: {
        type: 'object',
        properties: {
          action: { type: 'string', enum: ['scrape_text', 'scrape_links', 'scrape_images', 'scrape_table'] },
          url: { type: 'string' },
          selector: { type: 'string' },
          table_selector: { type: 'string' }
        }
      }
    },
    {
      name: 'email',
      description: 'メールの送信を行う',
      category: 'communication',
      schema: {
        type: 'object',
        properties: {
          action: { type: 'string', enum: ['send'] },
          to_email: { type: 'string' },
          subject: { type: 'string' },
          body: { type: 'string' }
        }
      }
    }
  ],
  
  // ファイルシステム関連
  workspaceFiles: [],
  currentDirectory: '/',
  
  // 実行履歴
  executionHistory: [],
  
  // WebSocket接続
  socket: null,
  isConnected: false,
  
  // アクション
  setAuthenticated: (isAuth, userData = null) => set({ isAuthenticated: isAuth, user: userData }),
  
  setInputMessage: (message) => set({ inputMessage: message }),
  
  setIsTyping: (typing) => set({ isTyping: typing }),
  
  addMessage: (message) => set((state) => ({
    messages: [...state.messages, {
      ...message,
      timestamp: new Date(),
      id: Date.now()
    }]
  })),
  
  sendMessage: async (content) => {
    const { addMessage, setIsTyping } = get()
    
    // ユーザーメッセージを追加
    addMessage({
      sender: 'user',
      content: content,
      type: 'text'
    })
    
    setIsTyping(true)
    
    try {
      // APIにメッセージを送信
      const response = await fetch('/api/chat/message', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${localStorage.getItem('token')}`
        },
        body: JSON.stringify({
          message: content,
          session_id: Date.now().toString()
        })
      })
      
      if (response.ok) {
        const data = await response.json()
        
        // AIの応答を追加
        addMessage({
          sender: 'assistant',
          content: data.response || 'メッセージを処理しました。',
          type: 'text'
        })
        
        // 実行計画があれば設定
        if (data.execution_plan) {
          set({ currentPlan: data.execution_plan })
        }
      } else {
        addMessage({
          sender: 'assistant',
          content: 'エラーが発生しました。もう一度お試しください。',
          type: 'error'
        })
      }
    } catch (error) {
      console.error('Send message error:', error)
      addMessage({
        sender: 'assistant',
        content: 'ネットワークエラーが発生しました。',
        type: 'error'
      })
    } finally {
      setIsTyping(false)
    }
  },
  
  setCurrentPlan: (plan) => set({ currentPlan: plan }),
  
  setShowPlanDialog: (show) => set({ showPlanDialog: show }),
  
  setPlanExecutionStatus: (status) => set({ planExecutionStatus: status }),
  
  addExecutionLog: (log) => set((state) => ({
    executionLogs: [...state.executionLogs, {
      ...log,
      timestamp: new Date().toISOString(),
      id: Date.now()
    }]
  })),
  
  clearExecutionLogs: () => set({ executionLogs: [] }),
  
  executePlan: async (plan) => {
    const { setPlanExecutionStatus, addExecutionLog } = get()
    
    setPlanExecutionStatus('running')
    addExecutionLog({
      event_type: 'execution_start',
      message: '実行計画を開始しました',
      data: { plan_id: plan.id, total_tasks: plan.tasks?.length || 0 }
    })
    
    try {
      const response = await fetch('/api/execution/start', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${localStorage.getItem('token')}`
        },
        body: JSON.stringify({
          plan: plan,
          session_id: Date.now().toString()
        })
      })
      
      if (response.ok) {
        const data = await response.json()
        setPlanExecutionStatus('completed')
        addExecutionLog({
          event_type: 'execution_complete',
          message: '実行計画が完了しました',
          data: data
        })
      } else {
        setPlanExecutionStatus('failed')
        addExecutionLog({
          event_type: 'execution_error',
          message: '実行計画が失敗しました',
          data: { error: 'HTTP error' }
        })
      }
    } catch (error) {
      setPlanExecutionStatus('failed')
      addExecutionLog({
        event_type: 'execution_error',
        message: '実行計画でエラーが発生しました',
        data: { error: error.message }
      })
    }
  },
  
  executeToolDirectly: async (toolName, parameters) => {
    const { addExecutionLog, addMessage } = get()
    
    addExecutionLog({
      event_type: 'tool_execution_start',
      message: `ツール実行開始: ${toolName}`,
      data: { tool_name: toolName, parameters }
    })
    
    try {
      const response = await fetch('/api/tools/execute', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${localStorage.getItem('token')}`
        },
        body: JSON.stringify({
          tool_name: toolName,
          parameters: parameters
        })
      })
      
      if (response.ok) {
        const data = await response.json()
        
        addExecutionLog({
          event_type: 'tool_execution_complete',
          message: `ツール実行完了: ${toolName}`,
          data: data
        })
        
        addMessage({
          sender: 'assistant',
          content: `ツール「${toolName}」の実行が完了しました。`,
          type: 'tool_result',
          data: data
        })
      } else {
        addExecutionLog({
          event_type: 'tool_execution_error',
          message: `ツール実行失敗: ${toolName}`,
          data: { error: 'HTTP error' }
        })
      }
    } catch (error) {
      addExecutionLog({
        event_type: 'tool_execution_error',
        message: `ツール実行エラー: ${toolName}`,
        data: { error: error.message }
      })
    }
  },
  
  loadWorkspaceFiles: async () => {
    try {
      const response = await fetch('/api/workspace/files', {
        headers: {
          'Authorization': `Bearer ${localStorage.getItem('token')}`
        }
      })
      
      if (response.ok) {
        const data = await response.json()
        set({ workspaceFiles: data.files || [] })
      }
    } catch (error) {
      console.error('Load workspace files error:', error)
    }
  },
  
  loadExecutionHistory: async () => {
    try {
      const response = await fetch('/api/execution/history', {
        headers: {
          'Authorization': `Bearer ${localStorage.getItem('token')}`
        }
      })
      
      if (response.ok) {
        const data = await response.json()
        set({ executionHistory: data.history || [] })
      }
    } catch (error) {
      console.error('Load execution history error:', error)
    }
  },
  
  connectWebSocket: () => {
    const { socket } = get()
    
    if (socket) {
      socket.close()
    }
    
    const newSocket = new WebSocket(`ws://localhost:5000/ws`)
    
    newSocket.onopen = () => {
      set({ socket: newSocket, isConnected: true })
      console.log('WebSocket connected')
    }
    
    newSocket.onmessage = (event) => {
      const data = JSON.parse(event.data)
      const { addMessage, addExecutionLog, setPlanExecutionStatus } = get()
      
      switch (data.type) {
        case 'message':
          addMessage({
            sender: 'assistant',
            content: data.content,
            type: 'text'
          })
          break
        case 'execution_log':
          addExecutionLog(data.log)
          break
        case 'execution_status':
          setPlanExecutionStatus(data.status)
          break
        default:
          console.log('Unknown WebSocket message:', data)
      }
    }
    
    newSocket.onclose = () => {
      set({ socket: null, isConnected: false })
      console.log('WebSocket disconnected')
    }
    
    newSocket.onerror = (error) => {
      console.error('WebSocket error:', error)
    }
  },
  
  disconnectWebSocket: () => {
    const { socket } = get()
    if (socket) {
      socket.close()
      set({ socket: null, isConnected: false })
    }
  },
  
  logout: () => {
    localStorage.removeItem('token')
    set({
      isAuthenticated: false,
      user: null,
      messages: [],
      inputMessage: '',
      isTyping: false,
      currentPlan: null,
      showPlanDialog: false,
      planExecutionStatus: 'idle',
      executionLogs: [],
      workspaceFiles: [],
      executionHistory: []
    })
    
    // WebSocket接続を切断
    const { disconnectWebSocket } = get()
    disconnectWebSocket()
  }
}))

export { useAppStore }

