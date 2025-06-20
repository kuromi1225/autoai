"""
ツールシステム - 拡張ツールマネージャー

このモジュールは、manus.aiやdevin.aiのような汎用自律型AIエージェントに
必要な包括的なツールシステムを実装します。
"""

import asyncio
import logging
import os
import subprocess
import json
import requests
from typing import Dict, List, Any, Optional
from abc import ABC, abstractmethod
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from PIL import Image, ImageDraw, ImageFont
import cv2
import numpy as np

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

class FileEditorTool(BaseTool):
    """ファイル編集ツール"""
    
    def __init__(self):
        super().__init__(
            name="file_editor",
            description="ファイルの読み書き、編集、検索を行う",
            category="file"
        )
        self.workspace_dir = os.environ.get("WORKSPACE_DIR", "/app/workspace")
        os.makedirs(self.workspace_dir, exist_ok=True)
    
    async def execute(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """ファイル操作を実行する"""
        action = parameters.get('action')
        file_path = parameters.get('file_path')
        
        try:
            if action == 'read':
                return await self._read_file(file_path)
            elif action == 'write':
                content = parameters.get('content', '')
                return await self._write_file(file_path, content)
            elif action == 'append':
                content = parameters.get('content', '')
                return await self._append_file(file_path, content)
            elif action == 'delete':
                return await self._delete_file(file_path)
            elif action == 'list':
                directory = parameters.get('directory', self.workspace_dir)
                return await self._list_files(directory)
            elif action == 'search':
                pattern = parameters.get('pattern', '')
                return await self._search_files(file_path, pattern)
            else:
                return {'success': False, 'error': f'Unknown action: {action}'}
                
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    async def _read_file(self, file_path: str) -> Dict[str, Any]:
        """ファイルを読み込む"""
        full_path = os.path.join(self.workspace_dir, file_path)
        
        if not os.path.exists(full_path):
            return {'success': False, 'error': 'File not found'}
        
        with open(full_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        return {
            'success': True,
            'content': content,
            'file_path': file_path,
            'size': len(content)
        }
    
    async def _write_file(self, file_path: str, content: str) -> Dict[str, Any]:
        """ファイルに書き込む"""
        full_path = os.path.join(self.workspace_dir, file_path)
        os.makedirs(os.path.dirname(full_path), exist_ok=True)
        
        with open(full_path, 'w', encoding='utf-8') as f:
            f.write(content)
        
        return {
            'success': True,
            'file_path': file_path,
            'size': len(content),
            'message': 'File written successfully'
        }
    
    async def _append_file(self, file_path: str, content: str) -> Dict[str, Any]:
        """ファイルに追記する"""
        full_path = os.path.join(self.workspace_dir, file_path)
        
        with open(full_path, 'a', encoding='utf-8') as f:
            f.write(content)
        
        return {
            'success': True,
            'file_path': file_path,
            'appended_size': len(content),
            'message': 'Content appended successfully'
        }
    
    async def _delete_file(self, file_path: str) -> Dict[str, Any]:
        """ファイルを削除する"""
        full_path = os.path.join(self.workspace_dir, file_path)
        
        if not os.path.exists(full_path):
            return {'success': False, 'error': 'File not found'}
        
        os.remove(full_path)
        
        return {
            'success': True,
            'file_path': file_path,
            'message': 'File deleted successfully'
        }
    
    async def _list_files(self, directory: str) -> Dict[str, Any]:
        """ディレクトリ内のファイルをリストする"""
        full_path = os.path.join(self.workspace_dir, directory)
        
        if not os.path.exists(full_path):
            return {'success': False, 'error': 'Directory not found'}
        
        files = []
        for item in os.listdir(full_path):
            item_path = os.path.join(full_path, item)
            files.append({
                'name': item,
                'type': 'directory' if os.path.isdir(item_path) else 'file',
                'size': os.path.getsize(item_path) if os.path.isfile(item_path) else 0
            })
        
        return {
            'success': True,
            'directory': directory,
            'files': files
        }
    
    async def _search_files(self, file_path: str, pattern: str) -> Dict[str, Any]:
        """ファイル内でパターンを検索する"""
        full_path = os.path.join(self.workspace_dir, file_path)
        
        if not os.path.exists(full_path):
            return {'success': False, 'error': 'File not found'}
        
        matches = []
        with open(full_path, 'r', encoding='utf-8') as f:
            for line_num, line in enumerate(f, 1):
                if pattern in line:
                    matches.append({
                        'line_number': line_num,
                        'line_content': line.strip(),
                        'match_position': line.find(pattern)
                    })
        
        return {
            'success': True,
            'file_path': file_path,
            'pattern': pattern,
            'matches': matches,
            'total_matches': len(matches)
        }
    
    def get_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "action": {
                    "type": "string",
                    "enum": ["read", "write", "append", "delete", "list", "search"],
                    "description": "実行するアクション"
                },
                "file_path": {
                    "type": "string",
                    "description": "ファイルパス（ワークスペース相対）"
                },
                "content": {
                    "type": "string",
                    "description": "ファイルの内容（write/appendアクション用）"
                },
                "directory": {
                    "type": "string",
                    "description": "ディレクトリパス（listアクション用）"
                },
                "pattern": {
                    "type": "string",
                    "description": "検索パターン（searchアクション用）"
                }
            },
            "required": ["action"]
        }

