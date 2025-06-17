"""
Secure Code Executor

Dockerソケットマウントを使用しない安全なコード実行環境
SSH経由でサンドボックスコンテナに接続してコードを実行
"""

import os
import subprocess
import tempfile
import time
import logging
from typing import Dict, Any, Optional, List
import paramiko
from io import StringIO

logger = logging.getLogger(__name__)

class SecureCodeExecutor:
    """安全なコード実行クラス"""
    
    def __init__(self):
        self.sandbox_host = os.getenv('SANDBOX_HOST', 'sandbox')
        self.sandbox_port = int(os.getenv('SANDBOX_PORT', '22'))
        self.sandbox_user = 'root'
        self.sandbox_password = 'sandbox'
        
        # リソース制限設定
        self.max_execution_time = int(os.getenv('MAX_EXECUTION_TIME', '300'))
        self.max_memory_mb = int(os.getenv('MAX_MEMORY_MB', '2048'))
        self.max_cpu_percent = int(os.getenv('MAX_CPU_PERCENT', '80'))
        self.max_processes = int(os.getenv('MAX_PROCESSES', '50'))
        self.max_file_size_mb = int(os.getenv('MAX_FILE_SIZE_MB', '100'))
        
        # サンドボックス設定
        self.sandbox_timeout = int(os.getenv('SANDBOX_TIMEOUT', '600'))
        self.max_output_size = int(os.getenv('SANDBOX_MAX_OUTPUT_SIZE', '10485760'))  # 10MB
        
    def _create_ssh_client(self) -> paramiko.SSHClient:
        """SSH接続を作成"""
        try:
            client = paramiko.SSHClient()
            client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            
            client.connect(
                hostname=self.sandbox_host,
                port=self.sandbox_port,
                username=self.sandbox_user,
                password=self.sandbox_password,
                timeout=30
            )
            
            return client
        except Exception as e:
            logger.error(f"SSH connection failed: {e}")
            raise Exception(f"サンドボックスへの接続に失敗しました: {e}")
    
    def _sanitize_code(self, code: str, language: str) -> str:
        """コードのサニタイズ"""
        # 危険なコマンドのブラックリスト
        dangerous_patterns = [
            'rm -rf',
            'sudo',
            'chmod 777',
            'mkfs',
            'dd if=',
            'fork()',
            'system(',
            'exec(',
            'eval(',
            '__import__',
            'subprocess.call',
            'os.system',
        ]
        
        code_lower = code.lower()
        for pattern in dangerous_patterns:
            if pattern in code_lower:
                raise ValueError(f"危険なコマンドが検出されました: {pattern}")
        
        return code
    
    def _create_resource_limited_command(self, command: str) -> str:
        """リソース制限付きコマンドを作成"""
        # ulimitを使用してリソース制限を設定
        limited_command = f"""
        ulimit -t {self.max_execution_time} && \
        ulimit -v {self.max_memory_mb * 1024} && \
        ulimit -u {self.max_processes} && \
        ulimit -f {self.max_file_size_mb * 1024} && \
        timeout {self.max_execution_time}s {command}
        """
        
        return limited_command.strip()
    
    def execute_python(self, code: str, requirements: Optional[List[str]] = None) -> Dict[str, Any]:
        """Pythonコードの実行"""
        try:
            # コードのサニタイズ
            sanitized_code = self._sanitize_code(code, 'python')
            
            # SSH接続
            client = self._create_ssh_client()
            
            try:
                # 作業ディレクトリの作成
                work_dir = f"/workspace/exec_{int(time.time())}"
                client.exec_command(f"mkdir -p {work_dir}")
                
                # 依存関係のインストール
                if requirements:
                    req_content = '\n'.join(requirements)
                    client.exec_command(f"echo '{req_content}' > {work_dir}/requirements.txt")
                    
                    stdin, stdout, stderr = client.exec_command(
                        f"cd {work_dir} && pip install -r requirements.txt --user --quiet"
                    )
                    install_result = stdout.read().decode('utf-8')
                    install_error = stderr.read().decode('utf-8')
                    
                    if stderr.channel.recv_exit_status() != 0:
                        logger.warning(f"Package installation warning: {install_error}")
                
                # Pythonファイルの作成
                client.exec_command(f"echo '{sanitized_code}' > {work_dir}/main.py")
                
                # リソース制限付きでPythonコードを実行
                command = f"cd {work_dir} && python main.py"
                limited_command = self._create_resource_limited_command(command)
                
                stdin, stdout, stderr = client.exec_command(limited_command)
                
                # 出力の取得（サイズ制限付き）
                output = stdout.read(self.max_output_size).decode('utf-8', errors='ignore')
                error = stderr.read(self.max_output_size).decode('utf-8', errors='ignore')
                exit_code = stdout.channel.recv_exit_status()
                
                # 作業ディレクトリのクリーンアップ
                client.exec_command(f"rm -rf {work_dir}")
                
                return {
                    'success': exit_code == 0,
                    'output': output,
                    'error': error,
                    'exit_code': exit_code,
                    'execution_time': None,  # SSH経由では正確な測定が困難
                    'language': 'python'
                }
                
            finally:
                client.close()
                
        except Exception as e:
            logger.error(f"Python execution failed: {e}")
            return {
                'success': False,
                'output': '',
                'error': str(e),
                'exit_code': -1,
                'execution_time': None,
                'language': 'python'
            }
    
    def execute_javascript(self, code: str) -> Dict[str, Any]:
        """JavaScriptコードの実行"""
        try:
            # コードのサニタイズ
            sanitized_code = self._sanitize_code(code, 'javascript')
            
            # SSH接続
            client = self._create_ssh_client()
            
            try:
                # 作業ディレクトリの作成
                work_dir = f"/workspace/exec_{int(time.time())}"
                client.exec_command(f"mkdir -p {work_dir}")
                
                # JavaScriptファイルの作成
                client.exec_command(f"echo '{sanitized_code}' > {work_dir}/main.js")
                
                # リソース制限付きでNode.jsコードを実行
                command = f"cd {work_dir} && node main.js"
                limited_command = self._create_resource_limited_command(command)
                
                stdin, stdout, stderr = client.exec_command(limited_command)
                
                # 出力の取得
                output = stdout.read(self.max_output_size).decode('utf-8', errors='ignore')
                error = stderr.read(self.max_output_size).decode('utf-8', errors='ignore')
                exit_code = stdout.channel.recv_exit_status()
                
                # 作業ディレクトリのクリーンアップ
                client.exec_command(f"rm -rf {work_dir}")
                
                return {
                    'success': exit_code == 0,
                    'output': output,
                    'error': error,
                    'exit_code': exit_code,
                    'execution_time': None,
                    'language': 'javascript'
                }
                
            finally:
                client.close()
                
        except Exception as e:
            logger.error(f"JavaScript execution failed: {e}")
            return {
                'success': False,
                'output': '',
                'error': str(e),
                'exit_code': -1,
                'execution_time': None,
                'language': 'javascript'
            }
    
    def execute_bash(self, script: str) -> Dict[str, Any]:
        """Bashスクリプトの実行"""
        try:
            # コードのサニタイズ
            sanitized_script = self._sanitize_code(script, 'bash')
            
            # SSH接続
            client = self._create_ssh_client()
            
            try:
                # 作業ディレクトリの作成
                work_dir = f"/workspace/exec_{int(time.time())}"
                client.exec_command(f"mkdir -p {work_dir}")
                
                # Bashスクリプトファイルの作成
                client.exec_command(f"echo '{sanitized_script}' > {work_dir}/script.sh")
                client.exec_command(f"chmod +x {work_dir}/script.sh")
                
                # リソース制限付きでBashスクリプトを実行
                command = f"cd {work_dir} && ./script.sh"
                limited_command = self._create_resource_limited_command(command)
                
                stdin, stdout, stderr = client.exec_command(limited_command)
                
                # 出力の取得
                output = stdout.read(self.max_output_size).decode('utf-8', errors='ignore')
                error = stderr.read(self.max_output_size).decode('utf-8', errors='ignore')
                exit_code = stdout.channel.recv_exit_status()
                
                # 作業ディレクトリのクリーンアップ
                client.exec_command(f"rm -rf {work_dir}")
                
                return {
                    'success': exit_code == 0,
                    'output': output,
                    'error': error,
                    'exit_code': exit_code,
                    'execution_time': None,
                    'language': 'bash'
                }
                
            finally:
                client.close()
                
        except Exception as e:
            logger.error(f"Bash execution failed: {e}")
            return {
                'success': False,
                'output': '',
                'error': str(e),
                'exit_code': -1,
                'execution_time': None,
                'language': 'bash'
            }
    
    def execute_code(self, code: str, language: str, requirements: Optional[List[str]] = None) -> Dict[str, Any]:
        """汎用コード実行メソッド"""
        language = language.lower()
        
        if language in ['python', 'py']:
            return self.execute_python(code, requirements)
        elif language in ['javascript', 'js', 'node']:
            return self.execute_javascript(code)
        elif language in ['bash', 'sh', 'shell']:
            return self.execute_bash(code)
        else:
            return {
                'success': False,
                'output': '',
                'error': f'サポートされていない言語です: {language}',
                'exit_code': -1,
                'execution_time': None,
                'language': language
            }
    
    def health_check(self) -> bool:
        """サンドボックスの健全性チェック"""
        try:
            client = self._create_ssh_client()
            try:
                stdin, stdout, stderr = client.exec_command("echo 'health_check'")
                output = stdout.read().decode('utf-8').strip()
                return output == 'health_check'
            finally:
                client.close()
        except Exception as e:
            logger.error(f"Health check failed: {e}")
            return False
    
    def get_resource_usage(self) -> Dict[str, Any]:
        """リソース使用量の取得"""
        try:
            client = self._create_ssh_client()
            try:
                # CPU使用率
                stdin, stdout, stderr = client.exec_command("top -bn1 | grep 'Cpu(s)' | awk '{print $2}' | cut -d'%' -f1")
                cpu_usage = stdout.read().decode('utf-8').strip()
                
                # メモリ使用量
                stdin, stdout, stderr = client.exec_command("free -m | awk 'NR==2{printf \"%.1f\", $3*100/$2 }'")
                memory_usage = stdout.read().decode('utf-8').strip()
                
                # ディスク使用量
                stdin, stdout, stderr = client.exec_command("df -h /workspace | awk 'NR==2{print $5}' | cut -d'%' -f1")
                disk_usage = stdout.read().decode('utf-8').strip()
                
                return {
                    'cpu_usage_percent': float(cpu_usage) if cpu_usage else 0.0,
                    'memory_usage_percent': float(memory_usage) if memory_usage else 0.0,
                    'disk_usage_percent': float(disk_usage) if disk_usage else 0.0,
                    'max_memory_mb': self.max_memory_mb,
                    'max_cpu_percent': self.max_cpu_percent,
                    'max_execution_time': self.max_execution_time
                }
            finally:
                client.close()
        except Exception as e:
            logger.error(f"Resource usage check failed: {e}")
            return {
                'cpu_usage_percent': 0.0,
                'memory_usage_percent': 0.0,
                'disk_usage_percent': 0.0,
                'max_memory_mb': self.max_memory_mb,
                'max_cpu_percent': self.max_cpu_percent,
                'max_execution_time': self.max_execution_time
            }

# グローバルインスタンス
secure_executor = SecureCodeExecutor()

