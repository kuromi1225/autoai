export const useAppStore = create(
  devtools(
    persist(
      immer((set, get) => ({
        // --- 状態 (State) ---
        isAuthenticated: false,
        user: null,
        authToken: null,
        currentView: 'login', // 'login', 'main', 'settings'
        error: null,
        loading: false,
        systemStatus: {
          backend_connected: false,
        },
        
        // チャット関連の状態
        messages: [],
        inputMessage: '', // ★ inputMessage を初期化
        isTyping: false,
        
        // 計画関連の状態
        currentPlan: null,
        showPlanDialog: false,
        planExecutionStatus: 'idle', // idle, running, completed, error
        executionLogs: [],

        // --- アクション (Actions) ---
        actions: {
          // --- 認証関連 ---
          setAuthenticated: (authenticated) => set((state) => {
            state.isAuthenticated = authenticated;
            if (!authenticated) {
              state.user = null;
              state.authToken = null;
              state.currentView = 'login';
              localStorage.removeItem('auth_token');
              localStorage.removeItem('user_info');
            }
          }),
          setUser: (user) => set({ user }),
          setAuthToken: (token) => set({ authToken: token }),
          initializeAuth: () => {
            const token = localStorage.getItem('auth_token');
            const userInfo = localStorage.getItem('user_info');
            if (token && userInfo) {
              try {
                set({
                  isAuthenticated: true,
                  user: JSON.parse(userInfo),
                  authToken: token,
                  currentView: 'main'
                });
              } catch (e) {
                console.error("Failed to parse auth info", e);
                get().actions.logout();
              }
            }
          },
          logout: () => {
            set({
              isAuthenticated: false,
              user: null,
              authToken: null,
              currentView: 'login'
            });
            localStorage.clear();
            toast.info("ログアウトしました。");
          },

          // --- UI関連 ---
          setCurrentView: (view) => set({ currentView: view }),
          setError: (error) => set({ error }),
          setLoading: (loading) => set({ loading }),
          
          // --- システム関連 ---
          checkBackendHealth: async () => {
            try {
              const response = await fetch('/api/health');
              set(state => { 
                state.systemStatus.backend_connected = response.ok;
              });
            } catch (error) {
              set(state => { 
                state.systemStatus.backend_connected = false; 
              });
            }
          },

          // --- チャット・計画関連 ---
          setInputMessage: (message) => set({ inputMessage: message }),
          addMessage: (message) => {
            const newMessage = { ...message, id: Date.now(), timestamp: new Date() };
            set((state) => {
              state.messages.push(newMessage);
            });
          },
          setIsTyping: (typing) => set({ isTyping: typing }),
          setShowPlanDialog: (show) => set({ showPlanDialog: show }),
          setCurrentPlan: (plan) => set({ currentPlan: plan }),

          sendMessage: async (messageContent) => {
            if (!messageContent.trim()) return;

            get().actions.addMessage({ type: 'user', content: messageContent });
            get().actions.setIsTyping(true);
            
            try {
              const res = await fetch('/api/chat', {
                method: 'POST',
                headers: { 
                  'Content-Type': 'application/json',
                  'Authorization': `Bearer ${get().authToken}`
                },
                body: JSON.stringify({ message: messageContent }),
              });

              if (!res.ok) throw new Error(`API Error: ${res.statusText}`);
              
              const data = await res.json();
              get().actions.addMessage({ type: 'assistant', content: data.response });

              if (data.plan) {
                get().actions.setCurrentPlan(data.plan);
                get().actions.setShowPlanDialog(true);
              }
            } catch (error) {
              console.error("Send message error:", error);
              get().actions.addMessage({ type: 'system', content: 'メッセージの送信に失敗しました。' });
              toast.error("メッセージの送信に失敗しました。");
            } finally {
              get().actions.setIsTyping(false);
            }
          },

          executePlan: async (planId) => {
            set({ planExecutionStatus: 'running', executionLogs: [] });
            toast.info(`計画 ${planId} の実行を開始します。`);
            
            try {
                const res = await fetch('/api/execute_plan', {
                    method: 'POST',
                    headers: { 
                      'Content-Type': 'application/json',
                      'Authorization': `Bearer ${get().authToken}`
                    },
                    body: JSON.stringify({ plan_id: planId }),
                });

                if (!res.ok) throw new Error('Plan execution failed to start');

                const data = await res.json();
                get().actions.addMessage({ type: 'system', content: data.message });

            } catch(e) {
                console.error("Execute plan error:", e);
                set({ planExecutionStatus: 'error' });
                toast.error("計画の実行開始に失敗しました。");
            }
          }
        }
      })),
      {
        name: 'devin-ai-store',
        partialize: (state) => ({
          theme: state.theme,
          // 認証情報などを永続化
          isAuthenticated: state.isAuthenticated,
          user: state.user,
          authToken: state.authToken
        }),
      }
    )
  )
);