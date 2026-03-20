# Meeting Outline

## 研究背景
围绕多篇论文的结构化抽取、横向比较、证据补全与研究空白验证。

## 代表工作
### 1. MAUP: 用于跨域少样本医学图像分割的无需训练多中心自适应不确定性感知提示
- 研究问题：跨域少样本医学图像分割 (CD-FSMIS) 目前依赖于源域上的繁重训练过程，降低了通用性和部署便捷性。此外，现有方法需要大量标注数据。直接应用如 SAM 之类的基础模型在捕捉完整结构、低对比度图像中的边界感知以及适应不同的解剖复杂度方面面临挑战。
- 方法：MAUP (多中心自适应不确定性感知提示) 是一种无需训练的方法，它使用预训练的 DINOv2 特征编码器适配 Segment Anything Model (SAM)。它采用 K-means 聚类进行多中心提示生成，利用不确定性感知提示选择聚焦于挑战性区域，基于目标复杂度进行自适应提示优化，并使用源自外围相似性图的负提示进行边界描绘。
- 数据集：Abd-MRI, Abd-CT, Card-MRI
- 指标：MAP
- 可展示亮点：与几种传统的 CD-FSMIS 模型和无需训练的 FSMIS 模型相比，在三个医学数据集上无需任何额外训练即可实现精确的分割结果。该模型在评估的数据集上实现了最先进性能。

### 2. UncertainSAM：Segment Anything Model 的快速高效不确定性量化
- 研究问题：由于 Segment Anything Model (SAM) 的类无关特性、任务模糊性和提示依赖性，对其不确定性进行量化具有挑战性。现有的不确定性量化 (UQ) 方法不太适用于 SAM。
- 方法：引入了一种贝叶斯熵公式，共同考虑偶然性、认知和任务不确定性。提出了 USAM，一种轻量级的后验 UQ 方法，使用在 SAM 预训练潜在表示上训练的 MLPs 来直接估计不确定性。
- 数据集：SA-V, MOSE, ADE20k, DAVIS, COCO
- 指标：Intersection over Union (IoU), Uncertainty Estimation Accuracy, Epistemic Gap
- 可展示亮点：USAM 在多个数据集上展示了卓越的预测能力。它提供了一种计算成本低廉的 UQ 替代方案，能够平衡效率与准确性之间的权衡。MLPs 的表现持平或超越了贝叶斯近似和现有的 UQ 方法。

### 3. 利用不确定性校正增强 Segment Anything Model 在自动提示医学图像分割中的可靠性
- 研究问题：SAM 及其医学变体需要逐片手动提示，增加了负担。现有的自动提示方法表现不佳且缺乏可靠性，尤其是在具有高结构复杂性和低对比度的医学成像中。
- 方法：UR-SAM 框架。使用定位框架进行自动提示生成。结合提示增强模块以获得一系列输入提示用于不确定性估计。使用基于不确定性的校正模块，利用不确定性分布来提高分割性能，无需微调 SAM。
- 数据集：Two public 3D medical datasets (22 head and neck organs, 13 abdominal organs)
- 指标：Dice Similarity Coefficient
- 可展示亮点：无需补充训练或微调，dice similarity coefficient 的分割性能提高了高达 10.7% 和 13.8%。

## 对比总结
研究主题聚焦于 围绕多篇论文的结构化抽取、横向比较、证据补全与研究空白验证。。 方法类别主要包括 Training-free Few-shot Learning, Uncertainty Quantification, Uncertainty Estimation。 常见数据集包括 Abd-MRI, Abd-CT, Card-MRI, SA-V, MOSE。 常见评测指标包括 MAP, Intersection over Union (IoU), Uncertainty Estimation Accuracy, Epistemic Gap, Dice Similarity Coefficient。 重复出现的局限主要集中在 However, FSMIS still requires a large num-
ber of labeled samples in the same domain for model training [6,18], even if the
target class for testing differs, e.g., both training and testing must be performed
on CT images., In order to address these limitations, we introduce a novel training-
free few-shot medical image segmentation model with Multi-center Adaptive
Uncertainty-aware Prompting (MAUP) strategy for the SAM model., In conclusion, the key contributions of our model
can be summarized as follows:

(1) We introduce a training-free model which addresses the limitations of
existing cross-domain few-shot medical image segmentation approaches via de-
signed innovative prompting strategy.。

## 候选 Research Gaps
- 现有工作反复暴露出 'However, FSMIS still requires a large num-
ber of labeled samples in the same domain for model training [6,18], even if the
target class for testing differs, e.g., both training and testing must be performed
on CT images.'，说明该方向仍存在待解决的稳定性或适用性问题。 [有冲突]