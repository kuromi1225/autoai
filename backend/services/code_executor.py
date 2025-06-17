"""
Code Executor - 安全なコード実行環境

このモジュールは、生成されたコードを安全に実行し、
結果を取得する機能を提供します。
"""

import os
import subprocess
import tempfile
import logging
import asyncio
import signal
import resource
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass
from enum import Enum
import docker
import json
import time

logger = logging.getLogger(__name__)

class ExecutionStatus(Enum):
    """実行ステータス"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    TIMEOUT = "timeout"
    CANCELLED = "cancelled"

class Language(Enum):
    """サポート言語"""
    PYTHON = "python"
    JAVASCRIPT = "javascript"
    BASH = "bash"
    SQL = "sql"

@dataclass
class ExecutionResult:
    """実行結果"""
    status: ExecutionStatus
    stdout: str
    stderr: str
    exit_code: int
    execution_time: float
    memory_usage: int
    files_created: List[str]
    error_message: Optional[str] = None

@dataclass
class ExecutionConfig:
    """実行設定"""
    timeout: int = 30  # 秒
    max_memory: int = 512  # MB
    max_cpu_time: int = 10  # 秒
    allow_network: bool = False
    allow_file_write: bool = True
    working_directory: str = "/tmp"
    environment_vars: Dict[str, str] = None

class CodeExecutor:
    """
    安全なコード実行環境
    
    機能:
    - サンドボックス化された実行環境
    - リソース制限
    - 複数言語サポート
    - セキュリティ制御
    """
    
    def __init__(
        self, 
        workspace_dir: str = "/app/workspace",
        use_docker: bool = True,
        docker_image: str = "python:3.11-slim"
    ):
        """
        コード実行環境を初期化
        
        Args:
            workspace_dir: 作業ディレクトリ
            use_docker: Docker使用フラグ
            docker_image: Dockerイメージ名
        """
        self.workspace_dir = workspace_dir
        self.use_docker = use_docker
        self.docker_image = docker_image
        
        # Docker クライアント
        self.docker_client = None
        if use_docker:
            try:
                self.docker_client = docker.from_env()
                logger.info("Docker client initialized")
            except Exception as e:
                logger.warning(f"Failed to initialize Docker: {e}")
                self.use_docker = False
        
        # 実行中のプロセス
        self.running_executions: Dict[str, subprocess.Popen] = {}
        
        # セキュリティ設定
        self.security_config = {
            "blocked_imports": [
                "os", "subprocess", "sys", "socket", "urllib",
                "requests", "http", "ftplib", "smtplib"
            ],
            "blocked_functions": [
                "exec", "eval", "compile", "__import__",
                "open", "file", "input", "raw_input"
            ],
            "max_file_size": 10 * 1024 * 1024,  # 10MB
            "allowed_extensions": [".py", ".js", ".sql", ".txt", ".json", ".csv"]
        }
    
    async def execute_code(
        self, 
        code: str, 
        language: Language,
        config: ExecutionConfig = None,
        execution_id: str = None
    ) -> ExecutionResult:
        """
        コードを実行
        
        Args:
            code: 実行するコード
            language: プログラミング言語
            config: 実行設定
            execution_id: 実行ID
            
        Returns:
            実行結果
        """
        if not config:
            config = ExecutionConfig()
        
        if not execution_id:
            execution_id = f"exec_{int(time.time())}"
        
        try:
            logger.info(f"Executing code: {execution_id} ({language.value})")
            
            # セキュリティチェック
            if not self._security_check(code, language):
                return ExecutionResult(
                    status=ExecutionStatus.FAILED,
                    stdout="",
                    stderr="Security check failed",
                    exit_code=1,
                    execution_time=0,
                    memory_usage=0,
                    files_created=[],
                    error_message="Code contains blocked operations"
                )
            
            # 実行環境の選択
            if self.use_docker and self.docker_client:
                return await self._execute_in_docker(code, language, config, execution_id)
            else:
                return await self._execute_locally(code, language, config, execution_id)
                
        except Exception as e:
            logger.error(f"Code execution failed: {e}")
            return ExecutionResult(
                status=ExecutionStatus.FAILED,
                stdout="",
                stderr=str(e),
                exit_code=1,
                execution_time=0,
                memory_usage=0,
                files_created=[],
                error_message=str(e)
            )
    
    async def _execute_in_docker(
        self, 
        code: str, 
        language: Language, 
        config: ExecutionConfig,
        execution_id: str
    ) -> ExecutionResult:
        """Dockerコンテナ内でコードを実行"""
        
        start_time = time.time()
        
        try:
            # 一時ディレクトリの作成
            with tempfile.TemporaryDirectory() as temp_dir:
                
                # コードファイルの作成
                code_file = self._create_code_file(code, language, temp_dir)
                
                # 実行コマンドの構築
                command = self._build_command(language, os.path.basename(code_file))
                
                # Dockerコンテナの設定
                container_config = {
                    "image": self.docker_image,
                    "command": command,
                    "working_dir": "/workspace",
                    "volumes": {temp_dir: {"bind": "/workspace", "mode": "rw"}},
                    "mem_limit": f"{config.max_memory}m",
                    "cpu_period": 100000,
                    "cpu_quota": config.max_cpu_time * 1000,
                    "network_disabled": not config.allow_network,
                    "remove": True,
                    "detach": True
                }
                
                # 環境変数の設定
                if config.environment_vars:
                    container_config["environment"] = config.environment_vars
                
                # コンテナの実行
                container = self.docker_client.containers.run(**container_config)
                
                # タイムアウト付きで結果を待機
                try:
                    result = container.wait(timeout=config.timeout)
                    exit_code = result["StatusCode"]
                    
                    # ログの取得
                    stdout = container.logs(stdout=True, stderr=False).decode('utf-8')
                    stderr = container.logs(stdout=False, stderr=True).decode('utf-8')
                    
                except docker.errors.APIError as e:
                    if "timeout" in str(e).lower():
                        container.kill()
                        return ExecutionResult(
                            status=ExecutionStatus.TIMEOUT,
                            stdout="",
                            stderr="Execution timed out",
                            exit_code=124,
                            execution_time=config.timeout,
                            memory_usage=0,
                            files_created=[],
                            error_message="Execution timed out"
                        )
                    raise
                
                execution_time = time.time() - start_time
                
                # 作成されたファイルの確認
                files_created = self._get_created_files(temp_dir)
                
                # メモリ使用量の取得（概算）
                memory_usage = self._estimate_memory_usage(stdout, stderr)
                
                status = ExecutionStatus.COMPLETED if exit_code == 0 else ExecutionStatus.FAILED
                
                return ExecutionResult(
                    status=status,
                    stdout=stdout,
                    stderr=stderr,
                    exit_code=exit_code,
                    execution_time=execution_time,
                    memory_usage=memory_usage,
                    files_created=files_created
                )
                
        except Exception as e:
            execution_time = time.time() - start_time
            logger.error(f"Docker execution failed: {e}")
            
            return ExecutionResult(
                status=ExecutionStatus.FAILED,
                stdout="",
                stderr=str(e),
                exit_code=1,
                execution_time=execution_time,
                memory_usage=0,
                files_created=[],
                error_message=str(e)
            )
    
    async def _execute_locally(
        self, 
        code: str, 
        language: Language, 
        config: ExecutionConfig,
        execution_id: str
    ) -> ExecutionResult:
        """ローカル環境でコードを実行"""
        
        start_time = time.time()
        
        try:
            # 一時ディレクトリの作成
            with tempfile.TemporaryDirectory() as temp_dir:
                
                # コードファイルの作成
                code_file = self._create_code_file(code, language, temp_dir)
                
                # 実行コマンドの構築
                command = self._build_command(language, code_file)
                
                # プロセスの実行
                process = await asyncio.create_subprocess_shell(
                    command,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                    cwd=temp_dir,
                    env=config.environment_vars,
                    preexec_fn=self._set_resource_limits if os.name != 'nt' else None
                )
                
                self.running_executions[execution_id] = process
                
                try:
                    # タイムアウト付きで実行
                    stdout, stderr = await asyncio.wait_for(
                        process.communicate(),
                        timeout=config.timeout
                    )
                    
                    exit_code = process.returncode
                    
                except asyncio.TimeoutError:
                    process.kill()
                    await process.wait()
                    
                    return ExecutionResult(
                        status=ExecutionStatus.TIMEOUT,
                        stdout="",
                        stderr="Execution timed out",
                        exit_code=124,
                        execution_time=config.timeout,
                        memory_usage=0,
                        files_created=[],
                        error_message="Execution timed out"
                    )
                
                finally:
                    if execution_id in self.running_executions:
                        del self.running_executions[execution_id]
                
                execution_time = time.time() - start_time
                
                # 出力のデコード
                stdout_str = stdout.decode('utf-8') if stdout else ""
                stderr_str = stderr.decode('utf-8') if stderr else ""
                
                # 作成されたファイルの確認
                files_created = self._get_created_files(temp_dir)
                
                # メモリ使用量の取得（概算）
                memory_usage = self._estimate_memory_usage(stdout_str, stderr_str)
                
                status = ExecutionStatus.COMPLETED if exit_code == 0 else ExecutionStatus.FAILED
                
                return ExecutionResult(
                    status=status,
                    stdout=stdout_str,
                    stderr=stderr_str,
                    exit_code=exit_code,
                    execution_time=execution_time,
                    memory_usage=memory_usage,
                    files_created=files_created
                )
                
        except Exception as e:
            execution_time = time.time() - start_time
            logger.error(f"Local execution failed: {e}")
            
            return ExecutionResult(
                status=ExecutionStatus.FAILED,
                stdout="",
                stderr=str(e),
                exit_code=1,
                execution_time=execution_time,
                memory_usage=0,
                files_created=[],
                error_message=str(e)
            )
    
    def _security_check(self, code: str, language: Language) -> bool:
        """セキュリティチェック"""
        
        code_lower = code.lower()
        
        # 危険なインポートのチェック
        for blocked_import in self.security_config["blocked_imports"]:
            if f"import {blocked_import}" in code_lower or f"from {blocked_import}" in code_lower:
                logger.warning(f"Blocked import detected: {blocked_import}")
                return False
        
        # 危険な関数のチェック
        for blocked_func in self.security_config["blocked_functions"]:
            if blocked_func in code_lower:
                logger.warning(f"Blocked function detected: {blocked_func}")
                return False
        
        # ファイルサイズのチェック
        if len(code.encode('utf-8')) > self.security_config["max_file_size"]:
            logger.warning("Code size exceeds limit")
            return False
        
        return True
    
    def _create_code_file(self, code: str, language: Language, temp_dir: str) -> str:
        """コードファイルを作成"""
        
        extensions = {
            Language.PYTHON: ".py",
            Language.JAVASCRIPT: ".js",
            Language.BASH: ".sh",
            Language.SQL: ".sql"
        }
        
        extension = extensions.get(language, ".txt")
        code_file = os.path.join(temp_dir, f"code{extension}")
        
        with open(code_file, 'w', encoding='utf-8') as f:
            f.write(code)
        
        # 実行権限の付与（必要な場合）
        if language == Language.BASH:
            os.chmod(code_file, 0o755)
        
        return code_file
    
    def _build_command(self, language: Language, code_file: str) -> str:
        """実行コマンドを構築"""
        
        commands = {
            Language.PYTHON: f"python {code_file}",
            Language.JAVASCRIPT: f"node {code_file}",
            Language.BASH: f"bash {code_file}",
            Language.SQL: f"sqlite3 :memory: < {code_file}"
        }
        
        return commands.get(language, f"cat {code_file}")
    
    def _set_resource_limits(self):
        """リソース制限を設定"""
        try:
            # CPU時間制限
            resource.setrlimit(resource.RLIMIT_CPU, (10, 10))
            
            # メモリ制限
            resource.setrlimit(resource.RLIMIT_AS, (512 * 1024 * 1024, 512 * 1024 * 1024))
            
            # ファイル数制限
            resource.setrlimit(resource.RLIMIT_NOFILE, (100, 100))
            
        except Exception as e:
            logger.warning(f"Failed to set resource limits: {e}")
    
    def _get_created_files(self, directory: str) -> List[str]:
        """作成されたファイルのリストを取得"""
        try:
            files = []
            for root, dirs, filenames in os.walk(directory):
                for filename in filenames:
                    file_path = os.path.join(root, filename)
                    rel_path = os.path.relpath(file_path, directory)
                    files.append(rel_path)
            return files
        except Exception as e:
            logger.error(f"Failed to get created files: {e}")
            return []
    
    def _estimate_memory_usage(self, stdout: str, stderr: str) -> int:
        """メモリ使用量を推定（概算）"""
        # 簡単な推定：出力サイズに基づく
        output_size = len(stdout.encode('utf-8')) + len(stderr.encode('utf-8'))
        estimated_memory = max(output_size * 2, 1024)  # 最低1KB
        return min(estimated_memory, 512 * 1024 * 1024)  # 最大512MB
    
    def cancel_execution(self, execution_id: str) -> bool:
        """実行をキャンセル"""
        try:
            if execution_id in self.running_executions:
                process = self.running_executions[execution_id]
                process.terminate()
                
                # 強制終了が必要な場合
                try:
                    process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait()
                
                del self.running_executions[execution_id]
                logger.info(f"Execution cancelled: {execution_id}")
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"Failed to cancel execution: {e}")
            return False
    
    def get_execution_status(self, execution_id: str) -> Optional[ExecutionStatus]:
        """実行ステータスを取得"""
        if execution_id in self.running_executions:
            process = self.running_executions[execution_id]
            if process.poll() is None:
                return ExecutionStatus.RUNNING
            else:
                return ExecutionStatus.COMPLETED
        
        return None
    
    def cleanup_old_executions(self, max_age_seconds: int = 3600):
        """古い実行をクリーンアップ"""
        current_time = time.time()
        to_remove = []
        
        for execution_id, process in self.running_executions.items():
            # プロセスの開始時間を取得（概算）
            try:
                if hasattr(process, 'create_time'):
                    create_time = process.create_time()
                    if current_time - create_time > max_age_seconds:
                        to_remove.append(execution_id)
            except:
                # プロセスが既に終了している場合
                if process.poll() is not None:
                    to_remove.append(execution_id)
        
        for execution_id in to_remove:
            self.cancel_execution(execution_id)
        
        return len(to_remove)
    
    def get_supported_languages(self) -> List[str]:
        """サポートされている言語のリストを取得"""
        return [lang.value for lang in Language]
    
    def validate_code_syntax(self, code: str, language: Language) -> Tuple[bool, str]:
        """コードの構文をチェック"""
        try:
            if language == Language.PYTHON:
                import ast
                ast.parse(code)
                return True, "Syntax is valid"
            
            elif language == Language.JAVASCRIPT:
                # 簡単な構文チェック（実際のJSパーサーが必要）
                if code.count('{') != code.count('}'):
                    return False, "Mismatched braces"
                if code.count('(') != code.count(')'):
                    return False, "Mismatched parentheses"
                return True, "Basic syntax check passed"
            
            else:
                return True, "Syntax check not implemented for this language"
                
        except SyntaxError as e:
            return False, f"Syntax error: {e}"
        except Exception as e:
            return False, f"Validation error: {e}"

