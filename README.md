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

4.  **启动**:
    ```bash
    python bot.py
    ```

## 指令

以下指令仅超级用户可用：

*   `/add_bot <qq>` 或 `/add_bot @机器人`: 添加机器人到监控列表。
*   `/del_bot <qq>` 或 `/del_bot @机器人`: 从监控列表移除机器人。
*   `/list_bots`: 查看当前监控列表。

## 原理

插件监听群消息，当检测到发送者和 @ 对象都在监控列表中时，记录一次交互。如果短时间内（30秒）交互次数超过阈值（3次），则判定为互怼循环，并禁言发送者。
