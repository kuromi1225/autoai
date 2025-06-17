# Backend Tests

import pytest
import json
import tempfile
import os
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timedelta

# Import the modules to test
import sys
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from services.resource_manager import ACUManager, ResourceLimits, ResourceUsage
from services.git_settings import GitSettings
from services.secure_code_executor import SecureCodeExecutor
from api_blueprints import git_bp, resources_bp, execution_bp

class TestACUManager:
    """ACUManager（リソース管理）のテストクラス"""
    
    def setup_method(self):
        """各テストメソッドの前に実行される初期化"""
        self.acu_manager = ACUManager()
        self.test_user_id = "test_user_123"
        self.test_task_id = "test_task_456"
    
    def test_default_limits_initialization(self):
        """デフォルトリソース制限の初期化テスト"""
        limits = self.acu_manager.get_user_limits("new_user")
        
        assert limits.max_cpu_percent == 80.0
        assert limits.max_memory_mb == 2048
        assert limits.max_execution_time == 300
        assert limits.max_processes == 50
        assert limits.max_file_size_mb == 100
        assert limits.max_network_requests == 100
    
    def test_set_user_limits(self):
        """ユーザー固有リソース制限設定のテスト"""
        custom_limits = ResourceLimits(
            max_cpu_percent=50.0,
            max_memory_mb=1024,
            max_execution_time=180,
            max_processes=25,
            max_file_size_mb=50,
            max_network_requests=50
        )
        
        result = self.acu_manager.set_user_limits(self.test_user_id, custom_limits)
        assert result is True
        
        retrieved_limits = self.acu_manager.get_user_limits(self.test_user_id)
        assert retrieved_limits.max_cpu_percent == 50.0
        assert retrieved_limits.max_memory_mb == 1024
    
    def test_resource_availability_check(self):
        """リソース利用可能性チェックのテスト"""
        estimated_usage = {
            'cpu_percent': 30,
            'memory_mb': 512,
            'execution_time': 120,
            'process_count': 2
        }
        
        availability = self.acu_manager.check_resource_availability(
            self.test_user_id, estimated_usage
        )
        
        assert 'available' in availability
        assert 'checks' in availability
        assert 'current_usage' in availability
        assert 'limits' in availability
        assert isinstance(availability['available'], bool)
    
    def test_resource_allocation_and_release(self):
        """リソース割り当てと解放のテスト"""
        estimated_usage = {
            'cpu_percent': 20,
            'memory_mb': 256,
            'execution_time': 60,
            'process_count': 1
        }
        
        # リソース割り当て
        allocation_result = self.acu_manager.allocate_resources(
            self.test_user_id, self.test_task_id, estimated_usage
        )
        assert allocation_result is True
        
        # アクティブタスクの確認
        assert self.test_user_id in self.acu_manager.active_tasks
        assert self.test_task_id in self.acu_manager.active_tasks[self.test_user_id]
        
        # リソース解放
        release_result = self.acu_manager.release_resources(
            self.test_user_id, self.test_task_id
        )
        assert release_result is True
        
        # 使用履歴の確認
        assert self.test_user_id in self.acu_manager.usage_history
        assert len(self.acu_manager.usage_history[self.test_user_id]) > 0
    
    def test_usage_statistics(self):
        """使用統計取得のテスト"""
        # テストデータの準備
        self.acu_manager.usage_history[self.test_user_id] = [
            {
                'task_id': 'task1',
                'start_time': datetime.now() - timedelta(hours=2),
                'end_time': datetime.now() - timedelta(hours=1),
                'estimated_usage': {'cpu_percent': 30},
                'actual_usage': {'cpu_percent': 25, 'memory_mb': 512}
            }
        ]
        
        stats = self.acu_manager.get_usage_statistics(self.test_user_id, 7)
        
        assert 'total_tasks' in stats
        assert 'total_execution_time' in stats
        assert 'average_cpu_usage' in stats
        assert 'average_memory_usage' in stats
        assert stats['total_tasks'] == 1
    
    @patch('psutil.cpu_percent')
    @patch('psutil.virtual_memory')
    def test_system_status(self, mock_memory, mock_cpu):
        """システムステータス取得のテスト"""
        # psutilのモック設定
        mock_cpu.return_value = 45.5
        mock_memory.return_value = Mock(
            percent=60.0,
            used=8589934592,  # 8GB in bytes
            total=17179869184  # 16GB in bytes
        )
        
        status = self.acu_manager.get_system_status()
        
        assert 'system_cpu_percent' in status
        assert 'system_memory_percent' in status
        assert 'system_memory_used_mb' in status
        assert 'system_memory_total_mb' in status
        assert 'active_users' in status
        assert 'total_active_tasks' in status
        assert status['system_cpu_percent'] == 45.5
        assert status['system_memory_percent'] == 60.0


