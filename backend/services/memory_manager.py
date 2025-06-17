"""
Memory Manager - 長期記憶システム

このモジュールは、ベクトルデータベースを使用してエージェントの長期記憶を管理します。
過去のタスク、解決策、学習内容を保存し、類似のタスクで活用できるようにします。
"""

import os
import logging
import json
import hashlib
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime
import numpy as np
from sentence_transformers import SentenceTransformer
import chromadb
from chromadb.config import Settings

logger = logging.getLogger(__name__)

class MemoryManager:
    """
    長期記憶システムを管理するクラス
    
    主な機能:
    - タスクの記憶保存
    - 類似タスクの検索
    - 解決策の蓄積
    - 学習内容の管理
    """
    
    def __init__(
        self,
        chroma_host: str = "localhost",
        chroma_port: int = 8000,
        embedding_model: str = "all-MiniLM-L6-v2",
        collection_name: str = "devin_memories"
    ):
        """
        MemoryManagerを初期化
        
        Args:
            chroma_host: ChromaDBホスト
            chroma_port: ChromaDBポート
            embedding_model: 埋め込みモデル名
            collection_name: コレクション名
        """
        self.chroma_host = chroma_host
        self.chroma_port = chroma_port
        self.embedding_model_name = embedding_model
        self.collection_name = collection_name
        
        # 埋め込みモデルの初期化
        try:
            self.embedding_model = SentenceTransformer(embedding_model)
            logger.info(f"Embedding model loaded: {embedding_model}")
        except Exception as e:
            logger.error(f"Failed to load embedding model: {e}")
            raise
        
        # ChromaDBクライアントの初期化
        try:
            self.chroma_client = chromadb.HttpClient(
                host=chroma_host,
                port=chroma_port,
                settings=Settings(allow_reset=True)
            )
            
            # コレクションの取得または作成
            self.collection = self.chroma_client.get_or_create_collection(
                name=collection_name,
                metadata={"description": "Devin AI Clone memories"}
            )
            
            logger.info(f"ChromaDB connected: {chroma_host}:{chroma_port}")
            
        except Exception as e:
            logger.error(f"Failed to connect to ChromaDB: {e}")
            # フォールバック：ローカルファイルベースのChromaDB
            try:
                self.chroma_client = chromadb.PersistentClient(
                    path="/app/data/chroma_db"
                )
                self.collection = self.chroma_client.get_or_create_collection(
                    name=collection_name
                )
                logger.info("Using local ChromaDB")
            except Exception as e2:
                logger.error(f"Failed to initialize local ChromaDB: {e2}")
                raise
    
    def store_memory(
        self,
        memory_type: str,
        content: str,
        metadata: Dict[str, Any],
        task_id: Optional[str] = None
    ) -> str:
        """
        記憶を保存
        
        Args:
            memory_type: 記憶の種類 (task, solution, error, learning)
            content: 記憶の内容
            metadata: メタデータ
            task_id: 関連するタスクID
            
        Returns:
            記憶ID
        """
        try:
            # 記憶IDの生成
            memory_id = self._generate_memory_id(content, memory_type)
            
            # 埋め込みベクトルの生成
            embedding = self.embedding_model.encode(content).tolist()
            
            # メタデータの拡張
            full_metadata = {
                "memory_type": memory_type,
                "task_id": task_id,
                "timestamp": datetime.utcnow().isoformat(),
                "content_hash": hashlib.md5(content.encode()).hexdigest(),
                **metadata
            }
            
            # ChromaDBに保存
            self.collection.add(
                ids=[memory_id],
                embeddings=[embedding],
                documents=[content],
                metadatas=[full_metadata]
            )
            
            logger.info(f"Memory stored: {memory_id} ({memory_type})")
            return memory_id
            
        except Exception as e:
            logger.error(f"Failed to store memory: {e}")
            raise
    
    def search_similar_memories(
        self,
        query: str,
        memory_types: Optional[List[str]] = None,
        limit: int = 5,
        similarity_threshold: float = 0.7
    ) -> List[Dict[str, Any]]:
        """
        類似する記憶を検索
        
        Args:
            query: 検索クエリ
            memory_types: 検索対象の記憶タイプ
            limit: 取得する記憶数
            similarity_threshold: 類似度の閾値
            
        Returns:
            類似記憶のリスト
        """
        try:
            # クエリの埋め込みベクトル生成
            query_embedding = self.embedding_model.encode(query).tolist()
            
            # フィルター条件の構築
            where_filter = {}
            if memory_types:
                where_filter["memory_type"] = {"$in": memory_types}
            
            # 類似検索の実行
            results = self.collection.query(
                query_embeddings=[query_embedding],
                n_results=limit,
                where=where_filter if where_filter else None
            )
            
            # 結果の整形
            memories = []
            if results['ids'] and results['ids'][0]:
                for i in range(len(results['ids'][0])):
                    # 類似度の計算（距離から類似度に変換）
                    distance = results['distances'][0][i]
                    similarity = 1 - distance  # コサイン距離の場合
                    
                    if similarity >= similarity_threshold:
                        memory = {
                            'id': results['ids'][0][i],
                            'content': results['documents'][0][i],
                            'metadata': results['metadatas'][0][i],
                            'similarity': similarity
                        }
                        memories.append(memory)
            
            logger.info(f"Found {len(memories)} similar memories for query: {query[:50]}...")
            return memories
            
        except Exception as e:
            logger.error(f"Failed to search memories: {e}")
            return []
    
    def store_task_memory(
        self,
        task_id: str,
        task_description: str,
        steps: List[Dict[str, Any]],
        result: Dict[str, Any],
        errors: List[Dict[str, Any]] = None
    ) -> List[str]:
        """
        タスクの記憶を保存
        
        Args:
            task_id: タスクID
            task_description: タスクの説明
            steps: 実行ステップ
            result: 実行結果
            errors: 発生したエラー
            
        Returns:
            保存された記憶IDのリスト
        """
        memory_ids = []
        
        try:
            # タスク全体の記憶を保存
            task_content = f"タスク: {task_description}\n"
            task_content += f"ステップ数: {len(steps)}\n"
            task_content += f"結果: {result.get('status', 'unknown')}"
            
            task_memory_id = self.store_memory(
                memory_type="task",
                content=task_content,
                metadata={
                    "task_description": task_description,
                    "steps_count": len(steps),
                    "result_status": result.get('status', 'unknown'),
                    "execution_time": result.get('execution_time', 0)
                },
                task_id=task_id
            )
            memory_ids.append(task_memory_id)
            
            # 成功したステップの記憶を保存
            for step in steps:
                if step.get('status') == 'completed':
                    step_content = f"ステップ: {step.get('title', '')}\n"
                    step_content += f"説明: {step.get('description', '')}\n"
                    step_content += f"結果: {step.get('result', '')}"
                    
                    step_memory_id = self.store_memory(
                        memory_type="solution",
                        content=step_content,
                        metadata={
                            "step_type": step.get('type', ''),
                            "step_title": step.get('title', ''),
                            "tools_used": step.get('tools', [])
                        },
                        task_id=task_id
                    )
                    memory_ids.append(step_memory_id)
            
            # エラーの記憶を保存
            if errors:
                for error in errors:
                    error_content = f"エラー: {error.get('message', '')}\n"
                    error_content += f"解決策: {error.get('solution', '')}"
                    
                    error_memory_id = self.store_memory(
                        memory_type="error",
                        content=error_content,
                        metadata={
                            "error_type": error.get('type', ''),
                            "error_code": error.get('code', ''),
                            "resolution_method": error.get('resolution_method', '')
                        },
                        task_id=task_id
                    )
                    memory_ids.append(error_memory_id)
            
            logger.info(f"Stored {len(memory_ids)} memories for task: {task_id}")
            return memory_ids
            
        except Exception as e:
            logger.error(f"Failed to store task memory: {e}")
            return memory_ids
    
    def get_relevant_memories(
        self,
        task_description: str,
        limit: int = 10
    ) -> Dict[str, List[Dict[str, Any]]]:
        """
        タスクに関連する記憶を取得
        
        Args:
            task_description: タスクの説明
            limit: 各タイプの記憶数
            
        Returns:
            記憶タイプ別の関連記憶
        """
        relevant_memories = {
            'tasks': [],
            'solutions': [],
            'errors': [],
            'learnings': []
        }
        
        try:
            # 各記憶タイプで検索
            memory_type_mapping = {
                'tasks': 'task',
                'solutions': 'solution',
                'errors': 'error',
                'learnings': 'learning'
            }
            
            for key, memory_type in memory_type_mapping.items():
                memories = self.search_similar_memories(
                    query=task_description,
                    memory_types=[memory_type],
                    limit=limit,
                    similarity_threshold=0.6
                )
                relevant_memories[key] = memories
            
            total_memories = sum(len(memories) for memories in relevant_memories.values())
            logger.info(f"Retrieved {total_memories} relevant memories for task")
            
            return relevant_memories
            
        except Exception as e:
            logger.error(f"Failed to get relevant memories: {e}")
            return relevant_memories
    
    def store_learning(
        self,
        learning_content: str,
        learning_type: str,
        source: str,
        confidence: float = 1.0
    ) -> str:
        """
        学習内容を保存
        
        Args:
            learning_content: 学習内容
            learning_type: 学習タイプ (pattern, best_practice, technique)
            source: 学習ソース
            confidence: 信頼度
            
        Returns:
            学習記憶ID
        """
        try:
            learning_memory_id = self.store_memory(
                memory_type="learning",
                content=learning_content,
                metadata={
                    "learning_type": learning_type,
                    "source": source,
                    "confidence": confidence
                }
            )
            
            logger.info(f"Learning stored: {learning_memory_id}")
            return learning_memory_id
            
        except Exception as e:
            logger.error(f"Failed to store learning: {e}")
            raise
    
    def _generate_memory_id(self, content: str, memory_type: str) -> str:
        """
        記憶IDを生成
        
        Args:
            content: 記憶内容
            memory_type: 記憶タイプ
            
        Returns:
            記憶ID
        """
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        content_hash = hashlib.md5(content.encode()).hexdigest()[:8]
        return f"{memory_type}_{timestamp}_{content_hash}"
    
    def get_memory_stats(self) -> Dict[str, Any]:
        """
        記憶統計を取得
        
        Returns:
            記憶統計情報
        """
        try:
            # コレクション内の全記憶を取得（メタデータのみ）
            all_memories = self.collection.get()
            
            total_count = len(all_memories['ids']) if all_memories['ids'] else 0
            
            # タイプ別統計
            type_counts = {}
            if all_memories['metadatas']:
                for metadata in all_memories['metadatas']:
                    memory_type = metadata.get('memory_type', 'unknown')
                    type_counts[memory_type] = type_counts.get(memory_type, 0) + 1
            
            return {
                'total_memories': total_count,
                'memory_types': type_counts,
                'collection_name': self.collection_name,
                'embedding_model': self.embedding_model_name
            }
            
        except Exception as e:
            logger.error(f"Failed to get memory stats: {e}")
            return {
                'total_memories': 0,
                'memory_types': {},
                'error': str(e)
            }
    
    def clear_memories(self, memory_type: Optional[str] = None) -> int:
        """
        記憶をクリア
        
        Args:
            memory_type: クリアする記憶タイプ（Noneの場合は全て）
            
        Returns:
            削除された記憶数
        """
        try:
            if memory_type:
                # 特定タイプの記憶を削除
                memories = self.collection.get(
                    where={"memory_type": memory_type}
                )
                if memories['ids']:
                    self.collection.delete(ids=memories['ids'])
                    deleted_count = len(memories['ids'])
                else:
                    deleted_count = 0
            else:
                # 全記憶を削除
                all_memories = self.collection.get()
                if all_memories['ids']:
                    self.collection.delete(ids=all_memories['ids'])
                    deleted_count = len(all_memories['ids'])
                else:
                    deleted_count = 0
            
            logger.info(f"Cleared {deleted_count} memories (type: {memory_type or 'all'})")
            return deleted_count
            
        except Exception as e:
            logger.error(f"Failed to clear memories: {e}")
            return 0

