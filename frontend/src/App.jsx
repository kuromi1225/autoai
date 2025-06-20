import React, { useEffect, useMemo } from 'react'
import { useAppStore } from '@/store/appStore'
import LoginPage from '@/components/LoginPage'
import SettingsPage from '@/components/SettingsPage'
import MainChatInterface from '@/components/MainChatInterface'
// import { Toaster } from '@/components/ui/sonner'
// import { toast } from 'sonner'

function App() {
  console.log('App component rendering...');
  
  // Zustandストアから必要な状態とアクションを取得
  const store = useAppStore()
  console.log('Store loaded:', store);
  
  // 状態を安定化するためにuseMemoを使用
  const {
    currentView,
    isAuthenticated,
    error,
    systemStatus,
    actions
  } = useMemo(() => {
    console.log('Creating memoized state...');
    return {
      currentView: store.currentView,
      isAuthenticated: store.isAuthenticated,
      error: store.error,
      systemStatus: store.systemStatus,
      actions: store.actions
    };
  }, [store.currentView, store.isAuthenticated, store.error, store.systemStatus, store.actions])
  
  console.log('App state:', { currentView, isAuthenticated, error });
  
  // 認証状態に基づくビューの決定
  if (!isAuthenticated) {
    return <LoginPage />
  }
  
  // 認証済みユーザーのビュー
  const renderCurrentView = () => {
    console.log('Rendering view:', currentView);
    switch (currentView) {
      case 'settings':
        return <SettingsPage />
      case 'main':
      default:
        return <MainChatInterface />
    }
  }
  
  return renderCurrentView()
}

export default App

