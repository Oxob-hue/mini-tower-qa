# GitHub 发布指引（MiniTower QA）

> 目标：把 `mini-tower-qa` 推到 GitHub 并让链接可放进简历。
> ⚠ 隐私提醒：仓库若设为 **Public**，请**不要把含个人信息的简历、本机绝对路径放进仓库**；
> 简历保留在本地（仓库外）即可。

## 0. 前置

- 已有 GitHub 账号（没有则注册 github.com，用户名建议简短正式）。
- 本机已装 Git（实测 git 2.55.0）。

## 1. 在 GitHub 上创建仓库（约 1 分钟）

1. 打开 https://github.com/new
2. Repository name：`mini-tower-qa`
3. 设为 **Public**（面试官可匿名查看）
4. 不要勾选 "Add a README / .gitignore / license"（避免与本地冲突）
5. Create repository → 复制页面给的远程地址（HTTPS 形式）：
   `https://github.com/Oxob-hue/mini-tower-qa.git`

## 2. 本地初始化并推第一次

在 PowerShell 执行（工作目录需为项目根）：

```powershell
cd mini-tower-qa

# 1) 初始化并提交（.gitignore 已排除 .venv / results / allure-* 等产物）
git init -b main
git add .
git status                  # 确认没有 .venv、allure-results、*.db 等大目录被加入
git commit -m "MiniTower QA: W1-W6 完整质量保障体系（79 tests, v0.5.1）"

# 2) 关联远程并推送
git remote add origin https://github.com/Oxob-hue/mini-tower-qa.git
git push -u origin main
```

> 首次推送会弹出 GitHub 登录/授权（浏览器），按提示完成即可。
> 如用 Token：生成 classic token（repo 权限）后，远程地址可写作
> `https://<用户名>:<TOKEN>@github.com/<用户名>/mini-tower-qa.git`（用完建议删除缓存）。

## 3. 推送后必做（提高被看到概率）

1. **仓库主页**：Edit → Description 写
   `游戏测试作品集：自研塔防数值引擎 + 79 条可复现测试（功能/数值/概率/性能/AI）+ SQL 反哺调优 + 缺陷闭环`。
2. **Topics**：加 `game-testing` `python` `automation-testing` `allure` `pytest` `数值测试` 等。
3. **README 顶部加"对 JD 对照"锚点**（可选）：把 docs/jd-review.md 的链接放在 README 前 3 行。
4. 复核 **.gitignore 生效**：确认仓库里没有 `.venv/`、`allure-results/`、`allure-report/`、`*.db`。
5. （可选）以后版本更新：`git add . && git commit -m "..." && git push`。

## 4. 简历里怎么写链接

- 放**真实可访问**的地址：`https://github.com/Oxob-hue/mini-tower-qa`
- 链接旁附一句引导：`内含：需求说明书、79 条用例追踪矩阵、缺陷复盘、5 份真实数据报告、演示脚本——全部可复跑`。
- 尚未推送前，简历里只放占位符，**不要放无效链接**。

## 5.（进阶可选）把 Allure 报告发布到 GitHub Pages

Allure 是前后端分离静态站，若直接放 Pages 子路径可能因相对路径加载失败。
推荐方案：本地保持 `allure open` 查看；若要公开，可把报告构建到 `docs/report` 后手工
验证相对路径，或用 GitHub Pages + 根路径部署（Actions 方案后续再配）。
> 简历阶段**不必**公开报告——README + 仓库可复跑命令已足够自证。
