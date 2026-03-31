---
name: validate-gap
description: Validate raw research gap candidates using light or strict review. Default validation level depends on task type, but explicit gap_validation_level overrides it. Use this skill for reviewing gap_candidates_raw, not for generating final user-facing output.
---

# Purpose
对 `gap_candidates_raw` 进行验证，支持 `light` 和 `strict` 两种审查模式。  
默认模式由任务类型决定，但如果显式传入 `gap_validation_level`，则以显式配置为准。

# Inputs
- task_type: survey / meeting_outline / gap_analysis
- gap_candidates_raw
- comparison_summary
- structured_fields
- 可选：gap_validation_level = light / strict
- 可选：retrieved_evidence
- 可选：human_review_signal

# Effective Validation Level
按以下规则确定实际验证级别：
1. 若显式传入 `gap_validation_level`，优先使用该值
2. 否则：
   - survey -> light
   - meeting_outline -> light
   - gap_analysis -> strict

# Outputs
输出：
- effective_validation_level
- validated_gap_candidates
- final_gap_candidates

其中每条验证结果建议包含：
- candidate_gap
- validation_result
- short_reason
- confidence
- coverage
- supporting_evidence
- counter_evidence
- human_review_needed

说明：
- `light` 模式下，可简化 `coverage / evidence / human_review_needed`
- `strict` 模式下，应尽量完整输出

# Instructions
1. 输入是 `gap_candidates_raw`，本 skill 负责审查，不负责提出候选。
2. 若实际验证级别为 `light`：
   - 做一次轻量筛查
   - 判断是否具备基本合理性
   - 检查是否存在明显冲突或明显已被覆盖
   - 输出简洁结论与理由
3. 若实际验证级别为 `strict`：
   - 对候选逐条执行更严格审查
   - 结合支持证据、反证、覆盖度进行裁决
   - 给出 confidence、coverage 与风险说明
   - 必要时标记 `human_review_needed`
4. 若证据不足，应明确标记“证据不足”，不要强行下结论。
5. 最终输出 `final_gap_candidates`，供 generate-output 使用。

# Guardrails
- 不要把候选 gap 自动视为真实 gap。
- 不要越过证据直接给出高确定性结论。
- 不负责最终面向用户的展示组织。
- 任务焦点由 generate-output 决定，而不是由本 skill 决定。

# Output Format
按候选逐条输出：
- candidate_gap
- validation_result
- short_reason
- confidence
- coverage
- supporting_evidence
- counter_evidence
- human_review_needed