class CodeExecutorTool(BaseTool):
    """コード実行ツール"""
    
    def __init__(self):
        super().__init__(
            name="code_executor",
            description="Python、JavaScript、Shellコードを実行する",
            category="code"
        )
        self.workspace_dir = os.environ.get("WORKSPACE_DIR", "/app/workspace")
    
    async def execute(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """コードを実行する"""
        language = parameters.get('language', 'python')
        code = parameters.get('code', '')
        
        try:
            if language == 'python':
                return await self._execute_python(code)
            elif language == 'javascript':
                return await self._execute_javascript(code)
            elif language == 'shell':
                return await self._execute_shell(code)
            else:
                return {'success': False, 'error': f'Unsupported language: {language}'}
                
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    async def _execute_python(self, code: str) -> Dict[str, Any]:
        """Pythonコードを実行する"""
        # セキュリティのため、制限された環境で実行
        restricted_globals = {
            '__builtins__': {
                'print': print,
                'len': len,
                'str': str,
                'int': int,
                'float': float,
                'list': list,
                'dict': dict,
                'range': range,
                'enumerate': enumerate,
                'zip': zip,
                'map': map,
                'filter': filter,
                'sum': sum,
                'max': max,
                'min': min,
                'abs': abs,
                'round': round,
            },
            'os': os,
            'json': json,
            'pandas': pd,
            'matplotlib': plt,
            'seaborn': sns,
            'numpy': np
        }
        
        # 出力をキャプチャ
        import io
        import sys
        from contextlib import redirect_stdout, redirect_stderr
        
        stdout_capture = io.StringIO()
        stderr_capture = io.StringIO()
        
        try:
            with redirect_stdout(stdout_capture), redirect_stderr(stderr_capture):
                exec(code, restricted_globals)
            
            return {
                'success': True,
                'output': stdout_capture.getvalue(),
                'error': stderr_capture.getvalue(),
                'language': 'python'
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'output': stdout_capture.getvalue(),
                'language': 'python'
            }
    
    async def _execute_javascript(self, code: str) -> Dict[str, Any]:
        """JavaScriptコードを実行する"""
        # Node.jsを使用してJavaScriptを実行
        try:
            result = subprocess.run(
                ['node', '-e', code],
                capture_output=True,
                text=True,
                timeout=30,
                cwd=self.workspace_dir
            )
            
            return {
                'success': result.returncode == 0,
                'output': result.stdout,
                'error': result.stderr,
                'language': 'javascript',
                'return_code': result.returncode
            }
            
        except subprocess.TimeoutExpired:
            return {
                'success': False,
                'error': 'Execution timeout',
                'language': 'javascript'
            }
    
    async def _execute_shell(self, code: str) -> Dict[str, Any]:
        """Shellコードを実行する"""
        try:
            result = subprocess.run(
                code,
                shell=True,
                capture_output=True,
                text=True,
                timeout=30,
                cwd=self.workspace_dir
            )
            
            return {
                'success': result.returncode == 0,
                'output': result.stdout,
                'error': result.stderr,
                'language': 'shell',
                'return_code': result.returncode
            }
            
        except subprocess.TimeoutExpired:
            return {
                'success': False,
                'error': 'Execution timeout',
                'language': 'shell'
            }
    
    def get_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "language": {
                    "type": "string",
                    "enum": ["python", "javascript", "shell"],
                    "description": "実行する言語"
                },
                "code": {
                    "type": "string",
                    "description": "実行するコード"
                }
            },
            "required": ["code"]
        }

