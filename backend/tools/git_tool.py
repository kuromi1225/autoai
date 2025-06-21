import subprocess
import os

WORKSPACE_DIR = "/app/workspace"

def clone_repository(repo_url, directory="."):
    """指定されたURLからGitリポジトリをクローンする"""
    path = os.path.join(WORKSPACE_DIR, directory)
    # 既存のディレクトリがある場合は削除（本番環境では注意）
    if os.path.exists(path) and os.listdir(path):
         # クリーンな状態で始めるために中身を削除するなどの処理
         # 安全のため、ここでは一旦何もしないでおくか、ユーザーに確認を促す
         # subprocess.run(["rm", "-rf", path]) # 例: 中身を強制削除する場合
         pass
    # ディレクトリが存在しない場合は作成
    os.makedirs(path, exist_ok=True)

    command = ["git", "clone", repo_url, path]
    result = subprocess.run(command, capture_output=True, text=True)
    if result.returncode != 0:
        # クローン失敗時、作成したディレクトリが空であれば削除する
        if not os.listdir(path):
            os.rmdir(path)
        return f"Error cloning repository: {result.stderr}"
    return f"Repository cloned successfully into '{path}'."

def commit(message):
    """ワークスペース内の変更をコミットする"""
    command = ["git", "-C", WORKSPACE_DIR, "add", "."]
    add_result = subprocess.run(command, capture_output=True, text=True)
    if add_result.returncode != 0:
        return f"Error adding changes: {add_result.stderr}"

    command = ["git", "-C", WORKSPACE_DIR, "commit", "-m", message]
    result = subprocess.run(command, capture_output=True, text=True)
    if result.returncode != 0:
        return f"Error committing changes: {result.stderr}"
    return "Changes committed successfully."

def push():
    """変更をリモートリポジトリにプッシュする"""
    command = ["git", "-C", WORKSPACE_DIR, "push"]
    result = subprocess.run(command, capture_output=True, text=True)
    if result.returncode != 0:
        return f"Error pushing changes: {result.stderr}"
    return "Changes pushed to remote repository successfully."
