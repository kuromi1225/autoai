"""
ファイルシステムとプロジェクト管理

このモジュールは、セキュアなファイルシステム管理と
プロジェクト管理機能を実装します。
"""

import os
import shutil
import json
import logging
from typing import Dict, List, Any, Optional, Union
from pathlib import Path
from datetime import datetime
import uuid
import mimetypes
import zipfile
import tempfile
from werkzeug.utils import secure_filename
from flask import current_app

logger = logging.getLogger(__name__)

class FileSystemManager:
    """セキュアなファイルシステム管理"""
    
    def __init__(self, workspace_root: str):
        self.workspace_root = Path(workspace_root)
        self.workspace_root.mkdir(parents=True, exist_ok=True)
        
        # 許可されるファイル拡張子
        self.allowed_extensions = {
            'text': ['.txt', '.md', '.json', '.xml', '.csv', '.log'],
            'code': ['.py', '.js', '.jsx', '.ts', '.tsx', '.html', '.css', '.java', '.cpp', '.c', '.go', '.rs'],
            'image': ['.png', '.jpg', '.jpeg', '.gif', '.svg', '.bmp', '.webp'],
            'document': ['.pdf', '.doc', '.docx', '.xls', '.xlsx', '.ppt', '.pptx'],
            'archive': ['.zip', '.tar', '.gz', '.rar'],
            'config': ['.yml', '.yaml', '.toml', '.ini', '.conf']
        }
        
        # 最大ファイルサイズ (100MB)
        self.max_file_size = 100 * 1024 * 1024
        
        # 禁止されるファイル名パターン
        self.forbidden_patterns = [
            '..', '.env', '.git', '__pycache__', 'node_modules'
        ]
    
    def _validate_path(self, path: Union[str, Path]) -> Path:
        """パスの安全性を検証"""
        path = Path(path)
        
        # 絶対パスを相対パスに変換
        if path.is_absolute():
            path = path.relative_to(path.anchor)
        
        # パストラバーサル攻撃を防ぐ
        resolved_path = (self.workspace_root / path).resolve()
        
        if not str(resolved_path).startswith(str(self.workspace_root.resolve())):
            raise ValueError(f"Path traversal detected: {path}")
        
        # 禁止パターンをチェック
        for part in path.parts:
            if any(pattern in part for pattern in self.forbidden_patterns):
                raise ValueError(f"Forbidden path pattern: {part}")
        
        return resolved_path
    
    def _get_file_info(self, file_path: Path) -> Dict[str, Any]:
        """ファイル情報を取得"""
        try:
            stat = file_path.stat()
            mime_type, _ = mimetypes.guess_type(str(file_path))
            
            return {
                'name': file_path.name,
                'path': str(file_path.relative_to(self.workspace_root)),
                'type': 'directory' if file_path.is_dir() else 'file',
                'size': stat.st_size if file_path.is_file() else 0,
                'mime_type': mime_type,
                'created_at': datetime.fromtimestamp(stat.st_ctime).isoformat(),
                'modified_at': datetime.fromtimestamp(stat.st_mtime).isoformat(),
                'permissions': oct(stat.st_mode)[-3:]
            }
        except Exception as e:
            logger.error(f"Error getting file info for {file_path}: {e}")
            return None
    
    def list_files(self, directory: str = "/", recursive: bool = False) -> List[Dict[str, Any]]:
        """ディレクトリ内のファイルをリスト"""
        try:
            dir_path = self._validate_path(directory)
            
            if not dir_path.exists():
                return []
            
            if not dir_path.is_dir():
                raise ValueError(f"Path is not a directory: {directory}")
            
            files = []
            
            if recursive:
                for item in dir_path.rglob('*'):
                    file_info = self._get_file_info(item)
                    if file_info:
                        files.append(file_info)
            else:
                for item in dir_path.iterdir():
                    file_info = self._get_file_info(item)
                    if file_info:
                        files.append(file_info)
            
            return sorted(files, key=lambda x: (x['type'] == 'file', x['name'].lower()))
            
        except Exception as e:
            logger.error(f"Error listing files in {directory}: {e}")
            raise
    
    def read_file(self, file_path: str, encoding: str = 'utf-8') -> str:
        """ファイルを読み込み"""
        try:
            full_path = self._validate_path(file_path)
            
            if not full_path.exists():
                raise FileNotFoundError(f"File not found: {file_path}")
            
            if not full_path.is_file():
                raise ValueError(f"Path is not a file: {file_path}")
            
            # ファイルサイズをチェック
            if full_path.stat().st_size > self.max_file_size:
                raise ValueError(f"File too large: {file_path}")
            
            with open(full_path, 'r', encoding=encoding) as f:
                return f.read()
                
        except Exception as e:
            logger.error(f"Error reading file {file_path}: {e}")
            raise
    
    def write_file(self, file_path: str, content: str, encoding: str = 'utf-8') -> Dict[str, Any]:
        """ファイルに書き込み"""
        try:
            full_path = self._validate_path(file_path)
            
            # ディレクトリを作成
            full_path.parent.mkdir(parents=True, exist_ok=True)
            
            # コンテンツサイズをチェック
            content_bytes = content.encode(encoding)
            if len(content_bytes) > self.max_file_size:
                raise ValueError(f"Content too large for file: {file_path}")
            
            with open(full_path, 'w', encoding=encoding) as f:
                f.write(content)
            
            return self._get_file_info(full_path)
            
        except Exception as e:
            logger.error(f"Error writing file {file_path}: {e}")
            raise
    
    def append_file(self, file_path: str, content: str, encoding: str = 'utf-8') -> Dict[str, Any]:
        """ファイルに追記"""
        try:
            full_path = self._validate_path(file_path)
            
            # ファイルが存在しない場合は作成
            if not full_path.exists():
                full_path.parent.mkdir(parents=True, exist_ok=True)
                full_path.touch()
            
            # 追記後のサイズをチェック
            current_size = full_path.stat().st_size if full_path.exists() else 0
            content_bytes = content.encode(encoding)
            
            if current_size + len(content_bytes) > self.max_file_size:
                raise ValueError(f"File would become too large: {file_path}")
            
            with open(full_path, 'a', encoding=encoding) as f:
                f.write(content)
            
            return self._get_file_info(full_path)
            
        except Exception as e:
            logger.error(f"Error appending to file {file_path}: {e}")
            raise
    
    def delete_file(self, file_path: str) -> bool:
        """ファイルまたはディレクトリを削除"""
        try:
            full_path = self._validate_path(file_path)
            
            if not full_path.exists():
                return False
            
            if full_path.is_dir():
                shutil.rmtree(full_path)
            else:
                full_path.unlink()
            
            return True
            
        except Exception as e:
            logger.error(f"Error deleting {file_path}: {e}")
            raise
    
    def create_directory(self, dir_path: str) -> Dict[str, Any]:
        """ディレクトリを作成"""
        try:
            full_path = self._validate_path(dir_path)
            full_path.mkdir(parents=True, exist_ok=True)
            
            return self._get_file_info(full_path)
            
        except Exception as e:
            logger.error(f"Error creating directory {dir_path}: {e}")
            raise
    
    def copy_file(self, source_path: str, dest_path: str) -> Dict[str, Any]:
        """ファイルをコピー"""
        try:
            source_full = self._validate_path(source_path)
            dest_full = self._validate_path(dest_path)
            
            if not source_full.exists():
                raise FileNotFoundError(f"Source file not found: {source_path}")
            
            # 宛先ディレクトリを作成
            dest_full.parent.mkdir(parents=True, exist_ok=True)
            
            if source_full.is_dir():
                shutil.copytree(source_full, dest_full, dirs_exist_ok=True)
            else:
                shutil.copy2(source_full, dest_full)
            
            return self._get_file_info(dest_full)
            
        except Exception as e:
            logger.error(f"Error copying {source_path} to {dest_path}: {e}")
            raise
    
    def move_file(self, source_path: str, dest_path: str) -> Dict[str, Any]:
        """ファイルを移動"""
        try:
            source_full = self._validate_path(source_path)
            dest_full = self._validate_path(dest_path)
            
            if not source_full.exists():
                raise FileNotFoundError(f"Source file not found: {source_path}")
            
            # 宛先ディレクトリを作成
            dest_full.parent.mkdir(parents=True, exist_ok=True)
            
            shutil.move(str(source_full), str(dest_full))
            
            return self._get_file_info(dest_full)
            
        except Exception as e:
            logger.error(f"Error moving {source_path} to {dest_path}: {e}")
            raise
    
    def search_files(self, pattern: str, directory: str = "/", case_sensitive: bool = False) -> List[Dict[str, Any]]:
        """ファイルを検索"""
        try:
            dir_path = self._validate_path(directory)
            
            if not dir_path.exists() or not dir_path.is_dir():
                return []
            
            results = []
            search_pattern = pattern if case_sensitive else pattern.lower()
            
            for item in dir_path.rglob('*'):
                item_name = item.name if case_sensitive else item.name.lower()
                
                if search_pattern in item_name:
                    file_info = self._get_file_info(item)
                    if file_info:
                        results.append(file_info)
            
            return results
            
        except Exception as e:
            logger.error(f"Error searching files with pattern {pattern}: {e}")
            raise
    
    def get_file_content_preview(self, file_path: str, max_lines: int = 50) -> Dict[str, Any]:
        """ファイル内容のプレビューを取得"""
        try:
            full_path = self._validate_path(file_path)
            
            if not full_path.exists() or not full_path.is_file():
                raise FileNotFoundError(f"File not found: {file_path}")
            
            file_info = self._get_file_info(full_path)
            mime_type = file_info.get('mime_type', '')
            
            # テキストファイルの場合のみプレビューを生成
            if mime_type and mime_type.startswith('text/'):
                try:
                    with open(full_path, 'r', encoding='utf-8') as f:
                        lines = []
                        for i, line in enumerate(f):
                            if i >= max_lines:
                                break
                            lines.append(line.rstrip())
                        
                        return {
                            'file_info': file_info,
                            'preview': '\n'.join(lines),
                            'is_truncated': i >= max_lines,
                            'total_lines': i + 1
                        }
                except UnicodeDecodeError:
                    return {
                        'file_info': file_info,
                        'preview': '[Binary file - cannot preview]',
                        'is_truncated': False,
                        'total_lines': 0
                    }
            else:
                return {
                    'file_info': file_info,
                    'preview': f'[{mime_type or "Unknown"} file - cannot preview]',
                    'is_truncated': False,
                    'total_lines': 0
                }
                
        except Exception as e:
            logger.error(f"Error getting file preview for {file_path}: {e}")
            raise

