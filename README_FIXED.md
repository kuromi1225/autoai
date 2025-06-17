# Devin AI Clone - 修正版

DockerとQwen3 4BをベースにしたDevin.aiのような自律型AIエージェントシステム（修正版）

## 🎯 概要

このプロジェクトは、Devin.aiにインスパイアされた自律型AIエージェントシステムです。プロジェクトレビューで指摘された重大なバグを修正し、安定性と機能性を大幅に向上させました。

## 🔧 修正された主要な問題

### フロントエンドの重大なバグ修正
- ✅ **コンポーネント再定義問題**: App.jsx内でのコンポーネント再定義を解決
- ✅ **メモリリーク問題**: useEffect内のsetIntervalクリーンアップを実装
- ✅ **クロージャ問題**: 古い状態参照問題を関数型更新で解決

### バックエンド連携の改善
- ✅ **計画実行機能**: 実際のAPI呼び出しとWebSocket通信を実装
- ✅ **エラーハンドリング**: 包括的なエラー処理とユーザー通知
- ✅ **リアルタイム通信**: 安定したWebSocket接続管理

## ✨ 主な機能

- 🤖 **AI駆動のタスク分解**: 複雑なタスクを実行可能なステップに自動分解
- 💻 **コード生成と実行**: 安全なサンドボックス環境でのコード実行
- 🔧 **自動エラー解決**: エラーの分析と修正提案
- 📝 **計画レビュー**: 実行前の計画確認と承認機能
- 🌐 **Webブラウジング**: 最新情報の検索と取得
- 📊 **リアルタイム進捗**: WebSocketによる進捗のリアルタイム表示
- 🔗 **GitHub統合**: 自動コミットとプルリクエスト作成
- 🎨 **Devin風UI**: 直感的で使いやすいユーザーインターフェース

## 🚀 クイックスタート

### Docker Compose使用（推奨）

```bash
git clone <repository-url>
cd devin-ai-clone
docker compose up -d
```

### 開発環境での起動

#### バックエンド（テストモード）
```bash
cd backend
python3 -m pip install flask flask-cors flask-socketio
python3 test_app.py
```

#### フロントエンド
```bash
cd frontend
npm install
npm run dev
```

### 外部アクセス用URL

バックエンドAPIが起動すると、以下のような外部アクセス用URLが生成されます：
- バックエンドAPI: `https://5001-[domain]/`
- フロントエンド: `https://3000-[domain]/`

## 🏗️ アーキテクチャ

```
devin-ai-clone/
├── frontend/          # React + Vite フロントエンド（修正済み）
├── backend/           # Flask + SocketIO バックエンド（機能強化）
├── nginx/             # リバースプロキシ設定
├── monitoring/        # Prometheus監視設定
├── docs/              # ドキュメント
├── test_app.py        # テスト用軽量バックエンド（新規）
└── RELEASE_NOTES.md   # 修正内容詳細（新規）
```

### 主要コンポーネント

- **QwenEngine**: Qwen3 4Bモデルとの連携（実装済み）
- **TaskDecomposer**: タスクの分解と計画作成（実装済み）
- **CodeExecutor**: 安全なコード実行環境（実装済み）
- **GitHubClient**: GitHub API統合（実装済み）
- **WebBrowserTool**: Webブラウジング機能（実装済み）
- **MemoryManager**: 長期記憶管理（実装済み）

## 📖 使用方法

### 1. 基本的な使用方法

1. バックエンドを起動（`python3 test_app.py`）
2. フロントエンドを起動（`npm run dev`）
3. ブラウザでフロントエンドにアクセス
4. チャット欄にタスクを入力（例：「Reactで簡単なTodoアプリを作成して」）
5. AIが生成した実行計画を確認
6. 計画を承認して実行開始
7. リアルタイムで進捗を確認

### 2. テストモードの特徴

