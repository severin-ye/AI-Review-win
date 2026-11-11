# 发布通用检查与产品验收

个人 AGENTS、Skill、Router 保持主导；本项目所选发布通用检查由已安装 gstack 的 `gstack-evidence run --reuse` 执行，再用明确 label 和 `--expect-cmd` 调用 `check --max-age 24`。`scripts/gstack-check.ps1` 只做 Windows 调用边界，不维护凭据算法、成功账本或自动重试；缺失工具或凭据不允许回退直接通过。默认 `%USERPROFILE%/.codex/skills/gstack/bin/gstack-evidence`，可用 `GSTACK_EVIDENCE` 明确指定已安装工具，要求已有 Bun。Windows PowerShell 编码命令保留路径和引号；原生 Bun 使用 `--no-env-file --config=NUL`。复用按 gstack 自身命令、工作树、环境和有效期规则，可能增加重跑；run与check均明确使用24小时有效期。

`scripts/finalize-delivery.ps1` 将类型、客户端许可证、Python授权服务测试、边界检查交给gstack。`-SkipValidation` 的旧语义曾跳过通用检查和产品烟测；现在仅以 check-only 核验已有通用凭据，任一缺失/过期即阻断，不执行通用命令；产品 package-smoke 始终执行。必要交付文件、禁止.data、版本/说明、ZIP条目/可读性与SHA256仍保留；通用测试不能替代真实产品验收。

定向工具回归：`powershell -NoProfile -File tests/gstack-release.test.ps1`；`-Integration` 仅在隔离工作副本创建.agent-status内小型Git/Bun夹具，验证官方evidence成功、复用、失败与check-only缺失拒绝，不安装/发布/访问用户数据。夹具保留由创建者交接，不上传。
