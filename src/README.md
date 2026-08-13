# LingJi `src/` 主线

`src/` 是 LingJi 长期正式能力主线。新的正式 Runtime、记忆、检索、采集、权限、任务、模型、存储和 Autopilot 能力默认进入这里；兼容目录不得演化成第二套正式产品。

## 边界

- 永久记忆正文以 Obsidian Vault + Git 为权威。
- `lingji_state.db` 只保存运行状态；`lingji_memory.db` 与 Qdrant 必须可重建。
- Desktop/Tauri 通过本地 Control API 使用 `src` 能力，不直接访问数据库或向量存储。
- Production 与 Acceptance 必须物理隔离。
- Secret 只保存在操作系统安全凭据存储中；仓库只允许同步脱敏认证状态。
- Autopilot 只执行已明确允许的低风险自动动作；永久记忆、真实正文授权和不可逆操作继续由用户决定。

## 发布约束

macOS 与 Windows 共用同一 `src` 主线。最终双平台 Artifact 必须绑定同一精确产品 Commit，并通过各自正式发行 Gate 后才能进入真机验收。
