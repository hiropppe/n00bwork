"""UI。カンマ区切りの数値入力 + Compute ボタン。B のコードは一切 import しない。"""

from __future__ import annotations

from PySide6.QtWidgets import (
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from .worker_client import WorkerClient


class MainWindow(QMainWindow):
    def __init__(self, client: WorkerClient):
        super().__init__()
        self._client = client
        self._pending_id: str | None = None

        self.setWindowTitle("A — Stats (via B_worker)")
        self.resize(480, 220)

        central = QWidget()
        layout = QVBoxLayout(central)

        layout.addWidget(QLabel("カンマ区切りの数値を入力:"))
        self._input = QLineEdit()
        self._input.setPlaceholderText("例: 1, 2, 3, 4, 5")
        self._input.returnPressed.connect(self._on_compute)
        layout.addWidget(self._input)

        self._button = QPushButton("Compute")
        self._button.clicked.connect(self._on_compute)
        self._button.setEnabled(False)  # worker が ready になるまで無効
        layout.addWidget(self._button)

        self._status = QLabel("worker を起動中…")
        self._status.setWordWrap(True)
        layout.addWidget(self._status)

        self._result = QLabel("")
        self._result.setWordWrap(True)
        self._result.setTextInteractionFlags(
            self._result.textInteractionFlags().TextSelectableByMouse
        )
        layout.addWidget(self._result)

        self.setCentralWidget(central)

        # worker のシグナルを UI に接続
        self._client.ready.connect(self._on_ready)
        self._client.result.connect(self._on_result)
        self._client.error.connect(self._on_error)
        self._client.worker_failed.connect(self._on_worker_failed)

    # --- worker イベント ---------------------------------------------------

    def _on_ready(self) -> None:
        self._button.setEnabled(True)
        self._status.setText("準備完了。数値を入力して Compute を押してください。")

    def _on_result(self, req_id: str, result: dict) -> None:
        if req_id != self._pending_id:
            return
        self._pending_id = None
        self._button.setEnabled(True)
        text = "  ".join(f"{k}={v:.4g}" for k, v in result.items())
        self._result.setText(text)
        self._status.setText("完了。")

    def _on_error(self, req_id: str, code: str, message: str) -> None:
        if req_id != self._pending_id:
            return
        self._pending_id = None
        self._button.setEnabled(True)
        self._result.setText("")
        self._status.setText(f"エラー [{code}]: {message}")

    def _on_worker_failed(self, message: str) -> None:
        self._button.setEnabled(False)
        self._status.setText(f"worker 異常: {message}")
        QMessageBox.critical(self, "Worker error", message)

    # --- UI 操作 -----------------------------------------------------------

    def _on_compute(self) -> None:
        raw = self._input.text().strip()
        if not raw:
            self._status.setText("数値を入力してください。")
            return
        try:
            values = [float(tok) for tok in raw.split(",") if tok.strip() != ""]
        except ValueError:
            self._status.setText("数値として解釈できないトークンがあります。")
            return
        if not values:
            self._status.setText("数値を入力してください。")
            return

        self._button.setEnabled(False)
        self._result.setText("")
        self._status.setText("計算中…")
        self._pending_id = self._client.request("stats.compute", {"values": values})
