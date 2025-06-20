"""
Devin AI Clone - メインアプリケーション

このファイルは、Devin AI Cloneのメインアプリケーションエントリーポイントです。
Flask、WebSocket、Celery、MCPサーバーを統合し、AIエージェントの機能を提供します。
"""

import os
import logging
from flask import Flask, request, jsonify
from flask_cors import CORS
from flask_socketio import SocketIO, emit
from celery import Celery
import redis
import asyncio
from datetime import datetime

# 新しいインポート
from models import db
from api_routes import register_api_routes, init_ai_system

# 認証サービスのインポート
from services.auth_service import AuthService, require_auth, require_role

# --- 修正箇所: 開始 ---
# Docker secretsを読み込むためのヘルパー関数
def get_secret(secret_id, default=None):
    """Dockerシークレットまたは環境変数から値を取得します。"""
    secret_path = f'/run/secrets/{secret_id}'
    if os.path.exists(secret_path):
        with open(secret_path, 'r') as f:
            return f.read().strip()
    # 環境変数もフォールバックとしてチェック
    return os.environ.get(secret_id.upper(), default)

# 設定クラス
class Config:
    """アプリケーションの設定を管理します。"""
    # シークレットキー
    SECRET_KEY = get_secret("jwt_secret_key", "a-secure-dev-secret-key")

    # データベース接続URLを環境変数とシークレットから構築
    db_user = os.environ.get('DB_USER', 'postgres')
    db_password = get_secret('db_password', 'password')
    db_host = os.environ.get('DB_HOST', 'postgres')
    db_port = os.environ.get('DB_PORT', '5432')
    db_name = os.environ.get('DB_NAME', 'devin_ai_clone')
    SQLALCHEMY_DATABASE_URI = f"postgresql://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}"
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # Redis接続URLを環境変数とシークレットから構築
    redis_host = os.environ.get('REDIS_HOST', 'redis')
    redis_port = os.environ.get('REDIS_PORT', '6379')
    redis_password = get_secret('redis_password')
    if redis_password:
        REDIS_URL = f"redis://:{redis_password}@{redis_host}:{redis_port}/0"
    else:
        REDIS_URL = f"redis://{redis_host}:{redis_port}/0"

    # その他の設定
    GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN")
    OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")
    QWEN_MODEL_PATH = os.environ.get("QWEN_MODEL_PATH", "/app/models/qwen")
    WORKSPACE_DIR = os.environ.get("WORKSPACE_DIR", "/app/workspace")

# --- 修正箇所: 終了 ---

# Flaskアプリケーションの作成
app = Flask(__name__)
app.config.from_object(Config)

# データベース初期化
db.init_app(app)

# CORS設定
CORS(app, origins="*")

# 認証サービスの初期化
auth_service = AuthService(app)
app.auth_service = auth_service

# SocketIO設定
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='eventlet', message_queue=app.config['REDIS_URL'])

# Celery設定
def make_celery(app):
    celery = Celery(
        app.import_name,
        backend=app.config["REDIS_URL"],
        broker=app.config["REDIS_URL"]
    )
    celery.conf.update(app.config)
    return celery

celery = make_celery(app)

# Redis接続
try:
    redis_client = redis.from_url(app.config["REDIS_URL"], decode_responses=True)
    redis_client.ping() # 接続テスト
    logging.info("Successfully connected to Redis.")
except redis.exceptions.ConnectionError as e:
    logging.error(f"Failed to connect to Redis: {e}")
    redis_client = None

# ログ設定
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# API ルートを登録
register_api_routes(app, socketio)

# AI システムを初期化
init_ai_system(app)

# 既存のルート（認証関連）
@app.route('/health')
def health_check():
    """ヘルスチェックエンドポイント"""
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.utcnow().isoformat(),
        'version': '1.0.0'
    })

@app.route('/api/auth/users')
def get_demo_users():
    """デモユーザー一覧を取得"""
    demo_users = [
        {
            'id': 'admin',
            'username': 'admin',
            'email': 'admin@example.com',
            'role': 'admin',
            'display_name': 'Administrator'
        },
        {
            'id': 'user',
            'username': 'user',
            'email': 'user@example.com',
            'role': 'user',
            'display_name': 'Regular User'
        }
    ]
    return jsonify(demo_users)

