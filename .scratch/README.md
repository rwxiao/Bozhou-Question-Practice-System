# 本地任务与工作资料

每个功能使用一个目录：`.scratch/<feature-slug>/`。

```text
.scratch/<feature-slug>/
├── spec.md              # 需求、范围和验收标准
├── notes.md             # 调研、参考链接和待解决问题
├── assets/              # 该功能需要的附件
└── issues/
    └── 01-<slug>.md     # 每个实施任务单独一个文件
```

以上文件按需创建，不必提前生成空文件。任务顶部记录 `Status: open`、`Status: claimed` 或 `Status: resolved`，讨论追加到 `## Comments` 下。

通用刷题网站可按题库、练习会话、错题复习等实际功能划分目录；这些只是命名示例，不代表已确定产品范围。

长期维护的产品设计、API、数据库和验证资料放在 `docs/`；截图放在 `docs/screenshots/`。领域术语和架构决策的位置分别为根目录 `GLOSSARY.md` 与 `docs/adr/`，在有实际内容时创建。

完整任务约定见 [issue-tracker.md](../docs/agents/issue-tracker.md)，领域文档规则见 [domain.md](../docs/agents/domain.md)。
