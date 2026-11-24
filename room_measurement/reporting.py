# 把统一测量结果写入 Word，保留候选状态、缺测原因及原始支持点 RMS。
from pathlib import Path
from docx import Document
from docx.shared import Inches,Pt,RGBColor
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.enum.table import WD_CELL_VERTICAL_ALIGNMENT


def new_document(title):
    doc=Document();section=doc.sections[0];section.page_width=Inches(8.5);section.page_height=Inches(11)
    section.top_margin=section.bottom_margin=Inches(.7);section.left_margin=section.right_margin=Inches(.7)
    for name in ['Normal','Title','Heading 1','Heading 2']:
        style=doc.styles[name];style.font.name='Calibri';style._element.get_or_add_rPr().rFonts.set(qn('w:eastAsia'),'微软雅黑')
        style.font.color.rgb=RGBColor(0,0,0)
        style.font.underline=False
        for border in list(style._element.iter(qn('w:pBdr'))):border.getparent().remove(border)
    doc.styles['Normal'].font.size=Pt(11);doc.styles['Normal'].paragraph_format.space_after=Pt(6)
    doc.add_paragraph(title,'Title');return doc


def table(doc,headers,rows):
    t=doc.add_table(rows=1,cols=len(headers));t.style='Table Grid'
    for cell,text in zip(t.rows[0].cells,headers):cell.text=str(text)
    trPr=t.rows[0]._tr.get_or_add_trPr();repeat=OxmlElement('w:tblHeader');trPr.append(repeat)
    borders=OxmlElement('w:tblBorders')
    for edge in ['top','left','bottom','right','insideH','insideV']:
        el=OxmlElement('w:'+edge);el.set(qn('w:val'),'single');el.set(qn('w:sz'),'4');el.set(qn('w:color'),'D9D9D9');borders.append(el)
    t._tbl.tblPr.append(borders)
    for row in rows:
        for c,text in zip(t.add_row().cells,row):c.text=str(text)
    widths=([1.35,5.75] if len(headers)==2 else
            [1.15,2.975,2.975] if len(headers)==3 and headers[0] in ['接口','模块'] else
            [7.1/len(headers)]*len(headers))
    t.autofit=False
    for col,width in zip(t.columns,widths):col.width=Inches(width)
    for row in t.rows:
        for cell,width in zip(row.cells,widths):
            cell.width=Inches(width);cell.vertical_alignment=WD_CELL_VERTICAL_ALIGNMENT.CENTER
            margins=OxmlElement('w:tcMar')
            for edge in ['top','left','bottom','right']:
                el=OxmlElement('w:'+edge);el.set(qn('w:w'),'80');el.set(qn('w:type'),'dxa');margins.append(el)
            cell._tc.get_or_add_tcPr().append(margins)
    for cell in t.rows[0].cells:
        shade=OxmlElement('w:shd');shade.set(qn('w:fill'),'D9E6F2');cell._tc.get_or_add_tcPr().append(shade)
        for run in cell.paragraphs[0].runs:run.bold=True
    doc.add_paragraph();return t


def write_report(result,path):
    doc=new_document('房间点云几何测量报告')
    doc.add_paragraph('本报告采用完整点云上的原版 Efficient RANSAC 支持点，经墙体规则筛选后进行 SVD 平面拟合并计算 RMS。无去噪滤波、无附近点恢复。数值是实测支持点的平面偏差，不自动代表整面实体墙的所有缺陷。')
    doc.add_paragraph('输入来源 '+str(result['provenance']['source']))
    doc.add_paragraph('点云 SHA256 '+result['provenance']['sha256'])
    doc.add_paragraph('坐标单位 m，距离及 RMS 单位 mm；点编号是原始点记录的零起始序号。')
    doc.add_heading('房间与结构状态',1)
    corners=result['structural'];dims=corners.get('room_dimensions')
    doc.add_paragraph('结构四角状态 '+corners['status']+'；'+corners.get('reason',corners.get('note','')))
    if dims:table(doc,['长 m','宽 m','高 m'],[[f"{dims[k]:.4f}" for k in ['length_m','width_m','height_m']]])
    else:doc.add_paragraph('房间长宽高待复核，不用支持点包围框替代结构尺寸。')
    doc.add_heading('墙面 RMS 汇总',1)
    def value(r):return f"{r['rms_mm']:.6f}" if r.get('status')=='ok' else '待复核'
    table(doc,['墙号','支持点 RMS','去洞口区域 RMS','整墙四角 RMS','局部 RMS'],[
        [w['wall_id'],value(w['support_rms']),value(w['surface_rms']),value(w['whole_wall_rms']),value(w['local_rms'])] for w in result['walls']])
    doc.add_paragraph('支持点 RMS 始终使用原版墙支持集。仅已确认洞口会从可用墙点中剔除；未确认的空洞只是候选，不据此更改主结果。整墙 RMS 必须通过结构四角检查；局部测区默认 1×1 m，以覆盖率选择，不按较小 RMS 挑选。')
    for w in result['walls']:
        doc.add_heading(w['wall_id']+' 测区与复核',2)
        doc.add_paragraph('原版支持点数 '+str(w['n_native_support'])+'；可用点数 '+str(w['n_available']))
        coverage=w['local_region'].get('coverage_fraction')
        doc.add_paragraph('局部测区 '+w['local_region']['status']+'；'+w['local_region'].get('reason','外部指定' if coverage is None else '覆盖率 '+str(round(coverage,3))))
        if w['openings']:
            table(doc,['洞口','状态','宽 m','高 m'],[[o.get('id','外部输入'),o['status'],f"{o.get('width_m',0):.3f}",f"{o.get('height_m',0):.3f}"] for o in w['openings']])
        else:doc.add_paragraph('未检出或未提供洞口；这不等于已证明没有门窗。')
        if w.get('structural_corners'):table(doc,['结构角点','X m','Y m','Z m'],[[i+1,*[f'{x:.4f}' for x in p]] for i,p in enumerate(w['structural_corners'])])
        if w['local_region'].get('corners_m'):table(doc,['局部角点','X m','Y m','Z m'],[[i+1,*[f'{x:.4f}' for x in p]] for i,p in enumerate(w['local_region']['corners_m'])])
    doc.add_heading('准确性与责任边界',1)
    doc.add_paragraph('门窗空洞可能由遮挡或缺失扫描形成。候选识别、四角外推和房间尺寸都需独立人工或高精度测量核验。未提供同测区真值，本报告不宣称工程精度合格；不把 RMS 更小作为更准确的依据。')
    doc.save(path)
