# Devin AI Clone - Windows Compatibility Guide

## 🔧 Windows環境での起動方法

### PowerShell (推奨)
```powershell
# 実行ポリシーを一時的に変更して実行
powershell.exe -ExecutionPolicy Bypass -File .\start.ps1

# または、実行ポリシーを永続的に変更
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
.\start.ps1
```

### コマンドプロンプト
```cmd
start.bat
```

### Git Bash / WSL
```bash
./start.sh
```

## 🐛 修正された問題

### 文字エンコーディングエラー
- **問題**: PowerShellスクリプトの日本語文字が文字化け
- **解決**: 全メッセージを英語に変更、UTF-8エンコーディングで保存

### 構文エラー
- **問題**: 文字化けによる構文エラー
- **解決**: スクリプト全体を英語で再作成

## 📋 起動オプション

### PowerShell版
```powershell
.\start.ps1           # 通常起動
.\start.ps1 -Clean    # クリーンアップ後起動
.\start.ps1 -Logs     # ログ表示付き起動
.\start.ps1 -Stop     # サービス停止
.\start.ps1 -Help     # ヘルプ表示
```

### バッチファイル版
```cmd
start.bat             # 通常起動のみ
```

## 🔍 トラブルシューティング

### 実行ポリシーエラー
```powershell
# エラー: このシステムではスクリプトの実行が無効になっています
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

### Docker未インストール
```
[ERROR] Docker is not installed or not accessible
```
→ Docker Desktopをインストール: https://www.docker.com/products/docker-desktop

### ポート競合
```
[WARNING] Port 8765 is in use
```
→ 使用中のサービスを停止するか、docker-compose.ymlでポート番号を変更

## 🎯 動作確認

起動成功時の表示例：
```
=== Devin AI Clone - Windows Startup ===

[SUCCESS] Docker found
[SUCCESS] Docker Compose found
[INFO] Initializing secrets...
[SUCCESS] Services started successfully!
[SUCCESS] All services are healthy!

=== Access Information ===
Main Application:  http://localhost:8765
ChromaDB Admin:    http://localhost:8767
Prometheus:        http://localhost:8768

Demo Accounts:
  admin / admin123 (Administrator)
  user / user123 (Regular User)
  demo / demo123 (Demo User)
```

## 🔐 セキュリティ

- シークレットファイルは自動生成されます
- 初回起動時に `secrets/` フォルダが作成されます
- 各サービス用のランダムパスワードが生成されます

これでWindows環境でも正常に動作するはずです！

