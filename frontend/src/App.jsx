import React, { useEffect, useMemo } from 'react'
import { useAppStore } from '@/store/appStore'
import LoginPage from '@/components/LoginPage'
import SettingsPage from '@/components/SettingsPage'
import MainChatInterface from '@/components/MainChatInterface'
import { Toaster } from '@/components/ui/sonner'
import { toast } from 'sonner'

function App() {
  // Zustandストアから必要な状態とアクションを取得
  const store = useAppStore()
  
  // 状態を安定化するためにuseMemoを使用
  const {
    currentView,
    isAuthenticated,
    error,
    systemStatus,
    actions
  } = useMemo(() => ({
    currentView: store.currentView,
    isAuthenticated: store.isAuthenticated,
    error: store.error,
    systemStatus: store.systemStatus,
    actions: store.actions
  }), [store.currentView, store.isAuthenticated, store.error, store.systemStatus, store.actions])
  
  // アプリケーション初期化
  useEffect(() => {
    // 認証情報の復元
    actions.initializeAuth()
  }, [actions])
  
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
    const checkHealth = async () => {
      await actions.checkBackendHealth()
    }
    
    // 初回チェック
    checkHealth()
    
    // 定期的なヘルスチェック
    const interval = setInterval(checkHealth, 30000) // 30秒ごと
    
    return () => clearInterval(interval)
  }, [actions])
  
  // 認証トークンの自動リフレッシュ
  useEffect(() => {
    if (!isAuthenticated) return
    
    const refreshInterval = setInterval(async () => {
      const success = await actions.refreshAuth()
      if (!success) {
        toast.error('セッションが期限切れです。再度ログインしてください。')
      }
    }, 25 * 60 * 1000) // 25分ごと（トークンの有効期限30分より前）
    
    return () => clearInterval(refreshInterval)
  }, [isAuthenticated, actions])
  
  // Git設定の読み込み
  useEffect(() => {
    if (isAuthenticated) {
      actions.loadGitSettings()
    }
  }, [isAuthenticated, actions])
  
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

