"""
Enhanced API Blueprints with Complete Error Handling

統一されたエラーハンドリングと完全実装されたAPIエンドポイント
"""

from flask import Blueprint, request, jsonify, current_app
from functools import wraps
import logging
import traceback
from datetime import datetime
from typing import Dict, Any, Optional, Tuple
import json

from services.jwt_auth import require_auth, require_role, get_auth_manager
from services.git_settings import GitSettings
from services.resource_manager import ACUManager
from services.secure_code_executor import SecureCodeExecutor
from services.secret_manager import get_secret_manager

logger = logging.getLogger(__name__)

# エラーコード定義
class ErrorCodes:
    # 一般的なエラー
    INVALID_REQUEST = "INVALID_REQUEST"
    UNAUTHORIZED = "UNAUTHORIZED"
    FORBIDDEN = "FORBIDDEN"
    NOT_FOUND = "NOT_FOUND"
    INTERNAL_ERROR = "INTERNAL_SERVER_ERROR"
    
    # 認証関連
    INVALID_CREDENTIALS = "INVALID_CREDENTIALS"
    TOKEN_EXPIRED = "TOKEN_EXPIRED"
    TOKEN_INVALID = "TOKEN_INVALID"
    
    # Git関連
    GIT_CONFIG_INVALID = "GIT_CONFIG_INVALID"
    GIT_CONNECTION_FAILED = "GIT_CONNECTION_FAILED"
    GIT_OPERATION_FAILED = "GIT_OPERATION_FAILED"
    
    # リソース関連
    RESOURCE_LIMIT_EXCEEDED = "RESOURCE_LIMIT_EXCEEDED"
    RESOURCE_UNAVAILABLE = "RESOURCE_UNAVAILABLE"
    
    # 実行関連
    CODE_VALIDATION_FAILED = "CODE_VALIDATION_FAILED"
    EXECUTION_FAILED = "EXECUTION_FAILED"
    EXECUTION_TIMEOUT = "EXECUTION_TIMEOUT"

class APIError(Exception):
    """API専用例外クラス"""
    
    def __init__(self, message: str, error_code: str, status_code: int = 400, details: Optional[Dict] = None):
        self.message = message
        self.error_code = error_code
        self.status_code = status_code
        self.details = details or {}
        super().__init__(self.message)