class BrowserTool(BaseTool):
    """ブラウザ自動化ツール"""
    
    def __init__(self):
        super().__init__(
            name="browser",
            description="ブラウザを自動化してWebページの操作を行う",
            category="browser"
        )
        self.driver = None
    
    async def execute(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """ブラウザ操作を実行する"""
        action = parameters.get('action')
        
        try:
            if action == 'start':
                return await self._start_browser()
            elif action == 'navigate':
                url = parameters.get('url')
                return await self._navigate(url)
            elif action == 'click':
                selector = parameters.get('selector')
                return await self._click(selector)
            elif action == 'input':
                selector = parameters.get('selector')
                text = parameters.get('text')
                return await self._input(selector, text)
            elif action == 'get_text':
                selector = parameters.get('selector')
                return await self._get_text(selector)
            elif action == 'screenshot':
                return await self._screenshot()
            elif action == 'stop':
                return await self._stop_browser()
            else:
                return {'success': False, 'error': f'Unknown action: {action}'}
                
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    async def _start_browser(self) -> Dict[str, Any]:
        """ブラウザを起動する"""
        if self.driver is not None:
            return {'success': True, 'message': 'Browser already running'}
        
        options = Options()
        options.add_argument('--headless')
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        
        self.driver = webdriver.Chrome(options=options)
        
        return {
            'success': True,
            'message': 'Browser started successfully'
        }
    
    async def _navigate(self, url: str) -> Dict[str, Any]:
        """指定URLに移動する"""
        if self.driver is None:
            await self._start_browser()
        
        self.driver.get(url)
        
        return {
            'success': True,
            'url': url,
            'title': self.driver.title,
            'current_url': self.driver.current_url
        }
    
    async def _click(self, selector: str) -> Dict[str, Any]:
        """要素をクリックする"""
        if self.driver is None:
            return {'success': False, 'error': 'Browser not started'}
        
        element = self.driver.find_element(By.CSS_SELECTOR, selector)
        element.click()
        
        return {
            'success': True,
            'selector': selector,
            'message': 'Element clicked successfully'
        }
    
    async def _input(self, selector: str, text: str) -> Dict[str, Any]:
        """要素にテキストを入力する"""
        if self.driver is None:
            return {'success': False, 'error': 'Browser not started'}
        
        element = self.driver.find_element(By.CSS_SELECTOR, selector)
        element.clear()
        element.send_keys(text)
        
        return {
            'success': True,
            'selector': selector,
            'text': text,
            'message': 'Text input successfully'
        }
    
    async def _get_text(self, selector: str) -> Dict[str, Any]:
        """要素のテキストを取得する"""
        if self.driver is None:
            return {'success': False, 'error': 'Browser not started'}
        
        element = self.driver.find_element(By.CSS_SELECTOR, selector)
        text = element.text
        
        return {
            'success': True,
            'selector': selector,
            'text': text
        }
    
    async def _screenshot(self) -> Dict[str, Any]:
        """スクリーンショットを撮る"""
        if self.driver is None:
            return {'success': False, 'error': 'Browser not started'}
        
        screenshot_path = os.path.join(
            os.environ.get("WORKSPACE_DIR", "/app/workspace"),
            f"screenshot_{int(asyncio.get_event_loop().time())}.png"
        )
        
        self.driver.save_screenshot(screenshot_path)
        
        return {
            'success': True,
            'screenshot_path': screenshot_path,
            'message': 'Screenshot saved successfully'
        }
    
    async def _stop_browser(self) -> Dict[str, Any]:
        """ブラウザを停止する"""
        if self.driver is not None:
            self.driver.quit()
            self.driver = None
        
        return {
            'success': True,
            'message': 'Browser stopped successfully'
        }
    
    def get_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "action": {
                    "type": "string",
                    "enum": ["start", "navigate", "click", "input", "get_text", "screenshot", "stop"],
                    "description": "実行するアクション"
                },
                "url": {
                    "type": "string",
                    "description": "ナビゲート先のURL（navigateアクション用）"
                },
                "selector": {
                    "type": "string",
                    "description": "CSSセレクター（click/input/get_textアクション用）"
                },
                "text": {
                    "type": "string",
                    "description": "入力するテキスト（inputアクション用）"
                }
            },
            "required": ["action"]
        }

