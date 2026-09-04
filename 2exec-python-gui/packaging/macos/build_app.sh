#!/usr/bin/env bash
# macOS: PyInstaller が生成した StatsGUI.app に b_worker を埋め込み、
# codesign + notarization して .dmg にする。
#
# 前提: Makefile の build-b → build-a を実行済み。
#   dist/StatsGUI.app … PyInstaller の BUNDLE が生成した A の .app
#       （Contents/MacOS/app_a + Contents/Frameworks/ に PySide6。numpy は無い）
#   dist/b_worker/    … PyInstaller one-folder の B（b_worker + numpy）
#
# 方針:
#   - .app は「手組みしない」。PyInstaller の BUNDLE に作らせた正しい .app を使う。
#     （手組みで onedir を Contents/MacOS に置くと、macOS ブートローダが依存を
#       Contents/Frameworks に探しに行き _internal を見つけられず起動に失敗する）
#   - B の one-folder を Contents/Resources/b_worker/ へ丸ごとネスト埋め込みし、
#     B 自身の _internal を保持したまま隔離する（numpy を A 側に混ぜない）。
#     paths.py は frozen 時 Contents/Resources/b_worker/b_worker を探す。
#   - A・B 両方を codesign（片方だけだと B 起動時に Gatekeeper で弾かれる）。
#   - notarization → staple → dmg 化。
#
# 署名なしのローカル検証だけしたい場合は SIGN_IDENTITY を空にすれば
# codesign/notarization をスキップして .app への埋め込みと .dmg 化だけ行う。
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
DIST="${REPO_ROOT}/dist"
APP_NAME="StatsGUI"
APP_BUNDLE="${DIST}/${APP_NAME}.app"

# 署名情報（環境変数で上書き可能）
SIGN_IDENTITY="${SIGN_IDENTITY:-}"                 # 例: "Developer ID Application: Your Name (TEAMID)"
NOTARY_PROFILE="${NOTARY_PROFILE:-}"               # `xcrun notarytool store-credentials` のプロファイル名
ENTITLEMENTS="${REPO_ROOT}/packaging/macos/entitlements.plist"

if [[ ! -d "${APP_BUNDLE}" ]]; then
    echo "ERROR: ${APP_BUNDLE} が無い。先に 'make build-a'（BUNDLE で .app 生成）を実行せよ。" >&2
    exit 1
fi
if [[ ! -x "${DIST}/b_worker/b_worker" ]]; then
    echo "ERROR: ${DIST}/b_worker/b_worker が無い。先に 'make build-b' を実行せよ。" >&2
    exit 1
fi

echo "==> B を Contents/Resources/b_worker/ へ埋め込み"
# B（one-folder）を Resources へ「丸ごと」ネスト埋め込みする。
# B 自身は .app/Contents/MacOS 配下ではなく Resources 配下に置かれるので、
# 起動時は通常の onedir として自分の隣の _internal を解決する（衝突しない）。
rm -rf "${APP_BUNDLE}/Contents/Resources/b_worker"
cp -R "${DIST}/b_worker" "${APP_BUNDLE}/Contents/Resources/b_worker"

if [[ -n "${SIGN_IDENTITY}" ]]; then
    echo "==> codesign（B → A の順で、深いものから署名）"
    # まず B 側の dylib/so、次に B 本体
    find "${APP_BUNDLE}/Contents/Resources/b_worker" -type f \( -name "*.dylib" -o -name "*.so" \) -print0 \
        | xargs -0 -I{} codesign --force --timestamp --options runtime \
            --sign "${SIGN_IDENTITY}" "{}"
    codesign --force --timestamp --options runtime \
        --entitlements "${ENTITLEMENTS}" \
        --sign "${SIGN_IDENTITY}" "${APP_BUNDLE}/Contents/Resources/b_worker/b_worker"

    # 最後にバンドル全体を deep 署名（A の Frameworks/実行ファイルを含む）
    codesign --force --timestamp --options runtime \
        --entitlements "${ENTITLEMENTS}" \
        --sign "${SIGN_IDENTITY}" --deep "${APP_BUNDLE}"

    echo "==> 署名検証"
    codesign --verify --deep --strict --verbose=2 "${APP_BUNDLE}"
else
    echo "==> SIGN_IDENTITY 未設定のため codesign をスキップ（ローカル検証用）"
fi

echo "==> .dmg を作成"
DMG_PATH="${DIST}/${APP_NAME}-0.1.0.dmg"
rm -f "${DMG_PATH}"
hdiutil create -volname "${APP_NAME}" -srcfolder "${APP_BUNDLE}" \
    -ov -format UDZO "${DMG_PATH}"

if [[ -n "${SIGN_IDENTITY}" && -n "${NOTARY_PROFILE}" ]]; then
    echo "==> notarization（.dmg を submit → staple）"
    xcrun notarytool submit "${DMG_PATH}" --keychain-profile "${NOTARY_PROFILE}" --wait
    xcrun stapler staple "${DMG_PATH}"
    xcrun stapler staple "${APP_BUNDLE}"
else
    echo "==> NOTARY_PROFILE 未設定のため notarization をスキップ"
fi

echo "完了: ${DMG_PATH}"