# 使用例とテスト関数
def test_memory_manager():
    """MemoryManagerのテスト"""
    try:
        memory_manager = MemoryManager()
        
        # テスト記憶の保存
        print("=== 記憶保存テスト ===")
        task_memory_id = memory_manager.store_memory(
            memory_type="task",
            content="Webアプリケーションを作成する",
            metadata={"difficulty": "medium", "domain": "web_development"}
        )
        print(f"Task memory stored: {task_memory_id}")
        
        solution_memory_id = memory_manager.store_memory(
            memory_type="solution",
            content="Flaskを使用してRESTful APIを実装",
            metadata={"technology": "Flask", "pattern": "REST"}
        )
        print(f"Solution memory stored: {solution_memory_id}")
        
        # 類似記憶の検索
        print("\n=== 類似記憶検索テスト ===")
        similar_memories = memory_manager.search_similar_memories(
            query="Webアプリを開発したい",
            limit=3
        )
        
        for memory in similar_memories:
            print(f"- {memory['metadata']['memory_type']}: {memory['content'][:50]}... (類似度: {memory['similarity']:.3f})")
        
        # 統計情報の取得
        print("\n=== 記憶統計 ===")
        stats = memory_manager.get_memory_stats()
        print(f"総記憶数: {stats['total_memories']}")
        print(f"タイプ別: {stats['memory_types']}")
        
    except Exception as e:
        print(f"Test failed: {e}")

if __name__ == "__main__":
    test_memory_manager()

