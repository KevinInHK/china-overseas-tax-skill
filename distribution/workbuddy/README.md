# WorkBuddy 提交准备

状态：基于普通版0.1.20的独立提交候选，版本0.1.20。尚未安装验证、提交审核或上架；个人主体类目及支持邮箱展示规则待平台确认。普通版和Codex候选包不受影响。

## 可填写的展示信息

- 中文名称：券商投资税务助手
- 英文名称：Overseas Brokerage Tax Assistant
- 作者展示名：Kevin（实名认证使用本人真实信息，不用昵称代替）
- 中文简介：整理境外券商账单与历史成本，测算中国大陆税收居民的投资所得和参考税额，解释CRS差异及股息扣税。
- 英文简介：Review overseas brokerage statements and cost basis, estimate investment income and tax for Chinese mainland tax residents, and explain CRS differences and dividend withholding.
- 使用方式：免费。不开通收入变现；不展示价格或付费升级。
- 项目主页：https://github.com/KevinInHK/china-overseas-tax-skill
- 隐私说明：https://github.com/KevinInHK/china-overseas-tax-skill/blob/main/PRIVACY.md
- 支持邮箱：china_overseas_tax@163.com
- 分类：待平台确认个人主体的实际适用类目，不擅自选择税务机关或税务师事务所类目，也不通过改名规避审核。

## 使用示例

1. 帮我核算2025年境外券商投资所得，先说明需要准备哪些账单。
2. 券商给我的分红扣了税，帮我解释扣税并整理抵免所需资料。
3. 对照我转述的CRS合计与年度账单，说明可以确认的差异。
4. 账单处理遇到问题，帮我准备一封联系作者的脱敏咨询邮件。

## 包和能力边界

在仓库根运行 `python scripts/build_workbuddy.py`，生成 `dist/china-overseas-tax-workbuddy-0.1.20.zip`。ZIP内是单一技能目录，包含必填中英文描述、作者及版本元数据、共享规则、脚本、隐私和支持资料。不包含OpenAI插件清单、客户文件、本机路径、邮箱凭据或独立邮件服务。

不关闭模型自动调用，不限定不存在的工具权限；Python、文件读取、OCR、网络及邮件工具是否可用以WorkBuddy实际环境为准。静态检查不等于客户端验证或平台审核。候选保留普通版支持入口规则，平台尚未确认其展示要求；后续仅按真实反馈调整，不假称已获许可。

## 提交顺序

1. 本人登录开放平台完成个人主体认证；身份证、人脸、手机号等由本人向官方提交，不提交到本仓库。
2. 先确认个人工具适用类目及邮箱入口规则，可使用[运营咨询草稿](operations-inquiry.md)。该草稿未发送。
3. 创建技能、上传候选ZIP，核对解析结果和平台必填字段；如有额外条件，以实际页面为准。
4. 在WorkBuddy可用环境做实际预览及主要流程验证，再提交审核；本次未执行此前暂缓的换环境和扩展案例测试。
5. 审核通过后再发布，不将本地导入成功描述为市场上架。

## 官方依据（2026-10-18查阅）

- [开放平台流程](https://open.workbuddy.cn/docs)
- [技能目录与元数据](https://open.workbuddy.cn/docs/skill)
- [个人主体认证](https://open.workbuddy.cn/docs/onboarding)
- [服务类目与资质说明](https://open.workbuddy.cn/docs/service-categories-enterprise)

公开文档未明确本工具的个人类目归属及作者邮箱展示限制；不能把“未找到限制”解读为已获批准。
