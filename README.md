# Fuck Off Bots

这是一个基于 NoneBot2 和 OneBot V11 的 QQ 机器人，用于管理群内的其他第三方机器人，防止它们因为互相 @ 而产生无限循环对话。

## 功能

*   **监控列表管理**: 只有在监控列表中的机器人互相 @ 才会触发检测。
*   **循环检测**: 如果监控列表中的机器人在短时间内频繁互相 @，将被判定为死循环。
*   **自动禁言**: 触发死循环的机器人将被自动禁言 10 分钟。

## 安装与配置

1.  **环境要求**: Python 3.9+
2.  **安装依赖**:
    ```bash
    pip install -r requirements.txt
    # 或者如果使用 pdm/poetry
    pdm install
    ```
    (本项目目前使用 `pyproject.toml` 管理依赖，可直接运行 `pip install nonebot2[fastapi] nonebot2[websockets] nonebot-adapter-onebot`)

3.  **配置**:
    修改 `.env` 文件：
    *   `PORT`: NapCat 的 WebSocket 端口（默认 8080）。
    *   `SUPERUSERS`: 超级用户 QQ 号列表，用于管理机器人列表。
    *   `ENABLED_GROUPS`: (可选) 启用的群号列表，例如 `["12345678", "87654321"]`。如果不设置或留空，则在所有群生效。

4.  **启动**:
    ```bash
    python bot.py
    ```

## 指令

以下指令仅超级用户可用，且仅在启用的群聊中有效（如果设置了 `ENABLED_GROUPS`）：

*   `/add_bot <qq>` 或 `/add_bot @机器人`: 添加机器人到监控列表。
*   `/del_bot <qq>` 或 `/del_bot @机器人`: 从监控列表移除机器人。
*   `/list_bots`: 查看当前监控列表。
*   `/update`: 更新机器人代码（自动执行 git pull，不会覆盖 .env 和 bots.json）。

## 原理

插件监听群消息，对监控列表中的机器人进行以下检测：

1.  **互怼检测**：当机器人 @ 或回复另一个监控列表中的机器人时，记录一次交互。如果短时间内（30秒）交互次数超过阈值（2次），判定为互怼。
2.  **刷屏检测**：如果机器人在短时间内（30秒）发送超过阈值（5条）的任意消息（无论是否 @），判定为刷屏。

触发任一条件后，发送者将被自动禁言 10 分钟，并**自动撤回**触发检测的相关消息。

## 高级配置

可以在 `.env` 文件中自定义以下参数（不配置则使用默认值）：

```properties
# 历史记录窗口（秒）
HISTORY_WINDOW=240
# 检测时间窗口（秒）
DETECTION_WINDOW=30
# 互怼阈值（次数）
INTERACTION_THRESHOLD=2
# 刷屏阈值（条数）
SPAM_THRESHOLD=5
# 禁言时长（秒）
BAN_DURATION=600
```
