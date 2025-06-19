import React, { useState, useEffect } from 'react'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Alert, AlertDescription } from '@/components/ui/alert'
import { LogIn, Eye, EyeOff, User, Lock, Info } from 'lucide-react'
import { useAppStore } from '@/store/appStore'
import { toast } from 'sonner'

const LoginPage = () => {
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [showPassword, setShowPassword] = useState(false)
  const [isLoading, setIsLoading] = useState(false)
  const [demoUsers, setDemoUsers] = useState([])
  const [showDemoUsers, setShowDemoUsers] = useState(false)
  
  const { actions } = useAppStore()

  // デモユーザー情報を取得
  useEffect(() => {
    const fetchDemoUsers = async () => {
      try {
        const response = await fetch('/api/auth/users')
        if (response.ok) {
          const data = await response.json()
          setDemoUsers(data.demo_users || [])
        }
      } catch (error) {
        console.log('デモユーザー情報の取得に失敗しました:', error)
      }
    }
    
    fetchDemoUsers()
  }, [])

  const handleLogin = async (e) => {
    e.preventDefault()
    
    if (!username || !password) {
      toast.error('ユーザー名とパスワードを入力してください')
      return
    }

    setIsLoading(true)

    try {
      const response = await fetch('/api/auth/login', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          username: (username || '').trim(),
          password: password
        })
      })

      const data = await response.json()

      if (response.ok && data.success) {
        // ログイン成功
        localStorage.setItem('auth_token', data.token)
        localStorage.setItem('user_info', JSON.stringify(data.user))
        
        // Zustandストアを更新
        actions.setAuthenticated(true)
        actions.setUser(data.user)
        actions.setCurrentView('main')
        
        toast.success(`ようこそ、${data.user.username}さん！`)
      } else {
        // ログイン失敗
        toast.error(data.error || 'ログインに失敗しました')
      }
    } catch (error) {
      console.error('ログインエラー:', error)
      toast.error('サーバーとの通信に失敗しました')
    } finally {
      setIsLoading(false)
    }
  }

  const handleDemoLogin = (demoUser) => {
    setUsername(demoUser.username)
    setPassword(demoUser.password)
    setShowDemoUsers(false)
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-blue-50 to-indigo-100 p-4">
      <div className="w-full max-w-md space-y-4">
        <Card>
          <CardHeader className="space-y-1">
            <div className="flex items-center justify-center mb-4">
              <div className="w-12 h-12 bg-blue-600 rounded-lg flex items-center justify-center">
                <LogIn className="w-6 h-6 text-white" />
              </div>
            </div>
            <CardTitle className="text-2xl text-center">
              Devin AI Clone
            </CardTitle>
            <CardDescription className="text-center">
              自律型AIエージェントにログイン
            </CardDescription>
          </CardHeader>
          <CardContent>
            <form onSubmit={handleLogin} className="space-y-4">
              <div className="space-y-2">
                <Label htmlFor="username">ユーザー名</Label>
                <div className="relative">
                  <User className="absolute left-3 top-3 h-4 w-4 text-gray-400" />
                  <Input
                    id="username"
                    type="text"
                    placeholder="ユーザー名を入力"
                    value={username}
                    onChange={(e) => setUsername(e.target.value)}
                    className="pl-10"
                    disabled={isLoading}
                  />
                </div>
              </div>
              
              <div className="space-y-2">
                <Label htmlFor="password">パスワード</Label>
                <div className="relative">
                  <Lock className="absolute left-3 top-3 h-4 w-4 text-gray-400" />
                  <Input
                    id="password"
                    type={showPassword ? "text" : "password"}
                    placeholder="パスワードを入力"
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    className="pl-10 pr-10"
                    disabled={isLoading}
                  />
                  <button
                    type="button"
                    onClick={() => setShowPassword(!showPassword)}
                    className="absolute right-3 top-3 h-4 w-4 text-gray-400 hover:text-gray-600"
                    disabled={isLoading}
                  >
                    {showPassword ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
                  </button>
                </div>
              </div>

              <Button 
                type="submit" 
                className="w-full" 
                disabled={isLoading}
              >
                {isLoading ? (
                  <div className="flex items-center space-x-2">
                    <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin"></div>
                    <span>ログイン中...</span>
                  </div>
                ) : (
                  'ログイン'
                )}
              </Button>
            </form>
          </CardContent>
        </Card>

        {/* デモユーザー情報 */}
        {demoUsers.length > 0 && (
          <Card>
            <CardHeader>
              <CardTitle className="text-sm flex items-center space-x-2">
                <Info className="w-4 h-4" />
                <span>開発用デモアカウント</span>
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="space-y-2">
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => setShowDemoUsers(!showDemoUsers)}
                  className="w-full"
                >
                  {showDemoUsers ? 'デモアカウントを隠す' : 'デモアカウントを表示'}
                </Button>
                
                {showDemoUsers && (
                  <div className="space-y-2 mt-3">
                    {demoUsers.map((user, index) => (
                      <div
                        key={index}
                        className="flex items-center justify-between p-2 bg-gray-50 rounded-md"
                      >
                        <div className="text-sm">
                          <div className="font-medium">{user.username}</div>
                          <div className="text-gray-500 text-xs">{user.role}</div>
                        </div>
                        <Button
                          variant="outline"
                          size="sm"
                          onClick={() => handleDemoLogin(user)}
                          disabled={isLoading}
                        >
                          使用
                        </Button>
                      </div>
                    ))}
                    <Alert>
                      <AlertDescription className="text-xs">
                        これらは開発用のテストアカウントです。本番環境では使用しないでください。
                      </AlertDescription>
                    </Alert>
                  </div>
                )}
              </div>
            </CardContent>
          </Card>
        )}
      </div>
    </div>
  )
}

export default LoginPage

