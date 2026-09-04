# 実装プラン: 2実行ファイル梱包 Python GUI アプリケーション（A + B_worker）

> このファイルは Claude Code に渡すコンテキスト兼実装プラン。
> GUI アプリ **A** から、別プロセスのサブシステム **B** を実行する構成のサンプルを実装する。
> A に B を `import` せず、B を**独立した frozen 実行ファイル**として同梱し、IPC で連携する。

---

## 0. 前提と決め打ち（気に入らなければここだけ差し替える）

このサンプルでは以下を決め打ちにしている。設計の骨子（プロセス分離・IPC・命綱・2バイナリ梱包）は保ったまま、題材だけ自由に差し替えてよい。

- **GUI フレームワーク**: PySide6（LGPL でパッケージング検証がしやすいため。PyQt6 でも設計は同一）
- **A の依存**: PySide6 のみ（B の依存を一切持たない ← これがこの設計の主目的）
- **B の依存**: numpy（A には無い依存。これで「依存衝突・不要ライブラリ混入回避」を実際に体感できる題材にする）
- **B の題材**: 受け取った数値列に対して統計量（mean/std/min/max/median）を計算して返す、程度の軽い処理。「A に import させたくない重めの依存を持つサブシステム」の代役
- **IPC 形態**: **常駐サブプロセス + NDJSON メッセージング**（A 起動時に B を1個上げ、リクエスト/レスポンスを回す）
- **命綱**: **B は stdin を read し続け、EOF（=親 A の死）で自死**。加えて正常終了時は shutdown メッセージ、Windows は保険で Job Object
- **対象 OS**: Windows / macOS
- **パッケージング**: 各々を PyInstaller one-folder で固め、1インストーラ（Windows: Inno Setup / macOS: .app 埋め込み → .dmg）にまとめる

---

## 1. 背景と設計判断（なぜこの形か）

### 要件

1. GUI アプリ A から、サブシステム B の機能を実行したい
2. B にはサーバ機能（HTTP エンドポイント等）が無い
3. **A に B を `import` してはいけない**
4. A から B を Python スクリプト/別実行ファイルとして起動するのは OK
5. A 起動時に B をサブプロセスとして上げて IPC するのは OK

### 「import 禁止」の確定した理由

- **ライブラリの衝突**（A と B で依存バージョンが噛み合わない）
- **A に不要なライブラリを混ぜたくない**（A のビルドを B の依存で汚したくない）

→ これは「依存の完全分離」が目的。したがって **B を A とは別の venv で固めた独立実行ファイルにする**のが本命解（後述の設計案 2）。クラッシュ隔離やグローバル状態汚染の回避も副次的に得られる。

### 採用しなかった代替案

- **A に import**: 要件3で禁止。理由（依存分離）とも真っ向から矛盾。
- **B を localhost の TCP/Unix ソケットサーバにする**: B は「サーバ機能を持たない」前提。薄いサーバを書くことになり、ポート衝突・FW の面倒も増える。子プロセスとの1対1通信に stdin/stdout パイプで十分。
- **同一 exe を別モードで self re-exec（1バイナリ化）**: B の依存が A のビルドに混ざるため、「A に不要ライブラリを混ぜない」という目的に反する。不採用。
- **埋め込み Python + B ソース同梱**: B を再ビルドせず差し替えられる利点はあるが、同梱物・パス解決の管理が重い。今回は不要。

### 起動負担について（重要な誤解の解消）

exe は A.exe / B_worker.exe の2つになるが、**ユーザが起動するのは A.exe だけ**。B_worker を起動するのは A（`QProcess`/`Popen`）であって、ユーザではない。よってラッパー起動スクリプトは不要で、運用上の起動は1アクションのまま。「2バイナリ」はディスク上の話に過ぎず、インストーラで1パッケージ・1ショートカットに隠蔽する。

---

## 2. アーキテクチャ

```
┌──────────────────────────────┐        NDJSON over            ┌──────────────────────────────┐
│  A.exe  (PySide6 GUI)        │  stdin/stdout (pipe)          │  B_worker.exe (numpy)        │
│                              │  ─────────────────────────▶   │                              │
│  - QMainWindow / UI          │   request  {id, method,...}   │  - stdin を1行=1メッセージで  │
│  - QProcess で B を常駐起動   │                               │    read（NDJSON）             │
│  - リクエスト送信/結果受信    │  ◀─────────────────────────   │  - B のロジックを import して  │
│  - B のコードは一切 import しない│   response {id, result}      │    実行（import はこの中だけ）  │
│                              │                               │  - stdout に結果を1行で書く    │
│                              │   stderr = ログ（別チャネル）  │  - stdin EOF で自死            │
└──────────────────────────────┘                               └──────────────────────────────┘
        A 専用 venv (PySide6)                                          B 専用 venv (numpy)
```

