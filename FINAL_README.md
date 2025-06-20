# AutoAI - 汎用自律型AIエージェント

## 概要

AutoAIは、manus.aiやdevin.aiのような汎用自律型AIエージェントシステムです。ユーザーの要求を理解し、適切なツールを選択・実行して、複雑なタスクを自動化します。

## 主要機能

### 🤖 AIエージェント機能
- **タスク計画**: 複雑な要求を実行可能なタスクに分解
- **実行エンジン**: タスクの順次実行と進捗管理
- **自律判断**: 状況に応じた最適なツール選択

### 🛠️ 包括的ツールシステム
- **ファイル操作**: 読み書き、検索、管理
- **コード実行**: Python、JavaScript、Shell
- **ブラウザ自動化**: Web操作、スクレイピング
- **データ分析**: CSV処理、可視化
- **画像生成**: AI画像生成、編集
- **API連携**: 外部サービス統合
- **メール送信**: 自動通知機能

### 💬 リアルタイム通信
- **WebSocket**: リアルタイム双方向通信
- **ストリーミング**: 実行進捗のライブ更新
- **通知システム**: イベント通知

### 📁 ファイル・プロジェクト管理
- **セキュアファイルシステム**: 安全なファイル操作
- **プロジェクト管理**: テンプレート、インポート/エクスポート
- **コードエディター**: 統合開発環境

### 🎨 モダンUI
- **レスポンシブデザイン**: デスクトップ・モバイル対応
- **タブインターフェース**: 効率的な作業環境
- **リアルタイム更新**: 即座の状態反映

## アーキテクチャ

### バックエンド (Python/Flask)
```
backend/
├── integrated_app.py              # メインアプリケーション
├── ai_agent_enhanced.py           # 拡張AIエージェント
├── task_planner.py               # タスク計画システム
├── execution_engine.py           # 実行エンジン
├── realtime_communication.py    # リアルタイム通信
├── file_system_manager.py       # ファイルシステム管理
├── workspace_api.py             # ワークスペースAPI
├── api_routes.py                # APIルート
├── auth.py                      # 認証システム
├── models.py                    # データモデル
└── tools/
    ├── enhanced_tool_manager.py  # ツールマネージャー
    └── api_tools.py             # API連携ツール
```

### フロントエンド (React/Vite)
```
frontend/src/
├── IntegratedApp.jsx                    # メインアプリケーション
├── components/
│   ├── EnhancedMainChatInterface.jsx   # チャットインターフェース
│   ├── ProjectManager.jsx              # プロジェクト管理
│   └── LoginPage.jsx                   # ログインページ
├── store/
│   └── enhancedAppStore.js             # 状態管理
└── services/
    └── webSocketService.js             # WebSocket通信
```

## セットアップ

### 必要な環境
- Python 3.11+
- Node.js 20+
- Redis (オプション)

### バックエンドセットアップ
```bash
cd backend
pip install flask flask-cors flask-socketio redis aiohttp beautifulsoup4 pandas
python integrated_app.py
```

### フロントエンドセットアップ
```bash
cd frontend
npm install
npm run dev
```

### 環境変数
```bash
# .env
SECRET_KEY=your-secret-key
WORKSPACE_ROOT=/path/to/workspace
REDIS_URL=redis://localhost:6379/0
OPENAI_API_KEY=your-openai-key
GITHUB_TOKEN=your-github-token
SMTP_SERVER=smtp.gmail.com
SMTP_USERNAME=your-email
SMTP_PASSWORD=your-password
```

## 使用方法

### 1. 基本的な使い方
1. ブラウザで `http://localhost:3000` にアクセス
2. アカウント作成またはログイン
3. チャットインターフェースで要求を入力
4. AIが自動的にタスクを計画・実行

### 2. プロジェクト管理
- 新規プロジェクト作成
- テンプレートの選択（Python、JavaScript、Web）
- ファイルの編集・管理
- プロジェクトのインポート/エクスポート

### 3. ツール実行
- 直接ツール実行パネルから操作
- パラメータをJSON形式で指定
- リアルタイムで実行結果を確認

## API仕様

### 認証
```http
POST /api/auth/login
POST /api/auth/register
POST /api/auth/logout
```

### チャット
```http
POST /api/chat/message
GET /api/chat/history
```

### ワークスペース
```http
GET /api/workspace/files
POST /api/workspace/file
PUT /api/workspace/file/{path}
DELETE /api/workspace/file/{path}
```

### プロジェクト
```http
GET /api/workspace/projects
POST /api/workspace/projects
GET /api/workspace/projects/{name}
PUT /api/workspace/projects/{name}
DELETE /api/workspace/projects/{name}
```

### ツール実行
```http
POST /api/tools/execute
GET /api/tools/list
```

## テスト

### 統合テスト実行
```bash
python test_integration.py
```

### 手動テスト
1. ヘルスチェック: `curl http://localhost:5000/health`
2. システム情報: `curl http://localhost:5000/api/system/info`

## セキュリティ

- **認証**: JWT トークンベース認証
- **ファイルアクセス**: パストラバーサル攻撃防止
- **入力検証**: 全入力の検証・サニタイズ
- **CORS**: 適切なCORS設定

## パフォーマンス

- **非同期処理**: WebSocketによるリアルタイム通信
- **ストリーミング**: 大容量データの効率的処理
- **キャッシュ**: Redis による高速データアクセス

## 拡張性

- **プラグインシステム**: 新しいツールの簡単追加
- **モジュラー設計**: 独立したコンポーネント
- **API ファースト**: 外部システムとの連携

## ライセンス

MIT License

## 貢献

1. Fork the repository
2. Create a feature branch
3. Commit your changes
4. Push to the branch
5. Create a Pull Request

## サポート

- GitHub Issues: バグレポート・機能要求
- Documentation: 詳細なドキュメント
- Examples: 使用例とチュートリアル

---

**AutoAI** - あなたの作業を自動化する、次世代AIエージェント

