import React, { useEffect, useCallback } from 'react'
import { useAppStore } from '@/store/appStore'
import LoginPage from '@/components/LoginPage'
import SettingsPage from '@/components/SettingsPage'
import MainChatInterface from '@/components/MainChatInterface'
import { Toaster } from '@/components/ui/sonner'
import { toast } from 'sonner'

function App() {
  // Zustandストアから状態とアクションを取得
  const currentView = useAppStore(state => state.currentView)
  const isAuthenticated = useAppStore(state => state.isAuthenticated)
  const error = useAppStore(state => state.error)
  const systemStatus = useAppStore(state => state.systemStatus)
  const actions = useAppStore(state => state.actions)
  
  // アクションをメモ化して安定化
  const initializeAuth = useCallback(() => {
    actions.initializeAuth()
  }, [actions])
  
  const checkBackendHealth = useCallback(async () => {
    await actions.checkBackendHealth()
  }, [actions])
  
  const refreshAuth = useCallback(async () => {
    const success = await actions.refreshAuth()
    if (!success) {
      toast.error('セッションが期限切れです。再度ログインしてください。')
    }
  }, [actions])
  
  const loadGitSettings = useCallback(() => {
    actions.loadGitSettings()
  }, [actions])
  
  // アプリケーション初期化
  useEffect(() => {
    initializeAuth()
  }, [initializeAuth])
  
  // エラー通知
  useEffect(() => {
    if (error) {
      toast.error(error)
      // エラーを表示後にクリア
      const timer = setTimeout(() => {
        actions.setError(null)
      }, 5000)
      
      return () => clearTimeout(timer)
    }
  }, [error, actions])
  
  // バックエンドヘルスチェック
  useEffect(() => {
    // 初回チェック
    checkBackendHealth()
    
    // 定期的なヘルスチェック
    const interval = setInterval(checkBackendHealth, 30000) // 30秒ごと
    
    return () => clearInterval(interval)
  }, [checkBackendHealth])
  
  // 認証トークンの自動リフレッシュ
  useEffect(() => {
    if (!isAuthenticated) return
    
    const refreshInterval = setInterval(refreshAuth, 25 * 60 * 1000) // 25分ごと
    
    return () => clearInterval(refreshInterval)
  }, [isAuthenticated, refreshAuth])
  
  // Git設定の読み込み
  useEffect(() => {
    if (isAuthenticated) {
      loadGitSettings()
    }
  }, [isAuthenticated, loadGitSettings])
  
  // バックエンド接続状態の監視
  useEffect(() => {
    if (!systemStatus.backend_connected) {
      toast.warning('バックエンドサーバーとの接続が不安定です')
    }
  }, [systemStatus.backend_connected])
  
  // 認証状態に基づくビューの決定
  if (!isAuthenticated) {
    return (
      <>
        <LoginPage />
        <Toaster position="top-right" />
      </>
    )
  }
  
  // 認証済みユーザーのビュー
  const renderCurrentView = () => {
    switch (currentView) {
      case 'settings':
        return <SettingsPage />
      case 'main':
      default:
        return <MainChatInterface />
    }
  }
  
  return (
    <>
      {renderCurrentView()}
      <Toaster position="top-right" />
    </>
  )
}

export default App