**肝**: 「A に import 禁止」は *A のプロセスに import しない* という意味。B を import するのは B_worker のプロセス内の薄いアダプタ（`worker.py` の中）なので、制約を守れる。

---

## 3. リポジトリ構成（提案）

```
repo/
├── README.md
├── Makefile                      # build 一括: B → A → package
├── protocol/
│   └── schema.md                 # NDJSON メッセージ契約（プロトコル定義）
├── app_a/                        # GUI アプリ A
│   ├── pyproject.toml            # 依存: PySide6 のみ
│   ├── app_a/
│   │   ├── __main__.py           # エントリ
│   │   ├── main_window.py        # UI
│   │   ├── worker_client.py      # B の起動・IPC・ライフサイクル管理
│   │   └── paths.py              # frozen/dev のパス & 実行ファイル解決
│   └── app_a.spec                # PyInstaller (one-folder)
├── subsystem_b/                  # サブシステム B + worker アダプタ
│   ├── pyproject.toml            # 依存: numpy（A には無い）
│   ├── b_core/
│   │   └── stats.py             # B の“本体”ロジック（import されるのはここ）
│   ├── worker.py                 # NDJSON ループ。ここで b_core を import する
│   └── b_worker.spec             # PyInstaller (one-folder)
├── packaging/
│   ├── windows/installer.iss     # Inno Setup
│   └── macos/build_app.sh        # A.app に B_worker を埋め込み → dmg
└── tests/
    ├── test_protocol.py          # メッセージのエンコード/デコード
    ├── test_worker.py            # worker を subprocess で叩く結合テスト
    └── test_lifecycle.py         # 親死亡で子が死ぬか（命綱）
```

> **ビルドの分離を保つ**: `app_a` と `subsystem_b` はそれぞれ独立の venv/pyproject で依存を管理する。この分離こそが「A に B の依存を混ぜない」の実体。

---

## 4. プロトコル（`protocol/schema.md`）

NDJSON（1行 = 1 JSON オブジェクト）。JSON-RPC 2.0 風。将来 B をサービス化しても移行しやすい形にする。

**ハンドシェイク（起動直後）**: B は最初に自分の情報を1行出す。

```json
{"type":"hello","protocol_version":1,"worker":"b_worker","capabilities":["stats.compute"]}
```

A は `protocol_version` を検証し、非互換なら B を落として UI にエラー表示。

**リクエスト（A → B）**:

```json
{"type":"request","id":"uuid-1","method":"stats.compute","params":{"values":[1,2,3,4]}}
```

**レスポンス（B → A）**:

```json
{"type":"response","id":"uuid-1","result":{"mean":2.5,"std":1.118,"min":1,"max":4,"median":2.5}}
```

**エラー**:

```json
{"type":"response","id":"uuid-1","error":{"code":"BAD_INPUT","message":"values must be numbers"}}
```

**シャットダウン（正常終了時 A → B）**:

```json
{"type":"shutdown"}
```

設計ルール:
- `id` でリクエスト/レスポンスを対応付け（並行リクエスト対応）
- framing は改行区切り（NDJSON）。値にバイナリ/長文を入れるなら 4byte length-prefix に切り替えられる余地を残す
- **stdout は結果チャネル専用**、ログ・スタックトレースは **stderr** に流す（混ざると parse が壊れる）
- タイムアウトは A 側で持つ（応答が来ない request を一定時間で失敗扱い）

---

## 5. コンポーネント仕様

### 5.1 サブシステム B（`subsystem_b/`）

**`b_core/stats.py`** — B の本体。numpy 依存。

- `compute(values: list[float]) -> dict`: mean/std/min/max/median を返す純粋関数。

**`worker.py`** — NDJSON ループ本体。**ここで初めて `from b_core import stats` する**（import は B のプロセス内のみ）。

擬似コード:

