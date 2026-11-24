# 当前主方法来源

## Efficient RANSAC

原作者 Ruwen Schnabel、Roland Wahl、Reinhard Klein，Computer Graphics Forum (2007)，Efficient RANSAC for Point-Cloud Shape Detection。

- 源码镜像：https://github.com/alessandro-gentilini/Efficient-RANSAC-for-Point-Cloud-Shape-Detection
- 固定提交：6e8b3633c1cca8ba1cd1d36169e44d1e88dbf75b。
- 原始 ReadMe 声明用于 research purposes only；保留该使用限制，不把原版代码重新授权为 MIT。
- native/eransac_main.cpp 是我们的适配入口：完整点云、仅平面 primitive、原始点索引输出、固定记录参数。
- native/build.py 只在构建副本中把两处时钟种子改为指定 seed，并使用 POINTSWITHINDEX 和 MinGW 兼容编译选项。源仓库保持原样，构建校验提交及工作区状态。

## 法向估计

- 使用 https://github.com/abner-math/PlaneDetection，固定提交 85a64ac8584c0a870dd61973228e186885c0cda2，原项目 GPL-3.0。
- native/normals_main.cpp 调用 NormalEstimator3d::QUICK，30 邻域 PCA，对完整点云估计法向；不调用 RSPD 平面检测。
- 原始依赖源码和本地二进制不随本项目 Git 默认提交，按 README 在本机获取和编译。原始许可证适用于相应依赖。

## 本项目代码

墙体规则、共面片段支持点并集、SVD/RMS、命令行、目录、可视化及审计属于本项目后处理，不归为原版 Efficient RANSAC 输出的端到端语义能力。

room_walls/vendor/io.py 与 geometry.py 源自用户项目 civl7023-wall-flatness 提交 56407caf4d1ec3c2234c890936cbf0677f6cda51；具体哈希见 vendor_provenance.json。SVD 与点云读取复用这些代码。

Chen 等人的论文是墙体几何测量思路参考；未复制其神经网络、训练权重或声称完整复现。

每次运行保存 native/bin/manifest.json 中的构建版本、二进制/适配器哈希、运行参数、原版支持点输出哈希和输入点云哈希。room_measurement 中的五接口、洞口候选、结构交点、局部测区和报告是本项目集成代码；不属于原版检测器。主流程不恢复附近点、不做滤波。
