# ツール管理システム

import asyncio
import logging
from typing import Dict, List, Any, Optional
from abc import ABC, abstractmethod

logger = logging.getLogger(__name__)

class BaseTool(ABC):
    """ツールの基底クラス"""
    
    def __init__(self, name: str, description: str, category: str):
        self.name = name
        self.description = description
        self.category = category
    
    @abstractmethod
    async def execute(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """ツールを実行する"""
        pass
    
    @abstractmethod
    def get_schema(self) -> Dict[str, Any]:
        """ツールの入力スキーマを取得する"""
        pass

class BrowserTool(BaseTool):
    """ブラウザ自動化ツール"""
    
    def __init__(self):
        super().__init__(
            name="browser",
            description="ブラウザを自動化してWebページの操作を行う",
            category="browser"
        )
    
    async def execute(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """ブラウザ操作を実行する"""
        
        action = parameters.get('action')
        url = parameters.get('url')
        
        try:
            if action == 'navigate':
                return await self._navigate(url)
            elif action == 'click':
                return await self._click(parameters.get('selector'))
            elif action == 'input':
                return await self._input(parameters.get('selector'), parameters.get('text'))
            elif action == 'screenshot':
                return await self._screenshot()
            elif action == 'get_text':
                return await self._get_text(parameters.get('selector'))
            else:
                raise ValueError(f"Unknown browser action: {action}")
                
        except Exception as e:
            logger.error(f"Browser tool execution failed: {e}")
            return {
                'success': False,
                'error': str(e),
                'tool': self.name
            }
    
    async def _navigate(self, url: str) -> Dict[str, Any]:
        """指定URLに移動する"""
        # 実装は後で追加
        return {
            'success': True,
            'action': 'navigate',
            'url': url,
            'message': f'Navigated to {url}'
        }
    
    async def _click(self, selector: str) -> Dict[str, Any]:
        """要素をクリックする"""
        # 実装は後で追加
        return {
            'success': True,
            'action': 'click',
            'selector': selector,
            'message': f'Clicked element: {selector}'
        }
    
    async def _input(self, selector: str, text: str) -> Dict[str, Any]:
        """テキストを入力する"""
        # 実装は後で追加
        return {
            'success': True,
            'action': 'input',
            'selector': selector,
            'text': text,
            'message': f'Input text to {selector}'
        }
    
    async def _screenshot(self) -> Dict[str, Any]:
        """スクリーンショットを撮る"""
        # 実装は後で追加
        return {
            'success': True,
            'action': 'screenshot',
            'message': 'Screenshot taken'
        }
    
    async def _get_text(self, selector: str) -> Dict[str, Any]:
        """要素のテキストを取得する"""
        # 実装は後で追加
        return {
            'success': True,
            'action': 'get_text',
            'selector': selector,
            'text': 'Sample text',
            'message': f'Got text from {selector}'
        }
    
    def get_schema(self) -> Dict[str, Any]:
        """ブラウザツールのスキーマ"""
        return {
            'type': 'object',
            'properties': {
                'action': {
                    'type': 'string',
                    'enum': ['navigate', 'click', 'input', 'screenshot', 'get_text'],
                    'description': '実行するアクション'
                },
                'url': {
                    'type': 'string',
                    'description': 'ナビゲート先のURL（navigateアクション用）'
                },
                'selector': {
                    'type': 'string',
                    'description': 'CSS セレクター'
                },
                'text': {
                    'type': 'string',
                    'description': '入力するテキスト（inputアクション用）'
                }
            },
            'required': ['action']
        }

class FileTool(BaseTool):
    """ファイル操作ツール"""
    
    def __init__(self):
        super().__init__(
            name="file",
            description="ファイルシステムの操作を行う",
            category="file"
        )
    
    async def execute(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """ファイル操作を実行する"""
        
        action = parameters.get('action')
        
        try:
            if action == 'read':
                return await self._read_file(parameters.get('path'))
            elif action == 'write':
                return await self._write_file(parameters.get('path'), parameters.get('content'))
            elif action == 'list':
                return await self._list_directory(parameters.get('path'))
            elif action == 'create_dir':
                return await self._create_directory(parameters.get('path'))
            elif action == 'delete':
                return await self._delete_file(parameters.get('path'))
            else:
                raise ValueError(f"Unknown file action: {action}")
                
        except Exception as e:
            logger.error(f"File tool execution failed: {e}")
            return {
                'success': False,
                'error': str(e),
                'tool': self.name
            }
    
    async def _read_file(self, path: str) -> Dict[str, Any]:
        """ファイルを読み込む"""
        # 実装は後で追加
        return {
            'success': True,
            'action': 'read',
            'path': path,
            'content': 'Sample file content',
            'message': f'Read file: {path}'
        }
    
    async def _write_file(self, path: str, content: str) -> Dict[str, Any]:
        """ファイルに書き込む"""
        # 実装は後で追加
        return {
            'success': True,
            'action': 'write',
            'path': path,
            'message': f'Wrote to file: {path}'
        }
    
    async def _list_directory(self, path: str) -> Dict[str, Any]:
        """ディレクトリの内容を一覧表示する"""
        # 実装は後で追加
        return {
            'success': True,
            'action': 'list',
            'path': path,
            'files': ['file1.txt', 'file2.txt', 'subdir/'],
            'message': f'Listed directory: {path}'
        }
    
    async def _create_directory(self, path: str) -> Dict[str, Any]:
        """ディレクトリを作成する"""
        # 実装は後で追加
        return {
            'success': True,
            'action': 'create_dir',
            'path': path,
            'message': f'Created directory: {path}'
        }
    
    async def _delete_file(self, path: str) -> Dict[str, Any]:
        """ファイルを削除する"""
        # 実装は後で追加
        return {
            'success': True,
            'action': 'delete',
            'path': path,
            'message': f'Deleted file: {path}'
        }
    
    def get_schema(self) -> Dict[str, Any]:
        """ファイルツールのスキーマ"""
        return {
            'type': 'object',
            'properties': {
                'action': {
                    'type': 'string',
                    'enum': ['read', 'write', 'list', 'create_dir', 'delete'],
                    'description': '実行するアクション'
                },
                'path': {
                    'type': 'string',
                    'description': 'ファイルまたはディレクトリのパス'
                },
                'content': {
                    'type': 'string',
                    'description': 'ファイルに書き込む内容（writeアクション用）'
                }
            },
            'required': ['action', 'path']
        }

class CodeTool(BaseTool):
    """コード実行ツール"""
    
    def __init__(self):
        super().__init__(
            name="code",
            description="プログラムコードを実行する",
            category="code"
        )
    
    async def execute(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """コードを実行する"""
        
        language = parameters.get('language')
        code = parameters.get('code')
        
        try:
            if language == 'python':
                return await self._execute_python(code)
            elif language == 'javascript':
                return await self._execute_javascript(code)
            elif language == 'shell':
                return await self._execute_shell(code)
            else:
                raise ValueError(f"Unsupported language: {language}")
                
        except Exception as e:
            logger.error(f"Code tool execution failed: {e}")
            return {
                'success': False,
                'error': str(e),
                'tool': self.name
            }
    
    async def _execute_python(self, code: str) -> Dict[str, Any]:
        """Pythonコードを実行する"""
        # 実装は後で追加
        return {
            'success': True,
            'language': 'python',
            'code': code,
            'output': 'Sample output',
            'message': 'Python code executed'
        }
    
    async def _execute_javascript(self, code: str) -> Dict[str, Any]:
        """JavaScriptコードを実行する"""
        # 実装は後で追加
        return {
            'success': True,
            'language': 'javascript',
            'code': code,
            'output': 'Sample output',
            'message': 'JavaScript code executed'
        }
    
    async def _execute_shell(self, code: str) -> Dict[str, Any]:
        """シェルコマンドを実行する"""
        # 実装は後で追加
        return {
            'success': True,
            'language': 'shell',
            'code': code,
            'output': 'Sample output',
            'message': 'Shell command executed'
        }
    
    def get_schema(self) -> Dict[str, Any]:
        """コードツールのスキーマ"""
        return {
            'type': 'object',
            'properties': {
                'language': {
                    'type': 'string',
                    'enum': ['python', 'javascript', 'shell'],
                    'description': 'プログラミング言語'
                },
                'code': {
                    'type': 'string',
                    'description': '実行するコード'
                }
            },
            'required': ['language', 'code']
        }

class APITool(BaseTool):
    """API呼び出しツール"""
    
    def __init__(self):
        super().__init__(
            name="api",
            description="外部APIを呼び出す",
            category="api"
        )
    
    async def execute(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """API呼び出しを実行する"""
        
        method = parameters.get('method', 'GET')
        url = parameters.get('url')
        headers = parameters.get('headers', {})
        data = parameters.get('data')
        
        try:
            # 実装は後で追加
            return {
                'success': True,
                'method': method,
                'url': url,
                'status_code': 200,
                'response': {'message': 'Sample API response'},
                'message': f'API call to {url} completed'
            }
                
        except Exception as e:
            logger.error(f"API tool execution failed: {e}")
            return {
                'success': False,
                'error': str(e),
                'tool': self.name
            }
    
    def get_schema(self) -> Dict[str, Any]:
        """APIツールのスキーマ"""
        return {
            'type': 'object',
            'properties': {
                'method': {
                    'type': 'string',
                    'enum': ['GET', 'POST', 'PUT', 'DELETE', 'PATCH'],
                    'description': 'HTTPメソッド'
                },
                'url': {
                    'type': 'string',
                    'description': 'API エンドポイントURL'
                },
                'headers': {
                    'type': 'object',
                    'description': 'HTTPヘッダー'
                },
                'data': {
                    'type': 'object',
                    'description': 'リクエストボディ'
                }
            },
            'required': ['url']
        }

class ToolManager:
    """ツール管理クラス"""
    
    def __init__(self):
        self.tools = {}
        self._register_default_tools()
    
    def _register_default_tools(self):
        """デフォルトツールを登録する"""
        self.register_tool(BrowserTool())
        self.register_tool(FileTool())
        self.register_tool(CodeTool())
        self.register_tool(APITool())
        self.register_tool(GitTool()) # GitToolを追加
    
    def register_tool(self, tool: BaseTool):
        """ツールを登録する"""
        self.tools[tool.name] = tool
        logger.info(f"Registered tool: {tool.name}")
    
    def get_tool(self, name: str) -> Optional[BaseTool]:
        """ツールを取得する"""
        return self.tools.get(name)
    
    def get_available_tools(self) -> List[Dict[str, Any]]:
        """利用可能なツールのリストを取得する"""
        return [
            {
                'name': tool.name,
                'description': tool.description,
                'category': tool.category,
                'schema': tool.get_schema()
            }
            for tool in self.tools.values()
        ]
    
    async def execute_tool(self, tool_name: str, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """ツールを実行する"""
        
        tool = self.get_tool(tool_name)
        if not tool:
            raise ValueError(f"Tool not found: {tool_name}")
        
        logger.info(f"Executing tool: {tool_name} with parameters: {parameters}")
        
        result = await tool.execute(parameters)
        
        logger.info(f"Tool execution completed: {tool_name}")
        
        return result

class GitTool(BaseTool):
    """Git操作ツール"""

    def __init__(self):
        super().__init__(
            name="git",
            description="Gitリポジトリの操作を行う",
            category="git"
        )
        # git_tool.pyから関数をインポート
        from backend.tools import git_tool as gt
        self.git_functions = {
            "clone": gt.clone_repository,
            "commit": gt.commit,
            "push": gt.push,
        }

    async def execute(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Git操作を実行する"""

        action = parameters.get('action')

        try:
            if action == 'clone':
                repo_url = parameters.get('repo_url')
                directory = parameters.get('directory', '.')
                result_message = self.git_functions["clone"](repo_url, directory)
                success = "Error" not in result_message
                return {
                    'success': success,
                    'action': 'clone',
                    'repo_url': repo_url,
                    'directory': directory,
                    'message': result_message
                }
            elif action == 'commit':
                message = parameters.get('message')
                result_message = self.git_functions["commit"](message)
                success = "Error" not in result_message
                return {
                    'success': success,
                    'action': 'commit',
                    'message': result_message
                }
            elif action == 'push':
                result_message = self.git_functions["push"]()
                success = "Error" not in result_message
                return {
                    'success': success,
                    'action': 'push',
                    'message': result_message
                }
            else:
                raise ValueError(f"Unknown git action: {action}")

        except Exception as e:
            logger.error(f"Git tool execution failed: {e}")
            return {
                'success': False,
                'error': str(e),
                'tool': self.name
            }

    def get_schema(self) -> Dict[str, Any]:
        """Gitツールのスキーマ"""
        return {
            'type': 'object',
            'properties': {
                'action': {
                    'type': 'string',
                    'enum': ['clone', 'commit', 'push'],
                    'description': '実行するGitアクション'
                },
                'repo_url': {
                    'type': 'string',
                    'description': 'クローンするリポジトリのURL (cloneアクション用)'
                },
                'directory': {
                    'type': 'string',
                    'description': 'クローン先のディレクトリ名 (cloneアクション用、オプション)'
                },
                'message': {
                    'type': 'string',
                    'description': 'コミットメッセージ (commitアクション用)'
                }
            },
            'required': ['action']
        }
