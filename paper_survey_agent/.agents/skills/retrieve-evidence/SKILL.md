---
name: retrieve-evidence
description: Retrieve supporting or counter evidence from paper text for field completion, comparison support, or gap validation. Use this skill when textual evidence is needed. Do not use it as the final answer generator.
---

# Purpose
在字段缺失、对比依据不足、研究空白候选需要验证时，从论文内容中检索支持证据、反证或覆盖度相关证据。

# Inputs
- retrieval_goal：field_completion / comparison_support / gap_validation
- 当前任务说明
- 论文语料或切片
- 可选：candidate_gap
- 可选：希望检索的证据类型（support / counter / coverage / both）

# Outputs
输出证据检索结果，建议包含：
- retrieval_goal
- evidence_type
- evidence_snippets
- source_paper
- evidence_summary
- relevance
- confidence

# Instructions
1. 先明确检索目标，再决定证据类型。
2. 对 gap_validation 场景，优先支持以下检索：
   - supporting evidence
   - counter evidence
   - coverage evidence
3. 返回最相关的证据片段，并标明来源论文。
4. 若没有足够证据，要明确说明“证据不足”。
5. 检索结果只提供证据，不负责最终裁决。

# Guardrails
- 不要把弱相关片段包装成强证据。
- 不要省略来源论文。
- 不要直接输出最终研究空白结论。

# Output Format
每条证据请包含：
- paper
- snippet
- evidence_type
- purpose
- confidence