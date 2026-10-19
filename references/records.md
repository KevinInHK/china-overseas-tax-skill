# 内部记录与辅助计算

客户不需要读本文件。模型理解账单后自行形成记录；来源定位、缺口及经济实质比表头匹配更重要。

用法：`python scripts/calculate.py INPUT.json --out RESULT.json`

查看`examples/synthetic-ledger.json`。所有金额和数量用十进制字符串，避免浮点丢失。配置：year，fx（每种币种的人民币/原币报价），fx_basis，capital_netting（per_disposal或country_year），netting_basis（后者必需），tax_rate（核验后的分类所得税率）。

每条事件有唯一id、ISO date、account、asset、currency、source（file和locator）、reviewed=true。日期先后同日由输入顺序确定；模型须以成交时间/序号验证顺序。

事件类型：
- buy/sell：数量quantity、税前成交amount、交易fees；金额与费用均正值且未重复扣。
- short/cover：卖空开仓/买回平仓，字段同上。
- split：factor改变股数，不改变总成本。
- transfer：quantity、to_account；配对转仓，保留批次及原始成本。
- dividend：amount默认是结单实际到账金额，config.dividend_basis=statement_net（程序默认）；可带amount_basis=statement_net。interest：amount按结单利息收入原始标签，不能混入股息。独立税前/抵免场景显式dividend_basis=gross，股息amount须为有依据的税前金额。
- withheld：amount、income_id、income_year、country、eligible=true、evidence（非空文字，说明凭证文件及位置）。链接目标年度被核算的收入/处置；扣税的法律性质、来源国与凭证资格由你核验。
- refund：amount、withholding_id；可发生次年，关联扣税而非当期收入。超过扣税原额是矛盾，不当零处理。
- 其他kind或reviewed=false：进入待复核。后续同账户资产的成本关联处置不可确认。

sell/cover/dividend/interest还需核验所得country和tax_category（capital或income）；产品的基础经济行为可确定时，按披露的方法记录tax_category。来源国暂未确定且只做未抵免测算时，credit_mode=deferred可用country=UNRESOLVED作明确待确认分组，不虚构国家，也不将其视为抵免国家；正式抵免前必须替换为有依据的来源国。境内来源或无法辨认本金和所得时另审。

输出是conditions、已完成处置及批次匹配、分国已核算税额、review队列、未结持仓。status=needs_data时禁止输出金额；ready也表示输入记录核算完成，不代表所有客户账户或纳税凭证已获税局认可。

可通过其他可验证计算方式处理helper暂不支持的产品，但清楚标注所用方法，不将工具的输入限制转嫁给客户。

完整性前置字段：completeness={verified:true, scope:客户约定范围, basis:覆盖与证据核验依据, gaps:[]}。由AI完成实际核验后填入，客户无需填表。不得以只选已知记录冒充完整范围。缺少确认或有复核项时status=needs_data，输出仅含缺口，不含计算结果。

对外解释conditions时必须列出fx每币种实际值及人民币/原币报价方向、fx_basis中的日期、来源和原因；明确成本方法为FIFO。不得仅显示JSON字段或笼统说年末汇率。另一个成本方法须另用经验证计算实现。

汇率复用记录至少保存year、filing_context、basis_date、status（拟用/最终）、rates（currency/value/quote_direction/publication_date/source）、selection_reason、cost_method、exceptions。补资料回答复用完整记录，不遗漏已核验数值；此记录与客户完整性门槛独立，不解锁税额输出。

0.1.6完整性含义更新：completeness审查核心交易与收入范围。credit_mode=deferred跳过境外抵免计算，允许核心齐全时输出base_ready和未抵免基础税额；缺失扣税凭证不能被填零或伪装verified。最终补缴额须等抵免核验。此前将全部抵免缺口一起拦截的规定已被替代。

