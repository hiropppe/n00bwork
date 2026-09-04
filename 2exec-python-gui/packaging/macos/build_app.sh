#!/usr/bin/env bash
# macOS: A.app に b_worker を埋め込み、codesign + notarization して .dmg にする。
#
# 前提: Makefile の build-b → build-a を実行済み。
#   dist/app_a/  … PyInstaller one-folder の A（app_a 実行ファイル + PySide6）
#   dist/b_worker/ … PyInstaller one-folder の B（b_worker + numpy）
#
# 方針:
#   - PyInstaller one-folder の A を .app バンドル構造に組み替え、
#     b_worker を Contents/Resources/ に埋め込む。
#     （A の paths.py は frozen 時 Contents/Resources/b_worker を探す）
#   - A・B 両方を codesign（片方だけだと B 起動時に Gatekeeper で弾かれる）。
#   - notarization → staple → dmg 化。
#
# 署名なしのローカル検証だけしたい場合は SIGN_IDENTITY を空にすれば
# codesign/notarization をスキップして .app / .dmg の組み立てだけ行う。
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
DIST="${REPO_ROOT}/dist"
APP_NAME="StatsGUI"
APP_BUNDLE="${DIST}/${APP_NAME}.app"

# 署名情報（環境変数で上書き可能）
SIGN_IDENTITY="${SIGN_IDENTITY:-}"                 # 例: "Developer ID Application: Your Name (TEAMID)"
NOTARY_PROFILE="${NOTARY_PROFILE:-}"               # `xcrun notarytool store-credentials` のプロファイル名
ENTITLEMENTS="${REPO_ROOT}/packaging/macos/entitlements.plist"

echo "==> A.app バンドルを組み立て"
rm -rf "${APP_BUNDLE}"
mkdir -p "${APP_BUNDLE}/Contents/MacOS"
mkdir -p "${APP_BUNDLE}/Contents/Resources"

# A（one-folder）の中身を Contents/MacOS/ へ
cp -R "${DIST}/app_a/." "${APP_BUNDLE}/Contents/MacOS/"

# B（one-folder）を Contents/Resources/ へ丸ごと埋め込む。
# paths.py は Contents/Resources/b_worker（実行ファイル）を探すので、
# b_worker one-folder の中身を Resources 直下に展開する。
cp -R "${DIST}/b_worker/." "${APP_BUNDLE}/Contents/Resources/"

# Info.plist
cat > "${APP_BUNDLE}/Contents/Info.plist" <<PLIST
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>CFBundleName</key><string>${APP_NAME}</string>
    <key>CFBundleDisplayName</key><string>Stats GUI</string>
    <key>CFBundleIdentifier</key><string>work.n00b.statsgui</string>
    <key>CFBundleVersion</key><string>0.1.0</string>
    <key>CFBundleShortVersionString</key><string>0.1.0</string>
    <key>CFBundlePackageType</key><string>APPL</string>
    <key>CFBundleExecutable</key><string>app_a</string>
    <key>LSMinimumSystemVersion</key><string>11.0</string>
    <key>NSHighResolutionCapable</key><true/>
</dict>
</plist>
PLIST

if [[ -n "${SIGN_IDENTITY}" ]]; then
    echo "==> codesign（A・B 両方に署名。B → A の順で深いものから）"
    # まず B の実行ファイルと dylib に署名
    find "${APP_BUNDLE}/Contents/Resources" -type f \( -name "*.dylib" -o -name "*.so" \) -print0 \
        | xargs -0 -I{} codesign --force --timestamp --options runtime \
            --sign "${SIGN_IDENTITY}" "{}"
    codesign --force --timestamp --options runtime \
        --entitlements "${ENTITLEMENTS}" \
        --sign "${SIGN_IDENTITY}" "${APP_BUNDLE}/Contents/Resources/b_worker"

    # 次に A の dylib と実行ファイル、最後にバンドル全体を deep 署名
    find "${APP_BUNDLE}/Contents/MacOS" -type f \( -name "*.dylib" -o -name "*.so" \) -print0 \
        | xargs -0 -I{} codesign --force --timestamp --options runtime \
            --sign "${SIGN_IDENTITY}" "{}"
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
