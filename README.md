# MechaPet V0.3

MechaPet 是运行在 Windows 桌面上的透明 Q 版 AI 宠物。V0.3 在 V0.2 的 DeepSeek 聊天、状态互动和气泡能力上，增加了可替换角色包、PNG 序列帧动画和桌面行走系统。

## 启动

环境要求为 Windows 10/11、Python 3.11+（当前开发验证使用 Python 3.13）。进入项目目录后运行：

```powershell
.\.venv\Scripts\python.exe main.py
```

首次安装时运行：

```powershell
py -3.13 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
Copy-Item .env.example .env
notepad .env
```

API Key 只写入被 Git 忽略的 `.env`，不要写进源码。

## 操作

- 左键按住：拖动；拖动会立即停止自动行走
- 左键单击：随机轻量互动
- 左键双击：打开聊天
- 右键：聊天、设置、退出
- 设置：选择或重新加载角色包、打开角色目录
- 只有右键菜单“退出”会彻底结束程序

## 角色包规范

每个角色是 `characters` 下的独立目录：

```text
characters/default/
├─ manifest.json
├─ portrait.png
├─ persona/prompt.txt
└─ sprites/
   ├─ idle/000.png ...
   ├─ blink/000.png ...
   ├─ walk/000.png ...
   └─ ...
```

支持动作：`idle`、`blink`、`walk`、`run`、`talk`、`wave`、`happy`、`curious`、`thinking`、`sad`、`sleepy`。缺少的动作自动回退到 `fallback_animation`，所以只有一张旧版 `pet.png` 也能运行。

所有帧必须为带 Alpha 通道的 PNG，尺寸与 `canvas.width/height` 完全一致，使用相同画布、身体比例和脚底锚点，并按 `000.png`、`001.png`、`002.png` 顺序命名。

示例 `manifest.json`：

```json
{
  "id": "default",
  "name": "默认角色",
  "version": 1,
  "portrait": "portrait.png",
  "canvas": {"width": 512, "height": 512, "anchor_x": 256, "anchor_y": 490},
  "animations": {
    "idle": {"path": "sprites/idle", "fps": 8, "loop": true},
    "walk": {"path": "sprites/walk", "fps": 12, "loop": true}
  },
  "fallback_animation": "idle",
  "persona_prompt": "persona/prompt.txt"
}
```

- `id`：不可重复的角色标识
- `name`：设置窗口显示名称
- `version`：角色包格式版本，当前为 1
- `portrait`：可选头像路径
- `canvas`：统一帧尺寸和脚底锚点
- `animations`：动画目录、FPS 和是否循环
- `fallback_animation`：缺失动作的替代动画
- `persona_prompt`：可选角色性格文本，为后续个性化接口保留

加载器会拒绝绝对路径、越界路径、错误尺寸、无 Alpha、空动画目录和过高 FPS。无效角色包会被跳过，不影响其他有效角色启动。

## 动画与移动

`SpriteAnimator` 使用 Qt `QTimer` 在 GUI 主线程播放帧，不使用阻塞循环。`MovementController` 使用 `QPropertyAnimation` 改变独立的移动坐标；动作偏移不改变角色基准位置，因此循环播放和连续行走不会积累位置误差。角色会自动左右翻转，并按当前屏幕的 `availableGeometry()` 限制移动范围。

## 项目结构

```text
MechaPet/
├─ main.py
├─ app/
│  ├─ character_pack.py       # manifest、安全与素材校验
│  ├─ character_manager.py    # 发现、选择、保存与重新加载
│  ├─ sprite_animator.py      # PNG 序列帧播放器
│  ├─ movement_controller.py  # 行走、跑动、朝向与边界
│  ├─ pet_controller.py       # 行为协调
│  ├─ pet_window.py           # 透明窗口、拖动与菜单
│  ├─ settings_window.py      # 配置和角色选择
│  ├─ chat_window.py          # Markdown 聊天 UI 与 QThread
│  └─ ai_client.py            # DeepSeek 与运行期上下文
├─ characters/default/
├─ assets/pet.png
├─ tests/
├─ .env.example
└─ requirements.txt
```

## 当前素材状态

默认角色包目前只包含由 `assets/pet.png` 兼容生成的一帧 `idle`。所有其他动作可正常请求，但会显示 idle fallback。要获得真正鲜活的动作，需要按相同画布和锚点补充各动作的透明 PNG 序列帧。

本版仍不引入 Live2D、Unity、Electron、语音、数据库、RAG 或 Agent。