class DataAnalysisTool(BaseTool):
    """データ分析ツール"""
    
    def __init__(self):
        super().__init__(
            name="data_analysis",
            description="データの読み込み、分析、可視化を行う",
            category="data"
        )
        self.workspace_dir = os.environ.get("WORKSPACE_DIR", "/app/workspace")
    
    async def execute(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """データ分析を実行する"""
        action = parameters.get('action')
        
        try:
            if action == 'load_csv':
                file_path = parameters.get('file_path')
                return await self._load_csv(file_path)
            elif action == 'analyze':
                data_id = parameters.get('data_id')
                return await self._analyze_data(data_id)
            elif action == 'visualize':
                data_id = parameters.get('data_id')
                chart_type = parameters.get('chart_type', 'line')
                return await self._visualize_data(data_id, chart_type)
            elif action == 'export':
                data_id = parameters.get('data_id')
                format_type = parameters.get('format', 'csv')
                return await self._export_data(data_id, format_type)
            else:
                return {'success': False, 'error': f'Unknown action: {action}'}
                
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    async def _load_csv(self, file_path: str) -> Dict[str, Any]:
        """CSVファイルを読み込む"""
        full_path = os.path.join(self.workspace_dir, file_path)
        
        if not os.path.exists(full_path):
            return {'success': False, 'error': 'File not found'}
        
        df = pd.read_csv(full_path)
        data_id = f"data_{int(asyncio.get_event_loop().time())}"
        
        # データを一時的に保存（実際の実装では適切なデータストレージを使用）
        setattr(self, data_id, df)
        
        return {
            'success': True,
            'data_id': data_id,
            'shape': df.shape,
            'columns': df.columns.tolist(),
            'head': df.head().to_dict('records')
        }
    
    async def _analyze_data(self, data_id: str) -> Dict[str, Any]:
        """データを分析する"""
        if not hasattr(self, data_id):
            return {'success': False, 'error': 'Data not found'}
        
        df = getattr(self, data_id)
        
        analysis = {
            'shape': df.shape,
            'columns': df.columns.tolist(),
            'dtypes': df.dtypes.to_dict(),
            'missing_values': df.isnull().sum().to_dict(),
            'numeric_summary': df.describe().to_dict() if len(df.select_dtypes(include=[np.number]).columns) > 0 else {},
            'categorical_summary': {}
        }
        
        # カテゴリカル変数の分析
        categorical_cols = df.select_dtypes(include=['object']).columns
        for col in categorical_cols:
            analysis['categorical_summary'][col] = df[col].value_counts().head().to_dict()
        
        return {
            'success': True,
            'data_id': data_id,
            'analysis': analysis
        }
    
    async def _visualize_data(self, data_id: str, chart_type: str) -> Dict[str, Any]:
        """データを可視化する"""
        if not hasattr(self, data_id):
            return {'success': False, 'error': 'Data not found'}
        
        df = getattr(self, data_id)
        
        plt.figure(figsize=(10, 6))
        
        if chart_type == 'line':
            numeric_cols = df.select_dtypes(include=[np.number]).columns
            if len(numeric_cols) > 0:
                df[numeric_cols].plot(kind='line')
        elif chart_type == 'bar':
            numeric_cols = df.select_dtypes(include=[np.number]).columns
            if len(numeric_cols) > 0:
                df[numeric_cols].plot(kind='bar')
        elif chart_type == 'histogram':
            numeric_cols = df.select_dtypes(include=[np.number]).columns
            if len(numeric_cols) > 0:
                df[numeric_cols].hist(bins=20, figsize=(12, 8))
        elif chart_type == 'correlation':
            numeric_cols = df.select_dtypes(include=[np.number]).columns
            if len(numeric_cols) > 1:
                correlation_matrix = df[numeric_cols].corr()
                sns.heatmap(correlation_matrix, annot=True, cmap='coolwarm')
        
        chart_path = os.path.join(
            self.workspace_dir,
            f"chart_{data_id}_{chart_type}_{int(asyncio.get_event_loop().time())}.png"
        )
        
        plt.savefig(chart_path, dpi=300, bbox_inches='tight')
        plt.close()
        
        return {
            'success': True,
            'data_id': data_id,
            'chart_type': chart_type,
            'chart_path': chart_path
        }
    
    async def _export_data(self, data_id: str, format_type: str) -> Dict[str, Any]:
        """データをエクスポートする"""
        if not hasattr(self, data_id):
            return {'success': False, 'error': 'Data not found'}
        
        df = getattr(self, data_id)
        
        export_path = os.path.join(
            self.workspace_dir,
            f"export_{data_id}_{int(asyncio.get_event_loop().time())}.{format_type}"
        )
        
        if format_type == 'csv':
            df.to_csv(export_path, index=False)
        elif format_type == 'json':
            df.to_json(export_path, orient='records', indent=2)
        elif format_type == 'excel':
            df.to_excel(export_path, index=False)
        else:
            return {'success': False, 'error': f'Unsupported format: {format_type}'}
        
        return {
            'success': True,
            'data_id': data_id,
            'format': format_type,
            'export_path': export_path
        }
    
    def get_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "action": {
                    "type": "string",
                    "enum": ["load_csv", "analyze", "visualize", "export"],
                    "description": "実行するアクション"
                },
                "file_path": {
                    "type": "string",
                    "description": "ファイルパス（load_csvアクション用）"
                },
                "data_id": {
                    "type": "string",
                    "description": "データID（analyze/visualize/exportアクション用）"
                },
                "chart_type": {
                    "type": "string",
                    "enum": ["line", "bar", "histogram", "correlation"],
                    "description": "チャートタイプ（visualizeアクション用）"
                },
                "format": {
                    "type": "string",
                    "enum": ["csv", "json", "excel"],
                    "description": "エクスポート形式（exportアクション用）"
                }
            },
            "required": ["action"]
        }

