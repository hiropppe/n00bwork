# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project overview

BERTopic を使った per-class なトピックモデリング（ホテルチェーン別のトピック分布分析）と、ローカル LLM (Ollama 経由 `qwen3:1.7b`) によるトピック表現生成を検証する R&D リポジトリ。すべての作業は `notebooks/` 配下の Jupyter ノートブックで行われ、再利用可能な Python モジュールは存在しない。

## Environment & commands

- Python 3.13 / `uv` で依存管理 (`pyproject.toml` + `uv.lock`)
- Devcontainer 前提: `compose.yaml` の `app` サービスがリポジトリを `/workspace` にマウント。`postCreateCommand` で `uv sync` が走る
- 依存追加後の同期: `uv sync`
- spaCy モデル (`PartOfSpeech` representation で必要):
  ```
  uv run python -m spacy download en_core_web_sm
  ```
- ノートブックは VS Code + Jupyter 拡張で実行する想定（devcontainer.json で指定済み）

### Ollama はホスト側で起動する

macOS の Docker は Apple Silicon GPU (Metal) にアクセスできないため、Ollama は**コンテナ内ではなくホスト側でネイティブ実行**する。コンテナからは `http://host.docker.internal:11434/v1` で接続する。`compose.yaml` の `ollama` サービスは意図的にコメントアウトされている。

## Notebook flow

`notebooks/` のノートブックには以下の依存関係がある。`hotel_reviews_with_transl.csv` がパイプラインのハブ。

1. `preprocessing_hotels.ipynb` — `opinrank+review+dataset.zip` を解凍、ロンドンのホテルレビューを抽出、`langdetect` + `deep-translator` (Google Translate) で英訳し `hotel_reviews_with_transl.csv` を生成
2. `topic_modeling_hotels.ipynb` — BERTopic で基本トピック化、`topics_per_class(classes=df.hotel)` でホテルチェーン別分布、`approximate_distribution` でトークンレベル分布、トピックマージ。リポジトリの中心ノートブック
3. `topic_representation_using_llm.ipynb` — BERTopic の `representation_model` として qwen3 (Ollama OpenAI 互換 API) を使い、トピックの短いラベルを LLM に生成させる
4. `topic_modeling_using_llm.ipynb` — RepresentationModel を介さず、代表ドキュメントを直接 LLM に渡してトピックリストを JSON で生成（structured output）
5. `intro.ipynb` — 20 Newsgroups での最小例（写経）
6. `test_tokenizers.ipynb` — 探索用（空）

## LLM integration gotchas

`topic_representation_using_llm.ipynb` のコメントにも記録されているが、再発しやすいので明示する。

- **`bertopic.representation.OpenAI` の `stop` トークンを上書きする必要がある**。BERTopic はデフォルトで `stop="\n"` を設定するため、qwen3 のレスポンスは `<think>\n` で始まり即停止しラベルが空になる。`generator_kwargs={"stop": "<|im_end|>"}` のように **truthy な値**で上書きする必要がある。`stop=None` は falsy なので内部で `"\n"` に再設定されてしまい効かない
- **qwen3 の thinking mode を無効化する**: プロンプト末尾に `/no_think` を付ける。これがないと `<think>...</think>` タグが出力されてラベルパースが壊れる
- **Structured output**: Ollama OpenAI 互換 API は `response_format={"type": "json_schema", "json_schema": {...}}` で JSON Schema を強制できる（`topic_modeling_using_llm.ipynb` 参照）
- 入力トークン数の確認には `transformers.AutoTokenizer.from_pretrained("Qwen/Qwen3-1.7B")` を使用（qwen3:1.7b のコンテキスト長は 40,960）

## Data & git hygiene

- `.gitignore` で `*.csv`, `*.html`, `*.pdf`, `*.zip`, `opinrankdataset/` を除外。データセット本体・生成物はコミットしない
- ノートブック (`.ipynb`) はセル出力込みでコミットされている。出力を保持したまま編集する
- ノートブック内のコメント・マークダウンは日本語で書かれている。それに合わせる

## References (linked in notebooks)

- 元記事: https://towardsdatascience.com/topics-per-class-using-bertopic-252314f2640/
- `topics_per_class` の `normalize_frequency` の挙動: https://github.com/MaartenGr/BERTopic/issues/446
- BERTopic Approximate Distributions: https://maartengr.github.io/BERTopic/getting_started/distribution/distribution.html
