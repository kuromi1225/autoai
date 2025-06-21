"""
VSCode統合システム

オープンソース版VSCode（Code-OSS）をWebベースで統合
AI支援機能、学習システム、拡張機能管理を提供
"""

import os
import json
import logging
import asyncio
import subprocess
import tempfile
import shutil
from typing import Dict, List, Optional, Any
from pathlib import Path
import aiofiles
import aiohttp
from datetime import datetime
import zipfile
import tarfile

logger = logging.getLogger(__name__)

class VSCodeIntegration:
    """VSCode統合システム"""
    
    def __init__(self, workspace_root: str = "/tmp/autoai_workspace"):
        self.workspace_root = Path(workspace_root)
        self.vscode_path = None
        self.server_process = None
        self.server_port = 8080
        self.is_running = False
        
        # 学習データ
        self.edit_history = []
        self.code_patterns = {}
        self.user_preferences = {}
        
        # 拡張機能
        self.extensions = {}
        self.ai_features = {}
        
        # 設定
        self.config = {
            "auto_save": True,
            "ai_assistance": True,
            "learning_enabled": True,
            "theme": "dark",
            "font_size": 14,
            "tab_size": 4
        }
    
    async def setup_vscode(self) -> bool:
        """VSCode（Code-OSS）をセットアップ"""
        try:
            logger.info("Setting up VSCode (Code-OSS)")
            
            # Code-OSS ダウンロード・インストール
            success = await self._download_code_oss()
            if not success:
                return False
            
            # 設定ファイル作成
            await self._create_config_files()
            
            # 拡張機能インストール
            await self._install_extensions()
            
            # AI機能セットアップ
            await self._setup_ai_features()
            
            logger.info("VSCode setup completed successfully")
            return True
            
        except Exception as e:
            logger.error(f"Error setting up VSCode: {e}")
            return False
    
    async def _download_code_oss(self) -> bool:
        """Code-OSSをダウンロード"""
        try:
            # Code-OSS Web版のダウンロードURL
            # 実際の実装では、最新版のURLを動的に取得
            code_server_url = "https://github.com/coder/code-server/releases/latest/download/code-server-linux-amd64.tar.gz"
            
            download_path = "/tmp/code-server.tar.gz"
            install_path = "/opt/code-server"
            
            logger.info("Downloading Code-OSS...")
            
            async with aiohttp.ClientSession() as session:
                async with session.get(code_server_url) as response:
                    if response.status == 200:
                        with open(download_path, 'wb') as f:
                            async for chunk in response.content.iter_chunked(8192):
                                f.write(chunk)
                    else:
                        logger.error(f"Failed to download Code-OSS: {response.status}")
                        return False
            
            # 展開
            logger.info("Extracting Code-OSS...")
            with tarfile.open(download_path, 'r:gz') as tar:
                tar.extractall('/tmp/')
            
            # インストール
            extracted_dir = None
            for item in os.listdir('/tmp/'):
                if item.startswith('code-server-') and os.path.isdir(f'/tmp/{item}'):
                    extracted_dir = f'/tmp/{item}'
                    break
            
            if extracted_dir:
                if os.path.exists(install_path):
                    shutil.rmtree(install_path)
                shutil.move(extracted_dir, install_path)
                
                # 実行権限付与
                os.chmod(f"{install_path}/bin/code-server", 0o755)
                
                self.vscode_path = f"{install_path}/bin/code-server"
                logger.info(f"Code-OSS installed at: {self.vscode_path}")
                return True
            else:
                logger.error("Failed to find extracted Code-OSS directory")
                return False
                
        except Exception as e:
            logger.error(f"Error downloading Code-OSS: {e}")
            return False
    
    async def _create_config_files(self):
        """設定ファイルを作成"""
        config_dir = self.workspace_root / ".vscode"
        config_dir.mkdir(exist_ok=True)
        
        # settings.json
        settings = {
            "workbench.colorTheme": "Default Dark+",
            "editor.fontSize": self.config["font_size"],
            "editor.tabSize": self.config["tab_size"],
            "files.autoSave": "afterDelay" if self.config["auto_save"] else "off",
            "editor.formatOnSave": True,
            "editor.codeActionsOnSave": {
                "source.organizeImports": True
            },
            "python.defaultInterpreterPath": "/usr/bin/python3",
            "python.linting.enabled": True,
            "python.linting.pylintEnabled": True,
            "javascript.suggest.autoImports": True,
            "typescript.suggest.autoImports": True,
            "git.enableSmartCommit": True,
            "git.autofetch": True,
            "autoai.enabled": True,
            "autoai.suggestions": True,
            "autoai.learning": self.config["learning_enabled"]
        }
        
        settings_path = config_dir / "settings.json"
        async with aiofiles.open(settings_path, 'w') as f:
            await f.write(json.dumps(settings, indent=2))
        
        # keybindings.json
        keybindings = [
            {
                "key": "ctrl+shift+a",
                "command": "autoai.askAssistant"
            },
            {
                "key": "ctrl+shift+g",
                "command": "autoai.generateCode"
            },
            {
                "key": "ctrl+shift+r",
                "command": "autoai.refactorCode"
            },
            {
                "key": "ctrl+shift+t",
                "command": "autoai.generateTests"
            }
        ]
        
        keybindings_path = config_dir / "keybindings.json"
        async with aiofiles.open(keybindings_path, 'w') as f:
            await f.write(json.dumps(keybindings, indent=2))
        
        # tasks.json
        tasks = {
            "version": "2.0.0",
            "tasks": [
                {
                    "label": "AutoAI: Analyze Code",
                    "type": "shell",
                    "command": "python",
                    "args": ["-m", "autoai.analyze", "${file}"],
                    "group": "build",
                    "presentation": {
                        "echo": True,
                        "reveal": "always",
                        "focus": False,
                        "panel": "shared"
                    }
                },
                {
                    "label": "AutoAI: Generate Tests",
                    "type": "shell",
                    "command": "python",
                    "args": ["-m", "autoai.test_generator", "${file}"],
                    "group": "test"
                }
            ]
        }
        
        tasks_path = config_dir / "tasks.json"
        async with aiofiles.open(tasks_path, 'w') as f:
            await f.write(json.dumps(tasks, indent=2))
    
    async def _install_extensions(self):
        """拡張機能をインストール"""
        if not self.vscode_path:
            return
        
        # 基本拡張機能リスト
        extensions = [
            "ms-python.python",
            "ms-vscode.vscode-typescript-next",
            "bradlc.vscode-tailwindcss",
            "esbenp.prettier-vscode",
            "ms-vscode.vscode-json",
            "redhat.vscode-yaml",
            "ms-vscode.vscode-eslint",
            "ms-vscode.vscode-css",
            "ms-vscode.vscode-html",
            "formulahendry.auto-rename-tag",
            "christian-kohler.path-intellisense",
            "ms-vscode.vscode-git",
            "eamodio.gitlens"
        ]
        
        for extension in extensions:
            try:
                cmd = [self.vscode_path, "--install-extension", extension]
                process = await asyncio.create_subprocess_exec(
                    *cmd,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE
                )
                stdout, stderr = await process.communicate()
                
                if process.returncode == 0:
                    logger.info(f"Installed extension: {extension}")
                    self.extensions[extension] = {
                        "installed": True,
                        "version": "latest"
                    }
                else:
                    logger.warning(f"Failed to install extension {extension}: {stderr.decode()}")
                    
            except Exception as e:
                logger.error(f"Error installing extension {extension}: {e}")
    
    async def _setup_ai_features(self):
        """AI機能をセットアップ"""
        # AI支援機能の設定
        self.ai_features = {
            "code_completion": {
                "enabled": True,
                "model": "qwq-32b",
                "confidence_threshold": 0.7
            },
            "code_generation": {
                "enabled": True,
                "templates": True,
                "documentation": True
            },
            "code_review": {
                "enabled": True,
                "auto_review": False,
                "suggestions": True
            },
            "refactoring": {
                "enabled": True,
                "auto_refactor": False,
                "patterns": True
            },
            "testing": {
                "enabled": True,
                "auto_generate": False,
                "coverage_analysis": True
            }
        }
        
        # AI機能用のカスタム拡張機能を作成
        await self._create_ai_extension()
    
    async def _create_ai_extension(self):
        """AI機能用のカスタム拡張機能を作成"""
        extension_dir = self.workspace_root / ".vscode" / "extensions" / "autoai"
        extension_dir.mkdir(parents=True, exist_ok=True)
        
        # package.json
        package_json = {
            "name": "autoai-assistant",
            "displayName": "AutoAI Assistant",
            "description": "AI-powered coding assistant for AutoAI",
            "version": "1.0.0",
            "engines": {
                "vscode": "^1.60.0"
            },
            "categories": ["Other"],
            "activationEvents": ["*"],
            "main": "./extension.js",
            "contributes": {
                "commands": [
                    {
                        "command": "autoai.askAssistant",
                        "title": "Ask AI Assistant"
                    },
                    {
                        "command": "autoai.generateCode",
                        "title": "Generate Code"
                    },
                    {
                        "command": "autoai.refactorCode",
                        "title": "Refactor Code"
                    },
                    {
                        "command": "autoai.generateTests",
                        "title": "Generate Tests"
                    }
                ],
                "menus": {
                    "editor/context": [
                        {
                            "command": "autoai.askAssistant",
                            "group": "autoai"
                        },
                        {
                            "command": "autoai.generateCode",
                            "group": "autoai"
                        },
                        {
                            "command": "autoai.refactorCode",
                            "group": "autoai"
                        }
                    ]
                }
            }
        }
        
        package_path = extension_dir / "package.json"
        async with aiofiles.open(package_path, 'w') as f:
            await f.write(json.dumps(package_json, indent=2))
        
        # extension.js
        extension_js = '''
const vscode = require('vscode');

function activate(context) {
    console.log('AutoAI Assistant extension is now active!');
    
    // AI Assistant command
    let askAssistant = vscode.commands.registerCommand('autoai.askAssistant', async () => {
        const editor = vscode.window.activeTextEditor;
        if (!editor) return;
        
        const selection = editor.selection;
        const selectedText = editor.document.getText(selection);
        
        const question = await vscode.window.showInputBox({
            prompt: 'Ask AI Assistant about your code',
            placeHolder: 'What would you like to know?'
        });
        
        if (question) {
            // Send request to AutoAI backend
            const response = await callAutoAI('ask_assistant', {
                code: selectedText,
                question: question,
                language: editor.document.languageId
            });
            
            vscode.window.showInformationMessage(response);
        }
    });
    
    // Code generation command
    let generateCode = vscode.commands.registerCommand('autoai.generateCode', async () => {
        const editor = vscode.window.activeTextEditor;
        if (!editor) return;
        
        const prompt = await vscode.window.showInputBox({
            prompt: 'Describe the code you want to generate',
            placeHolder: 'e.g., Create a function that sorts an array'
        });
        
        if (prompt) {
            const response = await callAutoAI('generate_code', {
                prompt: prompt,
                language: editor.document.languageId,
                context: editor.document.getText()
            });
            
            const position = editor.selection.active;
            editor.edit(editBuilder => {
                editBuilder.insert(position, response);
            });
        }
    });
    
    // Refactor code command
    let refactorCode = vscode.commands.registerCommand('autoai.refactorCode', async () => {
        const editor = vscode.window.activeTextEditor;
        if (!editor) return;
        
        const selection = editor.selection;
        const selectedText = editor.document.getText(selection);
        
        if (!selectedText) {
            vscode.window.showWarningMessage('Please select code to refactor');
            return;
        }
        
        const response = await callAutoAI('refactor_code', {
            code: selectedText,
            language: editor.document.languageId
        });
        
        editor.edit(editBuilder => {
            editBuilder.replace(selection, response);
        });
    });
    
    // Generate tests command
    let generateTests = vscode.commands.registerCommand('autoai.generateTests', async () => {
        const editor = vscode.window.activeTextEditor;
        if (!editor) return;
        
        const response = await callAutoAI('generate_tests', {
            code: editor.document.getText(),
            language: editor.document.languageId,
            filename: editor.document.fileName
        });
        
        // Create new test file
        const testFileName = editor.document.fileName.replace(/\\.(\\w+)$/, '.test.$1');
        const testUri = vscode.Uri.file(testFileName);
        
        vscode.workspace.fs.writeFile(testUri, Buffer.from(response, 'utf8'));
        vscode.window.showTextDocument(testUri);
    });
    
    context.subscriptions.push(askAssistant, generateCode, refactorCode, generateTests);
}

async function callAutoAI(endpoint, data) {
    try {
        const response = await fetch(`http://localhost:5000/api/vscode/${endpoint}`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify(data)
        });
        
        const result = await response.json();
        return result.response || 'No response from AI';
    } catch (error) {
        console.error('Error calling AutoAI:', error);
        return 'Error communicating with AI assistant';
    }
}

function deactivate() {}

module.exports = {
    activate,
    deactivate
};
'''
        
        extension_js_path = extension_dir / "extension.js"
        async with aiofiles.open(extension_js_path, 'w') as f:
            await f.write(extension_js)
    
    async def start_server(self, port: int = 8080) -> bool:
        """VSCodeサーバーを開始"""
        if not self.vscode_path:
            logger.error("VSCode not installed")
            return False
        
        try:
            self.server_port = port
            
            cmd = [
                self.vscode_path,
                "--bind-addr", f"0.0.0.0:{port}",
                "--auth", "none",
                "--disable-telemetry",
                str(self.workspace_root)
            ]
            
            logger.info(f"Starting VSCode server on port {port}")
            
            self.server_process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            # サーバー起動確認
            await asyncio.sleep(3)
            
            if self.server_process.returncode is None:
                self.is_running = True
                logger.info(f"VSCode server started successfully on http://localhost:{port}")
                return True
            else:
                logger.error("VSCode server failed to start")
                return False
                
        except Exception as e:
            logger.error(f"Error starting VSCode server: {e}")
            return False
    
    async def stop_server(self):
        """VSCodeサーバーを停止"""
        if self.server_process:
            try:
                self.server_process.terminate()
                await self.server_process.wait()
                self.is_running = False
                logger.info("VSCode server stopped")
            except Exception as e:
                logger.error(f"Error stopping VSCode server: {e}")
    
    async def record_edit(self, file_path: str, edit_data: Dict[str, Any]):
        """編集履歴を記録"""
        if not self.config["learning_enabled"]:
            return
        
        edit_record = {
            "timestamp": datetime.now().isoformat(),
            "file_path": file_path,
            "edit_data": edit_data,
            "language": edit_data.get("language"),
            "edit_type": edit_data.get("type"),  # insert, delete, replace
            "content": edit_data.get("content"),
            "position": edit_data.get("position")
        }
        
        self.edit_history.append(edit_record)
        
        # 最新1000件のみ保持
        if len(self.edit_history) > 1000:
            self.edit_history = self.edit_history[-1000:]
        
        # パターン学習
        await self._learn_patterns(edit_record)
    
    async def _learn_patterns(self, edit_record: Dict[str, Any]):
        """編集パターンを学習"""
        language = edit_record.get("language")
        edit_type = edit_record.get("edit_type")
        content = edit_record.get("content", "")
        
        if not language or not edit_type:
            return
        
        # 言語別パターン
        if language not in self.code_patterns:
            self.code_patterns[language] = {
                "common_patterns": {},
                "frequent_edits": {},
                "style_preferences": {}
            }
        
        patterns = self.code_patterns[language]
        
        # 頻繁な編集パターンを記録
        if edit_type not in patterns["frequent_edits"]:
            patterns["frequent_edits"][edit_type] = []
        
        patterns["frequent_edits"][edit_type].append({
            "content": content[:100],  # 最初の100文字のみ
            "timestamp": edit_record["timestamp"]
        })
        
        # 最新100件のみ保持
        if len(patterns["frequent_edits"][edit_type]) > 100:
            patterns["frequent_edits"][edit_type] = patterns["frequent_edits"][edit_type][-100:]
    
    def get_ai_suggestions(self, context: Dict[str, Any]) -> List[Dict[str, Any]]:
        """AI提案を取得"""
        suggestions = []
        
        language = context.get("language")
        current_code = context.get("code", "")
        cursor_position = context.get("position")
        
        # 学習したパターンに基づく提案
        if language in self.code_patterns:
            patterns = self.code_patterns[language]
            
            # 頻繁な編集パターンに基づく提案
            for edit_type, edits in patterns["frequent_edits"].items():
                if len(edits) > 5:  # 十分なデータがある場合
                    suggestions.append({
                        "type": "pattern_suggestion",
                        "description": f"Common {edit_type} pattern in {language}",
                        "confidence": min(len(edits) / 20.0, 1.0),
                        "suggestion": f"Based on your editing history, consider {edit_type}"
                    })
        
        return suggestions
    
    def get_status(self) -> Dict[str, Any]:
        """VSCode統合の状態を取得"""
        return {
            "vscode_installed": self.vscode_path is not None,
            "server_running": self.is_running,
            "server_port": self.server_port if self.is_running else None,
            "workspace_root": str(self.workspace_root),
            "extensions_count": len(self.extensions),
            "ai_features_enabled": self.config["ai_assistance"],
            "learning_enabled": self.config["learning_enabled"],
            "edit_history_count": len(self.edit_history),
            "learned_patterns": len(self.code_patterns)
        }
    
    async def update_config(self, new_config: Dict[str, Any]):
        """設定を更新"""
        self.config.update(new_config)
        
        # 設定ファイルを再作成
        await self._create_config_files()
        
        logger.info("VSCode configuration updated")


# グローバルVSCode統合インスタンス
_vscode_integration = None

def get_vscode_integration() -> VSCodeIntegration:
    """VSCode統合のシングルトンインスタンス取得"""
    global _vscode_integration
    if _vscode_integration is None:
        _vscode_integration = VSCodeIntegration()
    return _vscode_integration

async def initialize_vscode_integration(workspace_root: str = "/tmp/autoai_workspace") -> bool:
    """VSCode統合を初期化"""
    global _vscode_integration
    _vscode_integration = VSCodeIntegration(workspace_root)
    
    success = await _vscode_integration.setup_vscode()
    if success:
        await _vscode_integration.start_server()
    
    return success

