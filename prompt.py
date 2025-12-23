def system_prompt():
    return """
你是一名严谨的本科毕业设计导师助理与项目经理。
你的任务是基于用户给定的毕设主题、背景资料、当前阶段信息与总周数，进行合理的周度任务拆分，并产出每周周报。

强制要求（必须严格遵守）：
1) 只输出严格可被 json.loads 解析的 JSON；不要输出任何解释性文字。
2) 不要输出 Markdown，不要使用 ``` 包裹。
3) 字段名必须完全匹配要求，不得新增字段，不得缺失字段。
4) 内容必须具体可执行，避免空话套话；每周任务递进合理（调研/需求→设计→实现→实验→论文→答辩）。
5) 背景不足时可做合理补全，但不要编造具体实验数据、论文引用、项目外部事实。
6) 所有文本字段必须便于粘贴到 LaTeX：只能使用中文标点与阿拉伯数字；不要使用表情、特殊符号、长英文串、URL。
"""


def plan_prompt(weeks, user_prompt, background_text):
    prompt = f"""
请根据以下信息，为毕业设计做一个“{weeks}周”的总体周度拆分计划。

【毕设主题/用户目标】
{user_prompt}

【背景资料摘要/全文】
{background_text}

输出要求（必须严格遵守）：
1) 只输出 JSON 数组，长度必须为 {weeks}，且 week 必须从 1 到 {weeks} 连续递增。
2) 数组每个元素为对象，字段固定为（不得新增/缺失）：
   - week: 整数，从1到{weeks}
   - title: 本周主题（10-20字，能概括该周核心任务）
   - goals: 本周目标（2-4条，面向“要达成什么”）
   - deliverables: 本周产出物（1-4条，必须可验收，例如：需求文档v1、模型训练脚本、接口文档、实验对比表、论文第X章初稿等）
   - risks: 本周风险点（0-3条，每条包含风险+简短应对方向）
3) 任务分配要合理：前期调研与需求→中期方案设计与实现/实验→后期论文撰写、系统完善与答辩准备。
4) 每周 deliverables 要尽量独立且可检查，避免写成泛泛的“继续完善/继续推进”。

只输出 JSON，不要输出任何解释或多余文本。
"""
    return prompt


def weekly_prompt(week_plan, user_prompt, background_text, prev_week_summary, next_week_summary):
    prompt = f"""
你将基于“总体计划中的第{week_plan["week"]}周安排”，生成该周周报，包含三部分：
1) 主要工作内容和进展
2) 存在的主要问题和解决方法与思路
3) 下周工作计划

【毕设主题/用户目标】
{user_prompt}
【背景资料】
{background_text}
【本周计划（来自总体周度拆分，必须严格对齐）】
{week_plan}
【上周参考（若有，仅用于承接与避免重复，不要照抄）】
{prev_week_summary or "无"}
【下周参考（若有，仅用于衔接，不要照抄）】
{next_week_summary or "无"}

硬性对齐规则（必须遵守）：
- title 必须与本周计划中的 title 完全一致。
- progress 必须覆盖本周 deliverables/goals 的完成情况；每个 deliverable 至少对应 progress 的一条（完成/进行中/未完成+原因）。
- problems_and_solutions 围绕本周 risks 与本周实际阻碍；每条必须包含“问题”和“思路/动作”，且思路必须可执行。
- next_week_plan 承接本周未完成项，并与下周方向一致。

格式与长度硬约束（必须遵守，否则视为失败）：
- 只输出 JSON 对象，字段固定为：week,title,progress,problems_and_solutions,next_week_plan（不得新增/缺失）。
- progress 输出 3 条；problems_and_solutions 输出 2 条；next_week_plan 输出 3 条。
- 三个字段都必须用编号分点，分点之间用换行符 \\n 分隔！！！
- 三个字段都必须用编号分点，分点之间用换行符 \\n 分隔！！！
- 三个字段都必须用编号分点，分点之间用换行符 \\n 分隔！！！
- 编号必须严格为：
  - progress：1）...；\\n2）...；\\n3）...。
  - problems_and_solutions：1）...；\\n2）...。
  - next_week_plan：1）...；\\n2）...；\\n3）...。
- 字数：
  - progress 字段整体 100-120 字；
  - problems_and_solutions 字段整体 100-120 字；
  - next_week_plan 字段整体 100-120 字；
  （标点计入字数）
- 每条分点尽量 40-50 字，避免长句堆叠。
- problems_and_solutions 每条必须严格为单行格式（不要换行）：
  例如：1）问题：……；思路：……
- 禁止出现长英文串、URL、代码片段、连续超过8位的无分隔数字。

输出要求：
- 只输出 JSON，不要输出任何其它文字。
- week 必须等于 {week_plan["week"]}。
- title 必须等于 week_plan.title（一字不差）。
"""
    return prompt