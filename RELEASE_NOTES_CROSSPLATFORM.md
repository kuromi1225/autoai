# Devin AI Clone - クロスプラットフォーム対応版 リリースノート

## 🎉 v2.1.0 - クロスプラットフォーム対応版

### 🚀 新機能

#### クロスプラットフォーム対応
- **Windows完全対応**: PowerShell、コマンドプロンプト、Git Bash/WSLに対応
- **macOS対応**: ネイティブサポート
- **Linux対応**: 各種ディストリビューション対応

#### 起動スクリプト
- **start.sh**: Unix系OS用（macOS/Linux/WSL）
- **start.ps1**: PowerShell用（Windows推奨）
- **start.bat**: コマンドプロンプト用（Windows）

#### ネットワーク・ポート設定の改善
- **ネットワーク名変更**: `devin-ai-network`（競合回避）
- **サブネット変更**: `172.25.0.0/16`（競合回避）
- **ポート番号変更**: 一般的なポートとの競合を回避
  - メインアプリ: `8765` (旧: 8080)
  - HTTPS: `8766` (旧: 8443)
  - ChromaDB: `8767` (旧: 8001)
  - Prometheus: `8768` (旧: 9090)

### 🐛 修正された問題

#### Docker関連
- ✅ **ネットワーク競合エラー**: `Pool overlaps with other one on this address space`
- ✅ **ポート競合**: 80, 8080等の一般的なポートとの競合
- ✅ **ChromaDBヘルスチェック**: APIエンドポイントの修正

#### フロントエンド
- ✅ **白い画面問題**: Reactコンポーネントの無限ループ
- ✅ **TailwindCSS設定**: 必要な設定ファイルの追加
- ✅ **Zustandストア**: 状態管理の最適化

### 🔧 技術的改善

#### 自動化機能
- **シークレット自動生成**: JWT、DB、Redis、暗号化キー
- **環境設定自動化**: .envファイルの自動作成
- **ネットワーククリーンアップ**: 競合するネットワークの自動削除
- **ポート競合検出**: 使用中ポートの自動検出・警告

#### セキュリティ強化
- **Docker Secrets**: 本番環境対応の認証情報管理
- **権限制御**: ファイル権限の適切な設定
- **コンテナセキュリティ**: read-only、no-new-privileges等

#### 開発体験の向上
- **詳細なログ出力**: カラー付きステータス表示
- **エラーハンドリング**: 分かりやすいエラーメッセージ
- **ヘルスチェック**: 自動的なサービス状態確認

### 📁 新しいファイル

```
devin-ai-clone/
├── start.sh              # Unix系起動スクリプト
├── start.ps1             # PowerShell起動スクリプト  
├── start.bat             # Windows バッチファイル
├── README.md             # 更新されたドキュメント
├── Makefile              # 拡張された管理コマンド
└── docker-compose.yml    # 修正されたサービス定義
```

### 🚀 起動方法

#### Windows
```powershell
# PowerShell (推奨)
.\start.ps1

# コマンドプロンプト
start.bat

# Git Bash / WSL
./start.sh
```

#### macOS / Linux
```bash
./start.sh
```

### 📊 パフォーマンス

- **起動時間**: 約30-60秒（初回ビルド時は5-10分）
- **メモリ使用量**: 約4-6GB（全サービス起動時）
- **ディスク使用量**: 約2-3GB（イメージ含む）

### 🔗 アクセス情報

| サービス | URL | 説明 |
|---------|-----|------|
| メインアプリ | http://localhost:8765 | フロントエンド + API |
| ChromaDB | http://localhost:8767 | ベクトルDB管理画面 |
| Prometheus | http://localhost:8768 | 監視ダッシュボード |

### 🛠️ 管理コマンド

```bash
# 基本操作
make start              # サービス起動
make stop               # サービス停止
make restart            # サービス再起動
make logs               # ログ確認

# 開発・デバッグ
make health             # ヘルスチェック
make status             # サービス状態確認
make shell-backend      # バックエンドシェル
make clean              # 完全クリーンアップ

# データ管理
make backup-db          # データベースバックアップ
make restore-db         # データベース復元
```

### 🔄 アップグレード手順

既存のプロジェクトからのアップグレード：

1. **バックアップ作成**
   ```bash
   make backup-db
   ```

2. **サービス停止**
   ```bash
   make stop
   ```

3. **プロジェクト更新**
   ```bash
   # 新しいzipファイルを展開
   # または git pull
   ```

4. **再起動**
   ```bash
   ./start.sh  # または適切な起動スクリプト
   ```

### ⚠️ 注意事項

#### Windows環境
- **Docker Desktop必須**: WSL2バックエンド推奨
- **PowerShell実行ポリシー**: `Set-ExecutionPolicy RemoteSigned`が必要な場合があります
- **ファイルパス**: 長いパス名に注意（Windows制限）

#### macOS環境
- **Docker Desktop**: 最新版推奨
- **Rosetta 2**: Apple Siliconの場合、一部イメージで必要

#### Linux環境
- **Docker権限**: ユーザーをdockerグループに追加
- **systemd**: Docker自動起動の設定推奨

### 🐛 既知の問題

1. **初回起動時間**: イメージビルドで5-10分かかる場合があります
2. **メモリ不足**: 8GB未満のRAMでは動作が不安定な場合があります
3. **ポート競合**: 他のサービスが8765-8768を使用している場合は手動で停止が必要

### 📞 サポート

問題が発生した場合：

1. **ログ確認**: `make logs` または `docker compose logs`
2. **ヘルスチェック**: `make health`
3. **クリーンアップ**: `make clean` で完全リセット
4. **GitHub Issues**: バグ報告・機能要求

### 🎯 次期バージョン予定

- **v2.2.0**: AIエージェント機能の実装
- **v2.3.0**: GitHub統合の完成
- **v2.4.0**: Webブラウジング機能
- **v3.0.0**: 本格的な自律型エージェント

---

**リリース日**: 2025年6月17日  
**互換性**: Docker 20.10+, Docker Compose 2.0+  
**サポートOS**: Windows 10/11, macOS 10.15+, Linux (Ubuntu 20.04+)