class ImageGeneratorTool(BaseTool):
    """画像生成・編集ツール"""
    
    def __init__(self):
        super().__init__(
            name="image_generator",
            description="画像の生成、編集、変換を行う",
            category="media"
        )
        self.workspace_dir = os.environ.get("WORKSPACE_DIR", "/app/workspace")
    
    async def execute(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """画像操作を実行する"""
        action = parameters.get('action')
        
        try:
            if action == 'create':
                width = parameters.get('width', 800)
                height = parameters.get('height', 600)
                background_color = parameters.get('background_color', 'white')
                return await self._create_image(width, height, background_color)
            elif action == 'add_text':
                image_path = parameters.get('image_path')
                text = parameters.get('text')
                position = parameters.get('position', (50, 50))
                return await self._add_text(image_path, text, position)
            elif action == 'resize':
                image_path = parameters.get('image_path')
                width = parameters.get('width')
                height = parameters.get('height')
                return await self._resize_image(image_path, width, height)
            elif action == 'convert':
                image_path = parameters.get('image_path')
                format_type = parameters.get('format', 'PNG')
                return await self._convert_image(image_path, format_type)
            else:
                return {'success': False, 'error': f'Unknown action: {action}'}
                
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    async def _create_image(self, width: int, height: int, background_color: str) -> Dict[str, Any]:
        """新しい画像を作成する"""
        image = Image.new('RGB', (width, height), background_color)
        
        image_path = os.path.join(
            self.workspace_dir,
            f"created_image_{int(asyncio.get_event_loop().time())}.png"
        )
        
        image.save(image_path)
        
        return {
            'success': True,
            'image_path': image_path,
            'width': width,
            'height': height,
            'background_color': background_color
        }
    
    async def _add_text(self, image_path: str, text: str, position: tuple) -> Dict[str, Any]:
        """画像にテキストを追加する"""
        full_path = os.path.join(self.workspace_dir, image_path)
        
        if not os.path.exists(full_path):
            return {'success': False, 'error': 'Image not found'}
        
        image = Image.open(full_path)
        draw = ImageDraw.Draw(image)
        
        # デフォルトフォントを使用
        try:
            font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 24)
        except:
            font = ImageFont.load_default()
        
        draw.text(position, text, fill='black', font=font)
        
        output_path = os.path.join(
            self.workspace_dir,
            f"text_added_{int(asyncio.get_event_loop().time())}.png"
        )
        
        image.save(output_path)
        
        return {
            'success': True,
            'original_path': image_path,
            'output_path': output_path,
            'text': text,
            'position': position
        }
    
    async def _resize_image(self, image_path: str, width: int, height: int) -> Dict[str, Any]:
        """画像をリサイズする"""
        full_path = os.path.join(self.workspace_dir, image_path)
        
        if not os.path.exists(full_path):
            return {'success': False, 'error': 'Image not found'}
        
        image = Image.open(full_path)
        resized_image = image.resize((width, height))
        
        output_path = os.path.join(
            self.workspace_dir,
            f"resized_{width}x{height}_{int(asyncio.get_event_loop().time())}.png"
        )
        
        resized_image.save(output_path)
        
        return {
            'success': True,
            'original_path': image_path,
            'output_path': output_path,
            'original_size': image.size,
            'new_size': (width, height)
        }
    
    async def _convert_image(self, image_path: str, format_type: str) -> Dict[str, Any]:
        """画像形式を変換する"""
        full_path = os.path.join(self.workspace_dir, image_path)
        
        if not os.path.exists(full_path):
            return {'success': False, 'error': 'Image not found'}
        
        image = Image.open(full_path)
        
        output_path = os.path.join(
            self.workspace_dir,
            f"converted_{int(asyncio.get_event_loop().time())}.{format_type.lower()}"
        )
        
        image.save(output_path, format=format_type)
        
        return {
            'success': True,
            'original_path': image_path,
            'output_path': output_path,
            'format': format_type
        }
    
    def get_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "action": {
                    "type": "string",
                    "enum": ["create", "add_text", "resize", "convert"],
                    "description": "実行するアクション"
                },
                "width": {
                    "type": "integer",
                    "description": "画像の幅"
                },
                "height": {
                    "type": "integer",
                    "description": "画像の高さ"
                },
                "background_color": {
                    "type": "string",
                    "description": "背景色"
                },
                "image_path": {
                    "type": "string",
                    "description": "画像ファイルパス"
                },
                "text": {
                    "type": "string",
                    "description": "追加するテキスト"
                },
                "position": {
                    "type": "array",
                    "items": {"type": "integer"},
                    "description": "テキストの位置 [x, y]"
                },
                "format": {
                    "type": "string",
                    "enum": ["PNG", "JPEG", "GIF", "BMP"],
                    "description": "変換先の画像形式"
                }
            },
            "required": ["action"]
        }

