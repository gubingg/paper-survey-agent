---
name: extract-fields
description: Extract structured fields from one or more academic papers for downstream comparison, gap candidate generation, validation, and task-specific output generation. Use this skill for paper-level structured extraction only.
---

# Purpose
从单篇或多篇论文中提取结构化关键信息，供后续跨论文对比、研究空白候选生成、验证与输出使用。

# Inputs
- 论文原文、摘要、方法、实验等文本
- 可选：用户指定的提取字段
- 可选：论文标题或编号

# Outputs
按论文逐篇输出结构化结果，建议包含：
- paper_title
- research_problem
- task_setting
- core_method
- dataset
- metrics
- main_results
- strengths
- limitations
- future_work_if_stated

# Instructions
1. 逐篇提取，不要混淆不同论文的信息。
2. 优先提取文中明确表述的信息，不要主观补充。
3. 对缺失字段标记为“未明确提及”，不要编造。
4. 提取结果应尽量结构化、简洁，方便后续 compare-papers 使用。
5. 若用户指定某些字段，优先满足用户要求。

# Guardrails
- 不要做跨论文比较。
- 不要直接输出研究空白判断。
- 不要生成最终面向用户的综述/汇报内容。

# Output Format
返回结构化 JSON 或结构化 Markdown，每篇论文一条记录。