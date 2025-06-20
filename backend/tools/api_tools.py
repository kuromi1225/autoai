"""
API連携ツール

このモジュールは、外部APIとの連携機能を提供します。
"""

import asyncio
import aiohttp
import logging
from typing import Dict, List, Any, Optional
import json
import os

from tools.enhanced_tool_manager import BaseTool

logger = logging.getLogger(__name__)

class APIConnectorTool(BaseTool):
    """API連携ツール"""
    
    def __init__(self):
        super().__init__(
            name="api_connector",
            description="外部APIとの連携を行う",
            category="api"
        )
        self.session = None
    
    async def execute(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """API操作を実行する"""
        action = parameters.get('action')
        
        try:
            if action == 'request':
                method = parameters.get('method', 'GET')
                url = parameters.get('url')
                headers = parameters.get('headers', {})
                data = parameters.get('data')
                return await self._make_request(method, url, headers, data)
            elif action == 'openai_chat':
                messages = parameters.get('messages', [])
                model = parameters.get('model', 'gpt-3.5-turbo')
                return await self._openai_chat(messages, model)
            elif action == 'github_api':
                endpoint = parameters.get('endpoint')
                method = parameters.get('method', 'GET')
                data = parameters.get('data')
                return await self._github_api(endpoint, method, data)
            else:
                return {'success': False, 'error': f'Unknown action: {action}'}
                
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    async def _get_session(self):
        """HTTPセッションを取得"""
        if self.session is None:
            self.session = aiohttp.ClientSession()
        return self.session
    
    async def _make_request(self, method: str, url: str, headers: Dict[str, str], data: Any) -> Dict[str, Any]:
        """HTTP リクエストを実行"""
        session = await self._get_session()
        
        try:
            async with session.request(
                method=method,
                url=url,
                headers=headers,
                json=data if isinstance(data, dict) else None,
                data=data if not isinstance(data, dict) else None
            ) as response:
                
                response_text = await response.text()
                
                try:
                    response_json = await response.json()
                except:
                    response_json = None
                
                return {
                    'success': response.status < 400,
                    'status_code': response.status,
                    'headers': dict(response.headers),
                    'text': response_text,
                    'json': response_json,
                    'url': str(response.url)
                }
                
        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'url': url,
                'method': method
            }
    
    async def _openai_chat(self, messages: List[Dict[str, str]], model: str) -> Dict[str, Any]:
        """OpenAI Chat APIを呼び出す"""
        api_key = os.environ.get('OPENAI_API_KEY')
        if not api_key:
            return {'success': False, 'error': 'OpenAI API key not found'}
        
        headers = {
            'Authorization': f'Bearer {api_key}',
            'Content-Type': 'application/json'
        }
        
        data = {
            'model': model,
            'messages': messages,
            'max_tokens': 1000,
            'temperature': 0.7
        }
        
        return await self._make_request(
            'POST',
            'https://api.openai.com/v1/chat/completions',
            headers,
            data
        )
    
    async def _github_api(self, endpoint: str, method: str, data: Any) -> Dict[str, Any]:
        """GitHub APIを呼び出す"""
        token = os.environ.get('GITHUB_TOKEN')
        if not token:
            return {'success': False, 'error': 'GitHub token not found'}
        
        headers = {
            'Authorization': f'token {token}',
            'Accept': 'application/vnd.github.v3+json'
        }
        
        url = f'https://api.github.com/{endpoint.lstrip("/")}'
        
        return await self._make_request(method, url, headers, data)
    
    def get_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "action": {
                    "type": "string",
                    "enum": ["request", "openai_chat", "github_api"],
                    "description": "実行するアクション"
                },
                "method": {
                    "type": "string",
                    "enum": ["GET", "POST", "PUT", "DELETE", "PATCH"],
                    "description": "HTTPメソッド"
                },
                "url": {
                    "type": "string",
                    "description": "リクエストURL"
                },
                "headers": {
                    "type": "object",
                    "description": "リクエストヘッダー"
                },
                "data": {
                    "description": "リクエストデータ"
                },
                "messages": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "role": {"type": "string"},
                            "content": {"type": "string"}
                        }
                    },
                    "description": "チャットメッセージ（OpenAI用）"
                },
                "model": {
                    "type": "string",
                    "description": "使用するモデル（OpenAI用）"
                },
                "endpoint": {
                    "type": "string",
                    "description": "APIエンドポイント（GitHub用）"
                }
            },
            "required": ["action"]
        }