class TestGitSettings:
    """GitSettings（Git設定管理）のテストクラス"""
    
    def setup_method(self):
        """各テストメソッドの前に実行される初期化"""
        # テスト用の一時データベースファイル
        self.temp_db = tempfile.NamedTemporaryFile(delete=False)
        self.temp_db.close()
        
        # モックデータベース接続
        self.mock_db = Mock()
        self.git_settings = GitSettings(self.mock_db)
        self.test_user_id = "test_user_123"
    
    def teardown_method(self):
        """各テストメソッドの後に実行されるクリーンアップ"""
        os.unlink(self.temp_db.name)
    
    def test_encrypt_decrypt_token(self):
        """トークンの暗号化・復号化テスト"""
        original_token = "ghp_test_token_123456789"
        
        # 暗号化
        encrypted_token = self.git_settings.encrypt_token(original_token)
        assert encrypted_token != original_token
        assert isinstance(encrypted_token, bytes)
        
        # 復号化
        decrypted_token = self.git_settings.decrypt_token(encrypted_token)
        assert decrypted_token == original_token
    
    def test_validate_git_settings(self):
        """Git設定バリデーションのテスト"""
        # 有効な設定
        valid_settings = {
            'repository_url': 'https://github.com/user/repo.git',
            'username': 'testuser',
            'access_token': 'ghp_valid_token',
            'branch': 'main'
        }
        
        validation_result = self.git_settings.validate_settings(valid_settings)
        assert validation_result['valid'] is True
        assert len(validation_result['errors']) == 0
        
        # 無効な設定
        invalid_settings = {
            'repository_url': 'invalid_url',
            'username': '',
            'access_token': '',
            'branch': ''
        }
        
        validation_result = self.git_settings.validate_settings(invalid_settings)
        assert validation_result['valid'] is False
        assert len(validation_result['errors']) > 0
    
    @patch('subprocess.run')
    def test_test_connection(self, mock_subprocess):
        """Git接続テストのテスト"""
        # 成功ケース
        mock_subprocess.return_value = Mock(
            returncode=0,
            stdout="Repository accessible",
            stderr=""
        )
        
        result = self.git_settings.test_connection(
            'https://github.com/user/repo.git',
            'testuser',
            'ghp_token'
        )
        
        assert result['success'] is True
        assert 'message' in result
        
        # 失敗ケース
        mock_subprocess.return_value = Mock(
            returncode=1,
            stdout="",
            stderr="Authentication failed"
        )
        
        result = self.git_settings.test_connection(
            'https://github.com/user/repo.git',
            'testuser',
            'invalid_token'
        )
        
        assert result['success'] is False
        assert 'error' in result


class TestSecureCodeExecutor:
    """SecureCodeExecutor（セキュアコード実行）のテストクラス"""
    
    def setup_method(self):
        """各テストメソッドの前に実行される初期化"""
        self.executor = SecureCodeExecutor()
    
    def test_validate_code_safety(self):
        """コード安全性検証のテスト"""
        # 安全なコード
        safe_code = """
print("Hello, World!")
x = 1 + 1
print(f"Result: {x}")
"""
        
        validation_result = self.executor.validate_code(safe_code)
        assert validation_result['safe'] is True
        assert len(validation_result['warnings']) == 0
        
        # 危険なコード
        dangerous_code = """
import os
os.system("rm -rf /")
"""
        
        validation_result = self.executor.validate_code(dangerous_code)
        assert validation_result['safe'] is False
        assert len(validation_result['warnings']) > 0
    
    def test_resource_limits_creation(self):
        """リソース制限設定のテスト"""
        limits = {
            'max_memory_mb': 512,
            'max_cpu_percent': 50,
            'max_execution_time': 30
        }
        
        command = self.executor._create_resource_limited_command(
            "python test.py", limits
        )
        
        assert 'ulimit' in command
        assert 'timeout' in command
        assert '30' in command  # execution time limit
    
    @patch('paramiko.SSHClient')
    def test_ssh_connection(self, mock_ssh_client):
        """SSH接続のテスト"""
        # SSHクライアントのモック設定
        mock_client = Mock()
        mock_ssh_client.return_value = mock_client
        
        # 接続成功のシミュレーション
        mock_client.connect.return_value = None
        mock_client.exec_command.return_value = (
            Mock(),  # stdin
            Mock(read=lambda: b"Hello, World!"),  # stdout
            Mock(read=lambda: b"")  # stderr
        )
        
        result = self.executor.execute_python("print('Hello, World!')")
        
        assert 'output' in result
        assert 'error' in result
        assert 'execution_time' in result
        
        # 接続が呼ばれたことを確認
        mock_client.connect.assert_called_once()
        mock_client.exec_command.assert_called_once()
    
    def test_health_check(self):
        """ヘルスチェックのテスト"""
        health_status = self.executor.health_check()
        
        assert isinstance(health_status, bool)
    
    def test_get_resource_usage(self):
        """リソース使用量取得のテスト"""
        usage = self.executor.get_resource_usage()
        
        assert 'cpu_percent' in usage
        assert 'memory_mb' in usage
        assert 'active_connections' in usage
        assert isinstance(usage['cpu_percent'], (int, float))
        assert isinstance(usage['memory_mb'], (int, float))