```python
import sys, json
from b_core import stats

def main():
    # hello を最初に送る
    emit({"type": "hello", "protocol_version": 1,
          "worker": "b_worker", "capabilities": ["stats.compute"]})
    for line in sys.stdin:            # ← 命綱: 親が死ぬと stdin が閉じ、ループが自然終了 → exit
        line = line.strip()
        if not line:
            continue
        msg = json.loads(line)
        if msg.get("type") == "shutdown":
            break
        if msg.get("type") == "request":
            handle_request(msg)
    # ループを抜けた = EOF or shutdown → プロセス終了

def handle_request(msg):
    try:
        if msg["method"] == "stats.compute":
            result = stats.compute(msg["params"]["values"])
            emit({"type": "response", "id": msg["id"], "result": result})
        else:
            emit_error(msg["id"], "UNKNOWN_METHOD", msg["method"])
    except Exception as e:
        emit_error(msg["id"], "INTERNAL", str(e))

def emit(obj):
    sys.stdout.write(json.dumps(obj) + "\n")
    sys.stdout.flush()               # ← flush 必須（バッファに溜めない）
```

- `sys.stdin` の for ループが **stdin-EOF 自死**そのもの。親 A が落ちてパイプが閉じれば EOF で抜ける。
- 例外は必ず捕まえて error レスポンスにする。worker 自体は落とさない。
- `stdout.flush()` を忘れると A 側が結果を受け取れずハングするので注意。

### 5.2 GUI アプリ A（`app_a/`）

**`paths.py`** — frozen/dev のパス解決。

```python
import sys
from pathlib import Path

def worker_executable() -> Path:
    if getattr(sys, "frozen", False):
        # frozen: 自分（A.exe）の隣 / macOS は .app バンドル内
        base = Path(sys.executable).parent
        name = "b_worker.exe" if sys.platform == "win32" else "b_worker"
        return base / name
    else:
        # dev: subsystem_b/worker.py を、B の venv の python で起動
        return Path(__file__).resolve().parents[2] / "subsystem_b" / "worker.py"
```

**`worker_client.py`** — B の起動・IPC・ライフサイクル。**QProcess を使い、GUI イベントループを絶対にブロックしない**。

責務:
- 起動: `QProcess` で B を spawn。**env をサニタイズ**（frozen の `_MEIPASS` / `LD_LIBRARY_PATH` / `DYLD_LIBRARY_PATH` を子に継承させない ← これをやらないと B が A の同梱ライブラリを掴んで壊れる）。
- 送信: `request()` メソッド。`id` を採番して JSON を1行書く。呼び出し側には `id` かシグナルで結果を返す（asyncっぽく）。
- 受信: `readyReadStandardOutput` シグナルで stdout をバッファリングし、改行で分割 → JSON parse → `id` で待ち側にディスパッチ。
- ハンドシェイク: 最初の `hello` で `protocol_version` を検証。ダメなら B を終了させ UI にエラー。
- 監督: `finished`/`errorOccurred` で B の死を検知 → 再起動 or UI に通知。
- 終了: `QApplication.aboutToQuit` で `shutdown` 送信 → `waitForFinished` → 残れば `terminate()` → `kill()`。

env サニタイズ例:

```python
from PySide6.QtCore import QProcess, QProcessEnvironment

def _clean_env() -> QProcessEnvironment:
    env = QProcessEnvironment.systemEnvironment()
    for k in ("_MEIPASS", "_MEIPASS2", "LD_LIBRARY_PATH", "DYLD_LIBRARY_PATH"):
        env.remove(k)
    return env
```

**`main_window.py`** — UI。テキスト入力（カンマ区切りの数値）＋「Compute」ボタン。押すと `worker_client.request("stats.compute", {...})`、結果をラベルに表示。B のコードは一切 import しない。

**`__main__.py`** — `QApplication` 生成 → `worker_client` 起動 → `MainWindow` 表示 → `aboutToQuit` に shutdown フック接続。

---

## 6. ライフサイクル / 命綱（親死亡で子を確実に殺す）

「デーモン化するか否か」ではなく「**明示的に殺す仕組みを入れるか**」の問題。デフォルトでは親が死んでも子は孤児として生き残る（POSIX/Windows とも）。`multiprocessing daemon=True` は QProcess/Popen には無関係かつ親クラッシュに無力なので使わない。3層で守る:

1. **正常終了**: `aboutToQuit` で `shutdown` メッセージ → 待って terminate → kill。
2. **全 OS 共通の本命 = stdin-EOF 自死**: B は stdin を read し続け、親が死んでパイプが閉じたら EOF で終了（§5.1 のループ）。特権不要、macOS の穴も埋まる。
3. **保険（任意）**:
   - Windows: **Job Object** に `JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE` を付けて B を割り当て、A 死亡で OS に殺させる（pywin32）。
   - Linux: `prctl(PR_SET_PDEATHSIG, SIGKILL)`（今回対象外だが参考）。

