import React, { useState, useEffect, useRef } from 'react';
import { 
  Activity, 
  Users, 
  GitBranch, 
  Code, 
  Settings, 
  Monitor,
  Play,
  Pause,
  RefreshCw,
  AlertCircle,
  CheckCircle,
  Clock,
  Cpu,
  HardDrive,
  Network,
  Terminal,
  FileText,
  Eye,
  TrendingUp,
  BarChart3,
  PieChart,
  Zap
} from 'lucide-react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '../components/ui/card';
import { Button } from '../components/ui/button';
import { Badge } from '../components/ui/badge';
import { Progress } from '../components/ui/progress';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '../components/ui/tabs';
import { Alert, AlertDescription, AlertTitle } from '../components/ui/alert';

const IntegratedDashboard = () => {
  const [systemStatus, setSystemStatus] = useState({
    qwq_engine: { status: 'running', load: 65 },
    mcp_server: { status: 'running', connections: 3 },
    vscode_server: { status: 'running', port: 8080 },
    git_manager: { status: 'active', repos: 2 },
    multi_agent: { status: 'running', active_agents: 4 }
  });

  const [agentStats, setAgentStats] = useState({
    pm_001: { role: 'PM', tasks_completed: 15, quality_score: 92 },
    pg_001: { role: 'PG', tasks_completed: 28, quality_score: 88 },
    qa_001: { role: 'QA', tasks_completed: 12, quality_score: 95 },
    tester_001: { role: 'Tester', tasks_completed: 22, quality_score: 90 }
  });

  const [realtimeMetrics, setRealtimeMetrics] = useState({
    cpu_usage: 45,
    memory_usage: 62,
    disk_usage: 38,
    network_io: 1.2,
    active_tasks: 8,
    completed_today: 24
  });

  const [mcpStats, setMcpStats] = useState({
    total_requests: 1247,
    total_responses: 1245,
    active_connections: 3,
    average_response_time: 0.15,
    uptime: 86400
  });

  const [gitActivity, setGitActivity] = useState([
    { time: '10:30', action: 'commit', repo: 'autoai', message: 'feat: add multi-agent system' },
    { time: '10:15', action: 'push', repo: 'autoai', message: 'origin/likedevin' },
    { time: '09:45', action: 'merge', repo: 'autoai', message: 'feature/vscode-integration' },
    { time: '09:30', action: 'branch', repo: 'autoai', message: 'create feature/dashboard' }
  ]);

  const [activeTasks, setActiveTasks] = useState([
    { id: 'task_001', title: 'Implement QwQ-32B optimization', agent: 'PG', progress: 75, priority: 'high' },
    { id: 'task_002', title: 'Review MCP server performance', agent: 'QA', progress: 40, priority: 'medium' },
    { id: 'task_003', title: 'Test VSCode integration', agent: 'Tester', progress: 90, priority: 'high' },
    { id: 'task_004', title: 'Plan next sprint', agent: 'PM', progress: 25, priority: 'low' }
  ]);

  const wsRef = useRef(null);

  useEffect(() => {
    // WebSocket接続でリアルタイムデータを取得
    const connectWebSocket = () => {
      wsRef.current = new WebSocket('ws://localhost:5000/ws/dashboard');
      
      wsRef.current.onmessage = (event) => {
        const data = JSON.parse(event.data);
        
        switch (data.type) {
          case 'system_status':
            setSystemStatus(data.payload);
            break;
          case 'agent_stats':
            setAgentStats(data.payload);
            break;
          case 'realtime_metrics':
            setRealtimeMetrics(data.payload);
            break;
          case 'mcp_stats':
            setMcpStats(data.payload);
            break;
          case 'git_activity':
            setGitActivity(prev => [data.payload, ...prev.slice(0, 9)]);
            break;
          case 'task_update':
            setActiveTasks(prev => 
              prev.map(task => 
                task.id === data.payload.id ? { ...task, ...data.payload } : task
              )
            );
            break;
        }
      };

      wsRef.current.onclose = () => {
        // 再接続
        setTimeout(connectWebSocket, 5000);
      };
    };

    connectWebSocket();

    return () => {
      if (wsRef.current) {
        wsRef.current.close();
      }
    };
  }, []);

  const getStatusColor = (status) => {
    switch (status) {
      case 'running':
      case 'active':
        return 'text-green-500';
      case 'warning':
        return 'text-yellow-500';
      case 'error':
        return 'text-red-500';
      default:
        return 'text-gray-500';
    }
  };

  const getStatusIcon = (status) => {
    switch (status) {
      case 'running':
      case 'active':
        return <CheckCircle className="h-4 w-4" />;
      case 'warning':
        return <AlertCircle className="h-4 w-4" />;
      case 'error':
        return <AlertCircle className="h-4 w-4" />;
      default:
        return <Clock className="h-4 w-4" />;
    }
  };

  const getPriorityColor = (priority) => {
    switch (priority) {
      case 'high':
        return 'bg-red-100 text-red-800';
      case 'medium':
        return 'bg-yellow-100 text-yellow-800';
      case 'low':
        return 'bg-green-100 text-green-800';
      default:
        return 'bg-gray-100 text-gray-800';
    }
  };

  const formatUptime = (seconds) => {
    const hours = Math.floor(seconds / 3600);
    const minutes = Math.floor((seconds % 3600) / 60);
    return `${hours}h ${minutes}m`;
  };

  return (
    <div className="min-h-screen bg-gray-50 p-6">
      <div className="max-w-7xl mx-auto space-y-6">
        {/* ヘッダー */}
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-3xl font-bold text-gray-900">AutoAI v3.0 Dashboard</h1>
            <p className="text-gray-600">完全自律型開発環境 - 統合監視システム</p>
          </div>
          <div className="flex items-center space-x-4">
            <Button variant="outline" size="sm">
              <RefreshCw className="h-4 w-4 mr-2" />
              更新
            </Button>
            <Button variant="outline" size="sm">
              <Settings className="h-4 w-4 mr-2" />
              設定
            </Button>
          </div>
        </div>

        {/* システム状態概要 */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-5 gap-4">
          {Object.entries(systemStatus).map(([key, status]) => (
            <Card key={key}>
              <CardContent className="p-4">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-sm font-medium text-gray-600">
                      {key.replace('_', ' ').toUpperCase()}
                    </p>
                    <div className={`flex items-center mt-1 ${getStatusColor(status.status)}`}>
                      {getStatusIcon(status.status)}
                      <span className="ml-1 text-sm font-semibold">
                        {status.status}
                      </span>
                    </div>
                  </div>
                  <div className="text-right">
                    {status.load && (
                      <p className="text-xs text-gray-500">Load: {status.load}%</p>
                    )}
                    {status.connections && (
                      <p className="text-xs text-gray-500">Conn: {status.connections}</p>
                    )}
                    {status.port && (
                      <p className="text-xs text-gray-500">Port: {status.port}</p>
                    )}
                    {status.repos && (
                      <p className="text-xs text-gray-500">Repos: {status.repos}</p>
                    )}
                    {status.active_agents && (
                      <p className="text-xs text-gray-500">Agents: {status.active_agents}</p>
                    )}
                  </div>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>

        {/* メインコンテンツ */}
        <Tabs defaultValue="overview" className="space-y-4">
          <TabsList className="grid w-full grid-cols-6">
            <TabsTrigger value="overview">概要</TabsTrigger>
            <TabsTrigger value="agents">エージェント</TabsTrigger>
            <TabsTrigger value="mcp">MCP</TabsTrigger>
            <TabsTrigger value="vscode">VSCode</TabsTrigger>
            <TabsTrigger value="git">Git</TabsTrigger>
            <TabsTrigger value="system">システム</TabsTrigger>
          </TabsList>

          {/* 概要タブ */}
          <TabsContent value="overview" className="space-y-4">
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
              {/* リアルタイムメトリクス */}
              <Card>
                <CardHeader>
                  <CardTitle className="flex items-center">
                    <Activity className="h-5 w-5 mr-2" />
                    リアルタイムメトリクス
                  </CardTitle>
                </CardHeader>
                <CardContent className="space-y-4">
                  <div className="space-y-3">
                    <div>
                      <div className="flex justify-between text-sm">
                        <span>CPU使用率</span>
                        <span>{realtimeMetrics.cpu_usage}%</span>
                      </div>
                      <Progress value={realtimeMetrics.cpu_usage} className="mt-1" />
                    </div>
                    <div>
                      <div className="flex justify-between text-sm">
                        <span>メモリ使用率</span>
                        <span>{realtimeMetrics.memory_usage}%</span>
                      </div>
                      <Progress value={realtimeMetrics.memory_usage} className="mt-1" />
                    </div>
                    <div>
                      <div className="flex justify-between text-sm">
                        <span>ディスク使用率</span>
                        <span>{realtimeMetrics.disk_usage}%</span>
                      </div>
                      <Progress value={realtimeMetrics.disk_usage} className="mt-1" />
                    </div>
                  </div>
                  <div className="grid grid-cols-2 gap-4 pt-4 border-t">
                    <div className="text-center">
                      <p className="text-2xl font-bold text-blue-600">
                        {realtimeMetrics.active_tasks}
                      </p>
                      <p className="text-sm text-gray-600">アクティブタスク</p>
                    </div>
                    <div className="text-center">
                      <p className="text-2xl font-bold text-green-600">
                        {realtimeMetrics.completed_today}
                      </p>
                      <p className="text-sm text-gray-600">今日の完了</p>
                    </div>
                  </div>
                </CardContent>
              </Card>

              {/* アクティブタスク */}
              <Card>
                <CardHeader>
                  <CardTitle className="flex items-center">
                    <Clock className="h-5 w-5 mr-2" />
                    アクティブタスク
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="space-y-3">
                    {activeTasks.map((task) => (
                      <div key={task.id} className="border rounded-lg p-3">
                        <div className="flex items-center justify-between mb-2">
                          <h4 className="font-medium text-sm">{task.title}</h4>
                          <Badge className={getPriorityColor(task.priority)}>
                            {task.priority}
                          </Badge>
                        </div>
                        <div className="flex items-center justify-between">
                          <span className="text-xs text-gray-600">
                            担当: {task.agent}
                          </span>
                          <span className="text-xs text-gray-600">
                            {task.progress}%
                          </span>
                        </div>
                        <Progress value={task.progress} className="mt-2" />
                      </div>
                    ))}
                  </div>
                </CardContent>
              </Card>
            </div>

            {/* Git活動履歴 */}
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center">
                  <GitBranch className="h-5 w-5 mr-2" />
                  Git活動履歴
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className="space-y-2">
                  {gitActivity.map((activity, index) => (
                    <div key={index} className="flex items-center space-x-3 py-2 border-b last:border-b-0">
                      <span className="text-xs text-gray-500 w-12">{activity.time}</span>
                      <Badge variant="outline" className="text-xs">
                        {activity.action}
                      </Badge>
                      <span className="text-sm font-medium">{activity.repo}</span>
                      <span className="text-sm text-gray-600 flex-1">{activity.message}</span>
                    </div>
                  ))}
                </div>
              </CardContent>
            </Card>
          </TabsContent>

          {/* エージェントタブ */}
          <TabsContent value="agents" className="space-y-4">
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
              {Object.entries(agentStats).map(([agentId, stats]) => (
                <Card key={agentId}>
                  <CardHeader className="pb-3">
                    <CardTitle className="flex items-center justify-between">
                      <span className="text-lg">{stats.role}</span>
                      <Users className="h-5 w-5 text-gray-400" />
                    </CardTitle>
                    <CardDescription>{agentId}</CardDescription>
                  </CardHeader>
                  <CardContent>
                    <div className="space-y-3">
                      <div className="flex justify-between">
                        <span className="text-sm text-gray-600">完了タスク</span>
                        <span className="font-semibold">{stats.tasks_completed}</span>
                      </div>
                      <div className="flex justify-between">
                        <span className="text-sm text-gray-600">品質スコア</span>
                        <span className="font-semibold">{stats.quality_score}%</span>
                      </div>
                      <Progress value={stats.quality_score} className="mt-2" />
                    </div>
                  </CardContent>
                </Card>
              ))}
            </div>

            {/* エージェント詳細統計 */}
            <Card>
              <CardHeader>
                <CardTitle>エージェント詳細統計</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                  <div className="text-center">
                    <p className="text-3xl font-bold text-blue-600">
                      {Object.values(agentStats).reduce((sum, agent) => sum + agent.tasks_completed, 0)}
                    </p>
                    <p className="text-sm text-gray-600">総完了タスク</p>
                  </div>
                  <div className="text-center">
                    <p className="text-3xl font-bold text-green-600">
                      {Math.round(Object.values(agentStats).reduce((sum, agent) => sum + agent.quality_score, 0) / Object.keys(agentStats).length)}%
                    </p>
                    <p className="text-sm text-gray-600">平均品質スコア</p>
                  </div>
                  <div className="text-center">
                    <p className="text-3xl font-bold text-purple-600">
                      {Object.keys(agentStats).length}
                    </p>
                    <p className="text-sm text-gray-600">アクティブエージェント</p>
                  </div>
                </div>
              </CardContent>
            </Card>
          </TabsContent>

          {/* MCPタブ */}
          <TabsContent value="mcp" className="space-y-4">
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
              <Card>
                <CardContent className="p-4">
                  <div className="flex items-center justify-between">
                    <div>
                      <p className="text-sm font-medium text-gray-600">総リクエスト</p>
                      <p className="text-2xl font-bold">{mcpStats.total_requests.toLocaleString()}</p>
                    </div>
                    <TrendingUp className="h-8 w-8 text-blue-500" />
                  </div>
                </CardContent>
              </Card>
              <Card>
                <CardContent className="p-4">
                  <div className="flex items-center justify-between">
                    <div>
                      <p className="text-sm font-medium text-gray-600">アクティブ接続</p>
                      <p className="text-2xl font-bold">{mcpStats.active_connections}</p>
                    </div>
                    <Network className="h-8 w-8 text-green-500" />
                  </div>
                </CardContent>
              </Card>
              <Card>
                <CardContent className="p-4">
                  <div className="flex items-center justify-between">
                    <div>
                      <p className="text-sm font-medium text-gray-600">平均応答時間</p>
                      <p className="text-2xl font-bold">{mcpStats.average_response_time}s</p>
                    </div>
                    <Zap className="h-8 w-8 text-yellow-500" />
                  </div>
                </CardContent>
              </Card>
              <Card>
                <CardContent className="p-4">
                  <div className="flex items-center justify-between">
                    <div>
                      <p className="text-sm font-medium text-gray-600">稼働時間</p>
                      <p className="text-2xl font-bold">{formatUptime(mcpStats.uptime)}</p>
                    </div>
                    <Clock className="h-8 w-8 text-purple-500" />
                  </div>
                </CardContent>
              </Card>
            </div>

            <Card>
              <CardHeader>
                <CardTitle>MCP Server 詳細情報</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                  <div>
                    <h4 className="font-semibold mb-3">接続統計</h4>
                    <div className="space-y-2">
                      <div className="flex justify-between">
                        <span>成功率</span>
                        <span className="font-semibold">
                          {((mcpStats.total_responses / mcpStats.total_requests) * 100).toFixed(1)}%
                        </span>
                      </div>
                      <div className="flex justify-between">
                        <span>エラー率</span>
                        <span className="font-semibold text-red-600">
                          {(((mcpStats.total_requests - mcpStats.total_responses) / mcpStats.total_requests) * 100).toFixed(1)}%
                        </span>
                      </div>
                    </div>
                  </div>
                  <div>
                    <h4 className="font-semibold mb-3">パフォーマンス</h4>
                    <div className="space-y-2">
                      <div className="flex justify-between">
                        <span>RPS</span>
                        <span className="font-semibold">
                          {(mcpStats.total_requests / (mcpStats.uptime / 60)).toFixed(1)}
                        </span>
                      </div>
                      <div className="flex justify-between">
                        <span>スループット</span>
                        <span className="font-semibold text-green-600">高</span>
                      </div>
                    </div>
                  </div>
                </div>
              </CardContent>
            </Card>
          </TabsContent>

          {/* VSCodeタブ */}
          <TabsContent value="vscode" className="space-y-4">
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              <Card>
                <CardContent className="p-4">
                  <div className="flex items-center justify-between">
                    <div>
                      <p className="text-sm font-medium text-gray-600">サーバー状態</p>
                      <p className="text-lg font-bold text-green-600">実行中</p>
                    </div>
                    <Monitor className="h-8 w-8 text-green-500" />
                  </div>
                </CardContent>
              </Card>
              <Card>
                <CardContent className="p-4">
                  <div className="flex items-center justify-between">
                    <div>
                      <p className="text-sm font-medium text-gray-600">ポート</p>
                      <p className="text-lg font-bold">8080</p>
                    </div>
                    <Terminal className="h-8 w-8 text-blue-500" />
                  </div>
                </CardContent>
              </Card>
              <Card>
                <CardContent className="p-4">
                  <div className="flex items-center justify-between">
                    <div>
                      <p className="text-sm font-medium text-gray-600">AI機能</p>
                      <p className="text-lg font-bold text-purple-600">有効</p>
                    </div>
                    <Code className="h-8 w-8 text-purple-500" />
                  </div>
                </CardContent>
              </Card>
            </div>

            <Card>
              <CardHeader>
                <CardTitle>VSCode 統合機能</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                  <div>
                    <h4 className="font-semibold mb-3">利用可能な機能</h4>
                    <ul className="space-y-2">
                      <li className="flex items-center">
                        <CheckCircle className="h-4 w-4 text-green-500 mr-2" />
                        <span>AI コード補完</span>
                      </li>
                      <li className="flex items-center">
                        <CheckCircle className="h-4 w-4 text-green-500 mr-2" />
                        <span>自動リファクタリング</span>
                      </li>
                      <li className="flex items-center">
                        <CheckCircle className="h-4 w-4 text-green-500 mr-2" />
                        <span>テスト生成</span>
                      </li>
                      <li className="flex items-center">
                        <CheckCircle className="h-4 w-4 text-green-500 mr-2" />
                        <span>コードレビュー</span>
                      </li>
                    </ul>
                  </div>
                  <div>
                    <h4 className="font-semibold mb-3">学習統計</h4>
                    <div className="space-y-2">
                      <div className="flex justify-between">
                        <span>編集履歴</span>
                        <span className="font-semibold">1,247</span>
                      </div>
                      <div className="flex justify-between">
                        <span>学習パターン</span>
                        <span className="font-semibold">89</span>
                      </div>
                      <div className="flex justify-between">
                        <span>AI提案採用率</span>
                        <span className="font-semibold text-green-600">78%</span>
                      </div>
                    </div>
                  </div>
                </div>
                <div className="mt-6">
                  <Button className="w-full">
                    <Eye className="h-4 w-4 mr-2" />
                    VSCode を開く
                  </Button>
                </div>
              </CardContent>
            </Card>
          </TabsContent>

          {/* Gitタブ */}
          <TabsContent value="git" className="space-y-4">
            <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
              <Card>
                <CardContent className="p-4">
                  <div className="flex items-center justify-between">
                    <div>
                      <p className="text-sm font-medium text-gray-600">リポジトリ</p>
                      <p className="text-2xl font-bold">2</p>
                    </div>
                    <GitBranch className="h-8 w-8 text-blue-500" />
                  </div>
                </CardContent>
              </Card>
              <Card>
                <CardContent className="p-4">
                  <div className="flex items-center justify-between">
                    <div>
                      <p className="text-sm font-medium text-gray-600">今日のコミット</p>
                      <p className="text-2xl font-bold">8</p>
                    </div>
                    <FileText className="h-8 w-8 text-green-500" />
                  </div>
                </CardContent>
              </Card>
              <Card>
                <CardContent className="p-4">
                  <div className="flex items-center justify-between">
                    <div>
                      <p className="text-sm font-medium text-gray-600">アクティブブランチ</p>
                      <p className="text-2xl font-bold">3</p>
                    </div>
                    <GitBranch className="h-8 w-8 text-purple-500" />
                  </div>
                </CardContent>
              </Card>
              <Card>
                <CardContent className="p-4">
                  <div className="flex items-center justify-between">
                    <div>
                      <p className="text-sm font-medium text-gray-600">AI生成コミット</p>
                      <p className="text-2xl font-bold">85%</p>
                    </div>
                    <Zap className="h-8 w-8 text-yellow-500" />
                  </div>
                </CardContent>
              </Card>
            </div>

            <Card>
              <CardHeader>
                <CardTitle>Git 操作履歴</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="space-y-3">
                  {gitActivity.map((activity, index) => (
                    <div key={index} className="flex items-center space-x-4 p-3 border rounded-lg">
                      <Badge variant="outline">{activity.action}</Badge>
                      <div className="flex-1">
                        <p className="font-medium">{activity.repo}</p>
                        <p className="text-sm text-gray-600">{activity.message}</p>
                      </div>
                      <span className="text-sm text-gray-500">{activity.time}</span>
                    </div>
                  ))}
                </div>
              </CardContent>
            </Card>
          </TabsContent>

          {/* システムタブ */}
          <TabsContent value="system" className="space-y-4">
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              <Card>
                <CardContent className="p-4">
                  <div className="flex items-center justify-between">
                    <div>
                      <p className="text-sm font-medium text-gray-600">CPU</p>
                      <p className="text-2xl font-bold">{realtimeMetrics.cpu_usage}%</p>
                    </div>
                    <Cpu className="h-8 w-8 text-blue-500" />
                  </div>
                  <Progress value={realtimeMetrics.cpu_usage} className="mt-2" />
                </CardContent>
              </Card>
              <Card>
                <CardContent className="p-4">
                  <div className="flex items-center justify-between">
                    <div>
                      <p className="text-sm font-medium text-gray-600">メモリ</p>
                      <p className="text-2xl font-bold">{realtimeMetrics.memory_usage}%</p>
                    </div>
                    <HardDrive className="h-8 w-8 text-green-500" />
                  </div>
                  <Progress value={realtimeMetrics.memory_usage} className="mt-2" />
                </CardContent>
              </Card>
              <Card>
                <CardContent className="p-4">
                  <div className="flex items-center justify-between">
                    <div>
                      <p className="text-sm font-medium text-gray-600">ディスク</p>
                      <p className="text-2xl font-bold">{realtimeMetrics.disk_usage}%</p>
                    </div>
                    <HardDrive className="h-8 w-8 text-purple-500" />
                  </div>
                  <Progress value={realtimeMetrics.disk_usage} className="mt-2" />
                </CardContent>
              </Card>
            </div>

            <Card>
              <CardHeader>
                <CardTitle>システム詳細情報</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                  <div>
                    <h4 className="font-semibold mb-3">QwQ-32B エンジン</h4>
                    <div className="space-y-2">
                      <div className="flex justify-between">
                        <span>モデル負荷</span>
                        <span className="font-semibold">65%</span>
                      </div>
                      <div className="flex justify-between">
                        <span>推論速度</span>
                        <span className="font-semibold text-green-600">高速</span>
                      </div>
                      <div className="flex justify-between">
                        <span>メモリ使用量</span>
                        <span className="font-semibold">12.4 GB</span>
                      </div>
                    </div>
                  </div>
                  <div>
                    <h4 className="font-semibold mb-3">ネットワーク</h4>
                    <div className="space-y-2">
                      <div className="flex justify-between">
                        <span>I/O レート</span>
                        <span className="font-semibold">{realtimeMetrics.network_io} MB/s</span>
                      </div>
                      <div className="flex justify-between">
                        <span>接続数</span>
                        <span className="font-semibold">7</span>
                      </div>
                      <div className="flex justify-between">
                        <span>レイテンシ</span>
                        <span className="font-semibold text-green-600">低</span>
                      </div>
                    </div>
                  </div>
                </div>
              </CardContent>
            </Card>
          </TabsContent>
        </Tabs>
      </div>
    </div>
  );
};

export default IntegratedDashboard;

