# Meeting Outline

## 研究背景
围绕多篇论文的结构化抽取、横向比较、证据补全与研究空白验证。

## 代表工作
### 1. 利用不确定性校正增强 Segment Anything Model 用于自动提示医学图像分割的可靠性
- 研究问题：SAM 及其医学变体需要逐层手动提示，增加了负担。现有的自动提示方法由于高结构复杂性和低对比度，在医学成像中表现欠佳且缺乏可靠性。
- 方法：UR-SAM 框架，包含用于自动提示生成的定位框架、用于不确定性估计的提示增强模块，以及使用基于类别特定置信度过滤的基于不确定性的校正模块。
- 数据集：Public 3D medical dataset (22 head and neck organs), Public 3D medical dataset (13 abdominal organs)
- 指标：Dice Similarity Coefficient
- 可展示亮点：无需补充训练或微调，dice similarity coefficient 的分割性能提升高达 10.7% 和 13.8%。

### 2. 利用视觉基础模型实现高性能、免训练的开放词汇分割
- 研究问题：CLIP 在语义分割任务上的表现仍不理想，这是由于空间不变的语义特征和受限的分辨率所致。先前的改进方法解决了空间不变性问题，但未探索分辨率受限的问题，且滑动窗口策略（Segment-then-Splice）在高分辨率图像上受限于有限的感受野。
- 方法：Trident，一个采用 Splice-then-Segment 范式的免训练框架。它拼接从子图像中提取的由 CLIP 和 DINO 提取的特征，然后利用 SAM 的编码器创建相关矩阵以进行全局聚合。此外，它还提出了一种细化策略，将 CLIP 的粗略分割输出转换为 SAM 的提示。
- 数据集：Pascal VOC, Eight popular benchmarks
- 指标：MAP
- 可展示亮点：与之前的 SOTA 相比，在八个流行基准测试上的 mIoU 取得了显著提升。在免训练方法中超越了之前的 SOTA 结果，甚至与弱监督方法相比也显示出具有竞争力的结果。

### 3. MAUP: 用于跨域少样本医学图像分割的免训练多中心自适应不确定性感知提示
- 研究问题：跨域少样本医学图像分割 (CD-FSMIS) 模型目前依赖于对源医学域的大量训练过程，这降低了通用性和部署便利性。此外，将 SAM 等基础模型直接应用于 CD-FSMIS 面临挑战，包括捕捉完整结构、低对比度图像中的边界感知以及适应不同的解剖复杂性。
- 方法：MAUP（Multi-center Adaptive Uncertainty-aware Prompting）是一种免训练方法，它使用预训练的 DINOv2 特征编码器来适配 Segment Anything Model (SAM)。该方法采用 K-means 聚类进行多中心提示生成，专注于挑战性区域的不确定性感知提示选择，基于目标复杂性的自适应提示优化，以及用于负提示的基于形态学的周边相似性图。
- 数据集：Abd-MRI, Abd-CT, Card-MRI
- 指标：MAP
- 可展示亮点：与几种传统的 CD-FSMIS 模型和免训练 FSMIS 模型相比，在三个医学数据集上无需任何额外训练即可实现精确的分割结果。该模型在评估数据集上实现了最先进的性能。

## 对比总结
研究主题聚焦于 围绕多篇论文的结构化抽取、横向比较、证据补全与研究空白验证。。 方法类别主要包括 Medical Image Segmentation, Training-Free Open Vocabulary Segmentation, Training-free Few-shot Learning, Prompt Engineering, Medical Image Segmentation。 常见数据集包括 Public 3D medical dataset (22 head and neck organs), Public 3D medical dataset (13 abdominal organs), Pascal VOC, Eight popular benchmarks, Abd-MRI。 常见评测指标包括 MAP, Dice Similarity Coefficient。 重复出现的局限主要集中在 One notable limitation is that we use a relatively simple         segmentation and diagnosis: is the problem solved?” IEEE transactions
strategy to classify pixels in regions with high uncertainty,        on medical imaging, vol., Ren, “Sam meets
      the kits19 challenge,” Medical image analysis, vol., of segment anything model (sam) on multi-phase liver tumor segmen-
      the results of the emidec challenge,” Medical Image Analysis, vol.。

## 候选 Research Gaps
- 现有工作反复暴露出 'One notable limitation is that we use a relatively simple         segmentation and diagnosis: is the problem solved?” IEEE transactions
strategy to classify pixels in regions with high uncertainty,        on medical imaging, vol.'，说明该方向仍存在待解决的稳定性或适用性问题。 [有冲突]
- 当前评测指标较为单一，尚不足以全面反映方法在真实研究场景中的综合表现。 [不成立]