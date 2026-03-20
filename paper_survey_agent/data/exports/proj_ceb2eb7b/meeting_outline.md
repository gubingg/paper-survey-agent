# Meeting Outline

## 研究背景
围绕多篇论文的结构化抽取、横向比较、证据补全与研究空白验证。

## 代表工作
### 1. Enhancing the Reliability of Segment Anything Model for Auto-Prompting Medical Image Segmentation with Uncertainty Rectification
- 研究问题：SAM and its medical variants require slice-by-slice manual prompting, increasing burden. Existing auto-prompting attempts exhibit subpar performance and lack reliability, especially in medical imaging with high structural complexity and low contrast.
- 方法：UR-SAM framework incorporating a localization framework for automatic prompt generation, a prompt augmentation module for uncertainty estimation, and an uncertainty-based rectification module.
- 数据集：Public 3D medical dataset (22 head and neck organs), Public 3D medical dataset (13 abdominal organs)
- 指标：Dice Similarity Coefficient
- 可展示亮点：Improves segmentation performance with up to 10.7% and 13.8% in dice similarity coefficient without supplementary training or fine-tuning.

### 2. UncertainSAM: Fast and Efficient Uncertainty Quantification of the Segment Anything Model
- 研究问题：Quantifying the uncertainty of the Segment Anything Model (SAM) is challenging due to its ambiguous nature and class-agnostic foundation. Current uncertainty quantification (UQ) approaches are resource-intensive or poorly suited for SAM's unique task uncertainty.
- 方法：UncertainSAM (USAM), a lightweight post-hoc UQ method based on a Bayesian entropy formulation. It uses Multi-Layer Perceptrons (MLPs) to estimate aleatoric, epistemic, and task uncertainty directly from SAM's pretrained latent representations.
- 数据集：SA-V, MOSE, ADE20k, DAVIS, COCO
- 指标：Intersection over Union (IoU), Uncertainty Estimation, Epistemic Gap
- 可展示亮点：USAM demonstrates superior predictive capabilities on multiple datasets. It offers a computationally cheap UQ alternative that can support user-prompting, enhance semi-supervised pipelines, or balance the tradeoff between accuracy and cost efficiency.

### 3. MAUP: Training-free Multi-center Adaptive Uncertainty-aware Prompting for Cross-domain Few-shot Medical Image Segmentation
- 研究问题：Cross-domain Few-shot Medical Image Segmentation (CD-FSMIS) models rely on heavy training over source domains, degrading universality and ease of deployment. Direct application of Segment Anything Model (SAM) faces challenges in prompt coverage, boundary awareness, and adapting to varying anatomical complexities.
- 方法：MAUP (Multi-center Adaptive Uncertainty-aware Prompting). A training-free approach adapting SAM using DINOv2 feature encoder. Components include K-means clustering based multi-center prompts generation, uncertainty-aware prompts selection, adaptive prompt optimization, and negative prompts using periphery similarity maps.
- 数据集：Abd-MRI, Abd-CT, Card-MRI
- 指标：证据不足
- 可展示亮点：Achieves precise segmentation results across three medical datasets without any additional training compared with conventional CD-FSMIS models and training-free FSMIS model. Achieves state-of-the-art performance.

## 对比总结
研究主题聚焦于 围绕多篇论文的结构化抽取、横向比较、证据补全与研究空白验证。。 方法类别主要包括 Uncertainty Estimation, Uncertainty Quantification, Training-free Few-shot Learning。 常见数据集包括 Public 3D medical dataset (22 head and neck organs), Public 3D medical dataset (13 abdominal organs), SA-V, MOSE, ADE20k。 常见评测指标包括 Dice Similarity Coefficient, Intersection over Union (IoU), Uncertainty Estimation, Epistemic Gap, 证据不足。 重复出现的局限主要集中在 prompt by random shifting to generate augmented bounding
                                                          However, we argue that this simple ’correction’ may notbox prompts B = {b1, b2, · · · , bn}, where n is a pre-defined
                                                        improve the performance or even introduce additional segmen-
number for augmentation., However,
                                                                  distributed coordinate prompts from the ground truth mask., To be
specific, Abd-MRI consists of 20 cases of abdominal MRI scans from the ISBI
2019 Combined Healthy Organ Segmentation challenge (CHAOS) [9] and Abd-
CT consists of 20 cases of abdominal CT scans from the MICCAI 2015 multi-
atlas labeling Beyond The Cranial Vault challenge (BTCV) [11].。

## 候选 Research Gaps
- 现有工作反复暴露出 'prompt by random shifting to generate augmented bounding
                                                          However, we argue that this simple ’correction’ may notbox prompts B = {b1, b2, · · · , bn}, where n is a pre-defined
                                                        improve the performance or even introduce additional segmen-
number for augmentation.'，说明该方向仍存在待解决的稳定性或适用性问题。 [证据弱]