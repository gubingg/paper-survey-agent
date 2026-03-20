# Meeting Outline

## 研究背景
LLM-based Recommendation

## 代表工作
### 1. MAUP: Training-free Multi-center Adaptive Uncertainty-aware Prompting for Cross-domain Few-shot Medical Image Segmentation
- 研究问题：Cross-domain Few-shot Medical Image Segmentation (CD-FSMIS) models rely on heavy training procedures over source domains, degrading universality and ease of deployment. Direct application of Segment Anything Model (SAM) faces challenges in capturing complete structures, boundary awareness in low-contrast images, and adapting to varying anatomical complexities.
- 方法：MAUP (Multi-center Adaptive Uncertainty-aware Prompting) is a training-free strategy adapting SAM using DINOv2 feature encoder. It involves K-means clustering based multi-center prompts generation, uncertainty-aware prompts selection focusing on challenging regions, adaptive prompt optimization based on target complexity, and negative prompts using periphery similarity maps.
- 数据集：Abd-MRI, Abd-CT, Card-MRI
- 指标：待补充
- 可展示亮点：Achieves precise segmentation results across three medical datasets without any additional training compared with several conventional CD-FSMIS models and training-free FSMIS model. State-of-the-art performance.

### 2. EviPrompt: A Training-Free Evidential Prompt Generation Method
- 研究问题：EviPrompt: A Training-Free Evidential Prompt Generation Method
                       for Segment Anything Model in Medical Images

Yinsong Xu1,3, Jiaqi Tang2,3, Aidong Men1,, Qingchao Chen3*
                                1Beijing University of Posts and Telecommunications
                                 2The Chinese University of Hong Kong
2023                      3National Institute of Healt
- 方法：a novel method designed to automatically generate point     by adopting a more efficient method that does not require
prompts for medical images, thereby reducing the need for      external data or additional training.
- 数据集：The, SAM, Instead, We, Fr, Figure, Examples, Dataset
- 指标：accuracy, MAP
- 可展示亮点：illuminates a path for future advancements.

### 3. UncertainSAM: Fast and Efficient
- 研究问题：UncertainSAM: Fast and Efficient
                Uncertainty Quantification of the Segment Anything Model

Timo Kaiser 1 Thomas Norrenbrock 1 Bodo Rosenhahn 1

Abstract                         Input

UncertainSAM: Fast and Efficient
                Uncertainty Quantification of the Segment Anything Model

Timo Kaiser 1 Thomas Norrenbrock 1 Bodo Rosenhahn 1

Abstract                         Input
- 方法：• Introduces USAM, an estimator that outperforms ex-                                                        2.
- 数据集：USAM, UQ, Our, DAVIS, The, Large, COCO, For
- 指标：accuracy, AUC, MAP
- 可展示亮点：Our Entropy HY, HΘ, HA, HXP
          Coordinate Prompts
                               Prompt Encoder
                xP                                                                                             Output Variations
                                                                Mask Decoder

User                                                             Upsample        ˆA
    wi

### 4. AoP-SAM: Automation of Prompts for Efficient Segmentation
- 研究问题：AoP-SAM: Automation of Prompts for Efficient Segmentation

Yi Chen, Mu-Young Son, Chuanbo Hua, Joo-Young Kim

KAIST, Korea Advanced Institute of Science and Technology, Daejeon, 34141, South Korea
                                            {chenyi, kkt1690, cbhua, jooyoung1203}@kaist.ac.kr

Abstract                           The manual provision of prompts required for segmenting
- 方法：Figure 1: In SAM, automating prompt provision eliminates the need for manual input, significantly improving the efficiency of
mask segmentation.
- 数据集：AoP-SAM, Zhang, YOLOv8, Wang, Kirillov, This, Extensive, The
- 指标：accuracy, precision, MAP
- 可展示亮点：Acknowledgments                           Kirillov, A.; He, K.; Girshick, R.; Rother, C.; and Doll´ar,
                                                                             P.

### 5. This ICCV paper is the Open Access version, provided by the Computer Vision Foundation.
- 研究问题：Abstract                                    tics, have demonstrated remarkable capabilities in open-
                                                           vocabulary recognition.
- 方法：This ICCV paper is the Open Access version, provided by the Computer Vision Foundation.
- 数据集：Addition, Conversely, Trident, Query-Key, CLIP, DINO-B, Pascal, VOC
- 指标：accuracy, MAP
- 可展示亮点：in Tab.

### 6. Enhancing the Reliability of Segment Anything Model for Auto-Prompting Medical Image Segmentation with Uncertainty Rectification
- 研究问题：SAM and its medical variants require slice-by-slice manual prompting, which increases burden for applications. Existing auto-prompting attempts exhibit subpar performance and lack reliability, especially in medical imaging characterized by high structural complexity and low contrast.
- 方法：UR-SAM framework incorporating a localization framework for automatic prompt generation, a prompt augmentation module to obtain series of input prompts for uncertainty estimation, and an uncertainty-based rectification module to utilize the distribution of estimated uncertainty to improve segmentation performance without supplementary training or fine-tuning.
- 数据集：Public 3D medical dataset (22 head and neck organs), Public 3D medical dataset (13 abdominal organs)
- 指标：Dice Similarity Coefficient
- 可展示亮点：Improves segmentation performance with up to 10.7% and 13.8% in dice similarity coefficient without supplementary training or fine-tuning, demonstrating efficiency and broad capabilities for medical image segmentation without manual prompting.

## 对比总结
研究主题聚焦于 LLM-based Recommendation。 方法类别主要包括 transformer_or_llm, Training-free Few-shot Learning, Uncertainty Estimation and Auto-Prompting。 常见数据集包括 The, Abd-MRI, Abd-CT, Card-MRI, SAM。 常见评测指标包括 accuracy, MAP, AUC, precision, Dice Similarity Coefficient。 重复出现的局限主要集中在 EviPrompt: A Training-Free Evidential Prompt Generation Method for Segment Anything Model in Medical Images Yinsong Xu1,3, Jiaqi Tang2,3, Aidong Men1,, Qingchao Chen3* 1Beijing University of Posts and Telecommunications 2The Chinese University of Hong Kong 2023 3National Institute of Health Data Science, Peking University Abstract Medical image segmentation has immense clinical ap-Nov plicability but remains a challenge despite advancements in deep learning, However, it remains results, However, its truth ROIs) and others as evidence, we propose to select the application to medical images poses two significant chal- points with the highest belief mass as prompt points。

## 候选 Research Gaps
- 暂无候选研究空白。