class EnhancedToolManager:
    """拡張ツールマネージャー"""
    
    def __init__(self):
        self.tools: Dict[str, BaseTool] = {}
        self._register_default_tools()
    
    def _register_default_tools(self):
        """デフォルトツールを登録"""
        tools = [
            FileEditorTool(),
            CodeExecutorTool(),
            BrowserTool(),
            DataAnalysisTool(),
            ImageGeneratorTool()
        ]
        
        for tool in tools:
            self.register_tool(tool)
    
    def register_tool(self, tool: BaseTool):
        """ツールを登録"""
        self.tools[tool.name] = tool
        logger.info(f"Tool registered: {tool.name}")
    
    async def execute_tool(self, tool_name: str, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """ツールを実行"""
        if tool_name not in self.tools:
            return {'success': False, 'error': f'Tool not found: {tool_name}'}
        
        tool = self.tools[tool_name]
        
        try:
            result = await tool.execute(parameters)
            logger.info(f"Tool executed successfully: {tool_name}")
            return result
            
        except Exception as e:
            logger.error(f"Tool execution failed: {tool_name}, error: {str(e)}")
            return {'success': False, 'error': str(e)}
    
    def get_available_tools(self) -> Dict[str, Dict[str, Any]]:
        """利用可能なツールの一覧を取得"""
        return {
            name: {
                'name': tool.name,
                'description': tool.description,
                'category': tool.category,
                'schema': tool.get_schema()
            }
            for name, tool in self.tools.items()
        }
    
    def get_tool_schema(self, tool_name: str) -> Optional[Dict[str, Any]]:
        """ツールのスキーマを取得"""
        if tool_name in self.tools:
            return self.tools[tool_name].get_schema()
        return None

