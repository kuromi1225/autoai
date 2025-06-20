# Docker環境での完全リビルド手順

## 1. 全てのコンテナとボリュームを削除
```powershell
# 全てのコンテナを停止・削除
docker-compose down -v --remove-orphans

# 未使用のイメージとボリュームを削除
docker system prune -a -f --volumes

# 特定のボリュームを削除（必要に応じて）
docker volume rm autoai_frontend_dist
```

## 2. 最新のコードをプル
```powershell
git pull origin likedevin
```

## 3. キャッシュなしで完全リビルド
```powershell
# キャッシュを使わずにビルド
docker-compose build --no-cache

# サービスを起動
docker-compose up -d
```

## 4. ログの確認
```powershell
# フロントエンドのビルドログを確認
docker-compose logs frontend

# 全体のログを確認
docker-compose logs
```

## 5. 動作確認
- http://localhost:8765 にアクセス
- ログイン後にエラーが発生しないことを確認

## トラブルシューティング
もしまだエラーが発生する場合：

1. **Dockerデスクトップの再起動**
2. **WSL2の再起動**（Windows環境の場合）
3. **完全なDocker環境のリセット**：
   ```powershell
   docker system prune -a -f --volumes
   docker-compose up --build --force-recreate
   ```

