# Survey Draft

研究主题：围绕多篇论文的结构化抽取、横向比较、证据补全与研究空白验证。

## 方法脉络
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

MAUP: 面向跨域少样本医学图像分割的无需训练多中心自适应不确定性感知提示 聚焦于 CD-FSMIS 模型严重依赖源域训练，降低了通用性和部署便利性。直接应用如 SAM 之类的基础模型在捕捉完整结构、低对比度图像中的边界感知以及适应不同的解剖复杂性方面面临挑战。，采用 MAUP (多中心自适应不确定性感知提示) 利用预训练的 DINOv2 特征编码器适配 Segment Anything 模型 (SAM)。它采用 K-means 聚类生成多中心提示，针对挑战性区域进行不确定性感知提示选择，基于目标复杂度进行自适应提示优化，并使用外围相似度图生成负提示。，在 Abd-MRI, Abd-CT, Card-MRI 上进行评估，主要结果为 与传统的 CD-FSMIS 模型和无需训练的 FSMIS 模型相比，在三个医学数据集上无需任何额外训练即可实现精确的分割结果。达到了最先进的性能。。
局限：However, FSMIS still requires a large num-
ber of labeled samples in the same domain for model training [6,18], even if the
target class for testing differs, e.g., both training and testing must be performed
on CT images.；In order to address these limitations, we introduce a novel training-
free few-shot medical image segmentation model with Multi-center Adaptive
Uncertainty-aware Prompting (MAUP) strategy for the SAM model.。

UncertainSAM: Segment Anything Model 的快速高效不确定性量化 聚焦于 Segment Anything Model (SAM) 由于其类别无关的特性、任务模糊性和提示依赖性，缺乏可靠的不确定性量化。现有方法资源密集或不太适合 SAM 独特的不确定性来源。，采用 引入了一种贝叶斯熵公式，共同考虑偶然、认知和任务不确定性。提出了 USAM，这是一种轻量级的事后方法，使用 MLPs 直接从 SAM 的预训练潜在表示中估计不确定性。，在 SA-V, MOSE, ADE20k, DAVIS, COCO 上进行评估，主要结果为 USAM 在多个数据集上展示了卓越的预测能力。它能准确地将不确定性根源追溯到参数不足的模型、不足的提示或图像模糊性。它提供了一种计算成本低廉的贝叶斯近似替代方案，有助于平衡效率和准确性。。
局限：However,   models are denoted as Θ = {L,B+,S,T} and correspond
 the true task probability p(ˆa∣xI,xP,θ) is intractable.；Using the weighted entropy θ like ensembles or BNNs to estimate epistemic uncertainty
 are not applicable post-hoc and are highly cost-intensive for                  y
 foundation models.。

利用不确定性校正增强 Segment Anything Model 在自动提示医学图像分割中的可靠性 聚焦于 SAM 及其医学变体需要逐层手动提示，增加了负担。由于高结构复杂性和低对比度，自动提示尝试在医学成像中表现不佳且缺乏可靠性。，采用 UR-SAM 框架，包含用于自动提示生成的定位框架、用于不确定性估计的提示增强模块，以及使用基于类别特定置信度过滤的基于不确定性的校正模块。，在 Public 3D medical dataset (22 head and neck organs), Public 3D medical dataset (13 abdominal organs) 上进行评估，主要结果为 无需补充训练或微调，dice similarity coefficient 指标上的分割性能提升高达 10.7% 和 13.8%。。
局限：One notable limitation is that we use a relatively simple         segmentation and diagnosis: is the problem solved?” IEEE transactions
strategy to classify pixels in regions with high uncertainty,        on medical imaging, vol.；Ren, “Sam meets
      the kits19 challenge,” Medical image analysis, vol.。
