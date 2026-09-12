# L3 异地开发指南

本仓库属于 [CodePick 四层平台](https://github.com/jayson2hu/codepick-docs)。建议四个代码仓库保持同级目录，以便查阅关联实现；每个项目使用独立虚拟环境。

## 克隆与环境

需要 Git 和 Python 3.11 或更新版本。以下命令都从本仓库根目录执行。

```sh
git clone https://github.com/jayson2hu/pickblog.git
cd pickblog
python -m venv .venv
```

激活环境：Windows PowerShell 使用 `.venv\Scripts\Activate.ps1`；macOS/Linux 使用 `source .venv/bin/activate`。随后执行：

```sh
python -m pip install -e ".[dev]"
python scripts/l3_smoke.py
python scripts/run_reader_api.py
```

## 当前运行模式

后端 API 默认在独立开发模式运行，使用 L2 stub、沙箱计费和 mock 邮件。`.env.example` 是配置参考，真实配置自行保存在未跟踪的 `.env` 或进程环境变量中，按各启动入口说明加载。

前端需要 Node.js 20 或更新版本，在另一个终端运行：

```sh
cd apps/reader-web
npm ci
npm run dev
```

前端检查：`npm run typecheck`。完整交接验证：先在前端目录执行 `npx playwright install chromium`，再回仓库根目录运行 `python scripts/l3_verify.py`。真实 L2、支付、邮件和基础设施联调的门禁见 docs/L3-final-integration-checklist.md。

## 交接范围

提交包括当前源码、测试、迁移、配置示例与项目文档。依赖目录、构建产物、本地数据库、采集运行数据、日志和凭据不随仓库分发，需要在新环境重新安装或配置。

各层状态与验收证据见项目 README 和 docs；本文提供恢复开发的入口，不代表本次发布重新完成生产环境验收。
