import { useEffect, useMemo, useState } from 'react';
import { Toaster } from 'sonner';
import { useAppStore } from './store/appStore';
import LoginPage from './components/LoginPage';
import MainChatInterface from './components/MainChatInterface';
import SettingsPage from './components/SettingsPage';
import PlanReviewDialog from './components/PlanReviewDialog';

function App() {
  const [isInitializing, setIsInitializing] = useState(true);

  // Zustandストアから状態とアクションを一度に取得
  const {
    currentView,
    isAuthenticated,
    showPlanDialog,
    actions
  } = useAppStore(state => ({
    currentView: state.currentView,
    isAuthenticated: state.isAuthenticated,
    showPlanDialog: state.showPlanDialog,
    actions: state.actions,
  }));

  useEffect(() => {
    // アプリケーション起動時に一度だけ認証状態を初期化
    actions.initializeAuth();
    setIsInitializing(false);
  }, [actions]);

  // 初期化中はローディングスピナーなどを表示
  if (isInitializing) {
    return (
      <div className="flex h-screen w-screen items-center justify-center">
        <div className="h-16 w-16 animate-spin rounded-full border-4 border-solid border-primary border-t-transparent"></div>
      </div>
    );
  }

  const renderCurrentView = () => {
    if (!isAuthenticated) {
      return <LoginPage />;
    }
    
    switch (currentView) {
      case 'settings':
        return <SettingsPage />;
      case 'main':
      default:
        return <MainChatInterface />;
    }
  };

  return (
    <>
      {renderCurrentView()}
      {showPlanDialog && <PlanReviewDialog />}
      <Toaster />
    </>
  );
}

export default App;