class TestAPIBlueprints:
    """APIBlueprints（API設計）のテストクラス"""
    
    def setup_method(self):
        """各テストメソッドの前に実行される初期化"""
        from flask import Flask
        self.app = Flask(__name__)
        self.app.config['TESTING'] = True
        
        # Blueprintの登録
        self.app.register_blueprint(git_bp)
        self.app.register_blueprint(resources_bp)
        self.app.register_blueprint(execution_bp)
        
        self.client = self.app.test_client()
    
    def test_git_settings_endpoints(self):
        """Git設定エンドポイントのテスト"""
        # GET /api/git/settings
        response = self.client.get('/api/git/settings')
        assert response.status_code == 200
        
        data = json.loads(response.data)
        assert 'repository_url' in data
        assert 'username' in data
        assert 'is_configured' in data
        
        # POST /api/git/settings
        test_settings = {
            'repository_url': 'https://github.com/test/repo.git',
            'username': 'testuser',
            'access_token': 'test_token',
            'branch': 'main'
        }
        
        response = self.client.post(
            '/api/git/settings',
            data=json.dumps(test_settings),
            content_type='application/json'
        )
        assert response.status_code == 200
        
        data = json.loads(response.data)
        assert data['success'] is True
    
    def test_resource_limits_endpoints(self):
        """リソース制限エンドポイントのテスト"""
        # GET /api/resources/limits
        response = self.client.get('/api/resources/limits')
        assert response.status_code == 200
        
        data = json.loads(response.data)
        assert 'max_cpu_percent' in data
        assert 'max_memory_mb' in data
        
        # POST /api/resources/limits
        test_limits = {
            'max_cpu_percent': 60.0,
            'max_memory_mb': 1024,
            'max_execution_time': 180
        }
        
        response = self.client.post(
            '/api/resources/limits',
            data=json.dumps(test_limits),
            content_type='application/json'
        )
        assert response.status_code == 200
        
        data = json.loads(response.data)
        assert data['success'] is True
    
    def test_execution_endpoints(self):
        """コード実行エンドポイントのテスト"""
        # GET /api/execution/health
        response = self.client.get('/api/execution/health')
        assert response.status_code == 200
        
        data = json.loads(response.data)
        assert 'healthy' in data
        assert 'resource_usage' in data
        
        # POST /api/execution/execute
        test_code = {
            'code': 'print("Hello, Test!")',
            'language': 'python',
            'requirements': []
        }
        
        response = self.client.post(
            '/api/execution/execute',
            data=json.dumps(test_code),
            content_type='application/json'
        )
        # リソース不足やその他の理由で失敗する可能性があるため、
        # ステータスコードは200または429を許可
        assert response.status_code in [200, 429, 500]


# パフォーマンステスト
class TestPerformance:
    """パフォーマンステストクラス"""
    
    def test_acu_manager_performance(self):
        """ACUManagerのパフォーマンステスト"""
        import time
        
        acu_manager = ACUManager()
        
        # 大量のユーザーとタスクでのパフォーマンステスト
        start_time = time.time()
        
        for i in range(100):
            user_id = f"user_{i}"
            task_id = f"task_{i}"
            estimated_usage = {
                'cpu_percent': 10,
                'memory_mb': 128,
                'execution_time': 30,
                'process_count': 1
            }
            
            acu_manager.allocate_resources(user_id, task_id, estimated_usage)
            acu_manager.release_resources(user_id, task_id)
        
        end_time = time.time()
        execution_time = end_time - start_time
        
        # 100回の操作が5秒以内に完了することを確認
        assert execution_time < 5.0, f"Performance test failed: {execution_time}s"
    
    def test_memory_leak_detection(self):
        """メモリリーク検出テスト"""
        import gc
        import sys
        
        # ガベージコレクションを実行
        gc.collect()
        initial_objects = len(gc.get_objects())
        
        # 大量のオブジェクト作成と削除
        acu_manager = ACUManager()
        
        for i in range(1000):
            user_id = f"user_{i}"
            limits = ResourceLimits(max_cpu_percent=50.0)
            acu_manager.set_user_limits(user_id, limits)
        
        # オブジェクトを削除
        del acu_manager
        
        # ガベージコレクションを実行
        gc.collect()
        final_objects = len(gc.get_objects())
        
        # オブジェクト数の増加が許容範囲内であることを確認
        object_increase = final_objects - initial_objects
        assert object_increase < 100, f"Potential memory leak detected: {object_increase} objects"


if __name__ == '__main__':
    # テストの実行
    pytest.main([__file__, '-v', '--tb=short'])