@app.route('/api/auth/login', methods=['POST'])
def login():
    """ログイン処理"""
    data = request.get_json()
    username = data.get('username')
    password = data.get('password')
    
    # デモ用の簡単な認証
    if username in ['admin', 'user'] and password in ['admin', 'password']:
        # JWTトークンを生成（実装は後で）
        token = f"demo_token_{username}"
        
        return jsonify({
            'success': True,
            'token': token,
            'user': {
                'id': username,
                'username': username,
                'email': f'{username}@example.com',
                'role': 'admin' if username == 'admin' else 'user'
            }
        })
    else:
        return jsonify({
            'success': False,
            'error': 'Invalid credentials'
        }), 401

@app.route('/api/auth/refresh', methods=['POST'])
def refresh_token():
    """トークンリフレッシュ"""
    # 簡単な実装
    return jsonify({
        'success': True,
        'token': 'refreshed_token'
    })

# データベーステーブルの作成
@app.before_first_request
def create_tables():
    """アプリケーション起動時にデータベーステーブルを作成"""
    try:
        db.create_all()
        logger.info("Database tables created successfully")
    except Exception as e:
        logger.error(f"Failed to create database tables: {e}")

if __name__ == '__main__':
    # 開発環境での実行
    socketio.run(app, host='0.0.0.0', port=5000, debug=True)

    # その他の設定
    GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN")
    OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")
    QWEN_MODEL_PATH = os.environ.get("QWEN_MODEL_PATH", "/app/models/qwen")
    WORKSPACE_DIR = os.environ.get("WORKSPACE_DIR", "/app/workspace")

# --- 修正箇所: 終了 ---

# Flaskアプリケーションの作成
app = Flask(__name__)
app.config.from_object(Config)

# CORS設定
CORS(app, origins="*")

# 認証サービスの初期化
auth_service = AuthService(app)
app.auth_service = auth_service

# SocketIO設定
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='eventlet', message_queue=app.config['REDIS_URL'])

# Celery設定
def make_celery(app):
    celery = Celery(
        app.import_name,
        backend=app.config["REDIS_URL"],
        broker=app.config["REDIS_URL"]
    )
    celery.conf.update(app.config)
    return celery

celery = make_celery(app)

# Redis接続
try:
    redis_client = redis.from_url(app.config["REDIS_URL"], decode_responses=True)
    redis_client.ping() # 接続テスト
    logging.info("Successfully connected to Redis.")
except redis.exceptions.ConnectionError as e:
    logging.error(f"Failed to connect to Redis: {e}")
    redis_client = None

# ログ設定
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ヘルスチェックエンドポイント
@app.route("/health")
def health_check():
    """ヘルスチェックエンドポイント"""
    redis_status = 'disconnected'
    try:
        if redis_client:
            redis_client.ping()
            redis_status = 'connected'
        
        return jsonify({
            'status': 'healthy',
            'timestamp': datetime.utcnow().isoformat(),
            'services': {
                'redis': redis_status,
                'app': 'running',
                'auth': 'enabled'
            }
        }), 200
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return jsonify({
            'status': 'unhealthy',
            'timestamp': datetime.utcnow().isoformat(),
            'error': str(e),
            'services': {
                'redis': redis_status,
                'auth': 'enabled'
            }
        }), 503

