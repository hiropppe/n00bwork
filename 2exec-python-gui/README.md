# 2実行ファイル梱包 Python GUI アプリ（A + B_worker）

GUI アプリ **A**（PySide6）から、別プロセスのサブシステム **B**（numpy）を実行する構成のサンプル。
A に B を `import` せず、B を**独立した frozen 実行ファイル**として同梱し、NDJSON IPC で連携する。

**目的は「依存の完全分離」**: A のビルドに B の依存（numpy）を混ぜず、B のビルドに A の依存（PySide6）を混ぜない。

## アーキテクチャ

```
┌──────────────────────────────┐        NDJSON over            ┌──────────────────────────────┐
│  A  (PySide6 GUI)            │  stdin/stdout (pipe)          │  B_worker (numpy)            │
│  - QMainWindow / UI          │  ─────────────────────────▶   │  - stdin を1行=1メッセージで  │
│  - QProcess で B を常駐起動   │   request  {id, method,...}   │    read（NDJSON）             │
│  - B のコードは一切 import   │  ◀─────────────────────────   │  - b_core を import して実行  │
│    しない                    │   response {id, result}       │  - stdin EOF で自死           │
└──────────────────────────────┘   stderr = ログ（別チャネル）  └──────────────────────────────┘
        A 専用 venv (PySide6)                                          B 専用 venv (numpy)
```

**肝**: 「A に import 禁止」は *A のプロセスに import しない* の意。B を import するのは
B_worker プロセス内の薄いアダプタ（`worker.py`）だけなので、制約を守りつつ B を使える。

## リポジトリ構成

```
.
├── protocol/schema.md          # NDJSON メッセージ契約（プロトコル定義）
├── app_a/                      # GUI アプリ A（依存: PySide6 のみ）
│   ├── app_a/
│   │   ├── __main__.py         # エントリ（APP_A_SMOKE=1 で非GUIスモーク）
│   │   ├── main_window.py      # UI
│   │   ├── worker_client.py    # B の起動・IPC・ライフサイクル管理（QProcess）
│   │   └── paths.py            # frozen/dev のパス & 実行ファイル解決
│   ├── run_app_a.py            # frozen 用トップレベルランチャ
│   └── app_a.spec              # PyInstaller (one-folder)
├── subsystem_b/                # サブシステム B + worker アダプタ（依存: numpy）
│   ├── b_core/stats.py         # B の本体ロジック（import されるのはここ）
│   ├── worker.py               # NDJSON ループ。ここで b_core を import
│   └── b_worker.spec           # PyInstaller (one-folder)
├── packaging/
│   ├── windows/installer.iss   # Inno Setup（A + B_worker を1インストーラに）
│   └── macos/build_app.sh       # A.app に B_worker を埋め込み → dmg
├── tests/
│   ├── test_protocol.py        # メッセージのエンコード/デコード
│   ├── test_worker.py          # worker を subprocess で叩く結合テスト
│   └── test_lifecycle.py       # 親死亡で子が死ぬか（命綱）
└── Makefile                    # build 一括: B → A → assemble
```

## セットアップ

各コンポーネントは**独立の venv/pyproject** で依存を管理する。この分離が「A に B の依存を混ぜない」の実体。

```bash
# B 専用 venv（numpy）
cd subsystem_b && uv venv && uv pip install numpy pyinstaller && cd ..

# A 専用 venv（PySide6）
cd app_a && uv venv && uv pip install PySide6 pyinstaller && cd ..

# テスト用 venv（pytest）
uv venv .venv-test && uv pip install --python .venv-test pytest
```

`make venvs` で上記を一括実行できる。

## 開発実行

```bash
# GUI を起動（A が B の venv の python で worker.py を dev 起動する）
cd app_a && .venv/bin/python -m app_a

# 非GUIの IPC 疎通スモーク（offscreen）
make smoke
```

## テスト

```bash
make test        # または .venv-test/bin/pytest tests/ -v
```

- `test_protocol.py`: NDJSON メッセージの encode/decode、エラー形。
- `test_worker.py`: `worker.py` を subprocess 起動し request → response を検証（numpy 結合）。
- `test_lifecycle.py`: 命綱の検証。
  - shutdown メッセージで B が正常終了するか。
  - stdin-EOF（親の死を模擬）で B が自死するか。
  - 親プロセスを強制 kill → B が孤児として残らないか。

> B の venv（numpy）が無い場合、worker 結合テストは自動 skip される。

## ビルド & パッケージング

