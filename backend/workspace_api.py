"""
ワークスペース管理API

このモジュールは、ファイルシステムとプロジェクト管理のAPIエンドポイントを提供します。
"""

from flask import Blueprint, request, jsonify, send_file, current_app
from werkzeug.utils import secure_filename
import os
import tempfile
import logging
from typing import Dict, Any

from file_system_manager import FileSystemManager, ProjectManager
from auth import require_auth

logger = logging.getLogger(__name__)

# Blueprintを作成
workspace_bp = Blueprint('workspace', __name__, url_prefix='/api/workspace')

# ファイルシステムマネージャーを初期化
file_system = None
project_manager = None

def init_workspace_manager(app):
    """ワークスペースマネージャーを初期化"""
    global file_system, project_manager
    
    workspace_root = app.config.get('WORKSPACE_ROOT', '/tmp/autoai_workspace')
    file_system = FileSystemManager(workspace_root)
    project_manager = ProjectManager(file_system)

@workspace_bp.route('/files', methods=['GET'])
@require_auth
def list_files():
    """ファイル一覧を取得"""
    try:
        directory = request.args.get('directory', '/')
        recursive = request.args.get('recursive', 'false').lower() == 'true'
        
        files = file_system.list_files(directory, recursive)
        
        return jsonify({
            'success': True,
            'files': files,
            'directory': directory,
            'total': len(files)
        })
        
    except Exception as e:
        logger.error(f"Error listing files: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@workspace_bp.route('/file/<path:file_path>', methods=['GET'])
@require_auth
def get_file(file_path):
    """ファイル内容を取得"""
    try:
        preview = request.args.get('preview', 'false').lower() == 'true'
        
        if preview:
            max_lines = int(request.args.get('max_lines', 50))
            result = file_system.get_file_content_preview(file_path, max_lines)
            return jsonify({
                'success': True,
                'result': result
            })
        else:
            content = file_system.read_file(file_path)
            return jsonify({
                'success': True,
                'content': content,
                'file_path': file_path
            })
            
    except FileNotFoundError:
        return jsonify({
            'success': False,
            'error': 'File not found'
        }), 404
    except Exception as e:
        logger.error(f"Error getting file {file_path}: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@workspace_bp.route('/file', methods=['POST'])
@require_auth
def create_file():
    """新しいファイルを作成"""
    try:
        data = request.get_json()
        file_path = data.get('path')
        content = data.get('content', '')
        
        if not file_path:
            return jsonify({
                'success': False,
                'error': 'File path is required'
            }), 400
        
        file_info = file_system.write_file(file_path, content)
        
        return jsonify({
            'success': True,
            'file_info': file_info
        })
        
    except Exception as e:
        logger.error(f"Error creating file: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@workspace_bp.route('/file/<path:file_path>', methods=['PUT'])
@require_auth
def update_file(file_path):
    """ファイル内容を更新"""
    try:
        data = request.get_json()
        content = data.get('content', '')
        append = data.get('append', False)
        
        if append:
            file_info = file_system.append_file(file_path, content)
        else:
            file_info = file_system.write_file(file_path, content)
        
        return jsonify({
            'success': True,
            'file_info': file_info
        })
        
    except Exception as e:
        logger.error(f"Error updating file {file_path}: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@workspace_bp.route('/file/<path:file_path>', methods=['DELETE'])
@require_auth
def delete_file(file_path):
    """ファイルを削除"""
    try:
        success = file_system.delete_file(file_path)
        
        return jsonify({
            'success': success,
            'file_path': file_path
        })
        
    except Exception as e:
        logger.error(f"Error deleting file {file_path}: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@workspace_bp.route('/folder', methods=['POST'])
@require_auth
def create_folder():
    """新しいフォルダを作成"""
    try:
        data = request.get_json()
        folder_path = data.get('path')
        
        if not folder_path:
            return jsonify({
                'success': False,
                'error': 'Folder path is required'
            }), 400
        
        folder_info = file_system.create_directory(folder_path)
        
        return jsonify({
            'success': True,
            'folder_info': folder_info
        })
        
    except Exception as e:
        logger.error(f"Error creating folder: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@workspace_bp.route('/copy', methods=['POST'])
@require_auth
def copy_file():
    """ファイルをコピー"""
    try:
        data = request.get_json()
        source_path = data.get('source_path')
        dest_path = data.get('dest_path')
        
        if not source_path or not dest_path:
            return jsonify({
                'success': False,
                'error': 'Source and destination paths are required'
            }), 400
        
        file_info = file_system.copy_file(source_path, dest_path)
        
        return jsonify({
            'success': True,
            'file_info': file_info
        })
        
    except Exception as e:
        logger.error(f"Error copying file: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@workspace_bp.route('/move', methods=['POST'])
@require_auth
def move_file():
    """ファイルを移動"""
    try:
        data = request.get_json()
        source_path = data.get('source_path')
        dest_path = data.get('dest_path')
        
        if not source_path or not dest_path:
            return jsonify({
                'success': False,
                'error': 'Source and destination paths are required'
            }), 400
        
        file_info = file_system.move_file(source_path, dest_path)
        
        return jsonify({
            'success': True,
            'file_info': file_info
        })
        
    except Exception as e:
        logger.error(f"Error moving file: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@workspace_bp.route('/search', methods=['GET'])
@require_auth
def search_files():
    """ファイルを検索"""
    try:
        pattern = request.args.get('pattern', '')
        directory = request.args.get('directory', '/')
        case_sensitive = request.args.get('case_sensitive', 'false').lower() == 'true'
        
        if not pattern:
            return jsonify({
                'success': False,
                'error': 'Search pattern is required'
            }), 400
        
        results = file_system.search_files(pattern, directory, case_sensitive)
        
        return jsonify({
            'success': True,
            'results': results,
            'pattern': pattern,
            'total': len(results)
        })
        
    except Exception as e:
        logger.error(f"Error searching files: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@workspace_bp.route('/upload', methods=['POST'])
@require_auth
def upload_file():
    """ファイルをアップロード"""
    try:
        if 'file' not in request.files:
            return jsonify({
                'success': False,
                'error': 'No file provided'
            }), 400
        
        file = request.files['file']
        if file.filename == '':
            return jsonify({
                'success': False,
                'error': 'No file selected'
            }), 400
        
        # ファイル名をセキュアにする
        filename = secure_filename(file.filename)
        target_path = request.form.get('path', filename)
        
        # ファイル内容を読み取り
        content = file.read().decode('utf-8')
        
        # ファイルを保存
        file_info = file_system.write_file(target_path, content)
        
        return jsonify({
            'success': True,
            'file_info': file_info
        })
        
    except Exception as e:
        logger.error(f"Error uploading file: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@workspace_bp.route('/download/<path:file_path>', methods=['GET'])
@require_auth
def download_file(file_path):
    """ファイルをダウンロード"""
    try:
        # ファイルパスを検証
        full_path = file_system._validate_path(file_path)
        
        if not full_path.exists() or not full_path.is_file():
            return jsonify({
                'success': False,
                'error': 'File not found'
            }), 404
        
        return send_file(
            str(full_path),
            as_attachment=True,
            download_name=full_path.name
        )
        
    except Exception as e:
        logger.error(f"Error downloading file {file_path}: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

# プロジェクト管理API

@workspace_bp.route('/projects', methods=['GET'])
@require_auth
def list_projects():
    """プロジェクト一覧を取得"""
    try:
        projects = project_manager.list_projects()
        
        return jsonify({
            'success': True,
            'projects': projects,
            'total': len(projects)
        })
        
    except Exception as e:
        logger.error(f"Error listing projects: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@workspace_bp.route('/projects', methods=['POST'])
@require_auth
def create_project():
    """新しいプロジェクトを作成"""
    try:
        data = request.get_json()
        project_name = data.get('name')
        description = data.get('description', '')
        template = data.get('template')
        
        if not project_name:
            return jsonify({
                'success': False,
                'error': 'Project name is required'
            }), 400
        
        project_config = project_manager.create_project(project_name, description, template)
        
        return jsonify({
            'success': True,
            'project': project_config
        })
        
    except Exception as e:
        logger.error(f"Error creating project: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@workspace_bp.route('/projects/<project_name>', methods=['GET'])
@require_auth
def get_project(project_name):
    """特定のプロジェクトを取得"""
    try:
        project = project_manager.get_project(project_name)
        
        if not project:
            return jsonify({
                'success': False,
                'error': 'Project not found'
            }), 404
        
        return jsonify({
            'success': True,
            'project': project
        })
        
    except Exception as e:
        logger.error(f"Error getting project {project_name}: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@workspace_bp.route('/projects/<project_name>', methods=['PUT'])
@require_auth
def update_project(project_name):
    """プロジェクトを更新"""
    try:
        data = request.get_json()
        
        project_config = project_manager.update_project(project_name, data)
        
        return jsonify({
            'success': True,
            'project': project_config
        })
        
    except FileNotFoundError:
        return jsonify({
            'success': False,
            'error': 'Project not found'
        }), 404
    except Exception as e:
        logger.error(f"Error updating project {project_name}: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@workspace_bp.route('/projects/<project_name>', methods=['DELETE'])
@require_auth
def delete_project(project_name):
    """プロジェクトを削除"""
    try:
        success = project_manager.delete_project(project_name)
        
        return jsonify({
            'success': success,
            'project_name': project_name
        })
        
    except Exception as e:
        logger.error(f"Error deleting project {project_name}: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@workspace_bp.route('/projects/<project_name>/export', methods=['GET'])
@require_auth
def export_project(project_name):
    """プロジェクトをエクスポート"""
    try:
        zip_path = project_manager.export_project(project_name)
        
        return send_file(
            zip_path,
            as_attachment=True,
            download_name=f"{project_name}.zip"
        )
        
    except FileNotFoundError:
        return jsonify({
            'success': False,
            'error': 'Project not found'
        }), 404
    except Exception as e:
        logger.error(f"Error exporting project {project_name}: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@workspace_bp.route('/projects/import', methods=['POST'])
@require_auth
def import_project():
    """プロジェクトをインポート"""
    try:
        if 'file' not in request.files:
            return jsonify({
                'success': False,
                'error': 'No file provided'
            }), 400
        
        file = request.files['file']
        if file.filename == '':
            return jsonify({
                'success': False,
                'error': 'No file selected'
            }), 400
        
        project_name = request.form.get('project_name')
        
        # 一時ファイルに保存
        with tempfile.NamedTemporaryFile(delete=False, suffix='.zip') as temp_file:
            file.save(temp_file.name)
            
            # プロジェクトをインポート
            project_config = project_manager.import_project(temp_file.name, project_name)
            
            # 一時ファイルを削除
            os.unlink(temp_file.name)
        
        return jsonify({
            'success': True,
            'project': project_config
        })
        
    except Exception as e:
        logger.error(f"Error importing project: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

