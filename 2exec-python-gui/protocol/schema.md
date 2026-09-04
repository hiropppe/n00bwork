# プロトコル定義（NDJSON メッセージ契約）

A（GUI）と B_worker 間の IPC プロトコル。**1 行 = 1 JSON オブジェクト**（NDJSON）。
JSON-RPC 2.0 風の形にしており、将来 B をサービス化しても移行しやすい。

## チャネル

- **stdout**: 結果チャネル専用（このプロトコルのメッセージのみを流す）
- **stderr**: ログ・スタックトレース用（人間向け。ここに何を書いても parse は壊れない）
- **stdin**: A → B へのメッセージ。閉じられる（EOF）と B は自死する（命綱）

`stdout` にログを混ぜると受信側の parse が壊れるので厳禁。

## プロトコルバージョン

現在のバージョン: **1**

A は起動直後の `hello` で `protocol_version` を検証する。非互換なら B を落として UI にエラー表示する。

## メッセージ種別

### ハンドシェイク（B → A、起動直後の最初の1行）

B は起動すると真っ先に自分の情報を1行出す。

```json
{"type":"hello","protocol_version":1,"worker":"b_worker","capabilities":["stats.compute"]}
```

| フィールド | 型 | 説明 |
|---|---|---|
| `type` | string | 固定値 `"hello"` |
| `protocol_version` | number | プロトコルバージョン。A が検証する |
| `worker` | string | worker 名 |
| `capabilities` | string[] | 対応メソッドの一覧 |

### リクエスト（A → B）

```json
{"type":"request","id":"uuid-1","method":"stats.compute","params":{"values":[1,2,3,4]}}
```

| フィールド | 型 | 説明 |
|---|---|---|
| `type` | string | 固定値 `"request"` |
| `id` | string | リクエスト識別子。レスポンスと対応付ける |
| `method` | string | 呼び出すメソッド名 |
| `params` | object | メソッド引数 |

### レスポンス（B → A、成功）

```json
{"type":"response","id":"uuid-1","result":{"mean":2.5,"std":1.118,"min":1,"max":4,"median":2.5}}
```

| フィールド | 型 | 説明 |
|---|---|---|
| `type` | string | 固定値 `"response"` |
| `id` | string | 対応するリクエストの `id` |
| `result` | object | メソッドの返り値 |

### レスポンス（B → A、エラー）

```json
{"type":"response","id":"uuid-1","error":{"code":"BAD_INPUT","message":"values must be numbers"}}
```

| フィールド | 型 | 説明 |
|---|---|---|
| `type` | string | 固定値 `"response"` |
| `id` | string | 対応するリクエストの `id`（対応不能なら `null`） |
| `error.code` | string | エラーコード（下表参照） |
| `error.message` | string | 人間向けメッセージ |

### シャットダウン（A → B、正常終了時）

```json
{"type":"shutdown"}
```

B はこれを受けるとループを抜けて正常終了する。

## エラーコード

| コード | 意味 |
|---|---|
| `BAD_INPUT` | params の内容が不正（型・値） |
| `UNKNOWN_METHOD` | 未知の method |
| `INTERNAL` | worker 内部の想定外例外 |
| `PARSE_ERROR` | 受信行が JSON として parse できない |

## メソッド

### `stats.compute`

数値列の統計量を計算する。

**params**:

```json
{"values": [1, 2, 3, 4]}
```

- `values`: 数値の配列（空でないこと）

**result**:

```json
{"mean": 2.5, "std": 1.118, "min": 1, "max": 4, "median": 2.5}
```

## 設計ルール

- `id` でリクエスト/レスポンスを対応付ける（並行リクエスト対応）
- framing は改行区切り（NDJSON）。値にバイナリ/長文を入れるなら 4byte length-prefix
  に切り替えられる余地を残す
- タイムアウトは A 側で持つ（応答が来ない request を一定時間で失敗扱い）
- B は例外を error レスポンスに変換し、worker 自体は落とさない
