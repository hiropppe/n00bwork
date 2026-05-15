# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 目的

Confluence Data Center（セルフホスト）から Notion へのデータ移行ツール。現在は Jupyter Notebook ベースで API 調査・データ取得の検証を行っている段階。

## 環境構成

Docker Compose で 3 サービスが動く：

| サービス | ポート | 説明 |
|---------|--------|------|
| `jupyter` | 8888 | JupyterLab（Python 3.13 + uv） |
| `confluence` | 8090, 8091 | Atlassian Confluence Data Center（最新版） |
| `postgres` | 5432 | Confluence のバックエンド DB（PostgreSQL 17） |

```bash
docker compose up -d          # 全サービス起動
docker compose up --build -d jupyter  # パッケージ追加後に Jupyter を再ビルド
docker compose restart jupyter        # .env 変更後の環境変数反映
docker compose logs -f confluence     # Confluence の起動状況確認
```

## パッケージ管理

コンテナ内で uv を使用。`pyproject.toml` を変更したら Jupyter コンテナの再ビルドが必要。

```bash
# コンテナ内でパッケージを追加する場合（再ビルドなし・一時的）
docker compose exec jupyter uv sync

# pyproject.toml に追記した後の正式な反映
docker compose up --build -d jupyter
```

## 環境変数（`.env`）

`.env.example` を参考に `.env` を作成する。

```
# Confluence Cloud（移行元が Cloud の場合）
CONFLUENCE_URL=https://your-domain.atlassian.net
CONFLUENCE_USERNAME=your-email@example.com
CONFLUENCE_API_TOKEN=your-api-token

# Confluence Data Center ローカル検証環境
CONFLUENCE_DC_URL=http://confluence:8090
CONFLUENCE_DC_PAT=your-personal-access-token
```

**認証の注意点：**
- ローカル DC への接続は **Personal Access Token（PAT）を使用**。Basic 認証はデフォルト無効。
- PAT は `http://localhost:8090` → プロフィール → Personal Access Tokens で発行する。
- `atlassian-python-api` の接続は `Confluence(url=..., token=PAT)` で行う（`username`/`password` は使わない）。

## Confluence DC ライセンス

トライアルライセンスは 2025年3月で発行終了。ローカル検証には Atlassian 開発者向け Timebomb ライセンス（10ユーザー・3時間有効）を使用する。

取得先: `https://developer.atlassian.com/platform/marketplace/timebomb-licenses-for-testing-server-apps/`

失効したら画面（`http://localhost:8090`）から再入力する。`docker-compose.yml` の `ATL_LICENSE_KEY` コメント行を参照。

## ノートブック

`notebooks/` に作業用ノートブックを置く。CSV 出力は `.gitignore` 対象。

| ファイル | 内容 |
|---------|------|
| `confluence_dc_api_sample.ipynb` | DC API の基本動作確認（スペース・ページ・CQL・添付ファイル取得） |
| `confluence_macro_survey.ipynb` | 全スペース・全ページのマクロ使用状況を集計・可視化 |

## Confluence ストレージ形式とマクロのパース

ページ本文は `expand="body.storage"` で取得できる XML 形式（Storage Format）。マクロは `<ac:structured-macro ac:name="マクロ名">` として記録される。

```python
from bs4 import BeautifulSoup

soup = BeautifulSoup(page["body"]["storage"]["value"], "lxml")
for macro in soup.find_all("ac:structured-macro"):
    name = macro.get("ac:name")
```

ページ一覧は `get_all_pages_from_space(space=key, expand="body.storage", limit=100)` で本文と同時に取得できる（API 呼び出し回数の節約）。

## 日本語フォント

グラフの日本語表示には `japanize_matplotlib` を使う。

```python
import japanize_matplotlib  # import するだけで有効
```