# 認証エンドポイント
@app.route("/api/auth/login", methods=["POST"])
def login():
    """ログインエンドポイント"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'リクエストデータが必要です'}), 400
        
        username = data.get('username')
        password = data.get('password')
        
        if not username or not password:
            return jsonify({'error': 'ユーザー名とパスワードが必要です'}), 400
        
        result = auth_service.login(username, password)
        
        if result['success']:
            return jsonify({
                'success': True,
                'token': result['token'],
                'user': result['user'],
                'expires_in': result['expires_in']
            }), 200
        else:
            return jsonify({
                'success': False,
                'error': result['message']
            }), 401
            
    except Exception as e:
        logger.error(f"Login error: {e}")
        return jsonify({'error': 'ログイン処理中にエラーが発生しました'}), 500

@app.route("/api/auth/refresh", methods=["POST"])
def refresh_token():
    """トークンリフレッシュエンドポイント"""
    try:
        data = request.get_json()
        token = data.get('token') if data else None
        
        if not token:
            # Authorizationヘッダーからも確認
            if 'Authorization' in request.headers:
                auth_header = request.headers['Authorization']
                try:
                    token = auth_header.split(' ')[1]
                except IndexError:
                    pass
        
        if not token:
            return jsonify({'error': 'トークンが必要です'}), 400
        
        result = auth_service.refresh_token(token)
        
        if result['success']:
            return jsonify({
                'success': True,
                'token': result['token'],
                'expires_in': result['expires_in']
            }), 200
        else:
            return jsonify({
                'success': False,
                'error': result['message']
            }), 401
            
    except Exception as e:
        logger.error(f"Token refresh error: {e}")
        return jsonify({'error': 'トークンリフレッシュ中にエラーが発生しました'}), 500

@app.route("/api/auth/me", methods=["GET"])
@require_auth
def get_current_user():
    """現在のユーザー情報を取得"""
    return jsonify({
        'user': {
            'username': request.current_user['username'],
            'role': request.current_user['role'],
            'email': request.current_user['email']
        }
    }), 200

@app.route("/api/auth/users", methods=["GET"])
def get_demo_users():
    """デモ用ユーザー一覧を取得（開発用）"""
    return jsonify({
        'demo_users': [
            {'username': 'admin', 'password': 'admin123', 'role': 'admin'},
            {'username': 'user', 'password': 'user123', 'role': 'user'},
            {'username': 'demo', 'password': 'demo123', 'role': 'demo'}
        ],
        'note': 'これらは開発用のデモアカウントです'
    }), 200

# API ルート
@app.route("/api/")
def api_root():
    """API ルートエンドポイント"""
    return jsonify({
        'message': 'Devin AI Clone API',
        'version': '1.0.0',
        'timestamp': datetime.utcnow().isoformat(),
        'endpoints': {
            'health': '/health',
            'auth': {
                'login': '/api/auth/login',
                'refresh': '/api/auth/refresh',
                'me': '/api/auth/me',
                'demo_users': '/api/auth/users'
            },
            'status': '/api/status',
            'projects': '/api/projects',
            'tasks': '/api/tasks',
            'chat': '/api/chat',
            'websocket': '/ws'
        }
    })

@app.route("/api/status")
@require_auth
def api_status():
    """APIステータスエンドポイント（認証必要）"""
    return jsonify({
        'status': 'running',
        'timestamp': datetime.utcnow().isoformat(),
        'user': request.current_user['username'],
        'config': {
            'workspace_dir': app.config["WORKSPACE_DIR"],
            'model_path': app.config["QWEN_MODEL_PATH"],
            'github_configured': bool(app.config["GITHUB_TOKEN"]),
            'openai_configured': bool(app.config["OPENAI_API_KEY"])
        }
    })

@app.route("/api/projects", methods=["GET", "POST"])
@require_auth
def projects():
    """プロジェクト管理エンドポイント（認証必要）"""
    if request.method == 'GET':
        # プロジェクト一覧を返す
        return jsonify({
            'projects': [
                {
                    'id': 'default',
                    'name': 'Default Project',
                    'description': 'Default project for testing',
                    'status': 'active',
                    'owner': request.current_user['username'],
                    'created_at': datetime.utcnow().isoformat()
                }
            ]
        })
    
    elif request.method == 'POST':
        # 新しいプロジェクトを作成
        data = request.get_json()
        project_id = f"project_{int(datetime.utcnow().timestamp())}"
        
        return jsonify({
            'id': project_id,
            'name': data.get('name', 'New Project'),
            'description': data.get('description', ''),
            'status': 'active',
            'owner': request.current_user['username'],
            'created_at': datetime.utcnow().isoformat()
        }), 201

@app.route("/api/tasks", methods=["GET", "POST"])
@require_auth
def tasks():
    """タスク管理エンドポイント（認証必要）"""
    if request.method == 'GET':
        return jsonify({
            'tasks': []
        })
    
    elif request.method == 'POST':
        data = request.get_json()
        task_id = f"task_{int(datetime.utcnow().timestamp())}"
        
        # タスクを非同期で処理
        # process_task.delay(task_id, data)
        
        return jsonify({
            'task_id': task_id,
            'status': 'queued',
            'message': 'タスクがキューに追加されました',
            'created_by': request.current_user['username']
        }), 202
        
        return jsonify({
            'id': task_id,
            'status': 'queued',
            'message': 'Task queued for processing'
        }), 202

@app.route("/api/chat", methods=["POST"])
def chat():
    """チャットエンドポイント"""
    data = request.get_json()
    message = data.get('message', '')
    
    try:
        # タスク分析と計画作成
        from models.task_decomposer import TaskDecomposer
        from services.plan_reviewer import PlanReviewer
        
        task_decomposer = TaskDecomposer()
        plan_reviewer = PlanReviewer()
        
        # タスクを分析
        task_analysis = task_decomposer.analyze_task(message)
        
        # 実行計画を作成
        plan = plan_reviewer.create_plan(
            task_description=message,
            context={'user_input': message},
            user_preferences={}
        )
        
        response = f"タスクを分析し、実行計画を作成しました。{len(plan.steps)}個のステップで構成されています。"
        
        return jsonify({
            'response': response,
            'plan': plan.to_dict(),
            'timestamp': datetime.utcnow().isoformat()
        })
        
    except Exception as e:
        logger.error(f"Chat error: {e}")
        # フォールバック応答
        response = f"タスクを分析し、実行計画を作成しています..."
        
        # シンプルな計画を作成
        plan = {
            'plan_id': f'plan_{int(datetime.utcnow().timestamp())}',
            'title': 'タスクの実行',
            'description': message,
            'steps': [
                {
                    'id': 'step_1',
                    'title': '要件分析',
                    'description': 'タスクの詳細を分析し、技術要件を決定',
                    'estimated_time': 300,
                    'risk_level': 'low',
                    'reversible': True
                },
                {
                    'id': 'step_2',
                    'title': '実装',
                    'description': 'タスクを実装',
                    'estimated_time': 1200,
                    'risk_level': 'medium',
                    'reversible': True
                },
                {
                    'id': 'step_3',
                    'title': 'テスト',
                    'description': '実装をテスト',
                    'estimated_time': 600,
                    'risk_level': 'low',
                    'reversible': True
                }
            ],
            'estimated_total_time': 2100,
            'risk_assessment': {
                'overall_risk': 'medium',
                'high_risk_steps': 0,
                'medium_risk_steps': 1,
                'irreversible_steps': 0
            }
        }
        
        return jsonify({
            'response': response,
            'plan': plan,
            'timestamp': datetime.utcnow().isoformat()
        })

@app.route("/api/execute_plan", methods=["POST"])
def execute_plan():
    """計画実行エンドポイント"""
    data = request.get_json()
    plan_id = data.get('plan_id', '')
    
    try:
        # 計画実行を開始
        execute_plan_task.delay(plan_id)
        
        return jsonify({
            'status': 'started',
            'plan_id': plan_id,
            'message': '計画の実行を開始しました',
            'timestamp': datetime.utcnow().isoformat()
        })
        
    except Exception as e:
        logger.error(f"Plan execution error: {e}")
        return jsonify({
            'error': str(e),
            'timestamp': datetime.utcnow().isoformat()
        }), 500

@app.route("/api/web-search", methods=["POST"])
def web_search():
    """Web検索エンドポイント"""
    data = request.get_json()
    query = data.get('query', '')
    num_results = data.get('num_results', 5)
    
    try:
        from models.qwen_engine import QwenEngine
        qwen_engine = QwenEngine()
        
        results = qwen_engine.search_web(query, num_results)
        
        return jsonify({
            'results': results,
            'timestamp': datetime.utcnow().isoformat()
        })
        
    except Exception as e:
        logger.error(f"Web search error: {e}")
        return jsonify({
            'error': str(e),
            'timestamp': datetime.utcnow().isoformat()
        }), 500

@app.route("/api/plan", methods=["GET", "POST"])
def plan():
    """実行計画管理エンドポイント"""
    if request.method == 'GET':
        plan_id = request.args.get('plan_id')
        status = request.args.get('status')
        limit = int(request.args.get('limit', 10))
        
        try:
            from services.plan_reviewer import PlanReviewer
            plan_reviewer = PlanReviewer()
            
            if plan_id:
                # 特定の計画を取得
                plan = plan_reviewer.get_plan(plan_id)
                if plan:
                    return jsonify({
                        'plan': plan.to_dict(),
                        'timestamp': datetime.utcnow().isoformat()
                    })
                else:
                    return jsonify({
                        'error': 'Plan not found',
                        'timestamp': datetime.utcnow().isoformat()
                    }), 404
            else:
                # 計画一覧を取得
                from services.plan_reviewer import PlanStatus
                status_filter = PlanStatus(status) if status else None
                
                plans = plan_reviewer.list_plans(status=status_filter, limit=limit)
                
                return jsonify({
                    'plans': plans,
                    'timestamp': datetime.utcnow().isoformat()
                })
                
        except Exception as e:
            logger.error(f"Plan retrieval error: {e}")
            return jsonify({
                'error': str(e),
                'timestamp': datetime.utcnow().isoformat()
            }), 500
    
    elif request.method == 'POST':
        data = request.get_json()
        action = data.get('action', '')
        
        try:
            from services.plan_reviewer import PlanReviewer
            plan_reviewer = PlanReviewer()
            
            if action == 'create':
                task_description = data.get('task_description', '')
                context = data.get('context', {})
                user_preferences = data.get('user_preferences', {})
                
                plan = plan_reviewer.create_plan(
                    task_description=task_description,
                    context=context,
                    user_preferences=user_preferences
                )
                
                return jsonify({
                    'plan': plan.to_dict(),
                    'timestamp': datetime.utcnow().isoformat()
                }), 201
                
            elif action == 'submit_for_review':
                plan_id = data.get('plan_id', '')
                
                review_request = plan_reviewer.submit_for_review(plan_id)
                
                return jsonify({
                    'review_request': review_request,
                    'timestamp': datetime.utcnow().isoformat()
                })
                
            elif action == 'feedback':
                plan_id = data.get('plan_id', '')
                feedback_action = data.get('feedback_action', '')
                feedback = data.get('feedback', {})
                
                result = plan_reviewer.process_user_feedback(
                    plan_id=plan_id,
                    action=feedback_action,
                    feedback=feedback
                )
                
                return jsonify({
                    'result': result,
                    'timestamp': datetime.utcnow().isoformat()
                })
                
            else:
                return jsonify({
                    'error': 'Invalid action',
                    'timestamp': datetime.utcnow().isoformat()
                }), 400
                
        except Exception as e:
            logger.error(f"Plan operation error: {e}")
            return jsonify({
                'error': str(e),
                'timestamp': datetime.utcnow().isoformat()
            }), 500

@app.route("/api/self-improvement", methods=["GET", "POST"])
def self_improvement():
    """自己改善機能エンドポイント"""
    if request.method == 'GET':
        action = request.args.get('action', 'report')
        
        try:
            from services.self_improvement_tool import SelfImprovementTool
            improvement_tool = SelfImprovementTool()
            
            if action == 'report':
                # 改善報告書を取得
                report = improvement_tool.get_improvement_report()
                
                return jsonify({
                    'report': report,
                    'timestamp': datetime.utcnow().isoformat()
                })
                
            elif action == 'analyze':
                # ツールセットを分析
                issues = improvement_tool.analyze_tools()
                
                return jsonify({
                    'issues': [
                        {
                            'issue_id': issue.issue_id,
                            'file_path': issue.file_path,
                            'line_number': issue.line_number,
                            'issue_type': issue.issue_type.value,
                            'description': issue.description,
                            'severity': issue.severity,
                            'suggested_fix': issue.suggested_fix,
                            'timestamp': issue.timestamp.isoformat()
                        }
                        for issue in issues
                    ],
                    'timestamp': datetime.utcnow().isoformat()
                })
                
            else:
                return jsonify({
                    'error': 'Invalid action',
                    'timestamp': datetime.utcnow().isoformat()
                }), 400
                
        except Exception as e:
            logger.error(f"Self-improvement operation error: {e}")
            return jsonify({
                'error': str(e),
                'timestamp': datetime.utcnow().isoformat()
            }), 500
    
    elif request.method == 'POST':
        data = request.get_json()
        action = data.get('action', '')
        
        try:
            from services.self_improvement_tool import SelfImprovementTool, CodeIssue, IssueType
            improvement_tool = SelfImprovementTool()
            
            if action == 'auto_fix':
                issue_id = data.get('issue_id', '')
                
                # 問題を検索
                issue = None
                for existing_issue in improvement_tool.issues:
                    if existing_issue.issue_id == issue_id:
                        issue = existing_issue
                        break
                
                if not issue:
                    return jsonify({
                        'error': 'Issue not found',
                        'timestamp': datetime.utcnow().isoformat()
                    }), 404
                
                # 自動修正を試行
                fix_attempt = improvement_tool.auto_fix_issue(issue)
                
                return jsonify({
                    'fix_attempt': {
                        'attempt_id': fix_attempt.attempt_id,
                        'issue_id': fix_attempt.issue_id,
                        'fix_description': fix_attempt.fix_description,
                        'status': fix_attempt.status.value,
                        'test_results': fix_attempt.test_results,
                        'timestamp': fix_attempt.timestamp.isoformat()
                    },
                    'timestamp': datetime.utcnow().isoformat()
                })
                
            elif action == 'batch_fix':
                severity_filter = data.get('severity_filter', None)
                issue_type_filter = data.get('issue_type_filter', None)
                
                # フィルタに基づいて問題を選択
                issues_to_fix = []
                for issue in improvement_tool.issues:
                    if severity_filter and issue.severity != severity_filter:
                        continue
                    if issue_type_filter and issue.issue_type.value != issue_type_filter:
                        continue
                    issues_to_fix.append(issue)
                
                # バッチ修正を実行
                fix_results = []
                for issue in issues_to_fix[:10]:  # 最大10個まで
                    try:
                        fix_attempt = improvement_tool.auto_fix_issue(issue)
                        fix_results.append({
                            'attempt_id': fix_attempt.attempt_id,
                            'issue_id': fix_attempt.issue_id,
                            'status': fix_attempt.status.value,
                            'timestamp': fix_attempt.timestamp.isoformat()
                        })
                    except Exception as e:
                        fix_results.append({
                            'issue_id': issue.issue_id,
                            'status': 'error',
                            'error': str(e)
                        })
                
                return jsonify({
                    'batch_results': fix_results,
                    'total_processed': len(fix_results),
                    'timestamp': datetime.utcnow().isoformat()
                })
                
            else:
                return jsonify({
                    'error': 'Invalid action',
                    'timestamp': datetime.utcnow().isoformat()
                }), 400
                
        except Exception as e:
            logger.error(f"Self-improvement operation error: {e}")
            return jsonify({
                'error': str(e),
                'timestamp': datetime.utcnow().isoformat()
            }), 500

# WebSocketイベント
@socketio.on('connect')
def handle_connect():
    """WebSocket接続イベント"""
    logger.info(f"Client connected: {request.sid}")
    emit('status', {'message': 'Connected to Devin AI Clone'}) 

@socketio.on('disconnect')
def handle_disconnect():
    """WebSocket切断イベント"""
    logger.info(f"Client disconnected: {request.sid}")

@socketio.on('message')
def handle_message(data):
    """WebSocketメッセージイベント"""
    logger.info(f"Received message: {data}")
    
    # エコー応答
    emit('response', {
        'message': f"Echo: {data.get('message', '')}",
        'timestamp': datetime.utcnow().isoformat()
    })

@socketio.on('task_request')
def handle_task_request(data):
    """タスクリクエストイベント"""
    task_id = f"task_{int(datetime.utcnow().timestamp())}"
    
    # タスクを非同期で処理
    process_task.delay(task_id, data)
    
    emit('task_queued', {
        'task_id': task_id,
        'status': 'queued'
    })

# Celeryタスク
@celery.task
def process_task(task_id, task_data):
    """タスク処理（非同期）"""
    try:
        logger.info(f"Processing task: {task_id}")
        
        # タスク処理のシミュレーション
        import time
        time.sleep(2)
        
        # WebSocketで進捗を通知
        socketio.emit('task_progress', {
            'task_id': task_id,
            'progress': 50,
            'message': 'Processing...'
        })
        
        time.sleep(2)
        
        # 完了通知
        socketio.emit('task_completed', {
            'task_id': task_id,
            'status': 'completed',
            'result': 'Task completed successfully'
        })
        
        logger.info(f"Task completed: {task_id}")
        
    except Exception as e:
        logger.error(f"Task failed: {task_id}, error: {e}")
        
        socketio.emit('task_failed', {
            'task_id': task_id,
            'status': 'failed',
            'error': str(e)
        })

@celery.task
def execute_plan_task(plan_id):
    """計画実行タスク（非同期）"""
    try:
        logger.info(f"Executing plan: {plan_id}")
        
        # 計画実行開始の通知
        socketio.emit('plan_execution_started', {
            'plan_id': plan_id,
            'message': '計画の実行を開始しました'
        })
        
        # シミュレーション用のステップ
        steps = [
            {'id': 'step_1', 'title': '要件分析', 'estimated_time': 5},
            {'id': 'step_2', 'title': 'プロジェクト構造作成', 'estimated_time': 3},
            {'id': 'step_3', 'title': 'バックエンド実装', 'estimated_time': 20},
            {'id': 'step_4', 'title': 'フロントエンド実装', 'estimated_time': 30},
            {'id': 'step_5', 'title': 'GitHubコミット', 'estimated_time': 5}
        ]
        
        # 各ステップを順次実行
        for i, step in enumerate(steps):
            try:
                # ステップ開始の通知
                socketio.emit('step_started', {
                    'plan_id': plan_id,
                    'step_id': step['id'],
                    'step_index': i,
                    'step_title': step['title']
                })
                
                # ステップの実行（シミュレーション）
                import time
                execution_time = step['estimated_time']
                
                # 進捗の更新
                for progress in range(0, 101, 20):
                    time.sleep(execution_time / 5)
                    socketio.emit('step_progress', {
                        'plan_id': plan_id,
                        'step_id': step['id'],
                        'progress': progress,
                        'message': f'{step["title"]} - {progress}%完了'
                    })
                
                # ステップ完了の通知
                socketio.emit('step_completed', {
                    'plan_id': plan_id,
                    'step_id': step['id'],
                    'step_index': i,
                    'result': f'{step["title"]}が正常に完了しました'
                })
                
                # 全体の進捗を更新
                overall_progress = int((i + 1) / len(steps) * 100)
                socketio.emit('plan_progress', {
                    'plan_id': plan_id,
                    'progress': overall_progress,
                    'completed_steps': i + 1,
                    'total_steps': len(steps)
                })
                
            except Exception as step_error:
                logger.error(f"Step execution failed: {step['id']}, error: {step_error}")
                
                # ステップ失敗の通知
                socketio.emit('step_failed', {
                    'plan_id': plan_id,
                    'step_id': step['id'],
                    'step_index': i,
                    'error': str(step_error)
                })
                
                # 計画全体を失敗として処理
                socketio.emit('plan_execution_failed', {
                    'plan_id': plan_id,
                    'failed_step': step['id'],
                    'error': str(step_error)
                })
                return
        
        # 計画完了の通知
        socketio.emit('plan_execution_completed', {
            'plan_id': plan_id,
            'status': 'completed',
            'message': '計画が正常に完了しました',
            'completed_steps': len(steps)
        })
        
        logger.info(f"Plan execution completed: {plan_id}")
        
    except Exception as e:
        logger.error(f"Plan execution failed: {plan_id}, error: {e}")
        
        socketio.emit('plan_execution_failed', {
            'plan_id': plan_id,
            'error': str(e)
        })

# エラーハンドラー
@app.errorhandler(404)
def not_found(error):
    return jsonify({'error': 'Not found'}), 404

@app.errorhandler(500)
def internal_error(error):
    return jsonify({'error': 'Internal server error'}), 500

# メトリクスエンドポイント（Prometheus用）
@app.route("/metrics")
def metrics():
    """Prometheusメトリクスエンドポイント"""
    return "# Devin AI Clone Metrics\n# TODO: Implement metrics\n"

if __name__ == '__main__':
    # 開発環境での実行
    socketio.run(
        app, 
        host='0.0.0.0', 
        port=5000, 
        debug=os.environ.get('FLASK_ENV') == 'development',
        allow_unsafe_werkzeug=True
    )

@app.route("/api/parallel-execution", methods=["GET", "POST"])
def parallel_execution():
    """並列実行機能エンドポイント"""
    if request.method == 'GET':
        action = request.args.get('action', 'status')
        task_id = request.args.get('task_id')
        group_id = request.args.get('group_id')
        
        try:
            from services.parallel_task_executor import ParallelTaskExecutor
            from celery import Celery
            import redis
            
            # CeleryとRedisクライアントを初期化
            celery_app = Celery('devin_tasks', broker=app.config['REDIS_URL'], backend=app.config['REDIS_URL'])
            
            executor = ParallelTaskExecutor(celery_app, redis.from_url(app.config['REDIS_URL']))
            
            if action == 'status':
                # 実行状況を取得
                status = executor.get_execution_status(task_id)
                
                return jsonify({
                    'status': status,
                    'timestamp': datetime.utcnow().isoformat()
                })
                
            elif action == 'metrics':
                # パフォーマンスメトリクスを取得
                metrics = executor.get_performance_metrics()
                
                return jsonify({
                    'metrics': metrics,
                    'timestamp': datetime.utcnow().isoformat()
                })
                
            else:
                return jsonify({
                    'error': 'Invalid action',
                    'timestamp': datetime.utcnow().isoformat()
                }), 400
                
        except Exception as e:
            logger.error(f"Parallel execution operation error: {e}")
            return jsonify({
                'error': str(e),
                'timestamp': datetime.utcnow().isoformat()
            }), 500
    
    elif request.method == 'POST':
        data = request.get_json()
        action = data.get('action', '')
        
        try:
            from services.parallel_task_executor import ParallelTaskExecutor
            from models.task_decomposer import AdvancedTaskDecomposer
            from celery import Celery
            import redis
            
            # 必要なコンポーネントを初期化
            celery_app = Celery('devin_tasks', broker=app.config['REDIS_URL'], backend=app.config['REDIS_URL'])
            
            executor = ParallelTaskExecutor(celery_app, redis.from_url(app.config['REDIS_URL']))
            decomposer = AdvancedTaskDecomposer(qwen_engine)
            
            if action == 'execute_workflow':
                task_description = data.get('task_description', '')
                context = data.get('context', {})
                
                # タスクを分解
                task_nodes = decomposer.decompose_complex_task(task_description, context)
                
                # 並列実行分析
                parallel_analysis = decomposer.analyze_parallel_execution(task_nodes)
                
                # 並列ワークフローを実行
                def progress_callback(progress_info):
                    # WebSocketで進捗を送信
                    socketio.emit('task_progress', progress_info)
                
                workflow_result = executor.execute_parallel_workflow(
                    task_nodes, 
                    parallel_analysis,
                    progress_callback
                )
                
                return jsonify({
                    'workflow_result': workflow_result,
                    'task_nodes': [
                        {
                            'id': node.id,
                            'title': node.title,
                            'description': node.description,
                            'task_type': node.task_type.value,
                            'estimated_time': node.estimated_time
                        }
                        for node in task_nodes
                    ],
                    'parallel_analysis': parallel_analysis,
                    'timestamp': datetime.utcnow().isoformat()
                })
                
            elif action == 'cancel':
                task_id = data.get('task_id')
                group_id = data.get('group_id')
                
                # 実行をキャンセル
                cancel_result = executor.cancel_execution(task_id, group_id)
                
                return jsonify({
                    'cancel_result': cancel_result,
                    'timestamp': datetime.utcnow().isoformat()
                })
                
            elif action == 'retry':
                task_id = data.get('task_id', '')
                
                # 失敗したタスクを再試行
                retry_result = executor.retry_failed_task(task_id)
                
                return jsonify({
                    'retry_result': retry_result,
                    'timestamp': datetime.utcnow().isoformat()
                })
                
            else:
                return jsonify({
                    'error': 'Invalid action',
                    'timestamp': datetime.utcnow().isoformat()
                }), 400
                
        except Exception as e:
            logger.error(f"Parallel execution operation error: {e}")
            return jsonify({
                'error': str(e),
                'timestamp': datetime.utcnow().isoformat()
            }), 500
