# Devin AI Clone - クロスプラットフォーム対応版

DockerとQwen3 4BをベースにしたDevin.aiのような自律型AIエージェントシステムです。Windows、macOS、Linuxで動作します。

## 🚀 クイックスタート

### 前提条件

- **Docker Desktop** (Windows/Mac) または **Docker Engine** (Linux)
- **Git** (ソースコード取得用)
- **8GB以上のRAM** (推奨)

### 起動方法

#### Windows

**方法1: PowerShell (推奨)**
```powershell
# PowerShellを管理者権限で実行
.\start.ps1

# 監視サービスも含める場合
.\start.ps1 -Monitoring
```

**方法2: コマンドプロンプト**
```cmd
start.bat
```

**方法3: Git Bash / WSL**
```bash
chmod +x start.sh
./start.sh
```

#### macOS / Linux

```bash
chmod +x start.sh
./start.sh
```

### アクセス情報

起動完了後、以下のURLでアクセスできます：

- **メインアプリケーション**: http://localhost:8765
- **ChromaDB管理画面**: http://localhost:8767
- **Prometheus監視** (monitoring profile使用時): http://localhost:8768

## 🔧 ポート設定

従来の一般的なポート（80, 8080等）との競合を避けるため、以下のポートを使用します：

| サービス | ポート | 説明 |
|---------|--------|------|
| メインアプリ | 8765 | フロントエンド + API |
| HTTPS | 8766 | SSL/TLS接続用 |
| ChromaDB | 8767 | ベクトルデータベース管理 |
| Prometheus | 8768 | 監視・メトリクス |

## 🐛 トラブルシューティング

### ネットワーク競合エラー

```
Error response from daemon: Pool overlaps with other one on this address space
```

**解決方法:**
1. 起動スクリプトが自動的に競合するネットワークを削除します
2. 手動で削除する場合：
```bash
docker network rm devin-network
docker network rm devin-ai-clone_devin-network
```

### ポート競合エラー

ポートが使用中の場合、以下で確認できます：

**Windows:**
```powershell
netstat -ano | findstr :8765
```

**macOS/Linux:**
```bash
lsof -i :8765
```

### Docker関連のエラー

**Docker Desktopが起動していない (Windows/Mac):**
- Docker Desktopを起動してください

**権限エラー (Linux):**
```bash
sudo usermod -aG docker $USER
# ログアウト・ログインが必要
```

## 📁 プロジェクト構成

```
devin-ai-clone/
├── backend/              # Flask API サーバー
├── frontend/             # React フロントエンド
├── nginx/                # リバースプロキシ
├── chromadb/             # ベクトルデータベース
├── monitoring/           # Prometheus設定
├── secrets/              # 認証情報（自動生成）
├── docker-compose.yml    # サービス定義
├── start.sh              # Unix系起動スクリプト
├── start.ps1             # PowerShell起動スクリプト
├── start.bat             # Windows バッチファイル
└── README.md             # このファイル
```

## 🔐 セキュリティ

起動時に以下のシークレットファイルが自動生成されます：

- `secrets/jwt_secret_key.txt` - JWT認証用
- `secrets/db_password.txt` - データベースパスワード
- `secrets/redis_password.txt` - Redisパスワード
- `secrets/encryption_key.txt` - 暗号化キー

これらのファイルは本番環境では適切に管理してください。

## 🛠️ 開発・管理コマンド

### サービス管理

```bash
# サービス状態確認
docker compose ps

# ログ確認
docker compose logs -f

# 特定サービスのログ
docker compose logs -f backend

# サービス停止
docker compose down

# 完全クリーンアップ（データも削除）
docker compose down -v --remove-orphans

# サービス再起動
docker compose restart

# 特定サービスの再起動
docker compose restart backend
```

### 開発モード

フロントエンドの開発時：

```bash
cd frontend
npm install
npm run dev
# http://localhost:3000 でアクセス
```

バックエンドの開発時：

```bash
cd backend
pip install -r requirements.txt
python app.py
# http://localhost:5000 でアクセス
```

## 🌟 主要機能

### 実装済み機能

- ✅ **Dockerコンテナ化**: 完全なコンテナ環境
- ✅ **クロスプラットフォーム対応**: Windows/Mac/Linux
- ✅ **フロントエンド**: React + TailwindCSS
- ✅ **バックエンドAPI**: Flask + PostgreSQL + Redis
- ✅ **ベクトルデータベース**: ChromaDB統合
- ✅ **監視システム**: Prometheus統合
- ✅ **セキュリティ**: Docker Secrets + 権限制御

### 開発中の機能

- 🚧 **AIエージェント**: Qwen3 4B統合
- 🚧 **タスク管理**: 自動タスク分解・実行
- 🚧 **GitHub統合**: 自動コミット・プルリクエスト
- 🚧 **Webブラウジング**: 情報収集機能
- 🚧 **長期記憶**: 学習・経験蓄積

## 📝 ライセンス

MIT License

## 🤝 コントリビューション

プルリクエストやイシューの報告を歓迎します。

## 📞 サポート

問題が発生した場合：

1. [トラブルシューティング](#-トラブルシューティング)を確認
2. `docker compose logs`でログを確認
3. GitHubのIssuesで報告

---

**注意**: このプロジェクトは開発中です。本番環境での使用前に十分なテストを行ってください。

