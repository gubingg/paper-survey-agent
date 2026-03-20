# Meeting Outline

## 研究背景
围绕多篇论文的结构化抽取、横向比较、证据补全与研究空白验证。

## 代表工作
### 1. MAUP：用于跨域少样本医学图像分割的免训练多中心自适应不确定性感知提示
- 研究问题：跨域少样本医学图像分割 (CD-FSMIS) 模型依赖于源域上的繁重训练过程，这降低了通用性和部署便利性。直接应用像 SAM 这样的基础模型面临着捕捉完整结构、低对比度图像中的边界感知以及适应不同解剖复杂性的挑战。
- 方法：MAUP (多中心自适应不确定性感知提示) 是一种免训练策略，使用预训练的 DINOv2 特征编码器适配 Segment Anything Model (SAM)。它采用 K-means 聚类进行多中心提示，不确定性感知提示选择聚焦于挑战性区域，基于目标复杂性的自适应提示优化，以及基于形态学的负提示用于边界描绘。
- 数据集：Abd-MRI, Abd-CT, Card-MRI
- 指标：证据不足
- 可展示亮点：与几种传统的 CD-FSMIS 模型和免训练 FSMIS 模型相比，在三个医学数据集上无需任何额外训练即可实现精确的分割结果。在评估的数据集上实现了最先进的性能。

### 2. 通过不确定性校正增强 Segment Anything Model 在自动提示医学图像分割中的可靠性
- 研究问题：SAM 及其医学变体需要逐层手动提示，增加了负担。由于高结构复杂性和低对比度，自动提示尝试在医学成像中表现不佳且缺乏可靠性。
- 方法：UR-SAM 框架，包含一个用于自动提示生成的定位框架，一个用于不确定性估计的提示增强模块，以及一个使用基于类别特定置信度过滤的基于不确定性的校正模块。
- 数据集：Public 3D medical dataset (22 head and neck organs), Public 3D medical dataset (13 abdominal organs)
- 指标：Dice Similarity Coefficient
- 可展示亮点：无需补充训练或微调，在 dice similarity coefficient 上将分割性能提升了高达 10.7% 和 13.8%。

### 3. UncertainSAM: Fast and Efficient Uncertainty Quantification of the Segment Anything Model
- 研究问题：Quantifying uncertainty in the Segment Anything Model (SAM) is challenging due to ambiguous tasks, under-parameterized models, and insufficient prompts. Existing uncertainty quantification approaches are resource-intensive or poorly suited for SAM.
- 方法：UncertainSAM (USAM), a lightweight post-hoc uncertainty quantification method using Multi-Layer Perceptrons (MLPs) to estimate uncertainty directly from SAM's pretrained latent representations based on a Bayesian entropy formulation.
- 数据集：SA-V, MOSE, ADE20k, DAVIS, COCO
- 指标：Intersection over Union (IoU), Uncertainty Estimation, Epistemic Gap
- 可展示亮点：USAM demonstrates superior predictive capabilities on multiple datasets, offering a computationally cheap and easy-to-use UQ alternative. It helps balance the trade-off between efficiency and accuracy by estimating potential epistemic gaps.

## 对比总结
研究主题聚焦于 围绕多篇论文的结构化抽取、横向比较、证据补全与研究空白验证。。 方法类别主要包括 Training-free Few-shot Learning, Uncertainty Estimation, Uncertainty Quantification。 常见数据集包括 Abd-MRI, Abd-CT, Card-MRI, Public 3D medical dataset (22 head and neck organs), Public 3D medical dataset (13 abdominal organs)。 常见评测指标包括 证据不足, Dice Similarity Coefficient, Intersection over Union (IoU), Uncertainty Estimation, Epistemic Gap。 重复出现的局限主要集中在 prompt by random shifting to generate augmented bounding
                                                          However, we argue that this simple ’correction’ may notbox prompts B = {b1, b2, · · · , bn}, where n is a pre-defined
                                                        improve the performance or even introduce additional segmen-
number for augmentation., To be
specific, Abd-MRI consists of 20 cases of abdominal MRI scans from the ISBI
2019 Combined Healthy Organ Segmentation challenge (CHAOS) [9] and Abd-
CT consists of 20 cases of abdominal CT scans from the MICCAI 2015 multi-
atlas labeling Beyond The Cranial Vault challenge (BTCV) [11]., The Card-
MRI contains 45 cases of cardiac MRI scans collected from the MICCAI 2019
Multi-Sequence Cardiac MRI Segmentation Challenge [31].。

## 候选 Research Gaps
- 现有工作反复暴露出 'prompt by random shifting to generate augmented bounding
                                                          However, we argue that this simple ’correction’ may notbox prompts B = {b1, b2, · · · , bn}, where n is a pre-defined
                                                        improve the performance or even introduce additional segmen-
number for augmentation.'，说明该方向仍存在待解决的稳定性或适用性问题。 [有冲突]