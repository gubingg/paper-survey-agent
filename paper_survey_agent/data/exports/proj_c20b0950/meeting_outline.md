# Meeting Outline

## 研究背景
围绕多篇论文的结构化抽取、横向比较、证据补全与研究空白验证。

## 代表工作
### 1. 利用不确定性校正增强 Segment Anything Model 用于自动提示医学图像分割的可靠性
- 研究问题：SAM 及其医学变体需要逐层手动提示，增加了负担。现有的自动提示尝试表现不佳且缺乏可靠性，尤其是在具有高结构复杂性和低对比度的医学成像中。
- 方法：UR-SAM 框架利用定位框架进行自动提示生成，一个提示增强模块以获得一系列输入提示用于不确定性估计，以及一个基于不确定性的校正模块以利用不确定性分布改进分割。
- 数据集：Two public 3D medical datasets (22 head and neck organs, 13 abdominal organs)
- 指标：Dice Similarity Coefficient
- 可展示亮点：无需补充训练或微调，在 dice similarity coefficient 指标上分割性能提升高达 10.7% 和 13.8%。

### 2. MAUP：用于跨域少样本医学图像分割的免训练多中心自适应不确定性感知提示
- 研究问题：跨域少样本医学图像分割 (CD-FSMIS) 领域，当前模型依赖于源域的大量训练，降低了通用性和部署便利性。直接应用 Segment Anything Model (SAM) 在提示捕捉、边界感知以及适应解剖复杂性方面面临挑战。
- 方法：MAUP（多中心自适应不确定性感知提示）。一种利用 DINOv2 特征适配 SAM 的免训练方法。包括用于多中心提示的 K-means 聚类、不确定性感知提示选择、自适应提示优化以及使用外围相似性图的负提示。
- 数据集：Abd-MRI, Abd-CT, Card-MRI
- 指标：Segmentation Accuracy
- 可展示亮点：与传统的 CD-FSMIS 模型相比，无需任何额外训练即可在三个医学数据集上实现精确的分割结果。达到了最先进的性能。

### 3. UncertainSAM：Segment Anything Model 的快速高效不确定性量化
- 研究问题：由于 Segment Anything Model (SAM) 的类无关特性、提示模糊性以及图像模糊性，量化其不确定性具有挑战性。现有的不确定性量化方法资源消耗大或不太适合 SAM。
- 方法：UncertainSAM (USAM)，一种基于贝叶斯熵公式的轻量级后处理不确定性量化方法。它使用多层感知机 (MLPs) 直接从 SAM 的预训练潜在表示中估计偶然不确定性、认知不确定性和任务不确定性。
- 数据集：SA-V, MOSE, ADE20k, DAVIS, COCO
- 指标：Intersection over Union (IoU), Uncertainty Estimation, Epistemic Gap
- 可展示亮点：USAM 在多个数据集上展示了卓越的预测能力。它提供了一种计算成本低且易于使用的 UQ 替代方案。MLPs 的表现持平或超越了贝叶斯近似和现有的 UQ 方法。

## 对比总结
研究主题聚焦于 围绕多篇论文的结构化抽取、横向比较、证据补全与研究空白验证。。 方法类别主要包括 Uncertainty Estimation, Training-free Few-shot Learning, Uncertainty Quantification。 常见数据集包括 Two public 3D medical datasets (22 head and neck organs, 13 abdominal organs), Abd-MRI, Abd-CT, Card-MRI, SA-V。 常见评测指标包括 Dice Similarity Coefficient, Segmentation Accuracy, Intersection over Union (IoU), Uncertainty Estimation, Epistemic Gap。 重复出现的局限主要集中在 One notable limitation is that we use a relatively simple         segmentation and diagnosis: is the problem solved?” IEEE transactions
strategy to classify pixels in regions with high uncertainty,        on medical imaging, vol., Ren, “Sam meets
      the kits19 challenge,” Medical image analysis, vol., of segment anything model (sam) on multi-phase liver tumor segmen-
      the results of the emidec challenge,” Medical Image Analysis, vol.。

## 候选 Research Gaps
- 现有工作反复暴露出 'One notable limitation is that we use a relatively simple         segmentation and diagnosis: is the problem solved?” IEEE transactions
strategy to classify pixels in regions with high uncertainty,        on medical imaging, vol.'，说明该方向仍存在待解决的稳定性或适用性问题。 [有冲突]