class ProjectManager:
    """プロジェクト管理機能"""
    
    def __init__(self, file_system: FileSystemManager):
        self.file_system = file_system
        self.projects_dir = self.file_system.workspace_root / "projects"
        self.projects_dir.mkdir(exist_ok=True)
    
    def create_project(self, project_name: str, description: str = "", template: str = None) -> Dict[str, Any]:
        """新しいプロジェクトを作成"""
        try:
            # プロジェクト名をサニタイズ
            safe_name = secure_filename(project_name)
            if not safe_name:
                raise ValueError("Invalid project name")
            
            project_id = str(uuid.uuid4())
            project_path = self.projects_dir / safe_name
            
            # プロジェクトディレクトリを作成
            project_path.mkdir(exist_ok=True)
            
            # プロジェクト設定ファイルを作成
            project_config = {
                'id': project_id,
                'name': project_name,
                'description': description,
                'created_at': datetime.now().isoformat(),
                'updated_at': datetime.now().isoformat(),
                'template': template,
                'version': '1.0.0',
                'settings': {
                    'auto_save': True,
                    'backup_enabled': True,
                    'max_file_size': self.file_system.max_file_size
                }
            }
            
            config_path = project_path / ".project.json"
            with open(config_path, 'w', encoding='utf-8') as f:
                json.dump(project_config, f, indent=2)
            
            # テンプレートを適用
            if template:
                self._apply_template(project_path, template)
            
            return project_config
            
        except Exception as e:
            logger.error(f"Error creating project {project_name}: {e}")
            raise
    
    def _apply_template(self, project_path: Path, template: str):
        """プロジェクトテンプレートを適用"""
        templates = {
            'python': {
                'files': {
                    'main.py': '#!/usr/bin/env python3\n\ndef main():\n    print("Hello, World!")\n\nif __name__ == "__main__":\n    main()\n',
                    'requirements.txt': '# Add your dependencies here\n',
                    'README.md': f'# {project_path.name}\n\nProject description goes here.\n',
                    '.gitignore': '__pycache__/\n*.pyc\n*.pyo\n*.pyd\n.Python\nbuild/\ndevelop-eggs/\ndist/\ndownloads/\neggs/\n.eggs/\nlib/\nlib64/\nparts/\nsdist/\nvar/\nwheels/\n*.egg-info/\n.installed.cfg\n*.egg\n'
                },
                'directories': ['src', 'tests', 'docs']
            },
            'javascript': {
                'files': {
                    'index.js': 'console.log("Hello, World!");\n',
                    'package.json': json.dumps({
                        'name': project_path.name.lower(),
                        'version': '1.0.0',
                        'description': '',
                        'main': 'index.js',
                        'scripts': {'start': 'node index.js'},
                        'dependencies': {}
                    }, indent=2),
                    'README.md': f'# {project_path.name}\n\nProject description goes here.\n',
                    '.gitignore': 'node_modules/\nnpm-debug.log*\nyarn-debug.log*\nyarn-error.log*\n.env\n'
                },
                'directories': ['src', 'tests']
            },
            'web': {
                'files': {
                    'index.html': '<!DOCTYPE html>\n<html lang="ja">\n<head>\n    <meta charset="UTF-8">\n    <meta name="viewport" content="width=device-width, initial-scale=1.0">\n    <title>Title</title>\n    <link rel="stylesheet" href="style.css">\n</head>\n<body>\n    <h1>Hello, World!</h1>\n    <script src="script.js"></script>\n</body>\n</html>\n',
                    'style.css': 'body {\n    font-family: Arial, sans-serif;\n    margin: 0;\n    padding: 20px;\n    background-color: #f5f5f5;\n}\n\nh1 {\n    color: #333;\n    text-align: center;\n}\n',
                    'script.js': 'document.addEventListener("DOMContentLoaded", function() {\n    console.log("Page loaded");\n});\n',
                    'README.md': f'# {project_path.name}\n\nWeb project description goes here.\n'
                },
                'directories': ['assets', 'css', 'js', 'images']
            }
        }
        
        if template in templates:
            template_config = templates[template]
            
            # ディレクトリを作成
            for directory in template_config.get('directories', []):
                (project_path / directory).mkdir(exist_ok=True)
            
            # ファイルを作成
            for filename, content in template_config.get('files', {}).items():
                file_path = project_path / filename
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(content)
    
    def list_projects(self) -> List[Dict[str, Any]]:
        """プロジェクト一覧を取得"""
        try:
            projects = []
            
            for project_dir in self.projects_dir.iterdir():
                if project_dir.is_dir():
                    config_path = project_dir / ".project.json"
                    
                    if config_path.exists():
                        try:
                            with open(config_path, 'r', encoding='utf-8') as f:
                                project_config = json.load(f)
                                
                            # プロジェクト統計を追加
                            stats = self._get_project_stats(project_dir)
                            project_config['stats'] = stats
                            
                            projects.append(project_config)
                        except Exception as e:
                            logger.error(f"Error loading project config from {config_path}: {e}")
            
            return sorted(projects, key=lambda x: x.get('updated_at', ''), reverse=True)
            
        except Exception as e:
            logger.error(f"Error listing projects: {e}")
            raise
    
    def get_project(self, project_name: str) -> Optional[Dict[str, Any]]:
        """特定のプロジェクトを取得"""
        try:
            safe_name = secure_filename(project_name)
            project_path = self.projects_dir / safe_name
            config_path = project_path / ".project.json"
            
            if not config_path.exists():
                return None
            
            with open(config_path, 'r', encoding='utf-8') as f:
                project_config = json.load(f)
            
            # プロジェクト統計を追加
            stats = self._get_project_stats(project_path)
            project_config['stats'] = stats
            
            return project_config
            
        except Exception as e:
            logger.error(f"Error getting project {project_name}: {e}")
            raise
    
    def update_project(self, project_name: str, updates: Dict[str, Any]) -> Dict[str, Any]:
        """プロジェクト設定を更新"""
        try:
            safe_name = secure_filename(project_name)
            project_path = self.projects_dir / safe_name
            config_path = project_path / ".project.json"
            
            if not config_path.exists():
                raise FileNotFoundError(f"Project not found: {project_name}")
            
            with open(config_path, 'r', encoding='utf-8') as f:
                project_config = json.load(f)
            
            # 更新可能なフィールドのみを更新
            updatable_fields = ['description', 'settings', 'version']
            for field in updatable_fields:
                if field in updates:
                    project_config[field] = updates[field]
            
            project_config['updated_at'] = datetime.now().isoformat()
            
            with open(config_path, 'w', encoding='utf-8') as f:
                json.dump(project_config, f, indent=2)
            
            return project_config
            
        except Exception as e:
            logger.error(f"Error updating project {project_name}: {e}")
            raise
    
    def delete_project(self, project_name: str) -> bool:
        """プロジェクトを削除"""
        try:
            safe_name = secure_filename(project_name)
            project_path = self.projects_dir / safe_name
            
            if not project_path.exists():
                return False
            
            shutil.rmtree(project_path)
            return True
            
        except Exception as e:
            logger.error(f"Error deleting project {project_name}: {e}")
            raise
    
    def _get_project_stats(self, project_path: Path) -> Dict[str, Any]:
        """プロジェクトの統計情報を取得"""
        try:
            stats = {
                'total_files': 0,
                'total_size': 0,
                'file_types': {},
                'last_modified': None
            }
            
            last_modified = 0
            
            for item in project_path.rglob('*'):
                if item.is_file() and not item.name.startswith('.'):
                    stats['total_files'] += 1
                    
                    file_stat = item.stat()
                    stats['total_size'] += file_stat.st_size
                    
                    if file_stat.st_mtime > last_modified:
                        last_modified = file_stat.st_mtime
                    
                    # ファイル拡張子別の統計
                    ext = item.suffix.lower()
                    if ext:
                        stats['file_types'][ext] = stats['file_types'].get(ext, 0) + 1
            
            if last_modified > 0:
                stats['last_modified'] = datetime.fromtimestamp(last_modified).isoformat()
            
            return stats
            
        except Exception as e:
            logger.error(f"Error getting project stats for {project_path}: {e}")
            return {}
    
    def export_project(self, project_name: str) -> str:
        """プロジェクトをZIPファイルとしてエクスポート"""
        try:
            safe_name = secure_filename(project_name)
            project_path = self.projects_dir / safe_name
            
            if not project_path.exists():
                raise FileNotFoundError(f"Project not found: {project_name}")
            
            # 一時ファイルを作成
            temp_dir = tempfile.mkdtemp()
            zip_path = Path(temp_dir) / f"{safe_name}.zip"
            
            with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                for item in project_path.rglob('*'):
                    if item.is_file():
                        arcname = item.relative_to(project_path)
                        zipf.write(item, arcname)
            
            return str(zip_path)
            
        except Exception as e:
            logger.error(f"Error exporting project {project_name}: {e}")
            raise
    
    def import_project(self, zip_path: str, project_name: str = None) -> Dict[str, Any]:
        """ZIPファイルからプロジェクトをインポート"""
        try:
            zip_file_path = Path(zip_path)
            
            if not zip_file_path.exists():
                raise FileNotFoundError(f"ZIP file not found: {zip_path}")
            
            # プロジェクト名を決定
            if not project_name:
                project_name = zip_file_path.stem
            
            safe_name = secure_filename(project_name)
            project_path = self.projects_dir / safe_name
            
            # プロジェクトディレクトリを作成
            project_path.mkdir(exist_ok=True)
            
            # ZIPファイルを展開
            with zipfile.ZipFile(zip_file_path, 'r') as zipf:
                zipf.extractall(project_path)
            
            # プロジェクト設定ファイルが存在しない場合は作成
            config_path = project_path / ".project.json"
            if not config_path.exists():
                project_config = {
                    'id': str(uuid.uuid4()),
                    'name': project_name,
                    'description': f'Imported from {zip_file_path.name}',
                    'created_at': datetime.now().isoformat(),
                    'updated_at': datetime.now().isoformat(),
                    'template': None,
                    'version': '1.0.0',
                    'settings': {
                        'auto_save': True,
                        'backup_enabled': True,
                        'max_file_size': self.file_system.max_file_size
                    }
                }
                
                with open(config_path, 'w', encoding='utf-8') as f:
                    json.dump(project_config, f, indent=2)
            else:
                with open(config_path, 'r', encoding='utf-8') as f:
                    project_config = json.load(f)
            
            return project_config
            
        except Exception as e:
            logger.error(f"Error importing project from {zip_path}: {e}")
            raise