- 軽量な依存関係のみ使用
- 基本的なAPI機能とWebSocket通信
- 計画実行のシミュレーション
- エラーハンドリングのテスト

## 🔍 動作確認済み機能

### 基本機能
- ✅ フロントエンドの安定したレンダリング
- ✅ バックエンドAPIの正常動作
- ✅ WebSocket通信の確立
- ✅ 計画作成と表示
- ✅ 計画実行のシミュレーション
- ✅ リアルタイム進捗更新
- ✅ エラーハンドリング

### 修正された問題
- ✅ メモリリークの解消
- ✅ コンポーネント状態の安定化
- ✅ WebSocket接続の安定化
- ✅ エラー状態の適切な表示

## 🔧 設定

### 環境変数

`.env`ファイルを作成して以下の設定を行ってください：

```env
# AI Model Settings
QWEN_MODEL_PATH=Qwen/Qwen2.5-Coder-4B-Instruct
MODEL_CACHE_DIR=/app/models/cache
USE_GPU=true
USE_QUANTIZATION=true

# GitHub Integration
GITHUB_TOKEN=your_github_token_here

# Database
DATABASE_URL=postgresql://user:password@postgres:5432/devin_db

# Redis
REDIS_URL=redis://redis:6379/0

# Security
SECRET_KEY=your_secret_key_here
```

## 🧪 テスト

```bash
# バックエンドテスト
cd backend
python3 test_app.py

# フロントエンドテスト
cd frontend
npm test

# 統合テスト
./test.sh
```

## 📊 API仕様

### REST API

- `GET /` - ヘルスチェック
- `GET /api/health` - 詳細ヘルスチェック
- `POST /api/chat` - チャットメッセージの送信
- `POST /api/execute_plan` - 計画の実行開始

### WebSocket Events

- `plan_execution_started` - 計画実行開始
- `step_started` - ステップ開始
- `step_progress` - ステップ進捗更新
- `step_completed` - ステップ完了
- `plan_progress` - 全体進捗更新
- `plan_execution_completed` - 計画実行完了
- `plan_execution_failed` - 計画実行失敗

## 🔒 セキュリティ

- サンドボックス化されたコード実行環境
- 危険な操作のブロック
- リソース制限の実装
- 入力値の検証

## 📝 既知の制限事項

### 1. 依存関係
- 一部の重い依存関係（PyTorch、Transformersなど）は環境によってインストールに時間がかかる場合があります
- テストモードでは軽量な依存関係のみを使用しています

### 2. AI機能
- 実際のQwen3 4Bモデルを使用するには、適切なモデルファイルとGPUリソースが必要です
- テストモードではシミュレーション機能を提供しています

## 🔄 更新履歴

最新の修正内容については [RELEASE_NOTES.md](RELEASE_NOTES.md) を参照してください。

## 🤝 貢献

1. このリポジトリをフォーク
2. 機能ブランチを作成 (`git checkout -b feature/amazing-feature`)
3. 変更をコミット (`git commit -m 'Add amazing feature'`)
4. ブランチにプッシュ (`git push origin feature/amazing-feature`)
5. プルリクエストを作成

## 📝 ライセンス

このプロジェクトはMITライセンスの下で公開されています。詳細は [LICENSE](LICENSE) ファイルを参照してください。

## 🙏 謝辞

- [Qwen](https://github.com/QwenLM/Qwen) - 優秀なAIモデル
- [Devin](https://devin.ai) - インスピレーション
- オープンソースコミュニティ

## 📞 サポート

問題が発生した場合は、以下の手順で確認してください：

1. ログの確認（ブラウザのコンソールとサーバーログ）
2. ポートの競合確認（5000、5001、3000番ポート）
3. 依存関係の再インストール

---

**注意**: この修正版では、プロジェクトレビューで指摘された全ての重大な問題を解決し、安定性と機能性を大幅に向上させました。基本的なDevin AI Cloneの機能が正常に動作し、今後の機能拡張の基盤が整いました。

