import React, { useState, useEffect } from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Switch } from '@/components/ui/switch';
import { Textarea } from '@/components/ui/textarea';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Badge } from '@/components/ui/badge';
import { 
  Settings, 
  Github, 
  Save, 
  TestTube, 
  Trash2, 
  CheckCircle, 
  XCircle, 
  AlertTriangle,
  Info,
  Eye,
  EyeOff
} from 'lucide-react';

const SettingsPage = () => {
  const [gitSettings, setGitSettings] = useState({
    repository_url: '',
    branch: 'main',
    username: '',
    access_token: '',
    auto_commit: true,
    commit_message_template: 'Auto-commit by Devin AI: {task_description}',
    is_configured: false
  });

  const [loading, setLoading] = useState(false);
  const [testResult, setTestResult] = useState(null);
  const [alert, setAlert] = useState(null);
  const [showToken, setShowToken] = useState(false);

  // Git設定を読み込み
  useEffect(() => {
    loadGitSettings();
  }, []);

  const loadGitSettings = async () => {
    try {
      setLoading(true);
      const response = await fetch('/api/settings/git', {
        headers: {
          'X-User-ID': 'default' // 将来的にはユーザー認証から取得
        }
      });
      
      if (response.ok) {
        const data = await response.json();
        setGitSettings(data);
      } else {
        showAlert('error', 'Git設定の読み込みに失敗しました');
      }
    } catch (error) {
      showAlert('error', `エラー: ${error.message}`);
    } finally {
      setLoading(false);
    }
  };

  const saveGitSettings = async () => {
    try {
      setLoading(true);
      
      // バリデーション
      if (!gitSettings.repository_url || !gitSettings.username || !gitSettings.access_token) {
        showAlert('error', 'リポジトリURL、ユーザー名、アクセストークンは必須項目です');
        return;
      }

      const response = await fetch('/api/settings/git', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-User-ID': 'default'
        },
        body: JSON.stringify(gitSettings)
      });

      const result = await response.json();

      if (response.ok && result.success) {
        showAlert('success', 'Git設定を保存しました');
        loadGitSettings(); // 設定を再読み込み
      } else {
        showAlert('error', result.message || 'Git設定の保存に失敗しました');
      }
    } catch (error) {
      showAlert('error', `エラー: ${error.message}`);
    } finally {
      setLoading(false);
    }
  };

  const testGitConnection = async () => {
    try {
      setLoading(true);
      setTestResult(null);

      const response = await fetch('/api/settings/git/test', {
        method: 'POST',
        headers: {
          'X-User-ID': 'default'
        }
      });

      const result = await response.json();
      setTestResult(result);

      if (result.success) {
        showAlert('success', '接続テストに成功しました');
      } else {
        showAlert('error', result.message || '接続テストに失敗しました');
      }
    } catch (error) {
      showAlert('error', `エラー: ${error.message}`);
      setTestResult({
        success: false,
        message: error.message
      });
    } finally {
      setLoading(false);
    }
  };

  const deleteGitSettings = async () => {
    if (!confirm('Git設定を削除してもよろしいですか？')) {
      return;
    }

    try {
      setLoading(true);

      const response = await fetch('/api/settings/git', {
        method: 'DELETE',
        headers: {
          'X-User-ID': 'default'
        }
      });

      const result = await response.json();

      if (response.ok && result.success) {
        showAlert('success', 'Git設定を削除しました');
        setGitSettings({
          repository_url: '',
          branch: 'main',
          username: '',
          access_token: '',
          auto_commit: true,
          commit_message_template: 'Auto-commit by Devin AI: {task_description}',
          is_configured: false
        });
        setTestResult(null);
      } else {
        showAlert('error', result.message || 'Git設定の削除に失敗しました');
      }
    } catch (error) {
      showAlert('error', `エラー: ${error.message}`);
    } finally {
      setLoading(false);
    }
  };

  const showAlert = (type, message) => {
    setAlert({ type, message });
    setTimeout(() => setAlert(null), 5000);
  };

  const handleInputChange = (field, value) => {
    setGitSettings(prev => ({
      ...prev,
      [field]: value
    }));
  };

  return (
    <div className="container mx-auto p-6 max-w-4xl">
      <div className="flex items-center gap-2 mb-6">
        <Settings className="h-6 w-6" />
        <h1 className="text-2xl font-bold">設定</h1>
      </div>

      {alert && (
        <Alert className={`mb-6 ${
          alert.type === 'success' ? 'border-green-500 bg-green-50' :
          alert.type === 'error' ? 'border-red-500 bg-red-50' :
          'border-yellow-500 bg-yellow-50'
        }`}>
          <AlertDescription className={
            alert.type === 'success' ? 'text-green-700' :
            alert.type === 'error' ? 'text-red-700' :
            'text-yellow-700'
          }>
            {alert.message}
          </AlertDescription>
        </Alert>
      )}

      <Tabs defaultValue="git" className="space-y-6">
        <TabsList>
          <TabsTrigger value="git" className="flex items-center gap-2">
            <Github className="h-4 w-4" />
            Git連携
          </TabsTrigger>
          <TabsTrigger value="resources" disabled>
            リソース管理
          </TabsTrigger>
          <TabsTrigger value="security" disabled>
            セキュリティ
          </TabsTrigger>
        </TabsList>

        <TabsContent value="git">
          <Card>
            <CardHeader>
              <div className="flex items-center justify-between">
                <div>
                  <CardTitle className="flex items-center gap-2">
                    <Github className="h-5 w-5" />
                    Git連携設定
                  </CardTitle>
                  <CardDescription>
                    GitHubリポジトリとの連携を設定して、自動コミット機能を有効にします
                  </CardDescription>
                </div>
                <div className="flex items-center gap-2">
                  {gitSettings.is_configured && (
                    <Badge variant="outline" className="text-green-600 border-green-600">
                      <CheckCircle className="h-3 w-3 mr-1" />
                      設定済み
                    </Badge>
                  )}
                </div>
              </div>
            </CardHeader>
            <CardContent className="space-y-6">
              {/* 基本設定 */}
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div className="space-y-2">
                  <Label htmlFor="repository_url">リポジトリURL *</Label>
                  <Input
                    id="repository_url"
                    placeholder="https://github.com/username/repository"
                    value={gitSettings.repository_url}
                    onChange={(e) => handleInputChange('repository_url', e.target.value)}
                  />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="branch">ブランチ</Label>
                  <Input
                    id="branch"
                    placeholder="main"
                    value={gitSettings.branch}
                    onChange={(e) => handleInputChange('branch', e.target.value)}
                  />
                </div>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div className="space-y-2">
                  <Label htmlFor="username">GitHubユーザー名 *</Label>
                  <Input
                    id="username"
                    placeholder="your-username"
                    value={gitSettings.username}
                    onChange={(e) => handleInputChange('username', e.target.value)}
                  />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="access_token">アクセストークン *</Label>
                  <div className="relative">
                    <Input
                      id="access_token"
                      type={showToken ? "text" : "password"}
                      placeholder="ghp_xxxxxxxxxxxxxxxxxxxx"
                      value={gitSettings.access_token}
                      onChange={(e) => handleInputChange('access_token', e.target.value)}
                      className="pr-10"
                    />
                    <Button
                      type="button"
                      variant="ghost"
                      size="sm"
                      className="absolute right-0 top-0 h-full px-3"
                      onClick={() => setShowToken(!showToken)}
                    >
                      {showToken ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
                    </Button>
                  </div>
                  <p className="text-xs text-gray-500">
                    GitHub Settings → Developer settings → Personal access tokens で作成
                  </p>
                </div>
              </div>

              {/* 自動コミット設定 */}
              <div className="space-y-4">
                <div className="flex items-center space-x-2">
                  <Switch
                    id="auto_commit"
                    checked={gitSettings.auto_commit}
                    onCheckedChange={(checked) => handleInputChange('auto_commit', checked)}
                  />
                  <Label htmlFor="auto_commit">自動コミットを有効にする</Label>
                </div>

                <div className="space-y-2">
                  <Label htmlFor="commit_message_template">コミットメッセージテンプレート</Label>
                  <Textarea
                    id="commit_message_template"
                    placeholder="Auto-commit by Devin AI: {task_description}"
                    value={gitSettings.commit_message_template}
                    onChange={(e) => handleInputChange('commit_message_template', e.target.value)}
                    rows={3}
                  />
                  <p className="text-xs text-gray-500">
                    {'{task_description}'}はタスクの説明に置き換えられます
                  </p>
                </div>
              </div>

              {/* 接続テスト結果 */}
              {testResult && (
                <Alert className={testResult.success ? 'border-green-500 bg-green-50' : 'border-red-500 bg-red-50'}>
                  <div className="flex items-center gap-2">
                    {testResult.success ? (
                      <CheckCircle className="h-4 w-4 text-green-600" />
                    ) : (
                      <XCircle className="h-4 w-4 text-red-600" />
                    )}
                    <AlertDescription className={testResult.success ? 'text-green-700' : 'text-red-700'}>
                      {testResult.message}
                    </AlertDescription>
                  </div>
                  {testResult.success && testResult.repository_name && (
                    <div className="mt-2 text-sm text-green-600">
                      <p>リポジトリ: {testResult.repository_full_name}</p>
                      <p>プライベート: {testResult.private ? 'はい' : 'いいえ'}</p>
                    </div>
                  )}
                </Alert>
              )}

              {/* アクション */}
              <div className="flex flex-wrap gap-3 pt-4 border-t">
                <Button 
                  onClick={saveGitSettings} 
                  disabled={loading}
                  className="flex items-center gap-2"
                >
                  <Save className="h-4 w-4" />
                  {loading ? '保存中...' : '設定を保存'}
                </Button>
                
                <Button 
                  variant="outline" 
                  onClick={testGitConnection} 
                  disabled={loading || !gitSettings.repository_url || !gitSettings.access_token}
                  className="flex items-center gap-2"
                >
                  <TestTube className="h-4 w-4" />
                  接続テスト
                </Button>
                
                {gitSettings.is_configured && (
                  <Button 
                    variant="destructive" 
                    onClick={deleteGitSettings} 
                    disabled={loading}
                    className="flex items-center gap-2"
                  >
                    <Trash2 className="h-4 w-4" />
                    設定を削除
                  </Button>
                )}
              </div>

              {/* ヘルプ */}
              <Alert>
                <Info className="h-4 w-4" />
                <AlertDescription>
                  <strong>Personal Access Tokenの作成方法:</strong>
                  <ol className="list-decimal list-inside mt-2 space-y-1 text-sm">
                    <li>GitHub → Settings → Developer settings → Personal access tokens</li>
                    <li>"Generate new token" をクリック</li>
                    <li>必要な権限を選択: repo, workflow, write:packages</li>
                    <li>生成されたトークンをコピーして上記に貼り付け</li>
                  </ol>
                </AlertDescription>
              </Alert>
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="resources">
          <Card>
            <CardHeader>
              <CardTitle>リソース管理</CardTitle>
              <CardDescription>
                コード実行時のリソース制限を設定します（実装予定）
              </CardDescription>
            </CardHeader>
            <CardContent>
              <Alert>
                <AlertTriangle className="h-4 w-4" />
                <AlertDescription>
                  この機能は今後のアップデートで実装予定です。
                </AlertDescription>
              </Alert>
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="security">
          <Card>
            <CardHeader>
              <CardTitle>セキュリティ設定</CardTitle>
              <CardDescription>
                セキュリティ関連の設定を管理します（実装予定）
              </CardDescription>
            </CardHeader>
            <CardContent>
              <Alert>
                <AlertTriangle className="h-4 w-4" />
                <AlertDescription>
                  この機能は今後のアップデートで実装予定です。
                </AlertDescription>
              </Alert>
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  );
};

export default SettingsPage;

