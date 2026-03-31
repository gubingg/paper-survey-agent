---
name: compare-papers
description: Compare multiple academic papers across shared dimensions and generate raw research gap candidates for downstream validation. Use this skill after structured field extraction. Do not use it as the final presentation layer.
---

# Purpose
对多篇论文进行横向对比，并在对比基础上归纳潜在研究空白候选 `gap_candidates_raw`，供后续 gap 验证使用。

# Inputs
- 多篇论文的结构化字段结果
- 可选：用户指定的对比维度
- 可选：任务类型（survey / meeting_outline / gap_analysis）

# Outputs
输出以下内容：
- comparison_dimensions
- comparison_summary
- key_similarities
- key_differences
- method_or_setting_gaps
- gap_candidates_raw

其中 `gap_candidates_raw` 为未经严格裁决的候选研究空白列表，每条建议包含：
- candidate_gap
- basis_from_comparison
- related_papers
- tentative_priority

# Instructions
1. 先基于统一维度做横向对比，如研究问题、方法、数据集、指标、结果、优缺点。
2. 输出对比时要突出“共性、差异、覆盖不足、尚未充分探索的方向”。
3. 在完成对比后，基于以下线索归纳 `gap_candidates_raw`：
   - 方法覆盖不足
   - 数据集或场景覆盖不足
   - 指标或评估维度不足
   - 现有工作局限反复出现
   - 不同论文间存在冲突或未解决问题
4. `gap_candidates_raw` 只做候选提出，不做最终裁决。
5. 若依据不足，可降低候选优先级，但不要直接判定为真实 gap。

# Guardrails
- 不要把候选 gap 当作最终结论。
- 不要执行严格验证、反证裁决或覆盖度最终判断。
- 不要输出最终面向用户的成品文案。

# Output Format
请按以下顺序输出：
1. 对比维度与对比摘要
2. 核心共性与差异
3. `gap_candidates_raw`