孤児が残ると B が掴んだファイル/ロックで次回起動が詰まることがあるので、テスト（`test_lifecycle.py`）で「A を kill → B が消えるか」を必ず検証する。

---

## 7. Freeze & パッケージング（案X: 1インストーラ）

各コンポーネントを**それぞれの venv で** PyInstaller one-folder ビルド → 1つのインストーラにまとめる。

### ビルド順（Makefile / CI の3ステップ）

1. `subsystem_b` を B 専用 venv で `pyinstaller b_worker.spec` → `dist/b_worker/`（B_worker + numpy 同梱）
2. `app_a` を A 専用 venv で `pyinstaller app_a.spec` → `dist/app_a/`（A + PySide6 同梱）
3. B_worker を A の配布ディレクトリに配置し、インストーラ化

### Windows

- `packaging/windows/installer.iss`（Inno Setup）で `dist/app_a/*` と `b_worker.exe` を同一インストール先にまとめる。
- スタートメニューのショートカットは **A.exe だけ**を指す。
- A は `Path(sys.executable).parent / "b_worker.exe"` で B を解決。

### macOS

- `A.app/Contents/Resources/`（または `Contents/MacOS/`）に `b_worker` を埋め込む。
- 配布は `.dmg`（or 署名済み `.pkg`）。
- **重要**: A・B **両方**を codesign + notarization。片方だけ署名だと B 起動時に Gatekeeper で弾かれる。
- A は自分のバンドル位置から B を相対解決。

### プロトコルの互換管理

A と B は別ビルドなので、§4 の `protocol_version` をハンドシェイクで必ず検証する。将来 B だけ差し替えても不整合を起動時に検知できる。

---

## 8. テスト

- `test_protocol.py`: NDJSON メッセージの encode/decode、エラー形。
- `test_worker.py`: `worker.py` を実際に subprocess 起動し、request → response を検証（B のロジック結合）。
- `test_lifecycle.py`:
  - 親を通常終了 → shutdown で B が終わるか。
  - 親を強制 kill → stdin-EOF で B が孤児にならず消えるか。
- （任意）frozen 済みバイナリに対するスモークテスト: A.exe 起動 → 1リクエスト → 結果表示 → 終了で B も消える。

---

## 9. 実装マイルストーン（Claude Code への指示順）

1. リポジトリ雛形（§3 の構成）と2つの `pyproject.toml`（依存を分離）。
2. `protocol/schema.md` を確定（§4）。
3. `subsystem_b`: `b_core/stats.py` + `worker.py`（NDJSON ループ、hello、stdin-EOF 自死、flush）。`test_worker.py`。
4. `app_a`: `paths.py` → `worker_client.py`（QProcess・env サニタイズ・ハンドシェイク・監督・shutdown）→ `main_window.py` → `__main__.py`。dev 実行（frozen 前）で疎通確認。
5. `test_lifecycle.py`（命綱の検証）。
6. `b_worker.spec` / `app_a.spec` を書いて one-folder ビルド。frozen 同士で疎通確認（§5.1 パス解決 & env サニタイズがここで効く）。
7. パッケージング: まず対象1 OS（例: Windows + Inno Setup）で1インストーラ・1ショートカット → 起動〜B自死まで通す。次に macOS。
8. README にビルド手順・アーキ図・設計判断の要約。

### 完成の定義（DoD）

- ユーザは A.exe（/ A.app）1つだけを起動し、B の存在を意識しない。
- A の配布物に numpy が入らず、B の配布物に PySide6 が入らない（依存分離が実現できている）。
- A を強制終了しても B が孤児として残らない。
- 1インストーラ・1ショートカットで配布できる。

---

## 付録: 判断の分岐点（題材を変えるとき）

- **B の起動が重い / 状態を持つ / 高頻度** → 本プランの「常駐サブプロセス」が最適。
- **B の処理が単発・独立・起動が軽い** → 「都度サブプロセス起動」に切り替えると命綱の悩みがほぼ消える（処理後に B が自分で exit するため孤児が生まれにくい）。その場合 §6 の常駐向けの監督は簡略化してよい。
- IPC 量が増えて NDJSON が辛くなったら length-prefix framing、あるいは将来的に B をローカルサービス化（そのとき JSON-RPC の資産がそのまま活きる）。
