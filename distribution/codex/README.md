# OpenAI 目录提交候选版

当前候选：1.0.0-rc.6，基于普通版0.1.23。发布者展示名Kevin；实际目录开发者名称由上传时选择的已验证身份决定。尚未提交或获批。

本包是需要本地执行的skills-only插件，无MCP、hooks、遥测或作者后台。保留到账股息参考测算、独立税前抵免情景、员工激励股取得薪酬与后续卖出成本区分、年度固定汇总表。支持入口只在指定阶段或实际求助时展示，不以人工支持替代自助功能，外发邮件须由用户明确授权。

隐私、支持和使用条件已经提供公开GitHub页面，清单列出对应HTTPS地址；政策适用于该候选包，不代表官方已认可。人工支持结束后30日内删除不再必要的附件和工作副本，由发布者落实。

## 构建和检查

在仓库根运行 `python scripts/build_official.py`。同名ZIP存在时停止防覆盖。包内只含白名单文件、合成数据和逐文件散列，不包含真实客户账单或本机路径；共享算术脚本不作渠道改写。

解压后可在 `skills/china-overseas-tax-skill` 下运行 `python -m unittest discover -s tests`。封装静态检查和合成数据测试不能证明AI完整工作流、税法适用或平台安装成功。PDF/Excel/OCR依赖执行平台工具，未验证所有格式。干净桌面安装、换设备及扩展案例验证尚未完成，不能宣称已完成端到端验收。

## 上传前后边界

用户于2026-10-20报告身份审核通过，尚未由本仓库核验后台权限。上传后仍需等待技能扫描、处理实际错误并完成平台声明；只有平台审核通过后才能发布。桌面执行标记保留，不通过删除标记假装支持网页或手机执行。若后台不允许该标记，应按官方文档确认组织提交资格。

本次预检不替用户上传、提交审核或发布，也不更新WorkBuddy/SkillHub已提交版本。

## 官方依据（2026-10-20核对）

- [插件封装](https://developers.openai.com/plugins/build/plugins)
- [提交字段与流程](https://developers.openai.com/plugins/deploy/submission)
- [本地执行要求](https://developers.openai.com/plugins/deploy/desktop-only)
- [隐私、商业及质量规则](https://developers.openai.com/plugins/plugin-guidelines)

skills-only无需MCP审查的测试账号和演示视频；仍适用公开隐私政策、真实功能、数据最小化和技能安全扫描要求。提供邮箱不代表允许广告引流或未经授权发送资料。
