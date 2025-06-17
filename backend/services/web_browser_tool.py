"""
Web Browser Tool - Webブラウジング機能

このモジュールは、エージェントがインターネットを検索し、
Webページの内容を取得する機能を提供します。
"""

import requests
from bs4 import BeautifulSoup
import logging
from urllib.parse import urljoin, urlparse
import time
import re
from typing import List, Dict, Optional

logger = logging.getLogger(__name__)

class WebBrowserTool:
    """Webブラウジング機能を提供するクラス"""
    
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        })
        self.timeout = 10
        self.max_content_length = 50000  # 最大コンテンツ長
        
    def search(self, query: str, num_results: int = 10) -> Dict:
        """
        Google検索を実行し、結果を返す
        
        Args:
            query: 検索クエリ
            num_results: 取得する結果数
            
        Returns:
            検索結果の辞書（タイトル、URL、スニペットのリスト）
        """
        try:
            # DuckDuckGoを使用（Googleよりもアクセスしやすい）
            search_url = f"https://duckduckgo.com/html/?q={query}"
            
            response = self.session.get(search_url, timeout=self.timeout)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'html.parser')
            results = []
            
            # DuckDuckGoの検索結果を解析
            for result in soup.find_all('div', class_='result')[:num_results]:
                title_elem = result.find('a', class_='result__a')
                snippet_elem = result.find('a', class_='result__snippet')
                
                if title_elem:
                    title = title_elem.get_text(strip=True)
                    url = title_elem.get('href', '')
                    snippet = snippet_elem.get_text(strip=True) if snippet_elem else ""
                    
                    results.append({
                        'title': title,
                        'url': url,
                        'snippet': snippet
                    })
            
            logger.info(f"検索完了: {query} - {len(results)}件の結果")
            
            return {
                'query': query,
                'results': results,
                'total_results': len(results)
            }
            
        except Exception as e:
            logger.error(f"検索エラー: {e}")
            return {
                'query': query,
                'results': [],
                'total_results': 0,
                'error': str(e)
            }
    
    def browse_page(self, url: str) -> Dict:
        """
        指定されたURLのWebページにアクセスし、コンテンツを取得する
        
        Args:
            url: アクセスするURL
            
        Returns:
            ページ情報の辞書（タイトル、コンテンツ、リンクなど）
        """
        try:
            # URLの正規化
            if not url.startswith(('http://', 'https://')):
                url = 'https://' + url
            
            response = self.session.get(url, timeout=self.timeout)
            response.raise_for_status()
            
            # コンテンツサイズチェック
            if len(response.content) > self.max_content_length:
                content = response.content[:self.max_content_length]
                truncated = True
            else:
                content = response.content
                truncated = False
            
            soup = BeautifulSoup(content, 'html.parser')
            
            # タイトル取得
            title = soup.find('title')
            title_text = title.get_text(strip=True) if title else "タイトルなし"
            
            # メインコンテンツ抽出
            main_content = self._extract_main_content(soup)
            
            # リンク抽出
            links = self._extract_links(soup, url)
            
            # メタ情報取得
            meta_description = self._get_meta_description(soup)
            
            logger.info(f"ページ取得完了: {url}")
            
            return {
                'url': url,
                'title': title_text,
                'content': main_content,
                'meta_description': meta_description,
                'links': links[:20],  # 最大20個のリンク
                'truncated': truncated,
                'content_length': len(main_content)
            }
            
        except Exception as e:
            logger.error(f"ページ取得エラー ({url}): {e}")
            return {
                'url': url,
                'title': "",
                'content': "",
                'meta_description': "",
                'links': [],
                'truncated': False,
                'content_length': 0,
                'error': str(e)
            }
    
    def _extract_main_content(self, soup: BeautifulSoup) -> str:
        """メインコンテンツを抽出する"""
        # 不要なタグを削除
        for tag in soup(['script', 'style', 'nav', 'header', 'footer', 'aside']):
            tag.decompose()
        
        # メインコンテンツを探す
        main_selectors = [
            'main',
            'article',
            '.content',
            '.main-content',
            '#content',
            '#main',
            '.post-content',
            '.entry-content'
        ]
        
        main_content = None
        for selector in main_selectors:
            main_content = soup.select_one(selector)
            if main_content:
                break
        
        # メインコンテンツが見つからない場合はbodyを使用
        if not main_content:
            main_content = soup.find('body')
        
        if not main_content:
            return ""
        
        # テキストを抽出し、整形
        text = main_content.get_text(separator='\n', strip=True)
        
        # 連続する空行を削除
        text = re.sub(r'\n\s*\n', '\n\n', text)
        
        # 長すぎる場合は切り詰め
        if len(text) > 5000:
            text = text[:5000] + "..."
        
        return text
    
    def _extract_links(self, soup: BeautifulSoup, base_url: str) -> List[Dict]:
        """ページ内のリンクを抽出する"""
        links = []
        
        for link in soup.find_all('a', href=True):
            href = link.get('href')
            text = link.get_text(strip=True)
            
            if href and text:
                # 相対URLを絶対URLに変換
                absolute_url = urljoin(base_url, href)
                
                # 有効なURLかチェック
                parsed = urlparse(absolute_url)
                if parsed.scheme in ['http', 'https']:
                    links.append({
                        'text': text[:100],  # テキストを100文字に制限
                        'url': absolute_url
                    })
        
        return links
    
    def _get_meta_description(self, soup: BeautifulSoup) -> str:
        """メタディスクリプションを取得する"""
        meta_desc = soup.find('meta', attrs={'name': 'description'})
        if meta_desc:
            return meta_desc.get('content', '')
        
        # Open Graphのdescriptionも試す
        og_desc = soup.find('meta', attrs={'property': 'og:description'})
        if og_desc:
            return og_desc.get('content', '')
        
        return ""
    
    def search_and_browse(self, query: str, num_pages: int = 3) -> Dict:
        """
        検索を実行し、上位結果のページを自動的にブラウジングする
        
        Args:
            query: 検索クエリ
            num_pages: ブラウジングするページ数
            
        Returns:
            検索結果とページ内容の統合結果
        """
        # まず検索を実行
        search_results = self.search(query)
        
        if not search_results['results']:
            return search_results
        
        # 上位結果をブラウジング
        browsed_pages = []
        for i, result in enumerate(search_results['results'][:num_pages]):
            logger.info(f"ページをブラウジング中 ({i+1}/{num_pages}): {result['url']}")
            
            page_content = self.browse_page(result['url'])
            browsed_pages.append({
                'search_result': result,
                'page_content': page_content
            })
            
            # レート制限のため少し待機
            time.sleep(1)
        
        return {
            'query': query,
            'search_results': search_results['results'],
            'browsed_pages': browsed_pages,
            'summary': self._create_summary(query, browsed_pages)
        }
    
    def _create_summary(self, query: str, browsed_pages: List[Dict]) -> str:
        """ブラウジング結果の要約を作成する"""
        if not browsed_pages:
            return f"'{query}'に関する情報は見つかりませんでした。"
        
        summary_parts = [f"'{query}'に関する検索結果の要約:"]
        
        for i, page in enumerate(browsed_pages, 1):
            page_content = page['page_content']
            search_result = page['search_result']
            
            if page_content.get('error'):
                summary_parts.append(f"{i}. {search_result['title']} - アクセスエラー")
            else:
                content_preview = page_content['content'][:200] + "..." if len(page_content['content']) > 200 else page_content['content']
                summary_parts.append(f"{i}. {page_content['title']}")
                summary_parts.append(f"   URL: {page_content['url']}")
                summary_parts.append(f"   内容: {content_preview}")
                summary_parts.append("")
        
        return "\n".join(summary_parts)

# 使用例とテスト関数
def test_web_browser_tool():
    """WebBrowserToolのテスト"""
    browser = WebBrowserTool()
    
    # 検索テスト
    print("=== 検索テスト ===")
    search_results = browser.search("Python Flask tutorial")
    print(f"検索結果数: {search_results['total_results']}")
    for result in search_results['results'][:3]:
        print(f"- {result['title']}: {result['url']}")
    
    # ページブラウジングテスト
    print("\n=== ページブラウジングテスト ===")
    if search_results['results']:
        first_url = search_results['results'][0]['url']
        page_content = browser.browse_page(first_url)
        print(f"ページタイトル: {page_content['title']}")
        print(f"コンテンツ長: {page_content['content_length']}")
        print(f"リンク数: {len(page_content['links'])}")
    
    # 統合テスト
    print("\n=== 統合テスト ===")
    integrated_results = browser.search_and_browse("Docker compose tutorial", 2)
    print(integrated_results['summary'])

if __name__ == "__main__":
    test_web_browser_tool()