```bash
make build-b          # 1. B_worker（numpy 同梱、PySide6 なし）→ dist/b_worker/
make build-a          # 2. A（PySide6 同梱、numpy なし）→ dist/app_a/
make assemble         # 3. B 一式を dist/app_a/b_worker/ にネスト同梱
make verify-isolation # 依存分離の検証（A に numpy なし / B に PySide6 なし）
```

`make all` で 1→2→3 を一括実行。

> **assemble の要点**: PyInstaller 6.x の one-folder は依存を `_internal/` に置く。
> B の中身を A のフォルダにマージすると **A の `_internal/` に numpy が混入し、
> Python ランタイムも衝突する**。そこで B の one-folder を丸ごと
> `dist/app_a/b_worker/` サブフォルダとして**ネスト**し、それぞれが自分の
> `_internal/` を保持したまま隔離する。配布物のレイアウト:
>
> ```
> dist/app_a/
> ├── app_a                 # A 本体
> ├── _internal/            # A の依存（PySide6。numpy は無い）
> └── b_worker/             # B 一式（隔離）
>     ├── b_worker          # B 本体
>     └── _internal/        # B の依存（numpy。PySide6 は無い）
> ```
>
> A は frozen 時 `Path(sys.executable).parent / "b_worker" / "b_worker"` で B を解決する。

### frozen スモーク

```bash
APP_A_SMOKE=1 QT_QPA_PLATFORM=offscreen ./dist/app_a/app_a
# → [smoke] PASS （frozen A が frozen B を起動し stats.compute を1周）
```

### Windows

`packaging/windows/installer.iss`（Inno Setup）で assemble 済みの `dist/app_a/*`
（A + `b_worker/` サブフォルダ）を同一インストール先へ再帰配置する。スタートメニューの
ショートカットは **A.exe だけ**を指す。A は
`Path(sys.executable).parent / "b_worker" / "b_worker.exe"` で B を解決する。

### macOS

`.app` は **PyInstaller の `BUNDLE` が生成**する（`app_a.spec` の末尾で macOS 時のみ
`dist/StatsGUI.app` を出力）。手組みで onedir を `Contents/MacOS/` に置くと、macOS の
ブートローダが依存を `Contents/Frameworks/` に探しに行き `_internal/` を見つけられず
起動に失敗するため。

`packaging/macos/build_app.sh` は生成済みの `StatsGUI.app` の
`Contents/Resources/b_worker/` に B 一式を埋め込み、A・B **両方**を codesign +
notarization して `.dmg` 化する（片方だけ署名だと B 起動時に Gatekeeper で弾かれる）。

```bash
# ローカル検証（署名なし）
./packaging/macos/build_app.sh

# 署名・notarization つき
SIGN_IDENTITY="Developer ID Application: Your Name (TEAMID)" \
NOTARY_PROFILE="your-notary-profile" \
  ./packaging/macos/build_app.sh
```

## 設計判断（要約）

- **なぜ import しないのか**: ライブラリ衝突の回避と、A のビルドに B の依存を混ぜないため。
  → B を A とは別 venv で固めた独立実行ファイルにするのが本命解。
- **なぜ常駐サブプロセス + NDJSON か**: B は「サーバ機能を持たない」前提。子プロセスとの
  1:1 通信に stdin/stdout パイプで十分。TCP サーバ化はポート衝突・FW の面倒が増える。
- **命綱（親死亡で子を確実に殺す）**は3層:
  1. 正常終了: `aboutToQuit` で `shutdown` → 待って `terminate` → `kill`。
  2. 全 OS 共通の本命 = **stdin-EOF 自死**: B は stdin を read し続け、親が死んでパイプが
     閉じたら EOF でループを抜けて終了。特権不要、macOS の穴も埋まる。
  3. 保険（任意）: Windows は Job Object、Linux は `prctl(PR_SET_PDEATHSIG)`。
- **env サニタイズ**: frozen の A が子 B を起動する際、`_MEIPASS` / `LD_LIBRARY_PATH` /
  `DYLD_LIBRARY_PATH` 等を子に継承させない。継承すると B が A の同梱ライブラリを掴んで壊れる。
- **プロトコル互換管理**: A と B は別ビルドなので、起動直後の `hello` で `protocol_version`
  を検証する。将来 B だけ差し替えても不整合を起動時に検知できる。

## 完成の定義（DoD）

- [x] ユーザは A 1つだけを起動し、B の存在を意識しない（B は A が起動）。
- [x] A の配布物に numpy が入らず、B の配布物に PySide6 が入らない（`make verify-isolation`）。
- [x] A を強制終了しても B が孤児として残らない（`test_lifecycle.py`）。
- [x] 1インストーラ・1ショートカットで配布できる（Inno Setup / .dmg）。
