"""Focused regression checks for the Qt-native chat Markdown display."""

import os
import sys
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from PyQt6.QtWidgets import QApplication

from app.chat_window import ChatWindow


def fragment_format(chat: ChatWindow, needle: str):
    block = chat.history.document().begin()
    while block.isValid():
        iterator = block.begin()
        while not iterator.atEnd():
            fragment = iterator.fragment()
            if needle in fragment.text():
                return fragment.charFormat()
            iterator += 1
        block = block.next()
    raise AssertionError(f"Rendered fragment not found: {needle}")


def main() -> None:
    app = QApplication.instance() or QApplication([])
    chat = ChatWindow(fake_reply=True)
    markdown = """我记住了：**9527**

这是 *测试文字*

运行 `python main.py`

今天可以做：

- 理论力学
- 材料力学
- 流体力学

1. 第一点
2. 第二点

```python
print("Hello MechaPet")
```

<script>alert('blocked')</script>"""
    chat.show_reply(markdown)

    plain = chat.history.toPlainText()
    html = chat.history.document().toHtml()
    bold_format = fragment_format(chat, "9527")
    italic_format = fragment_format(chat, "测试文字")
    inline_code_format = fragment_format(chat, "python main.py")
    checks = {
        "bold_rendered": (
            "**9527**" not in plain and bold_format.fontWeight() >= 700
        ),
        "italic_rendered": (
            "*测试文字*" not in plain and italic_format.fontItalic()
        ),
        "inline_code_rendered": (
            "`python main.py`" not in plain
            and (
                inline_code_format.fontFixedPitch()
                or "mono" in " ".join(inline_code_format.fontFamilies() or []).lower()
            )
        ),
        "unordered_list_rendered": "<ul" in html and "理论力学" in plain,
        "ordered_list_rendered": "<ol" in html and "第一点" in plain,
        "code_block_rendered": "print(&quot;Hello MechaPet&quot;)" in html,
        "raw_html_not_executed": "<script>" not in html.lower(),
        "role_labels_preserved": "MechaPet：" in plain,
    }
    for name, passed in checks.items():
        print(f"{name}={passed}")
    if not all(checks.values()):
        raise SystemExit("Markdown display regression check failed")

    del chat
    app.processEvents()


if __name__ == "__main__":
    main()
