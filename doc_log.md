# 项目更改日志

## 2024-03-21
- 将 README.md 从中文翻译成英文
- 将 doc_Structure_Description.md 从中文翻译成英文
- 更新项目文档以保持所有文件的一致性
- 将 `安装程序.spec` 重命名为 `installer_cn.spec` 以更好地支持国际化

## 2024-03-22
- 将 doc_Structure_Description.md 的详细内容整合到 docs/ARCHITECTURE.md 中
- 更新了架构文档，添加了详细的目录结构说明
- 保持了文档的一致性和完整性

## 2024-03-29
- 重构了构建系统的目录结构
  - 将 `build_logs` 目录移入 `build` 目录
  - 将 `dist` 目录移入 `build` 目录
  - 创建 `specs` 目录统一管理所有 `.spec` 文件
  - 将 `ai_review.spec` 和 `installer.spec` 移入 `build/specs` 目录
- 更新了 `build_all.py` 和 `installer.spec` 以适应新的目录结构
- 使用绝对路径处理资源文件，提高了构建过程的可靠性
- 更新了项目结构文档以反映这些更改
