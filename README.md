# MechaPet V0.2

MechaPet 是一只运行在 Windows 桌面上的透明 Q 版 AI 宠物。V0.2 在稳定的聊天能力上增加了状态、轻量动作、待机行为和跟随式回复气泡。

## 已实现

- 无标题栏、无边框、透明背景的桌宠窗口
- PNG Alpha 透明角色，缺失或损坏时显示透明占位角色
- 普通窗口上方置顶，不显示为任务栏普通应用窗口
- 左键拖动，右键菜单（聊天、设置、退出）
- 关闭聊天或设置窗口不会关闭桌宠
- 独立的 DeepSeek 客户端和当前运行期对话上下文
- `QThread` 异步网络请求，不阻塞 PyQt 主线程
- API Key 缺失、无效、限流、超时、网络及响应格式错误处理
- Windows DPI 缩放适配
- `idle/happy/curious/thinking/talking/sad/sleepy` 状态模型
- PNG 轻量呼吸、弹跳、点头、摇头和挥手动作
- 单击随机互动，双击打开已有聊天窗口
- DeepSeek 结构化情绪、动作与回复联动
- 跟随宠物、屏幕边缘自适应并自动消失的回复气泡
- 30～90 秒低频待机随机行为
- 状态素材缓存与 `assets/pet.png` 自动 fallback
- 不记录 API Key 的轮转日志

## 环境要求

- Windows 10/11
- Python 3.11 或更高版本

本项目开发验证使用 Python 3.13.15 和 PyQt6 6.11.0。

## 安装与启动

在 PowerShell 中进入项目目录后执行：

```powershell
py -3.13 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
Copy-Item .env.example .env
notepad .env
.\.venv\Scripts\python.exe main.py
```

如果系统的 `py` 启动器没有识别 Python，可用实际解释器路径创建 `.venv`。本项目当前已经创建好虚拟环境，日常启动只需要最后一条命令。

## DeepSeek 配置

不要把 Key 写入 Python 文件。复制 `.env.example` 为 `.env`，只填写你自己的值：

```dotenv
DEEPSEEK_API_KEY=你的_API_Key
DEEPSEEK_BASE_URL=https://api.deepseek.com
DEEPSEEK_MODEL=deepseek-v4-flash
```

`.env` 已被 `.gitignore` 忽略。设置窗口只显示“已配置/未配置”，绝不会显示 Key 内容。修改 `.env` 后需要重启程序才能重新载入配置。

## 使用方法

- 左键按住宠物：拖动位置
- 左键单击宠物：触发一次轻量互动
- 左键双击宠物：打开聊天
- 右键宠物：打开菜单
- 聊天：打开或重新聚焦聊天窗口
- 设置：查看 API 和模型配置状态
- 退出：彻底结束程序

点击聊天窗口的关闭按钮只会隐藏聊天窗口。只有宠物右键菜单中的“退出”会结束整个程序。

## 项目结构

```text
MechaPet/
├─ main.py                 # 程序入口与 QApplication 生命周期
├─ app/
│  ├─ __init__.py
│  ├─ pet_window.py        # 透明桌宠、拖动和右键菜单
│  ├─ pet_controller.py    # 状态、动作、AI 与气泡协调
│  ├─ pet_state.py         # 宠物状态模型
│  ├─ resource_manager.py  # 状态素材缓存和 fallback
│  ├─ action_controller.py # 非阻塞 PNG 位移动画
│  ├─ behavior_controller.py # 低频待机行为
│  ├─ speech_bubble.py     # 跟随式回复气泡
│  ├─ chat_window.py       # 聊天 UI 和 QThread 工作线程
│  ├─ ai_client.py         # DeepSeek 请求与运行期上下文
│  ├─ ai_response.py       # 结构化回复及健壮 JSON 解析
│  ├─ config.py            # .env 配置加载
│  └─ settings_window.py   # 不暴露密钥的配置状态窗口
├─ assets/
│  └─ pet.png              # 带 Alpha 通道的 Q 版角色
├─ .env.example
├─ .gitignore
├─ requirements.txt
└─ README.md
```

## V0.2 边界与后续方向

此版本不包含 Live2D、语音、数据库、长期记忆、RAG 或 Agent。后续可在不改动窗口主干的前提下，分别增加角色渲染器、语音服务、记忆仓库和工具调用层。

## 常见问题

- 宠物显示占位图：确认 `assets/pet.png` 存在且是有效 PNG。
- 聊天提示未配置 Key：确认项目根目录存在 `.env`，然后重启 MechaPet。
- 网络错误：检查网络、DeepSeek 服务状态以及防火墙设置。
- 退出后仍想启动：再次运行 `.\.venv\Scripts\python.exe main.py`。
