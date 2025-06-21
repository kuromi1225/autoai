"""
AutoAI バックエンドアプリケーション - メインエントリーポイント

Docker環境専用版app_docker.pyを使用してRead-only filesystem エラーを回避
"""

# Docker環境専用版アプリケーションをインポート
from app_docker import app, socketio

if __name__ == '__main__':
    # Docker環境専用版アプリケーションを起動
    socketio.run(app, host='0.0.0.0', port=5000, debug=False)

# WSGI アプリケーション（Gunicorn用）
application = app