class WebScrapingTool(BaseTool):
    """Webスクレイピングツール"""
    
    def __init__(self):
        super().__init__(
            name="web_scraping",
            description="Webページからデータを抽出する",
            category="web"
        )
    
    async def execute(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Webスクレイピングを実行する"""
        action = parameters.get('action')
        
        try:
            if action == 'scrape_text':
                url = parameters.get('url')
                selector = parameters.get('selector')
                return await self._scrape_text(url, selector)
            elif action == 'scrape_links':
                url = parameters.get('url')
                return await self._scrape_links(url)
            elif action == 'scrape_images':
                url = parameters.get('url')
                return await self._scrape_images(url)
            elif action == 'scrape_table':
                url = parameters.get('url')
                table_selector = parameters.get('table_selector', 'table')
                return await self._scrape_table(url, table_selector)
            else:
                return {'success': False, 'error': f'Unknown action: {action}'}
                
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    async def _scrape_text(self, url: str, selector: str = None) -> Dict[str, Any]:
        """テキストを抽出する"""
        from bs4 import BeautifulSoup
        import aiohttp
        
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                if response.status != 200:
                    return {'success': False, 'error': f'HTTP {response.status}'}
                
                html = await response.text()
                soup = BeautifulSoup(html, 'html.parser')
                
                if selector:
                    elements = soup.select(selector)
                    texts = [elem.get_text(strip=True) for elem in elements]
                else:
                    texts = [soup.get_text(strip=True)]
                
                return {
                    'success': True,
                    'url': url,
                    'selector': selector,
                    'texts': texts,
                    'count': len(texts)
                }
    
    async def _scrape_links(self, url: str) -> Dict[str, Any]:
        """リンクを抽出する"""
        from bs4 import BeautifulSoup
        import aiohttp
        from urllib.parse import urljoin
        
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                if response.status != 200:
                    return {'success': False, 'error': f'HTTP {response.status}'}
                
                html = await response.text()
                soup = BeautifulSoup(html, 'html.parser')
                
                links = []
                for link in soup.find_all('a', href=True):
                    href = link['href']
                    absolute_url = urljoin(url, href)
                    links.append({
                        'text': link.get_text(strip=True),
                        'href': href,
                        'absolute_url': absolute_url
                    })
                
                return {
                    'success': True,
                    'url': url,
                    'links': links,
                    'count': len(links)
                }
    
    async def _scrape_images(self, url: str) -> Dict[str, Any]:
        """画像を抽出する"""
        from bs4 import BeautifulSoup
        import aiohttp
        from urllib.parse import urljoin
        
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                if response.status != 200:
                    return {'success': False, 'error': f'HTTP {response.status}'}
                
                html = await response.text()
                soup = BeautifulSoup(html, 'html.parser')
                
                images = []
                for img in soup.find_all('img'):
                    src = img.get('src')
                    if src:
                        absolute_url = urljoin(url, src)
                        images.append({
                            'src': src,
                            'absolute_url': absolute_url,
                            'alt': img.get('alt', ''),
                            'title': img.get('title', '')
                        })
                
                return {
                    'success': True,
                    'url': url,
                    'images': images,
                    'count': len(images)
                }
    
    async def _scrape_table(self, url: str, table_selector: str) -> Dict[str, Any]:
        """テーブルデータを抽出する"""
        from bs4 import BeautifulSoup
        import aiohttp
        import pandas as pd
        
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                if response.status != 200:
                    return {'success': False, 'error': f'HTTP {response.status}'}
                
                html = await response.text()
                
                # pandasのread_htmlを使用
                try:
                    tables = pd.read_html(html)
                    
                    if not tables:
                        return {'success': False, 'error': 'No tables found'}
                    
                    # 最初のテーブルを返す
                    df = tables[0]
                    
                    return {
                        'success': True,
                        'url': url,
                        'table_data': df.to_dict('records'),
                        'columns': df.columns.tolist(),
                        'shape': df.shape
                    }
                    
                except Exception as e:
                    return {'success': False, 'error': f'Table parsing failed: {str(e)}'}
    
    def get_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "action": {
                    "type": "string",
                    "enum": ["scrape_text", "scrape_links", "scrape_images", "scrape_table"],
                    "description": "実行するアクション"
                },
                "url": {
                    "type": "string",
                    "description": "スクレイピング対象のURL"
                },
                "selector": {
                    "type": "string",
                    "description": "CSSセレクター（scrape_textアクション用）"
                },
                "table_selector": {
                    "type": "string",
                    "description": "テーブルのCSSセレクター（scrape_tableアクション用）"
                }
            },
            "required": ["action", "url"]
        }

class EmailTool(BaseTool):
    """メール送信ツール"""
    
    def __init__(self):
        super().__init__(
            name="email",
            description="メールの送信を行う",
            category="communication"
        )
    
    async def execute(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """メール操作を実行する"""
        action = parameters.get('action')
        
        try:
            if action == 'send':
                to_email = parameters.get('to_email')
                subject = parameters.get('subject')
                body = parameters.get('body')
                return await self._send_email(to_email, subject, body)
            else:
                return {'success': False, 'error': f'Unknown action: {action}'}
                
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    async def _send_email(self, to_email: str, subject: str, body: str) -> Dict[str, Any]:
        """メールを送信する"""
        import smtplib
        from email.mime.text import MIMEText
        from email.mime.multipart import MIMEMultipart
        
        # 環境変数からSMTP設定を取得
        smtp_server = os.environ.get('SMTP_SERVER', 'smtp.gmail.com')
        smtp_port = int(os.environ.get('SMTP_PORT', '587'))
        smtp_username = os.environ.get('SMTP_USERNAME')
        smtp_password = os.environ.get('SMTP_PASSWORD')
        
        if not smtp_username or not smtp_password:
            return {'success': False, 'error': 'SMTP credentials not configured'}
        
        try:
            # メッセージを作成
            msg = MIMEMultipart()
            msg['From'] = smtp_username
            msg['To'] = to_email
            msg['Subject'] = subject
            
            msg.attach(MIMEText(body, 'plain'))
            
            # SMTPサーバーに接続して送信
            server = smtplib.SMTP(smtp_server, smtp_port)
            server.starttls()
            server.login(smtp_username, smtp_password)
            
            text = msg.as_string()
            server.sendmail(smtp_username, to_email, text)
            server.quit()
            
            return {
                'success': True,
                'to_email': to_email,
                'subject': subject,
                'message': 'Email sent successfully'
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': f'Failed to send email: {str(e)}'
            }
    
    def get_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "action": {
                    "type": "string",
                    "enum": ["send"],
                    "description": "実行するアクション"
                },
                "to_email": {
                    "type": "string",
                    "description": "送信先メールアドレス"
                },
                "subject": {
                    "type": "string",
                    "description": "メール件名"
                },
                "body": {
                    "type": "string",
                    "description": "メール本文"
                }
            },
            "required": ["action", "to_email", "subject", "body"]
        }

