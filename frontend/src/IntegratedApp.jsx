import React from 'react'
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom'
import { Toaster } from '@/components/ui/sonner'
import { useAppStore } from './store/enhancedAppStore'
import { useWebSocket, NotificationCenter, ConnectionStatus } from './services/webSocketService'
import LoginPage from './components/LoginPage'
import EnhancedMainChatInterface from './components/EnhancedMainChatInterface'
import ProjectManager from './components/ProjectManager'
import { useEffect } from 'react'

function App() {
  const { isAuthenticated, user } = useAppStore()
  const { connect, disconnect, connectionStatus } = useWebSocket()

  useEffect(() => {
    // 認証されている場合はWebSocket接続を開始
    if (isAuthenticated && user) {
      const token = localStorage.getItem('token')
      if (token) {
        connect(token, user.id)
      }
    } else {
      disconnect()
    }

    // クリーンアップ
    return () => {
      disconnect()
    }
  }, [isAuthenticated, user])

  return (
    <Router>
      <div className="min-h-screen bg-gray-50">
        {/* 通知センター */}
        <NotificationCenter />
        
        {/* メインコンテンツ */}
        <Routes>
          <Route 
            path="/login" 
            element={
              isAuthenticated ? <Navigate to="/" replace /> : <LoginPage />
            } 
          />
          <Route 
            path="/" 
            element={
              isAuthenticated ? (
                <div className="h-screen flex flex-col">
                  {/* ヘッダー */}
                  <header className="bg-white border-b border-gray-200 px-6 py-3">
                    <div className="flex items-center justify-between">
                      <div className="flex items-center space-x-4">
                        <h1 className="text-xl font-bold text-gray-900">
                          AutoAI - 汎用自律型AIエージェント
                        </h1>
                        <ConnectionStatus />
                      </div>
                      <div className="flex items-center space-x-4">
                        <span className="text-sm text-gray-600">
                          ようこそ、{user?.username || 'ユーザー'}さん
                        </span>
                      </div>
                    </div>
                  </header>
                  
                  {/* メインコンテンツ */}
                  <main className="flex-1 overflow-hidden">
                    <EnhancedMainChatInterface />
                  </main>
                </div>
              ) : (
                <Navigate to="/login" replace />
              )
            } 
          />
          <Route 
            path="/projects" 
            element={
              isAuthenticated ? (
                <div className="h-screen flex flex-col">
                  <header className="bg-white border-b border-gray-200 px-6 py-3">
                    <div className="flex items-center justify-between">
                      <h1 className="text-xl font-bold text-gray-900">
                        プロジェクト管理
                      </h1>
                      <ConnectionStatus />
                    </div>
                  </header>
                  <main className="flex-1 overflow-hidden p-6">
                    <ProjectManager />
                  </main>
                </div>
              ) : (
                <Navigate to="/login" replace />
              )
            } 
          />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>

        {/* Toast通知 */}
        <Toaster 
          position="top-right"
          toastOptions={{
            duration: 4000,
            style: {
              background: 'white',
              color: 'black',
              border: '1px solid #e5e7eb'
            }
          }}
        />
      </div>
    </Router>
  )
}

export default App

