"""
AutoAI バックエンドアプリケーション - メインエントリーポイント

修正版app_fixed.pyを使用してSQLAlchemyエラーを回避
"""

# 修正版アプリケーションをインポート
from app_fixed import app, socketio

if __name__ == '__main__':
    # 修正版アプリケーションを起動
    socketio.run(app, host='0.0.0.0', port=5000, debug=False)

# WSGI アプリケーション（Gunicorn用）
application = app

