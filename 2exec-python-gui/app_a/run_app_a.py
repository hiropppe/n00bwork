"""PyInstaller / dev 共通のトップレベルエントリ。

frozen 時にエントリスクリプトを直接実行すると相対 import が壊れるため、
パッケージ `app_a` を import 経由で起動する薄いランチャにする。
"""

import sys

from app_a.__main__ import main

if __name__ == "__main__":
    sys.exit(main())