def handle_api_errors(f):
    """APIエラーハンドリングデコレーター"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        try:
            return f(*args, **kwargs)
        except APIError as e:
            logger.warning(f"API Error in {f.__name__}: {e.message}")
            return jsonify({
                'success': False,
                'error': {
                    'code': e.error_code,
                    'message': e.message,
                    'details': e.details
                },
                'timestamp': datetime.utcnow().isoformat()
            }), e.status_code
        except Exception as e:
            logger.error(f"Unexpected error in {f.__name__}: {str(e)}")
            logger.error(traceback.format_exc())
            return jsonify({
                'success': False,
                'error': {
                    'code': ErrorCodes.INTERNAL_ERROR,
                    'message': 'An unexpected error occurred',
                    'details': {'trace_id': datetime.utcnow().isoformat()}
                },
                'timestamp': datetime.utcnow().isoformat()
            }), 500
    return decorated_function

def validate_json_request(required_fields: list = None):
    """JSONリクエストバリデーションデコレーター"""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not request.is_json:
                raise APIError(
                    "Request must be JSON",
                    ErrorCodes.INVALID_REQUEST,
                    400
                )
            
            data = request.get_json()
            if not data:
                raise APIError(
                    "Request body is required",
                    ErrorCodes.INVALID_REQUEST,
                    400
                )
            
            if required_fields:
                missing_fields = [field for field in required_fields if field not in data]
                if missing_fields:
                    raise APIError(
                        f"Missing required fields: {', '.join(missing_fields)}",
                        ErrorCodes.INVALID_REQUEST,
                        400,
                        {'missing_fields': missing_fields}
                    )
            
            return f(*args, **kwargs)
        return decorated_function
    return decorator

# Git設定管理Blueprint
git_bp = Blueprint('git', __name__, url_prefix='/api/git')

@git_bp.route('/settings', methods=['GET'])
@require_auth
@handle_api_errors
def get_git_settings():
    """Git設定を取得"""
    user = getattr(request, 'current_user', None)
    
    try:
        git_settings = GitSettings()
        settings = git_settings.get_user_settings(user['id'])
        
        # アクセストークンをマスク
        if settings.get('access_token'):
            settings['access_token'] = '***'
        
        return jsonify({
            'success': True,
            'data': settings
        })
        
    except Exception as e:
        raise APIError(
            "Failed to retrieve Git settings",
            ErrorCodes.INTERNAL_ERROR,
            500,
            {'original_error': str(e)}
        )

@git_bp.route('/settings', methods=['POST'])
@require_auth
@handle_api_errors
@validate_json_request(['repository_url', 'username', 'access_token'])
def save_git_settings():
    """Git設定を保存"""
    user = getattr(request, 'current_user', None)
    data = request.get_json()
    
    try:
        git_settings = GitSettings()
        
        # 設定の検証
        validation_result = git_settings.validate_settings(data)
        if not validation_result['valid']:
            raise APIError(
                "Invalid Git settings",
                ErrorCodes.GIT_CONFIG_INVALID,
                400,
                {'validation_errors': validation_result['errors']}
            )
        
        # 設定を保存
        success = git_settings.save_user_settings(user['id'], data)
        if not success:
            raise APIError(
                "Failed to save Git settings",
                ErrorCodes.INTERNAL_ERROR,
                500
            )
        
        return jsonify({
            'success': True,
            'message': 'Git設定を保存しました'
        })
        
    except APIError:
        raise
    except Exception as e:
        raise APIError(
            "Failed to save Git settings",
            ErrorCodes.INTERNAL_ERROR,
            500,
            {'original_error': str(e)}
        )

@git_bp.route('/test', methods=['POST'])
@require_auth
@handle_api_errors
def test_git_connection():
    """Git接続をテスト"""
    user = getattr(request, 'current_user', None)
    
    try:
        git_settings = GitSettings()
        settings = git_settings.get_user_settings(user['id'])
        
        if not settings.get('is_configured'):
            raise APIError(
                "Git settings not configured",
                ErrorCodes.GIT_CONFIG_INVALID,
                400
            )
        
        # 接続テスト
        result = git_settings.test_connection(
            settings['repository_url'],
            settings['username'],
            settings['access_token']
        )
        
        if not result['success']:
            raise APIError(
                "Git connection test failed",
                ErrorCodes.GIT_CONNECTION_FAILED,
                400,
                {'test_result': result}
            )
        
        return jsonify({
            'success': True,
            'message': '接続テストが成功しました',
            'data': result
        })
        
    except APIError:
        raise
    except Exception as e:
        raise APIError(
            "Connection test failed",
            ErrorCodes.GIT_CONNECTION_FAILED,
            500,
            {'original_error': str(e)}
        )

# リソース管理Blueprint
resources_bp = Blueprint('resources', __name__, url_prefix='/api/resources')

@resources_bp.route('/limits', methods=['GET'])
@require_auth
@handle_api_errors
def get_resource_limits():
    """ユーザーのリソース制限を取得"""
    user = getattr(request, 'current_user', None)
    
    try:
        acu_manager = ACUManager()
        limits = acu_manager.get_user_limits(user['id'])
        
        return jsonify({
            'success': True,
            'data': {
                'max_cpu_percent': limits.max_cpu_percent,
                'max_memory_mb': limits.max_memory_mb,
                'max_execution_time': limits.max_execution_time,
                'max_processes': limits.max_processes,
                'max_file_size_mb': limits.max_file_size_mb,
                'max_network_requests': limits.max_network_requests
            }
        })
        
    except Exception as e:
        raise APIError(
            "Failed to retrieve resource limits",
            ErrorCodes.INTERNAL_ERROR,
            500,
            {'original_error': str(e)}
        )

@resources_bp.route('/limits', methods=['POST'])
@require_role('admin')
@handle_api_errors
@validate_json_request(['user_id'])
def set_resource_limits():
    """ユーザーのリソース制限を設定（管理者のみ）"""
    data = request.get_json()
    
    try:
        from services.resource_manager import ResourceLimits
        
        acu_manager = ACUManager()
        
        # 新しい制限を作成
        limits = ResourceLimits(
            max_cpu_percent=data.get('max_cpu_percent', 80.0),
            max_memory_mb=data.get('max_memory_mb', 2048),
            max_execution_time=data.get('max_execution_time', 300),
            max_processes=data.get('max_processes', 50),
            max_file_size_mb=data.get('max_file_size_mb', 100),
            max_network_requests=data.get('max_network_requests', 100)
        )
        
        success = acu_manager.set_user_limits(data['user_id'], limits)
        if not success:
            raise APIError(
                "Failed to set resource limits",
                ErrorCodes.INTERNAL_ERROR,
                500
            )
        
        return jsonify({
            'success': True,
            'message': 'リソース制限を設定しました'
        })
        
    except APIError:
        raise
    except Exception as e:
        raise APIError(
            "Failed to set resource limits",
            ErrorCodes.INTERNAL_ERROR,
            500,
            {'original_error': str(e)}
        )

@resources_bp.route('/usage', methods=['GET'])
@require_auth
@handle_api_errors
def get_resource_usage():
    """リソース使用状況を取得"""
    user = getattr(request, 'current_user', None)
    days = request.args.get('days', 7, type=int)
    
    try:
        acu_manager = ACUManager()
        
        # 使用統計を取得
        stats = acu_manager.get_usage_statistics(user['id'], days)
        
        # 現在のシステム状況
        system_status = acu_manager.get_system_status()
        
        return jsonify({
            'success': True,
            'data': {
                'user_stats': stats,
                'system_status': system_status
            }
        })
        
    except Exception as e:
        raise APIError(
            "Failed to retrieve resource usage",
            ErrorCodes.INTERNAL_ERROR,
            500,
            {'original_error': str(e)}
        )

# コード実行Blueprint
execution_bp = Blueprint('execution', __name__, url_prefix='/api/execution')

@execution_bp.route('/health', methods=['GET'])
@handle_api_errors
def execution_health():
    """実行環境のヘルスチェック"""
    try:
        executor = SecureCodeExecutor()
        is_healthy = executor.health_check()
        resource_usage = executor.get_resource_usage()
        
        return jsonify({
            'success': True,
            'data': {
                'healthy': is_healthy,
                'resource_usage': resource_usage,
                'timestamp': datetime.utcnow().isoformat()
            }
        })
        
    except Exception as e:
        raise APIError(
            "Health check failed",
            ErrorCodes.INTERNAL_ERROR,
            500,
            {'original_error': str(e)}
        )

@execution_bp.route('/execute', methods=['POST'])
@require_auth
@handle_api_errors
@validate_json_request(['code', 'language'])
def execute_code():
    """コードを実行"""
    user = getattr(request, 'current_user', None)
    data = request.get_json()
    
    try:
        acu_manager = ACUManager()
        executor = SecureCodeExecutor()
        
        code = data['code']
        language = data['language']
        requirements = data.get('requirements', [])
        
        # コードの安全性検証
        validation_result = executor.validate_code(code)
        if not validation_result['safe']:
            raise APIError(
                "Code validation failed",
                ErrorCodes.CODE_VALIDATION_FAILED,
                400,
                {
                    'warnings': validation_result['warnings'],
                    'blocked_patterns': validation_result.get('blocked_patterns', [])
                }
            )
        
        # リソース利用可能性チェック
        estimated_usage = {
            'cpu_percent': 30,  # 推定値
            'memory_mb': 256,   # 推定値
            'execution_time': 60,  # 推定値
            'process_count': 1
        }
        
        availability = acu_manager.check_resource_availability(user['id'], estimated_usage)
        if not availability['available']:
            raise APIError(
                "Insufficient resources",
                ErrorCodes.RESOURCE_UNAVAILABLE,
                429,
                {'availability_check': availability}
            )
        
        # タスクIDを生成
        task_id = f"exec_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}_{user['id'][:8]}"
        
        # リソースを割り当て
        allocation_success = acu_manager.allocate_resources(user['id'], task_id, estimated_usage)
        if not allocation_success:
            raise APIError(
                "Resource allocation failed",
                ErrorCodes.RESOURCE_UNAVAILABLE,
                500
            )
        
        try:
            # コード実行
            if language.lower() == 'python':
                result = executor.execute_python(code, requirements)
            else:
                raise APIError(
                    f"Unsupported language: {language}",
                    ErrorCodes.INVALID_REQUEST,
                    400
                )
            
            return jsonify({
                'success': True,
                'data': {
                    'task_id': task_id,
                    'output': result.get('output', ''),
                    'error': result.get('error', ''),
                    'execution_time': result.get('execution_time', 0),
                    'resource_usage': result.get('resource_usage', {})
                }
            })
            
        finally:
            # リソースを解放
            acu_manager.release_resources(user['id'], task_id)
        
    except APIError:
        raise
    except Exception as e:
        raise APIError(
            "Code execution failed",
            ErrorCodes.EXECUTION_FAILED,
            500,
            {'original_error': str(e)}
        )

@execution_bp.route('/tasks/<task_id>/status', methods=['GET'])
@require_auth
@handle_api_errors
def get_task_status(task_id):
    """タスクの実行状況を取得"""
    user = getattr(request, 'current_user', None)
    
    try:
        acu_manager = ACUManager()
        
        # ユーザーのアクティブタスクを確認
        if user['id'] not in acu_manager.active_tasks:
            raise APIError(
                "Task not found",
                ErrorCodes.NOT_FOUND,
                404
            )
        
        user_tasks = acu_manager.active_tasks[user['id']]
        if task_id not in user_tasks:
            raise APIError(
                "Task not found",
                ErrorCodes.NOT_FOUND,
                404
            )
        
        task_info = user_tasks[task_id]
        
        return jsonify({
            'success': True,
            'data': {
                'task_id': task_id,
                'status': 'running',
                'start_time': task_info['start_time'].isoformat(),
                'estimated_usage': task_info['estimated_usage'],
                'current_usage': task_info.get('current_usage', {})
            }
        })
        
    except APIError:
        raise
    except Exception as e:
        raise APIError(
            "Failed to get task status",
            ErrorCodes.INTERNAL_ERROR,
            500,
            {'original_error': str(e)}
        )

# 計画管理Blueprint
plan_bp = Blueprint('plan', __name__, url_prefix='/api/plan')

@plan_bp.route('/create', methods=['POST'])
@require_auth
@handle_api_errors
@validate_json_request(['description'])
def create_plan():
    """実行計画を作成"""
    user = getattr(request, 'current_user', None)
    data = request.get_json()
    
    try:
        # TODO: 実際のAIモデルとの連携
        # 現在はモック実装
        
        plan = {
            'plan_id': f"plan_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}_{user['id'][:8]}",
            'title': f"計画: {data['description'][:50]}...",
            'description': data['description'],
            'steps': [
                {
                    'id': 'step_1',
                    'title': 'プロジェクト初期化',
                    'description': 'プロジェクトディレクトリを作成し、基本構造をセットアップします',
                    'estimated_time': 60,
                    'risk_level': 'low',
                    'reversible': True
                },
                {
                    'id': 'step_2',
                    'title': 'コード生成',
                    'description': '要求仕様に基づいてコードを生成します',
                    'estimated_time': 300,
                    'risk_level': 'medium',
                    'reversible': True
                }
            ],
            'estimated_total_time': 360,
            'risk_assessment': {
                'overall_risk': 'medium',
                'high_risk_steps': 0,
                'medium_risk_steps': 1,
                'irreversible_steps': 0
            }
        }
        
        return jsonify({
            'success': True,
            'data': plan
        })
        
    except Exception as e:
        raise APIError(
            "Failed to create plan",
            ErrorCodes.INTERNAL_ERROR,
            500,
            {'original_error': str(e)}
        )

@plan_bp.route('/<plan_id>/execute', methods=['POST'])
@require_auth
@handle_api_errors
def execute_plan(plan_id):
    """計画を実行"""
    user = getattr(request, 'current_user', None)
    
    try:
        # TODO: 実際の計画実行ロジック
        # 現在はモック実装
        
        logger.info(f"Executing plan {plan_id} for user {user['username']}")
        
        return jsonify({
            'success': True,
            'message': f'計画 {plan_id} の実行を開始しました',
            'data': {
                'plan_id': plan_id,
                'execution_id': f"exec_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}",
                'status': 'started'
            }
        })
        
    except Exception as e:
        raise APIError(
            "Failed to execute plan",
            ErrorCodes.EXECUTION_FAILED,
            500,
            {'original_error': str(e)}
        )

def register_blueprints(app):
    """すべてのBlueprintを登録"""
    app.register_blueprint(git_bp)
    app.register_blueprint(resources_bp)
    app.register_blueprint(execution_bp)
    app.register_blueprint(plan_bp)
    
    # グローバルエラーハンドラー
    @app.errorhandler(404)
    def not_found(error):
        return jsonify({
            'success': False,
            'error': {
                'code': ErrorCodes.NOT_FOUND,
                'message': 'The requested resource was not found',
                'details': {}
            },
            'timestamp': datetime.utcnow().isoformat()
        }), 404
    
    @app.errorhandler(405)
    def method_not_allowed(error):
        return jsonify({
            'success': False,
            'error': {
                'code': ErrorCodes.INVALID_REQUEST,
                'message': 'Method not allowed',
                'details': {'allowed_methods': error.description}
            },
            'timestamp': datetime.utcnow().isoformat()
        }), 405
    
    @app.errorhandler(500)
    def internal_error(error):
        return jsonify({
            'success': False,
            'error': {
                'code': ErrorCodes.INTERNAL_ERROR,
                'message': 'Internal server error',
                'details': {'trace_id': datetime.utcnow().isoformat()}
            },
            'timestamp': datetime.utcnow().isoformat()
        }), 500

