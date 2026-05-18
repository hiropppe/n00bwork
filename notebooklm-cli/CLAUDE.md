# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 概要

NotebookLM を CLI から操作するテスト・検証環境。`notebooklm-py` ライブラリを Docker コンテナ上で動かす。

## 環境構成

- **実行環境**: Docker コンテナ（`python` サービス）
- **Python**: 3.13（`ghcr.io/astral-sh/uv:python3.13-bookworm-slim`）
- **パッケージ管理**: uv（venv は `/opt/venv` に固定、ボリュームマウント外）
- **ブラウザ**: Playwright + Chromium（ビルド時にインストール済み）
- **認証セッション**: ホストの `~/.notebooklm/` をコンテナの `/root/.notebooklm/` にマウントして共有

## コマンド

コンテナ内のコマンドはすべて `docker compose exec python uv run ...` 経由で実行する。

```bash
# コンテナビルド（依存インストール・Chromiumも含む）
docker compose build

# コンテナ起動
docker compose up -d

# コマンド実行例
docker compose exec python uv run notebooklm list
docker compose exec python uv run python your_script.py
docker compose exec python uv run pytest
docker compose exec python uv run ruff check .
```

## 認証（初回のみ）

`notebooklm login` はブラウザの GUI が必要なためコンテナ内では直接実行できない。
ホスト macOS 側で一度実行してセッションを保存する：

```bash
# ホスト側（macOS）で実行
uv tool install 'notebooklm-py[browser]'
$(uv tool dir)/notebooklm-py/bin/playwright install chromium
notebooklm login
```

- `uvx notebooklm-py` は不可（実行ファイル名が `notebooklm`）
- `[browser]` extra の指定と playwright ブラウザバイナリのインストールが必要
- `uvx` は一時環境のためブラウザが見つからないことがある → `uv tool install` を使う

セッションは `~/.notebooklm/` に保存され、コンテナは同ディレクトリをマウントして参照する。
セッション切れの際はホスト側で `notebooklm login` を再実行する。

## Tips

### ファイルのプロンプトを `ask` に渡す

```bash
docker compose exec python uv run notebooklm ask "$(cat prompt.txt)"
```

### 複数行プロンプトをインラインで渡す

変数にヒアドキュメントで代入してから渡す：

```bash
prompt=$(cat <<'EOF'
以下の観点で要約してください。

- ポイント1
- ポイント2
EOF
)
docker compose exec python uv run notebooklm ask "$prompt"
```

コマンド一発で書く場合：

```bash
docker compose exec python uv run notebooklm ask "$(cat <<'EOF'
以下の観点で要約してください。

- ポイント1
- ポイント2
EOF
)"
```

`'EOF'` とシングルクォートで囲むと `$変数` の展開が抑制される。展開したい場合は `EOF`（クォートなし）にする。

## 依存関係の追加

```bash
# pyproject.toml を更新してから再ビルド
uv add <package>
docker compose build
```

`pyproject.toml` / `uv.lock` を変更したら `docker compose build` で `/opt/venv` を再作成する。
