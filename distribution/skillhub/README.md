# 腾讯SkillHub提交准备

目标平台为 https://skillhub.cn ，API为 https://api.skillhub.cn 。不要混用讯飞或其他同名SkillHub的CLI、账号和发布协议。

状态：候选包0.1.22已准备；尚未认证、提交或上架。WorkBuddy审核独立进行，OpenAI上架仍暂停。

构建：`python scripts/build_skillhub.py`，产物为`dist/china-overseas-tax-skillhub-0.1.22.zip`。作者Kevin，名称“境外券商投资税额测算”，沿用MIT许可及已有共享规则；不含客户账单、凭据、收费推广、平台后端或自动发信工具。

## 已核实的发布路径

2026-10-18从官网安装入口读取官方分发包，CLI版本为2026.8.5。官方程序支持`publish <目录或ZIP> --dry-run --json`：预检只校验元数据，不发起发布请求；实际发布使用个人Token，经鉴权调用`POST /api/v1/community/skills/publish`。元数据要求slug、version和displayName，另支持summary、description、tags、license、homepage。

官方CLI下载到维护项目的`tools/skillhub-cli/`，不提交到GitHub；未安装同名npm包、浏览器插件或修改全局环境。未来使用须以官网实际分发版本为准。

## 必须由用户协助的账号环节

登录官网并完成其要求的认证及协议。个人中心若提供个人API Token，可在本机运行官方`login`保存；不要将Token贴到聊天、截图或仓库，也不要公开上传凭据。命令行登录需要`skh_`开头的个人Token；当前CLI不提供扫码登录命令。企业或其他平台Token不可替代。

本机尚未发现SkillHub个人登录凭据。拿到已验证的本机登录后，先运行`auth whoami`核对身份，再执行发布；依据返回的实际status和publicUrl区分待审核、发布失败和已公开，不能只因HTTP成功就宣称上架。认证或条款不明确时交由用户完成，不绕过限制。

官网若提供网页上传或GitHub导入，也可按实际页面执行。作者邮箱展示、服务类目及个人税务工具资格尚未取得平台明确结论；如平台提出额外要求应如实处理，不改名隐瞒能力。

## 官方来源

- https://github.com/Tencent/skillhub
- https://raw.githubusercontent.com/Tencent/skillhub/main/README.md
- https://skillhub.cn/install/install.sh

官方仓库自身MIT许可不等于已核实平台全部发布条款；正式发布前以登录后实际协议为准。

本次官方CLI dry-run已通过，包内容哈希及共享计算代码一致性已核验。实际执行`auth whoami`确认尚未登录；尚无发布请求。

2026-10-19：规则更新候选0.1.23，加入合理推算优先及固定年度主表；已提交0.1.22的审核状态不变，本次不自动重新提交或撤回。

2026-10-19到账口径更新：普通版0.1.22、WorkBuddy/SkillHub候选0.1.24、Codex候选1.0.0-rc.4。默认不还原税前股息，独立税前抵免路径与到账参考测算分开；已提交市场旧包不自动更新。

2026-10-19激励股规则更新：普通版0.1.23、WorkBuddy/SkillHub候选0.1.25、Codex候选1.0.0-rc.5。禁止仅据“免费/成本0”采用零税务成本主结果；主动重建取得时点价值，取得薪酬单列。此前待审提交不自动改变。
