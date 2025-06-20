/**
 * Zustand State Management Store
 * 
 * アプリケーション全体の状態管理を行うZustandストア
 */

import { create } from 'zustand'
import { devtools, persist } from 'zustand/middleware'
import { immer } from 'zustand/middleware/immer'

// Zustandストアの作成
export const useAppStore = create(
  devtools(
    persist(
      immer((set, get) => ({
        // 認証状態
        isAuthenticated: false,
        user: null,
        authToken: null,

        // UI状態
        currentView: 'login', // 'login', 'main', 'settings'
        sidebarOpen: true,
        theme: 'light',

        // システム状態
        systemStatus: {
          backend_connected: false,
          ai_model_loaded: false,
          github_connected: false
        },

        // エラー状態
        error: null,
        loading: false,

        // チャット状態
        messages: [],
        inputMessage: '',
        isTyping: false,
        currentTask: null,
        taskHistory: [],

        // 計画実行状態
        currentPlan: null,
        showPlanDialog: false,
        planExecutionStatus: 'idle', // 'idle', 'running', 'completed', 'error'
        executionLogs: [],

        // プロジェクト状態
        currentProject: null,
        projects: [],

        // Git設定
        gitSettings: {
          username: '',
          email: '',
          token: ''
        },

        // アクション
        actions: {
          // 認証関連
          setAuthenticated: (authenticated) => set((state) => {
            state.isAuthenticated = authenticated
            if (!authenticated) {
              state.user = null
              state.authToken = null
              state.currentView = 'login'
              // ローカルストレージからも削除
              if (typeof window !== 'undefined') {
                localStorage.removeItem('auth_token')
                localStorage.removeItem('user_info')
              }
            }
          }),

          setUser: (user) => set((state) => {
            state.user = user
          }),

          setAuthToken: (token) => set((state) => {
            state.authToken = token
            if (typeof window !== 'undefined') {
              if (token) {
                localStorage.setItem('auth_token', token)
              } else {
                localStorage.removeItem('auth_token')
              }
            }
          }),

          // 初期化時にローカルストレージから認証情報を復元
          initializeAuth: () => {
            if (typeof window !== 'undefined') {
              const token = localStorage.getItem('auth_token')
              const userInfo = localStorage.getItem('user_info')
              
              if (token && userInfo) {
                try {
                  const user = JSON.parse(userInfo)
                  set((state) => {
                    state.isAuthenticated = true
                    state.user = user
                    state.authToken = token
                    state.currentView = 'main'
                  })
                } catch (error) {
                  console.error('認証情報の復元に失敗:', error)
                  // 無効なデータの場合はクリア
                  localStorage.removeItem('auth_token')
                  localStorage.removeItem('user_info')
                }
              }
            }
          },

          // UI状態
          setCurrentView: (view) => set((state) => {
            state.currentView = view
          }),

          setSidebarOpen: (open) => set((state) => {
            state.sidebarOpen = open
          }),

          setTheme: (theme) => set((state) => {
            state.theme = theme
          }),

          // エラー処理
          setError: (error) => set((state) => {
            state.error = error
          }),

          setLoading: (loading) => set((state) => {
            state.loading = loading
          }),

          // システム状態
          setSystemStatus: (status) => set((state) => {
            state.systemStatus = { ...state.systemStatus, ...status }
          }),

          // バックエンドヘルスチェック
          checkBackendHealth: async () => {
            try {
              const response = await fetch('/health')
              const data = await response.json()
              
              set((state) => {
                state.systemStatus.backend_connected = response.ok
              })
              
              return response.ok
            } catch (error) {
              set((state) => {
                state.systemStatus.backend_connected = false
              })
              return false
            }
          },

          // 認証トークンのリフレッシュ
          refreshAuth: async () => {
            const { authToken } = get()
            if (!authToken) return false

            try {
              const response = await fetch('/api/auth/refresh', {
                method: 'POST',
                headers: {
                  'Content-Type': 'application/json',
                  'Authorization': `Bearer ${authToken}`
                }
              })

              if (response.ok) {
                const data = await response.json()
                if (data.success) {
                  set((state) => {
                    state.authToken = data.token
                  })
                  localStorage.setItem('auth_token', data.token)
                  return true
                }
              }
              
              // リフレッシュ失敗時はログアウト
              get().actions.setAuthenticated(false)
              return false
            } catch (error) {
              console.error('トークンリフレッシュエラー:', error)
              get().actions.setAuthenticated(false)
              return false
            }
          },

          // チャット関連
          setInputMessage: (message) => set((state) => {
            state.inputMessage = message
          }),

          setIsTyping: (typing) => set((state) => {
            state.isTyping = typing
          }),

          addMessage: (message) => set((state) => {
            state.messages.push({
              id: Date.now(),
              timestamp: new Date(),
              ...message
            })
          }),

          clearMessages: () => set((state) => {
            state.messages = []
          }),

          // 計画実行関連
          setCurrentPlan: (plan) => set((state) => {
            state.currentPlan = plan
          }),

          setShowPlanDialog: (show) => set((state) => {
            state.showPlanDialog = show
          }),

          setPlanExecutionStatus: (status) => set((state) => {
            state.planExecutionStatus = status
          }),

          addExecutionLog: (log) => set((state) => {
            state.executionLogs.push(log)
          }),

          clearExecutionLogs: () => set((state) => {
            state.executionLogs = []
          }),

          // メッセージ送信
          sendMessage: async (message) => {
            const { authToken } = get()
            
            // ユーザーメッセージを追加
            get().actions.addMessage({
              type: 'user',
              content: message
            })

            // タイピング状態を開始
            get().actions.setIsTyping(true)

            try {
              // バックエンドにメッセージを送信
              const response = await fetch('/api/chat/message', {
                method: 'POST',
                headers: {
                  'Content-Type': 'application/json',
                  'Authorization': `Bearer ${authToken}`
                },
                body: JSON.stringify({ message })
              })

              if (response.ok) {
                const data = await response.json()
                
                // AIの応答を追加
                get().actions.addMessage({
                  type: 'assistant',
                  content: data.response
                })

                // 計画が含まれている場合は表示
                if (data.plan) {
                  get().actions.setCurrentPlan(data.plan)
                  get().actions.setShowPlanDialog(true)
                }
              } else {
                get().actions.addMessage({
                  type: 'system',
                  content: 'メッセージの送信に失敗しました。'
                })
              }
            } catch (error) {
              console.error('メッセージ送信エラー:', error)
              get().actions.addMessage({
                type: 'system',
                content: 'ネットワークエラーが発生しました。'
              })
            } finally {
              // タイピング状態を終了
              get().actions.setIsTyping(false)
            }
          },

          // 計画実行
          executePlan: async (planId) => {
            const { authToken } = get()
            
            try {
              get().actions.setPlanExecutionStatus('running')
              get().actions.clearExecutionLogs()

              const response = await fetch('/api/plan/execute', {
                method: 'POST',
                headers: {
                  'Content-Type': 'application/json',
                  'Authorization': `Bearer ${authToken}`
                },
                body: JSON.stringify({ plan_id: planId })
              })

              if (response.ok) {
                get().actions.setPlanExecutionStatus('completed')
                return true
              } else {
                get().actions.setPlanExecutionStatus('error')
                return false
              }
            } catch (error) {
              console.error('計画実行エラー:', error)
              get().actions.setPlanExecutionStatus('error')
              return false
            }
          },

          // ログアウト
          logout: () => {
            get().actions.setAuthenticated(false)
            get().actions.clearMessages()
            get().actions.clearExecutionLogs()
            get().actions.setCurrentPlan(null)
            get().actions.setInputMessage('')
          },

          // タスク関連
          setCurrentTask: (task) => set((state) => {
            state.currentTask = task
          }),

          addTaskToHistory: (task) => set((state) => {
            state.taskHistory.unshift({
              id: Date.now(),
              timestamp: new Date().toISOString(),
              ...task
            })
            // 履歴は最大100件まで
            if (state.taskHistory.length > 100) {
              state.taskHistory = state.taskHistory.slice(0, 100)
            }
          }),

          // プロジェクト関連
          setCurrentProject: (project) => set((state) => {
            state.currentProject = project
          }),

          setProjects: (projects) => set((state) => {
            state.projects = projects
          }),

          // Git設定
          setGitSettings: (settings) => set((state) => {
            state.gitSettings = { ...state.gitSettings, ...settings }
          }),

          loadGitSettings: async () => {
            // Git設定をローカルストレージから読み込み
            if (typeof window !== 'undefined') {
              const savedSettings = localStorage.getItem('git_settings')
              if (savedSettings) {
                try {
                  const settings = JSON.parse(savedSettings)
                  set((state) => {
                    state.gitSettings = { ...state.gitSettings, ...settings }
                  })
                } catch (error) {
                  console.error('Git設定の読み込みに失敗:', error)
                }
              }
            }
          },

          saveGitSettings: (settings) => {
            set((state) => {
              state.gitSettings = { ...state.gitSettings, ...settings }
            })
            
            // ローカルストレージに保存
            if (typeof window !== 'undefined') {
              localStorage.setItem('git_settings', JSON.stringify(get().gitSettings))
            }
          }
        }
      })),
      {
        name: 'devin-ai-store',
        partialize: (state) => ({
          theme: state.theme,
          sidebarOpen: state.sidebarOpen,
          gitSettings: state.gitSettings
        })
      }
    ),
    {
      name: 'devin-ai-store'
    }
  )
)

