---
name: generate-output
description: Generate final outputs for survey, meeting outline, or gap analysis based on upstream extraction, comparison, and validated gap results. Output focus is determined by task type, not by validation depth alone.
---

# Purpose
根据任务类型生成最终输出。  
即使多个任务都经过 gap 验证，不同任务的输出侧重点仍由 `task_type` 决定。

# Inputs
- task_type: survey / meeting_outline / gap_analysis
- structured_fields
- comparison_summary
- final_gap_candidates
- 可选：effective_validation_level
- 可选：validation_details

# Output Focus Rule
输出重点由 `task_type` 决定，而不是单纯由 `effective_validation_level` 决定：

- survey：
  以论文综述为主，gap 作为未来方向/讨论方向的一部分，不作为主轴
- meeting_outline：
  以组会汇报结构和讨论重点为主，gap 作为讨论点或未来方向的一部分，不作为主轴
- gap_analysis：
  以研究空白为主轴，重点展示验证结果、证据、反证、覆盖度、置信度与人工复核信息

即使 survey / meeting_outline 使用 strict 验证，输出重点仍保持原任务导向，不改成 gap_analysis 风格。

# Instructions
1. 先识别 `task_type`，再确定输出组织方式。
2. 若 `task_type = survey`：
   - 输出研究主题概览
   - 方法与路线梳理
   - 多论文对比总结
   - 将 gap 作为“未来方向 / 讨论方向”一节进行简要呈现
3. 若 `task_type = meeting_outline`：
   - 输出适合组会汇报的提纲、重点论文、方法差异、讨论问题
   - 将 gap 作为“讨论点 / 后续可关注方向”进行简要呈现
4. 若 `task_type = gap_analysis`：
   - 以 gap 为核心组织输出
   - 展示 validation_result、confidence、coverage
   - 展示 supporting_evidence、counter_evidence
   - 必要时展示 human_review_needed
5. 不要因为验证更严格，就自动改变 survey / meeting_outline 的主输出结构。

# Guardrails
- 不要混淆三种任务的输出风格。
- 不要把 survey / meeting_outline 直接写成 gap_analysis 报告。
- 若上游结果不足，应明确说明信息不足。

# Output Format
- survey：综述型总结
- meeting_outline：汇报提纲 / 讨论提纲
- gap_analysis：结构化研究空白分析报告