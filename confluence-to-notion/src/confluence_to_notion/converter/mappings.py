"""Confluence → Notion 変換で使う定数マップ"""

# Confluence コードブロック言語名 → Notion API 言語名
# Notion が受け付ける言語: https://developers.notion.com/reference/block#code
NOTION_SUPPORTED_LANGUAGES = {
    "abap", "arduino", "bash", "basic", "c", "clojure", "coffeescript",
    "c++", "c#", "css", "dart", "diff", "docker", "elixir", "elm",
    "erlang", "flow", "fortran", "f#", "gherkin", "glsl", "go", "graphql",
    "groovy", "haskell", "html", "java", "javascript", "json", "julia",
    "kotlin", "latex", "less", "lisp", "livescript", "lua", "makefile",
    "markdown", "markup", "matlab", "mermaid", "nix", "objective-c", "ocaml",
    "pascal", "perl", "php", "plain text", "powershell", "prolog", "protobuf",
    "python", "r", "reason", "ruby", "rust", "sass", "scala", "scheme",
    "scss", "shell", "sql", "swift", "typescript", "vb.net", "verilog",
    "vhdl", "visual basic", "webassembly", "xml", "yaml", "java/c/c++/c#",
}

LANGUAGE_ALIASES = {
    "none": "plain text",
    "text": "plain text",
    "sh": "shell",
    "bash": "bash",
    "zsh": "shell",
    "js": "javascript",
    "ts": "typescript",
    "py": "python",
    "rb": "ruby",
    "rs": "rust",
    "go": "go",
    "cs": "c#",
    "cpp": "c++",
    "c++": "c++",
    "objc": "objective-c",
    "ps1": "powershell",
    "powershell": "powershell",
    "dockerfile": "docker",
    "yml": "yaml",
}


def normalize_language(lang: str | None) -> str:
    if not lang:
        return "plain text"
    lang = lang.lower().strip()
    if lang in LANGUAGE_ALIASES:
        return LANGUAGE_ALIASES[lang]
    if lang in NOTION_SUPPORTED_LANGUAGES:
        return lang
    return "plain text"


# Confluence 情報パネル系マクロ → Notion callout カラー
COLOR_MAP: dict[str, str] = {
    "info": "blue_background",
    "tip": "green_background",
    "note": "yellow_background",
    "warning": "red_background",
    "panel": "gray_background",
}

# Confluence 情報パネル系マクロ → callout アイコン絵文字
EMOJI_MAP: dict[str, str] = {
    "info": "ℹ️",
    "tip": "💡",
    "note": "⚠️",
    "warning": "🚨",
    "panel": "📋",
}

# Notion 非対応マクロ（警告 callout に変換）
UNSUPPORTED_MACROS: set[str] = {
    "toc",
    "pagetree",
    "livesearch",
    "taskreport",
    "page-index",
    "recently-updated",
    "breadcrumbs",
    "excerpt",
    "excerpt-include",
    "anchor",
}

# Notion テキストカラー（Confluence のカラー値を最近傍マッピング）
NOTION_TEXT_COLORS = {
    "red", "orange", "yellow", "green", "blue", "purple", "pink",
    "gray", "brown",
    "red_background", "orange_background", "yellow_background",
    "green_background", "blue_background", "purple_background",
    "pink_background", "gray_background", "brown_background",
}
