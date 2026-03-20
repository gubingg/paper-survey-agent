# Meeting Outline

## 研究背景
围绕多篇论文的结构化抽取、横向比较、证据补全与研究空白验证。

## 代表工作
### 1. UncertainSAM：Segment Anything Model 快速且高效的不确定性量化
- 研究问题：由于 Segment Anything Model (SAM) 的类无关特性、任务模糊性以及多种不确定性来源（认知、偶然、任务），量化其不确定性具有挑战性。现有方法资源密集或适用性差。
- 方法：引入了用于 SAM 中 UQ 的贝叶斯熵公式，以及 USAM，这是一种轻量级的后处理方法，使用 MLPs 从 SAM 的潜在表示中估计不确定性。
- 数据集：SA-V, MOSE, ADE20k, DAVIS, COCO
- 指标：Intersection over Union (IoU), Uncertainty Estimation, Epistemic Gap
- 可展示亮点：USAM 在多个数据集上展示了卓越的预测能力，提供了一种计算成本低廉的 UQ 替代方案。MLPs 的表现持平或超越贝叶斯近似及现有 UQ 方法。有助于平衡效率与准确性的权衡。

### 2. MAUP：用于跨域少样本医学图像分割的免训练多中心自适应不确定性感知提示
- 研究问题：跨域少样本医学图像分割 (CD-FSMIS) 模型严重依赖源域训练，降低了通用性和部署便利性。直接应用如 SAM 等基础模型在提示捕捉、边界感知以及适应不同解剖复杂性方面面临挑战。
- 方法：MAUP (多中心自适应不确定性感知提示) 是一种利用 DINOv2 特征适配 SAM 的免训练方法。它采用 K-means 聚类生成多中心提示、不确定性感知提示选择、自适应提示优化，并通过外围相似性图生成负提示。
- 数据集：Abd-MRI, Abd-CT, Card-MRI
- 指标：Segmentation Accuracy
- 可展示亮点：与传统的 CD-FSMIS 模型相比，无需额外训练即可在三个医学数据集上实现精确的分割结果。达到了最先进的性能。

### 3. 利用不确定性校正增强 Segment Anything Model 在自动提示医学图像分割中的可靠性
- 研究问题：SAM 及其医学变体需要逐片手动提示，增加了负担。现有的自动提示方法由于高结构复杂性和低对比度，在医学成像中表现不佳且缺乏可靠性。
- 方法：UR-SAM 框架使用原始 SAM 或 MedSAM 作为基础，包含一个用于自动生成提示的定位框架、一个用于不确定性估计的提示增强模块，以及一个使用基于类特定置信度过滤的基于不确定性的校正模块。
- 数据集：Public 3D medical dataset (22 head and neck organs), Public 3D medical dataset (13 abdominal organs)
- 指标：Dice Similarity Coefficient
- 可展示亮点：无需补充训练或微调，dice similarity coefficient 提高了多达 10.7% 和 13.8%。

## 对比总结
研究主题聚焦于 围绕多篇论文的结构化抽取、横向比较、证据补全与研究空白验证。。 方法类别主要包括 Uncertainty Quantification, Training-free Few-shot Learning, Uncertainty Estimation。 常见数据集包括 SA-V, MOSE, ADE20k, DAVIS, COCO。 常见评测指标包括 Intersection over Union (IoU), Uncertainty Estimation, Epistemic Gap, Segmentation Accuracy, Dice Similarity Coefficient。 重复出现的局限主要集中在 prompt by random shifting to generate augmented bounding
                                                          However, we argue that this simple ’correction’ may notbox prompts B = {b1, b2, · · · , bn}, where n is a pre-defined
                                                        improve the performance or even introduce additional segmen-
number for augmentation., 理论上的贝叶斯近似计算成本高昂, To be
specific, Abd-MRI consists of 20 cases of abdominal MRI scans from the ISBI
2019 Combined Healthy Organ Segmentation challenge (CHAOS) [9] and Abd-
CT consists of 20 cases of abdominal CT scans from the MICCAI 2015 multi-
atlas labeling Beyond The Cranial Vault challenge (BTCV) [11].。

## 候选 Research Gaps
- 现有工作反复暴露出 'prompt by random shifting to generate augmented bounding
                                                          However, we argue that this simple ’correction’ may notbox prompts B = {b1, b2, · · · , bn}, where n is a pre-defined
                                                        improve the performance or even introduce additional segmen-
number for augmentation.'，说明该方向仍存在待解决的稳定性或适用性问题。 [证据弱]