# Redmine 検証環境（Docker）

Redmine 最新版の機能を触って確認するためのローカル環境。

| 項目 | 値 |
| --- | --- |
| Redmine | 7.0.1.stable（Rails 8.1.3.1） |
| DB | PostgreSQL 17 (alpine) |
| URL | http://localhost:3000 |
| 初期ログイン | `admin` / `admin`（初回ログイン時にパスワード変更を求められる） |

デフォルトデータ（トラッカー・ステータス・ロール・優先度）は日本語で投入済み、
表示言語の既定も `ja` に設定済み。

## 使い方

```sh
cp .env.example .env      # 初回のみ。REDMINE_SECRET_KEY_BASE を設定する
                          #   openssl rand -hex 64
docker compose up -d      # 起動
docker compose logs -f redmine   # ログ追跡
docker compose stop       # 停止（データは残る）
docker compose start      # 再開
```

作り直す場合:

```sh
docker compose down -v    # -v でDB・添付ファイルも破棄
docker compose up -d
# デフォルトデータの再投入
docker compose exec redmine sh -c 'cd /usr/src/redmine && RAILS_ENV=production REDMINE_LANG=ja bundle exec rake redmine:load_default_data'
```

## ファイル構成

```
compose.yaml     サービス定義
.env             ポート番号・DB認証情報・秘密鍵（gitignore 済み）
.env.example     .env のひな形
plugins/         プラグイン置き場（コンテナの plugins/ にマウント）
themes/          テーマ置き場（既定では未マウント。下記参照）
```

永続データは Docker の名前付きボリューム:
- `redmine-lab_db-data` — PostgreSQL のデータ
- `redmine-lab_files` — 添付ファイル

## バージョンを切り替える

`.env` の `REDMINE_TAG` を変えて `docker compose up -d`。
利用可能なタグは https://hub.docker.com/_/redmine で確認できる（`6.1`, `7.0` など）。

**注意**: ダウングレードは DB マイグレーションが巻き戻らないため動かない。
古いバージョンを試すときは `docker compose down -v` でデータを消してから起動する。

## プラグインを試す

`plugins/` にプラグインのディレクトリを配置して再起動するだけ。
`REDMINE_PLUGINS_MIGRATE=true` を設定しているので、起動時にプラグインの
マイグレーションが自動実行される。

```sh
git clone <plugin-repo> plugins/<plugin_name>
docker compose restart redmine
```

## テーマを試す

`compose.yaml` の `./themes:/usr/src/redmine/public/themes` の行を有効化する前に、
同梱テーマ（alternate / classic）をホスト側にコピーしておく。
そうしないと空ディレクトリで上書きされ、テーマ選択肢が消える。

```sh
docker compose cp redmine:/usr/src/redmine/public/themes/. ./themes/
# compose.yaml の themes 行をアンコメントしてから
docker compose up -d
```

## rails / rake コマンドを叩く

`SECRET_KEY_BASE` を `REDMINE_` 接頭辞なしで渡しているので、
`docker compose exec` からもそのまま実行できる。

```sh
# コンソール
docker compose exec redmine sh -c 'cd /usr/src/redmine && RAILS_ENV=production bundle exec rails console'

# マイグレーション状態
docker compose exec redmine sh -c 'cd /usr/src/redmine && RAILS_ENV=production bundle exec rake db:migrate:status'

# DB に直接つなぐ
docker compose exec db psql -U redmine -d redmine
```

## メール送信を試す場合

`configuration.yml` をこのディレクトリに置き、`compose.yaml` の該当マウント行を
有効化する。ローカル検証なら MailHog / Mailpit をサービスとして足して
`smtp_settings` をそこに向けるのが手軽。
