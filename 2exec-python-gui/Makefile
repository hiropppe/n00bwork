# 2実行ファイル梱包 GUI アプリのビルド一括。
#
# ビルド順（§7）:
#   1. subsystem_b を B 専用 venv で PyInstaller → dist/b_worker/
#   2. app_a を A 専用 venv で PyInstaller → dist/app_a/
#   3. B_worker を A の配布ディレクトリへ配置 → インストーラ化（OS 別）
#
# 依存分離を保つため、A と B はそれぞれの venv でビルドする。

REPO := $(CURDIR)
B_DIR := $(REPO)/subsystem_b
A_DIR := $(REPO)/app_a
B_VENV := $(B_DIR)/.venv
A_VENV := $(A_DIR)/.venv
TEST_VENV := $(REPO)/.venv-test

ifeq ($(OS),Windows_NT)
	B_PY := $(B_VENV)/Scripts/python.exe
	A_PY := $(A_VENV)/Scripts/python.exe
	TEST_PY := $(TEST_VENV)/Scripts/python.exe
	WORKER_BIN := b_worker.exe
else
	B_PY := $(B_VENV)/bin/python
	A_PY := $(A_VENV)/bin/python
	TEST_PY := $(TEST_VENV)/bin/python
	WORKER_BIN := b_worker
endif

.PHONY: all venvs test build-b build-a assemble clean

all: build-b build-a assemble

# --- 開発環境 ---------------------------------------------------------------

venvs:
	cd $(B_DIR) && uv venv && uv pip install numpy pyinstaller
	cd $(A_DIR) && uv venv && uv pip install PySide6 pyinstaller
	uv venv $(TEST_VENV) && uv pip install --python $(TEST_VENV) pytest

test:
	$(TEST_PY) -m pytest tests/ -v

smoke:
	cd $(A_DIR) && QT_QPA_PLATFORM=offscreen $(A_PY) smoke_ipc.py

# --- ビルド -----------------------------------------------------------------

# 1. B_worker（numpy 同梱、PySide6 なし）
build-b:
	cd $(B_DIR) && $(B_PY) -m PyInstaller --noconfirm --clean --distpath $(REPO)/dist --workpath $(REPO)/build/b b_worker.spec

# 2. A（PySide6 同梱、numpy なし）
build-a:
	cd $(A_DIR) && $(A_PY) -m PyInstaller --noconfirm --clean --distpath $(REPO)/dist --workpath $(REPO)/build/a app_a.spec

# 3. B_worker を A の配布ディレクトリへ「B の one-folder ごと」ネスト配置する。
#    PyInstaller one-folder は依存を _internal/ に置くため、中身をマージすると
#    A の _internal に numpy が混入し Python ランタイムも衝突する。B は自分の
#    _internal を保持したまま b_worker/ サブフォルダとして隔離する。
assemble:
	rm -rf $(REPO)/dist/app_a/b_worker
	cp -R $(REPO)/dist/b_worker $(REPO)/dist/app_a/b_worker
	@echo "assembled: dist/app_a/b_worker/ に B の one-folder を隔離同梱"

# 依存分離の検証: A 自身のランタイム(_internal)に numpy が無く、
# B 自身のランタイム(_internal)に PySide6 が無いこと。
# （B は dist/app_a/b_worker/ 配下に隔離されているので、そこは A の領域として数えない）
verify-isolation:
	@echo "== A 自身の _internal に numpy が混入していないか =="
	@! find $(REPO)/dist/app_a/_internal -iname 'numpy*' | grep . || (echo "FAIL: numpy が A の _internal に混入" && exit 1)
	@echo "OK: A に numpy なし"
	@echo "== B 自身の _internal に PySide6 が混入していないか =="
	@! find $(REPO)/dist/b_worker/_internal \( -iname 'PySide6*' -o -iname 'shiboken6*' \) | grep . || (echo "FAIL: PySide6 が B に混入" && exit 1)
	@echo "OK: B に PySide6 なし"

clean:
	rm -rf $(REPO)/build $(REPO)/dist