0.1.7测算门槛：基础身份/范围、交易、真实成本费用、结单实际到账收入齐全即同轮交付报告；产品全名等非必要缺口放报告后。completeness审查原始数字与覆盖，不要求所有产品元数据已完善。分类或处理假设在报告明确披露，不将假设记成已证明事实。

0.1.8：capital_netting默认broker_year；credit_mode默认deferred。每事件broker统一券商主体，同券商账户跨账户年度互抵，不跨券商。输出brokers含全年卖出额、已实现对应收入、成本费用、净所得及税额；两种销售额不一致须解释开仓/平仓及期间差异。broker_year抵免必须另完成分国限额与基数分配核验，不复用逐笔或分国净额生成的抵免结果。

现有calculate.py会拒绝country=CN的境外所得辅助计算。已查明的来源事实不得为通过工具改成其他国家或UNRESOLVED；默认完整账户归集涉及此类产品时，保留事实并用另行可核验的十进制计算完成披露的账户范围测算，同时说明正式申报适用差异。不得让辅助工具限制变成静默删掉产品或亏损的理由；该测算不能冒充已确认的境外来源或分国抵免结果。

## 普通逾期滞纳金辅助工具

`python scripts/late_fees.py INPUT.json [--out RESULT.json]`；省略out只输出到终端，不落盘。标准库，无需新依赖；与年度FIFO计算分开，不能把年度辅助结果直接当已核定未缴本金。AI解释事实后自行映射输入，客户不用填JSON。

可运行合成例：`python scripts/late_fees.py examples/synthetic-late-fees.json`。示例日期和金额只用于验证，不得复用为客户事实或默认截止日。

输入字段：tax_principal_rmb（尚未减下列缴款的本项人民币本金总额，十进制字符串、分位精度）；principal_status（verified或assumed_before_credit，后者为明确未抵免假设情景）；principal_basis（本金及抵免依据）；due_date、due_date_basis（期限及来源）；as_of_date（实际截至日）；applicability=ordinary、applicability_basis（已核验的一般逾期适用依据）；payment_history_basis（缴款历史覆盖或客户明确未缴陈述来源）；payments（明确为空表示该范围无缴款，否则每条date、principal_rmb、source）。缴款仅包含分配到该项本金的部分，不含滞纳金；不同期限分开调用。假设情景必须在依据中明示未核实事实，不能以假设规避已知付款或抵免。

日期YYYY-MM-DD，金额不接受浮点、负数及非有限值。工具拒绝未来付款和超本项本金缴款；payments缺失不默认为无付款。依据缺失或非ordinary返回needs_confirmation，不含估算金额；工具不自动裁定适用例外。estimate仍是算术估算，不是税局核定；scenario_estimate更须按假设情景对外标注。

输出分段起止、本金、天数、精确及显示滞纳金、总计、剩余本金及逾期后每日增量。缴款当天先计费再减本金，同日多次缴款只计一次当日计费；期限日前付款先减本金。未逾期不计费，零本金不计天数；无自动复利或封顶。最终金额高精度累计后统一四舍五入。默认没有“本金+滞纳金总欠款”字段，以免待定税额被冒充最终应付。

## 合理推算与固定交付补充

年度核算按[年度交付规则](annual-delivery.md)执行。字段可由现有资料及公开数据合理重建，不把缺少单独证明直接当作不可测算。推算比例可用于测算并记录范围和依据，抵免凭证另行完善；已核实、重建及纯假设情景分别标注。不得通过伪填verified或缩小账户范围绕过真实门槛。

## 到账口径与程序约束（0.1.22）

默认dividend_basis=statement_net；不自动gross-up。含该口径股息时输出status=statement_net_estimate，incomes的net_received_rmb及amount_basis标明金额性质，不标为gross_rmb；仅允许credit_mode=deferred，程序拒绝在净额口径直接减境外税。独立税前/抵免情景必须显式gross，并用对应税前输入和已核验抵免证据；不能只改标签。旧版示例税前抵免路径已显式标为gross，不改变默认到账规则。输出为参考算术，不是最终申报税额。
