"""
MCP Server - Model Context Protocol サーバー

このモジュールは、AIモデルが様々なツールと統一的に通信するための
MCPサーバーを実装します。
"""

import asyncio
import json
import logging
import os
import subprocess
import tempfile
from typing import Dict, List, Any, Optional, Callable
from dataclasses import dataclass, asdict
from pathlib import Path
import aiohttp
from aiohttp import web
import websockets
from pydantic import BaseModel, ValidationError

logger = logging.getLogger(__name__)

class MCPRequest(BaseModel):
    """MCP リクエストモデル"""
    id: str
    method: str
    params: Dict[str, Any] = {}

class MCPResponse(BaseModel):
    """MCP レスポンスモデル"""
    id: str
    result: Optional[Dict[str, Any]] = None
    error: Optional[Dict[str, str]] = None

@dataclass
class ToolDefinition:
    """ツール定義"""
    name: str
    description: str
    parameters: Dict[str, Any]
    handler: Callable

class MCPServer:
    """
    Model Context Protocol サーバー
    
    AIモデルが以下のツールを使用できるようにします：
    - ファイル操作
    - シェル実行
    - Git操作
    - コード分析
    - Web検索
    """
    
    def __init__(self, workspace_dir: str = "/app/workspace"):
        """
        MCPサーバーを初期化
        
        Args:
            workspace_dir: 作業ディレクトリ
        """
        self.workspace_dir = Path(workspace_dir)
        self.workspace_dir.mkdir(parents=True, exist_ok=True)
        
        # ツールの登録
        self.tools: Dict[str, ToolDefinition] = {}
        self._register_tools()
        
        # 実行中のプロセス
        self.running_processes: Dict[str, subprocess.Popen] = {}
        
    def _register_tools(self):
        """利用可能なツールを登録"""
        
        # ファイル読み取り
        self.tools["file_read"] = ToolDefinition(
            name="file_read",
            description="ファイルの内容を読み取る",
            parameters={
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "ファイルパス"},
                    "encoding": {"type": "string", "default": "utf-8"}
                },
                "required": ["path"]
            },
            handler=self._file_read
        )
        
        # ファイル書き込み
        self.tools["file_write"] = ToolDefinition(
            name="file_write",
            description="ファイルに内容を書き込む",
            parameters={
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "ファイルパス"},
                    "content": {"type": "string", "description": "書き込む内容"},
                    "encoding": {"type": "string", "default": "utf-8"}
                },
                "required": ["path", "content"]
            },
            handler=self._file_write
        )
        
        # ディレクトリ作成
        self.tools["mkdir"] = ToolDefinition(
            name="mkdir",
            description="ディレクトリを作成する",
            parameters={
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "ディレクトリパス"},
                    "parents": {"type": "boolean", "default": True}
                },
                "required": ["path"]
            },
            handler=self._mkdir
        )
        
        # ファイル一覧
        self.tools["list_files"] = ToolDefinition(
            name="list_files",
            description="ディレクトリ内のファイル一覧を取得",
            parameters={
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "ディレクトリパス", "default": "."},
                    "recursive": {"type": "boolean", "default": False}
                }
            },
            handler=self._list_files
        )
        
        # シェル実行
        self.tools["shell_exec"] = ToolDefinition(
            name="shell_exec",
            description="シェルコマンドを実行する",
            parameters={
                "type": "object",
                "properties": {
                    "command": {"type": "string", "description": "実行するコマンド"},
                    "cwd": {"type": "string", "description": "作業ディレクトリ"},
                    "timeout": {"type": "number", "default": 30}
                },
                "required": ["command"]
            },
            handler=self._shell_exec
        )
        
        # Git操作
        self.tools["git_init"] = ToolDefinition(
            name="git_init",
            description="Gitリポジトリを初期化",
            parameters={
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "リポジトリパス", "default": "."}
                }
            },
            handler=self._git_init
        )
        
        self.tools["git_add"] = ToolDefinition(
            name="git_add",
            description="ファイルをGitに追加",
            parameters={
                "type": "object",
                "properties": {
                    "files": {"type": "array", "items": {"type": "string"}, "description": "追加するファイル"},
                    "path": {"type": "string", "description": "リポジトリパス", "default": "."}
                },
                "required": ["files"]
            },
            handler=self._git_add
        )
        
        self.tools["git_commit"] = ToolDefinition(
            name="git_commit",
            description="変更をコミット",
            parameters={
                "type": "object",
                "properties": {
                    "message": {"type": "string", "description": "コミットメッセージ"},
                    "path": {"type": "string", "description": "リポジトリパス", "default": "."}
                },
                "required": ["message"]
            },
            handler=self._git_commit
        )
        
        # コード分析
        self.tools["analyze_code"] = ToolDefinition(
            name="analyze_code",
            description="コードを静的解析",
            parameters={
                "type": "object",
                "properties": {
                    "file_path": {"type": "string", "description": "分析するファイルパス"},
                    "language": {"type": "string", "description": "プログラミング言語"}
                },
                "required": ["file_path"]
            },
            handler=self._analyze_code
        )
        
        # テスト実行
        self.tools["run_tests"] = ToolDefinition(
            name="run_tests",
            description="テストを実行",
            parameters={
                "type": "object",
                "properties": {
                    "test_path": {"type": "string", "description": "テストファイル/ディレクトリ"},
                    "framework": {"type": "string", "description": "テストフレームワーク", "default": "pytest"}
                }
            },
            handler=self._run_tests
        )
    
    async def handle_request(self, request_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        MCPリクエストを処理
        
        Args:
            request_data: リクエストデータ
            
        Returns:
            レスポンスデータ
        """
        try:
            # リクエストの検証
            mcp_request = MCPRequest(**request_data)
            
            # メソッドの処理
            if mcp_request.method == "tools/list":
                result = await self._list_tools()
            elif mcp_request.method == "tools/call":
                result = await self._call_tool(mcp_request.params)
            else:
                raise ValueError(f"Unknown method: {mcp_request.method}")
            
            return MCPResponse(id=mcp_request.id, result=result).dict()
            
        except ValidationError as e:
            return MCPResponse(
                id=request_data.get("id", "unknown"),
                error={"code": "invalid_request", "message": str(e)}
            ).dict()
        except Exception as e:
            logger.error(f"MCP request failed: {e}")
            return MCPResponse(
                id=request_data.get("id", "unknown"),
                error={"code": "internal_error", "message": str(e)}
            ).dict()
    
    async def _list_tools(self) -> Dict[str, Any]:
        """利用可能なツール一覧を返す"""
        tools_list = []
        for tool in self.tools.values():
            tools_list.append({
                "name": tool.name,
                "description": tool.description,
                "inputSchema": tool.parameters
            })
        
        return {"tools": tools_list}
    
    async def _call_tool(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """ツールを呼び出す"""
        tool_name = params.get("name")
        tool_params = params.get("arguments", {})
        
        if tool_name not in self.tools:
            raise ValueError(f"Unknown tool: {tool_name}")
        
        tool = self.tools[tool_name]
        
        try:
            result = await tool.handler(**tool_params)
            return {"content": [{"type": "text", "text": json.dumps(result, ensure_ascii=False)}]}
        except Exception as e:
            logger.error(f"Tool execution failed: {e}")
            raise
    
    # ツールハンドラーの実装
    
    async def _file_read(self, path: str, encoding: str = "utf-8") -> Dict[str, Any]:
        """ファイルを読み取る"""
        file_path = self._resolve_path(path)
        
        try:
            with open(file_path, 'r', encoding=encoding) as f:
                content = f.read()
            
            return {
                "success": True,
                "content": content,
                "size": len(content),
                "path": str(file_path)
            }
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def _file_write(self, path: str, content: str, encoding: str = "utf-8") -> Dict[str, Any]:
        """ファイルに書き込む"""
        file_path = self._resolve_path(path)
        
        try:
            # ディレクトリを作成
            file_path.parent.mkdir(parents=True, exist_ok=True)
            
            with open(file_path, 'w', encoding=encoding) as f:
                f.write(content)
            
            return {
                "success": True,
                "bytes_written": len(content.encode(encoding)),
                "path": str(file_path)
            }
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def _mkdir(self, path: str, parents: bool = True) -> Dict[str, Any]:
        """ディレクトリを作成"""
        dir_path = self._resolve_path(path)
        
        try:
            dir_path.mkdir(parents=parents, exist_ok=True)
            return {"success": True, "path": str(dir_path)}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def _list_files(self, path: str = ".", recursive: bool = False) -> Dict[str, Any]:
        """ファイル一覧を取得"""
        dir_path = self._resolve_path(path)
        
        try:
            files = []
            if recursive:
                for file_path in dir_path.rglob("*"):
                    files.append({
                        "name": file_path.name,
                        "path": str(file_path.relative_to(self.workspace_dir)),
                        "type": "directory" if file_path.is_dir() else "file",
                        "size": file_path.stat().st_size if file_path.is_file() else None
                    })
            else:
                for file_path in dir_path.iterdir():
                    files.append({
                        "name": file_path.name,
                        "path": str(file_path.relative_to(self.workspace_dir)),
                        "type": "directory" if file_path.is_dir() else "file",
                        "size": file_path.stat().st_size if file_path.is_file() else None
                    })
            
            return {"success": True, "files": files}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def _shell_exec(self, command: str, cwd: str = None, timeout: float = 30) -> Dict[str, Any]:
        """シェルコマンドを実行"""
        work_dir = self._resolve_path(cwd) if cwd else self.workspace_dir
        
        try:
            process = await asyncio.create_subprocess_shell(
                command,
                cwd=work_dir,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            stdout, stderr = await asyncio.wait_for(
                process.communicate(), 
                timeout=timeout
            )
            
            return {
                "success": True,
                "exit_code": process.returncode,
                "stdout": stdout.decode('utf-8', errors='replace'),
                "stderr": stderr.decode('utf-8', errors='replace'),
                "command": command
            }
        except asyncio.TimeoutError:
            return {"success": False, "error": "Command timed out"}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def _git_init(self, path: str = ".") -> Dict[str, Any]:
        """Gitリポジトリを初期化"""
        return await self._shell_exec("git init", cwd=path)
    
    async def _git_add(self, files: List[str], path: str = ".") -> Dict[str, Any]:
        """ファイルをGitに追加"""
        files_str = " ".join(f'"{f}"' for f in files)
        return await self._shell_exec(f"git add {files_str}", cwd=path)
    
    async def _git_commit(self, message: str, path: str = ".") -> Dict[str, Any]:
        """変更をコミット"""
        return await self._shell_exec(f'git commit -m "{message}"', cwd=path)
    
    async def _analyze_code(self, file_path: str, language: str = None) -> Dict[str, Any]:
        """コードを静的解析"""
        full_path = self._resolve_path(file_path)
        
        if not full_path.exists():
            return {"success": False, "error": "File not found"}
        
        try:
            # ファイル拡張子から言語を推定
            if not language:
                ext = full_path.suffix.lower()
                language_map = {
                    '.py': 'python',
                    '.js': 'javascript',
                    '.ts': 'typescript',
                    '.java': 'java',
                    '.cpp': 'cpp',
                    '.c': 'c'
                }
                language = language_map.get(ext, 'unknown')
            
            # 基本的な分析
            with open(full_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            lines = content.split('\n')
            analysis = {
                "language": language,
                "lines_of_code": len(lines),
                "blank_lines": sum(1 for line in lines if not line.strip()),
                "comment_lines": 0,
                "file_size": len(content),
                "functions": [],
                "classes": [],
                "imports": []
            }
            
            # Python固有の分析
            if language == 'python':
                analysis.update(self._analyze_python_code(content))
            
            return {"success": True, "analysis": analysis}
            
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def _analyze_python_code(self, content: str) -> Dict[str, Any]:
        """Pythonコードの詳細分析"""
        import ast
        
        try:
            tree = ast.parse(content)
            
            functions = []
            classes = []
            imports = []
            
            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef):
                    functions.append({
                        "name": node.name,
                        "line": node.lineno,
                        "args": [arg.arg for arg in node.args.args]
                    })
                elif isinstance(node, ast.ClassDef):
                    classes.append({
                        "name": node.name,
                        "line": node.lineno,
                        "methods": [n.name for n in node.body if isinstance(n, ast.FunctionDef)]
                    })
                elif isinstance(node, (ast.Import, ast.ImportFrom)):
                    if isinstance(node, ast.Import):
                        imports.extend([alias.name for alias in node.names])
                    else:
                        imports.append(node.module)
            
            return {
                "functions": functions,
                "classes": classes,
                "imports": list(set(imports))
            }
            
        except SyntaxError as e:
            return {
                "syntax_error": {
                    "line": e.lineno,
                    "message": e.msg
                }
            }
    
    async def _run_tests(self, test_path: str = None, framework: str = "pytest") -> Dict[str, Any]:
        """テストを実行"""
        if framework == "pytest":
            command = f"python -m pytest {test_path or ''} -v"
        elif framework == "unittest":
            command = f"python -m unittest {test_path or 'discover'} -v"
        else:
            return {"success": False, "error": f"Unsupported test framework: {framework}"}
        
        return await self._shell_exec(command)
    
    def _resolve_path(self, path: str) -> Path:
        """パスを解決してワークスペース内に制限"""
        if path is None:
            return self.workspace_dir
        
        resolved = (self.workspace_dir / path).resolve()
        
        # セキュリティ: ワークスペース外へのアクセスを防ぐ
        try:
            resolved.relative_to(self.workspace_dir)
        except ValueError:
            raise ValueError(f"Path outside workspace: {path}")
        
        return resolved
    
    def get_tool_list(self) -> List[Dict[str, Any]]:
        """ツール一覧を取得"""
        return [
            {
                "name": tool.name,
                "description": tool.description,
                "parameters": tool.parameters
            }
            for tool in self.tools.values()
        ]

