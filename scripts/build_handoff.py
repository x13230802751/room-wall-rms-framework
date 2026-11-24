# 根据已完成验证生成中文任务分工说明与可交付 Word 文档。
from pathlib import Path
import json
import sys
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from room_measurement.reporting import new_document,table


def main():
    evidence=json.loads((ROOT/'results/integration_verification.json').read_text(encoding='utf-8'))
    assert evidence['status']=='passed'
    doc=new_document('房间点云测量框架与个人任务说明')
    pages=[]
    def p(text):doc.add_paragraph(text);pages.append(text+'\n')
    def h(text):doc.add_heading(text,1);pages.append('## '+text+'\n')
    def t(headers,rows):
        table(doc,headers,rows);pages.append('| '+' | '.join(headers)+' |\n|'+ '|'.join(['---']*len(headers))+'|\n'+'\n'.join('| '+' | '.join(map(str,row))+' |' for row in rows)+'\n')
    def page():doc.add_page_break()
    p('本说明面向负责墙面粗糙度的小组成员和总框架集成人员。我们已把完整房间点云到墙面 RMS 的方法接入一套五接口框架，并保留门窗、墙角、局部测区的替换入口。主方法固定使用原版 Efficient RANSAC 的支持点，不增加滤波或附近点恢复。')
    p('“接口可以接通”和“所有工程测量结果已经达到准确度要求”是两件事。当前分墙与 RMS 已用 M04、M26 完整输入验证；门窗默认输出几何候选，结构四角证据不足时明确待复核，不能用估计结果冒充实体真值。')
    h('一 课程 Task 1 总共要完成什么')
    p('以课程 2026 CIVL 7023_Project1_Requirements.pdf 第 3 页为准，Task 1 的目标结果是房间长宽高、门窗宽高和墙面粗糙度。第 4 页还要求几何测量文献综述、框架创新性和合理测量表现，特别是测量误差。首页的拉孔和预埋件等是典型测量项目举例，不宜自行全部扩为本模块必交项。')
    t(['工作','小组需交付的内容'],[
        ['总体方案','说明点云如何经过识别、选区、计算，得到可核查结果'],
        ['房间尺寸','长、宽、高及定义；可靠平面或角点；不能只报点云包围框'],
        ['门窗尺寸','洞口身份、位置、宽高和边界；遮挡与空洞区分'],
        ['墙面粗糙度','每面墙的测量区域、原始点和 RMS 数值'],
        ['评价与展示','文献、实现说明、结果、真值差异与失败案例；按课程安排准备展示和书面材料']])
    p('你上传的框架图是小组实现架构：分墙、门窗、墙角、局部测区、RMS 五接口，最后生成 Word 报告。它不是课程原文逐项规定的算法，五个接口可以各自替换。Project 1 的 Task 2 是另一项 YOLO 任务，不在本文墙面粗糙度工作范围内。')
    page();h('二 你这一块具体做什么')
    p('你的核心任务可以一句话说明：输入一个完整房间的点云，自动提取墙面候选，使用这些墙面的原版支持点计算粗糙度 RMS，并把点坐标、编号、参考平面和结果交给总框架。你不需要先手动选四个点；自动结构角点与局部角点由对应接口提供。')
    t(['类别','具体约定'],[
        ['必须输入','单房间 PCD 或带 x,y,z 表头的 CSV；明确坐标单位 m/mm；默认 +Z 向上，也可指定 up'],
        ['可选输入','队友确认的门窗四角；特定局部测区四角；替换的五接口函数'],
        ['主要输出','墙候选数量和墙号；每墙 support_rms；原始点序号、XYZ、拟合平面和点到面的距离'],
        ['框架输出','洞口候选、结构角点状态、房间尺寸状态、1×1 m 局部区域、各区域 RMS、JSON 和 Word'],
        ['单位与编号','内部 XYZ/角点为米，RMS 为毫米；原始编号从 0 起，是点记录序号而不是文件文本行号']])
    p('“支持点”是原版 Efficient RANSAC 判断属于某个平面的那些输入点。“取回原始点”指按这些索引回到原始点云取 XYZ，不是在平面附近再找一圈点。算法内部使用随机抽样找平面，但给算法的输入是完整有限点云，没有预先体素降采样。')
    p('建议分工：你负责原版检测接入、墙体规则、支持点来源、SVD/RMS 和该部分误差评估。队友负责或确认门窗语义、真实测区/角点、房间尺寸验证和总体展示。当前仓库提供了这些模块的可运行几何候选版本，便于集成，不代表已经替队友完成了全部实体精度验证。')
    page();h('三 我们采用的方法与五接口')
    p('处理顺序：读取完整点云并统一单位 → 全部有限点估计 30 邻域 PCA 法向 → 原版 Efficient RANSAC 仅提取平面 → 方向、尺寸和接地规则筛墙 → 保留原始支持点 → SVD 拟合 → RMS。相近共面片段可以仅对已有支持点取并集，不加入新点。')
    p('对选定点集先求平均中心 c，再用 SVD 得到最佳拟合面的单位法向 n。每个点 p 到面的正交距离为 d=(p−c)·n，RMS=1000×sqrt(mean(d²))。乘 1000 是从米转为毫米。这个数表示实际点集对最佳平面的偏离程度，不能自动等同直尺检测或工程合格判断。')
    t(['接口','当前实现','需要注意'],[
        ['分墙','完整点云原版支持点与墙规则','墙号是本次运行编号，仍可能误检或漏检'],
        ['门窗','连续空洞、边界线拟合候选','空洞可能是遮挡；仅 confirmed 区域用于几何排除'],
        ['墙角','本墙、邻墙与地/顶面相交','四墙闭合和最近实测点距离检查不过则待复核'],
        ['局部测区','覆盖率优先的 1×1 m 区域','默认覆盖率至少 80%，避开洞口；不挑 RMS 最小的地方'],
        ['RMS','可用原始支持点与四角相交后重拟合','不平滑、不按残差删点、不使用法向恢复带']])
    p('图中的“保留洞口外原始墙点”是空间测量域的定义，不是去噪滤波。默认未确认的洞口候选不会更改 support_rms；确认后得到单独的 surface_rms。局部与整墙四角内测量也单独标识，避免把不同点集的 RMS 混为同一个指标。')
    p('我们参考 Chen 的几何测量思路，但没有其语义网络和训练权重。准确名称是 Efficient RANSAC 加墙体规则与支持点 RMS，不是完整 Chen 模型复现。')
    page();h('四 目前已经完成哪些工作')
    p('已完成稳定的函数接口、来源哈希和原始索引约定，增加门窗候选、结构四角质量检查、局部测区、外部确认区域输入、统一 JSON/CSV 输出和 Word 报告。缺少顶面或结构支持时进入框架图的“整墙待复核”分支，不填造假的四角。')
    rows=[]
    for r in evidence['records']:
        rows.append([r['room'],str(r['n_input']),str(r['n_wall_candidates']),str(sum(w['local_status']=='ok' for w in r['walls'])),r['structural_status']])
    t(['房间','输入点数','墙候选','有效局部区','结构四角'],rows)
    t(['房间','墙号','原版支持点 RMS mm'],[[r['room'],w['wall'],f"{w['support_rms_mm']:.6f}"] for r in evidence['records'] for w in r['walls']])
    p('8 面墙的支持点集合均独立核对为原版输出对应支持点的并集，原始坐标与点号一致。RMS 也用协方差特征值法独立复算。实测结果与此前原版 Efficient RANSAC 支持点实验一致。数值计算验证通过，不能据此宣称物理测量精度已经得到证明。')
    p('M04 的照片对应候选 W01 为 1.351416 mm；M26 门对面候选 W03 为 1.142207 mm。官方 1.8/1.0 mm 参考缺少精确测区边界，现阶段只能报告参考差异，不称作同测区真实误差。')
    page();gt_start=len(pages);h('官方 GT 与当前墙面 RMS 对照')
    p('课程数据说明给出了两面指定墙的人工测量 GT：M04 配图标出的墙为 1.8 mm，M26 门对面的墙为 1.0 mm。下表将这些官方值与当前无滤波主方法的 support_rms 并列。墙号采用本仓库 M04、M26 完整点云验证运行的编号，换参数或换运行后应重新核对墙身份。')
    comparison=[]
    for room,wid,gt in [('M04','W01',1.8),('M26','W03',1.0)]:
        record=next(r for r in evidence['records'] if r['room']==room)
        wall=next(w for w in record['walls'] if w['wall']==wid)
        measured=wall['support_rms_mm'];delta=measured-gt
        comparison.append([room+' / '+wid,f'{gt:.1f}',f'{measured:.6f}',f'{delta:+.6f}',f'{abs(delta):.6f}',f'{abs(delta)/gt*100:.2f}%'])
    t(['房间 / 墙号','官方 GT mm','我们计算 mm','有符号差 mm','绝对差 mm','相对绝对差'],comparison)
    p('有符号差 = 我们的 RMS − 官方 GT；绝对差 = |有符号差|；相对绝对差 = 绝对差 / 官方 GT × 100%。差异使用未舍入计算值计算，表格保留六位小数便于复查，不代表实体测量精度达到六位小数。M04 的结果低于参考值，M26 的结果高于参考值。')
    p('来源：课程数据 project/data/readme(1).md 的 Ground-Truth Measurements 部分，M26 的 Wall flatness (RMS) 行（第 27 行）和 M04 的同名行（第 39 行）。说明称 GT 来自人工测量，但未给出精确测区四角、原始测点集合和完整测量规程。M04 按配图墙候选映射为 W01；M26 按门对面墙候选映射为 W03。这是当前几何与照片对应关系，不是官方提供的算法墙号。')
    p('我们的数值来源：results/integration_verification.json 中对应墙的 support_rms_mm；原始完整运行结果保存在本地 outputs/M04_full/result.json 和 outputs/M26_full/result.json。M04 W01 使用 113162 个原版支持点，M26 W03 使用 136039 个原版支持点。方法为 Efficient RANSAC 支持点 → 墙体规则 → SVD → RMS，无滤波、无附近点恢复。这里不使用 local_rms，也不使用四角裁剪后的 whole_wall_rms。')
    p('评价边界：上述是相对于官方 GT 的参考差异。当前尚未严格确认官方测区与算法支持集完全一致，因此不能将它直接认定为同测区算法误差或据此声称工程精度合格。应先确认墙身份与测区边界，再用同测区参考值评估。原版检测器对支持点的筛选可能排除真实表面偏差，RMS 更小不等于更准确。')
    (ROOT/'docs/gt_comparison.md').write_text('\n'.join(pages[gt_start:]),encoding='utf-8')
    page();h('五 总框架如何使用你的成果')
    p('仓库： https://github.com/x13230802751/room-wall-rms-framework 。这是新仓库，旧仓库保持不变。原始课程点云、课件、旧实验和本地依赖不上传。可先使用仓库提供的合成房间生成脚本验证安装。')
    p('安装顺序：Git 克隆 → Python 虚拟环境 → pip install -e . → scripts/fetch_native.py 获取固定原版源码 → native/build.py 编译 → python -m room_measurement 运行。当前验证平台为 Windows 和 MinGW g++，详细命令见 README。')
    p("运行示例：python -m room_measurement --cloud room.pcd --unit m --up 0 0 1 --out outputs/my_room。输出目录必须为空或不存在。程序默认同时写 result.json 和 report.docx。")
    t(['文件或入口','作用'],[
        ['room_measurement.pipeline.run','总控入口，完整点云直接走通五接口'],
        ['Interfaces','替换 split/openings/corners/local/rms 任一模块'],
        ['docs/interfaces.md','函数参数、返回值、单位、原始点号、JSON 与失败状态约定'],
        ['result.json','机器可读汇总，包含各测量域及复核状态'],
        ['Wxx/*.csv 和 indices.npz','原始点索引、坐标、逐点距离，支持结果追溯'],
        ['report.docx','洞口候选、结构四角、局部区域与各类 RMS 的可读报告']])
    p('接队友的门窗算法时，只替换 openings 回调，返回带墙号、状态和米单位四角的列表。也可用 annotations JSON 提供已确认洞口和局部测区，必须写入匹配点云 SHA256、schema_version=1、coordinate_unit=m。坐标或点云来源不一致会报错。')
    p('截至本次对接，没有收到框架图对应的其他主程序源码。因此当前验收针对按图建立的接口契约与新总控；若队友已有不同函数签名，需按接口文档增加字段映射，不能宣称已验证尚未提供的外部代码。')
    page();h('六 还需要小组完成什么')
    p('第一，确认实际墙身份和测区。墙号是算法编号，不能按哪个 RMS 更接近参考值来选墙。请把照片、点云位置、墙面四角或人工区域标签对应起来，并统一整墙还是局部区域的定义。')
    p('第二，复核门窗候选和结构角点。门窗可由扫描空缺或遮挡形成；当前几何算法输出候选，确认后再用其尺寸和排除区域。真实房间的结构四角未通过支持距离检查时，应由队友改进结构识别或补充可靠几何输入。')
    p('第三，提供独立参考评价。建议分别评价墙实例检出、点集 Precision/Recall/IoU、角点距离误差、门窗/房间尺寸误差，以及相同测区的 RMS 绝对误差、MAE/RMSE。漏墙和失败样本要进入统计，不能只挑成功结果。')
    p('第四，补齐课程文献综述、方法选择理由、创新点、失败案例和展示材料。图中的 Word 报告是测量结果输出，不自动替代课程要求的完整项目说明。课程安排如有额外展示或提交要求，以老师通知为准。')
    p('当前方法的限制必须保留：原版检测器可能把真实鼓包排除在支持点外，因此低 RMS 不一定表示整面墙更平；固定参数对稀疏和遮挡场景仍可能漏墙。此前滤波研究未证明普遍收益，本次发布不接入滤波实验。')
    p('交付判断：你的模块已经具备完整点云到墙面支持点 RMS 的运行能力，并已与图示总框架的五接口、测区传递及报告链路接通。整个 Task 1 的最终工程准确性验收，仍需要小组完成同测区真值、门窗和房间尺寸的独立验证。')
    doc.save(ROOT/'docs/项目总体框架与个人任务说明.docx')
    (ROOT/'docs/handoff.md').write_text('# 房间点云测量框架与个人任务说明\n\n'+'\n'.join(pages),encoding='utf-8')
    print('Saved handoff DOCX and Markdown')


if __name__=='__main__':main()
