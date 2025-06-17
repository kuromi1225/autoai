# Devin AI Clone - API仕様書

## 概要

Devin AI Clone APIは、自律型AIエージェントシステムのバックエンドサービスです。RESTful APIとWebSocketを組み合わせて、リアルタイムなタスク実行と進捗管理を提供します。

## ベースURL

```
http://localhost:5000
```

## 認証

現在のバージョンでは、基本的な認証機能を提供しています。将来のバージョンでは、JWT認証が実装される予定です。

## エンドポイント一覧

### ヘルスチェック

#### GET /health

システムの健康状態を確認します。

**レスポンス例:**
```json
{
  "status": "healthy",
  "timestamp": "2025-06-13T18:00:00.000Z",
  "services": {
    "redis": "connected",
    "app": "running"
  }
}
```

### API ルート

#### GET /api/

API の基本情報とエンドポイント一覧を取得します。

**レスポンス例:**
```json
{
  "message": "Devin AI Clone API",
  "version": "1.0.0",
  "timestamp": "2025-06-13T18:00:00.000Z",
  "endpoints": {
    "health": "/health",
    "status": "/api/status",
    "projects": "/api/projects",
    "tasks": "/api/tasks",
    "chat": "/api/chat",
    "websocket": "/ws"
  }
}
```

#### GET /api/status

API の現在のステータスと設定情報を取得します。

**レスポンス例:**
```json
{
  "status": "running",
  "timestamp": "2025-06-13T18:00:00.000Z",
  "config": {
    "workspace_dir": "/app/workspace",
    "model_path": "/app/models/qwen",
    "github_configured": true,
    "openai_configured": false
  }
}
```

### プロジェクト管理

#### GET /api/projects

プロジェクト一覧を取得します。

**レスポンス例:**
```json
{
  "projects": [
    {
      "id": "default",
      "name": "Default Project",
      "description": "Default project for testing",
      "status": "active",
      "created_at": "2025-06-13T18:00:00.000Z"
    }
  ]
}
```

#### POST /api/projects

新しいプロジェクトを作成します。

**リクエストボディ:**
```json
{
  "name": "My New Project",
  "description": "Project description"
}
```

**レスポンス例:**
```json
{
  "id": "project_1718308800",
  "name": "My New Project",
  "description": "Project description",
  "status": "active",
  "created_at": "2025-06-13T18:00:00.000Z"
}
```

### タスク管理

#### GET /api/tasks

タスク一覧を取得します。

**レスポンス例:**
```json
{
  "tasks": []
}
```

#### POST /api/tasks

新しいタスクを作成し、非同期で実行します。

**リクエストボディ:**
```json
{
  "description": "Create a web application",
  "priority": 1,
  "metadata": {
    "type": "development",
    "language": "python"
  }
}
```

**レスポンス例:**
```json
{
  "id": "task_1718308800",
  "status": "queued",
  "message": "Task queued for processing"
}
```

### チャット

#### POST /api/chat

AIエージェントとチャットします。

**リクエストボディ:**
```json
{
  "message": "Hello, can you help me create a web application?"
}
```

**レスポンス例:**
```json
{
  "response": "受信したメッセージ: Hello, can you help me create a web application?",
  "timestamp": "2025-06-13T18:00:00.000Z"
}
```

## WebSocket API

### 接続

```javascript
const socket = io('http://localhost:5000');
```

### イベント

#### connect

WebSocket接続が確立されたときに発生します。

**受信データ:**
```json
{
  "message": "Connected to Devin AI Clone"
}
```

#### message

メッセージを送信します。

**送信データ:**
```json
{
  "message": "Hello AI"
}
```

**受信データ:**
```json
{
  "message": "Echo: Hello AI",
  "timestamp": "2025-06-13T18:00:00.000Z"
}
```

#### task_request

タスクの実行を要求します。

**送信データ:**
```json
{
  "description": "Create a simple web page",
  "priority": 1
}
```

**受信データ:**
```json
{
  "task_id": "task_1718308800",
  "status": "queued"
}
```

#### task_progress

タスクの進捗を受信します。

**受信データ:**
```json
{
  "task_id": "task_1718308800",
  "progress": 50,
  "message": "Processing..."
}
```

#### task_completed

タスクの完了を受信します。

**受信データ:**
```json
{
  "task_id": "task_1718308800",
  "status": "completed",
  "result": "Task completed successfully"
}
```

#### task_failed

タスクの失敗を受信します。

**受信データ:**
```json
{
  "task_id": "task_1718308800",
  "status": "failed",
  "error": "Error message"
}
```

## エラーハンドリング

### HTTPステータスコード

- `200 OK`: 成功
- `201 Created`: リソース作成成功
- `202 Accepted`: 非同期処理受付
- `400 Bad Request`: 不正なリクエスト
- `404 Not Found`: リソースが見つからない
- `500 Internal Server Error`: サーバー内部エラー
- `503 Service Unavailable`: サービス利用不可

### エラーレスポンス形式

```json
{
  "error": "Error message",
  "timestamp": "2025-06-13T18:00:00.000Z",
  "details": {
    "code": "ERROR_CODE",
    "description": "Detailed error description"
  }
}
```

## レート制限

現在のバージョンでは、レート制限は実装されていません。将来のバージョンで追加される予定です。

## 使用例

### Python

```python
import requests
import socketio

# REST API使用例
response = requests.get('http://localhost:5000/api/status')
print(response.json())

# WebSocket使用例
sio = socketio.Client()

@sio.event
def connect():
    print('Connected to server')
    sio.emit('message', {'message': 'Hello from Python'})

@sio.event
def response(data):
    print('Received:', data)

sio.connect('http://localhost:5000')
sio.wait()
```

### JavaScript

```javascript
// REST API使用例
fetch('http://localhost:5000/api/status')
  .then(response => response.json())
  .then(data => console.log(data));

// WebSocket使用例
const socket = io('http://localhost:5000');

socket.on('connect', () => {
  console.log('Connected to server');
  socket.emit('message', { message: 'Hello from JavaScript' });
});

socket.on('response', (data) => {
  console.log('Received:', data);
});
```

### cURL

```bash
# ヘルスチェック
curl http://localhost:5000/health

# プロジェクト作成
curl -X POST http://localhost:5000/api/projects \
  -H "Content-Type: application/json" \
  -d '{"name": "Test Project", "description": "Test description"}'

# チャット
curl -X POST http://localhost:5000/api/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "Hello AI"}'
```

## 開発者向け情報

### ローカル開発

```bash
# 開発サーバー起動
flask run --host=0.0.0.0 --port=5000 --debug

# テスト実行
python -m pytest tests/

# API文書生成
swagger-codegen generate -i api-spec.yaml -l html2 -o docs/
```

### デバッグ

```bash
# ログレベル設定
export FLASK_ENV=development
export LOG_LEVEL=DEBUG

# デバッグモードで起動
python app.py
```

## 今後の予定

### v1.1.0
- JWT認証の実装
- レート制限の追加
- API バージョニング

### v1.2.0
- GraphQL API の追加
- リアルタイム通知の強化
- パフォーマンス最適化

### v2.0.0
- マルチテナント対応
- 高度な権限管理
- 分散処理対応

---

この API 仕様書は、Devin AI Clone の現在の実装に基づいています。最新の情報については、[GitHub リポジトリ](https://github.com/your-username/devin-ai-clone)を参照してください。

