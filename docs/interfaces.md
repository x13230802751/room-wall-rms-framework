# 五接口对接规范

版本 1.0。输入单个房间，不要求四角点。内部 XYZ 与所有角点统一为米，RMS 为毫米；原始点编号是零起始点记录序号，不是 PCD 文件的物理文本行号。

## 公共数据

`Room` 定义于 `room_measurement/contracts.py`：`xyz_m` 为原始顺序 N×3 坐标，`walls` 为候选墙字典列表，`floor/ceiling` 为参考平面，`up` 为归一化向上向量，`provenance` 保存来源 SHA256、单位和点数。原始非有限点位置保留在编号空间，但不参与计算。

每个墙字典包含 `id`、`support_indices`、`plane_center_m`、`plane_normal`、`u`、`v`、`native_plane_ids`。`support_indices` 精确指向原版 Efficient RANSAC 的支持点，不得按距离补点。`u/v` 是正交单位墙面坐标轴。原始点坐标只根据索引取回，不能把投影点或平滑点当成测量坐标。

## 五个函数

| 接口 | Python 函数签名 | 返回内容 |
|---|---|---|
| 分墙 | `split_room(source, unit, up)` | `Room`，完整原版支持点与墙规则结果；无模型训练、无滤波、无恢复带 |
| 门窗 | `detect_openings(room, wall)` | 列表，每项包含 id、wall_id、status、kind、corners_m、width_m、height_m、center_m；自动结果是 candidate |
| 墙角 | `structural_corners(room)` | status、walls、room_dimensions；闭合失败或角点离实测点太远时 needs_review |
| 局部区域 | `select_local_region(room, wall, indices, openings)` | status、corners_m、coverage_fraction、selection_rule；默认 1×1 m、50 mm 诊断网格、覆盖率≥80% |
| RMS | `calculate_rms(room, wall, indices, corners_m=None)` | status、rms_mm、n_selected、拟合面、point_indices、selected_xyz_m、signed_distance_mm |

局部网格只用来选择空间区域，不是点云降采样或去噪。RMS 在最终几何区域内重新拟合，保留全部传入的原始支持点，不作残差删点，也没有 50 mm 厚度带。

`corners_m` 是按边界循环排列的四点，必须形成凸四边形并在墙参考面 10 mm 容差内。该容差检查角点几何合法性，不用于删除测量点。ROI 只按墙平面二维投影相交；不对测量点设置额外法向距离门槛。

## 替换队友模块

```python
from room_measurement.contracts import Interfaces
from room_measurement.pipeline import run

def teammate_openings(room, wall):
    # Return [] if no opening is identified; do not label scan occlusions as confirmed.
    return []

result = run(
    source='room.pcd', unit='m', up=(0, 0, 1), out='outputs/team_run',
    interfaces=Interfaces(openings=teammate_openings),
)
```

`Interfaces` 的五个可选字段为 split、openings、corners、local、rms，未替换项使用默认实现。总控仅承诺上述契约，不推测尚未提供的其他总控代码的函数签名。

## 外部门窗及测区文件

第一次运行后从 `result.json` 取点云 SHA256 和墙号，创建以下 JSON。以下坐标只是格式示意，不能直接用于官方点云。

```json
{
  "schema_version": 1,
  "source_sha256": "replace_with_result_provenance_sha256",
  "coordinate_unit": "m",
  "walls": {
    "W01": {
      "openings": [{
        "id": "D01", "status": "confirmed", "kind": "door",
        "corners_m": [[0,1,0],[0,2,0],[0,2,2],[0,1,2]]
      }],
      "local_corners_m": [[0,0,0.5],[0,1,0.5],[0,1,1.5],[0,0,1.5]]
    }
  }
}
```

使用 `--annotations file.json`。SHA 不符、未知墙号、非米坐标标记或无效四边形会报错。confirmed 表示调用者已确认该区域是要排除的洞口，不代表软件自动验证了人工判断。candidate 不会从主支持点结果中删除，但局部选区会避开它，以免测区跨过疑似开口。

## 输出分层

- `support_rms`：原版墙支持点 RMS，始终保持主方法定义。
- `surface_rms`：从支持集排除 confirmed 洞口投影后的 RMS；没有确认洞口时与 support_rms 相同。
- `whole_wall_rms`：结构四角可靠时，在四角内的可用原始墙点上计算；否则 needs_review，不伪造数值。
- `local_rms`：默认自动 1×1 m 或外部明确四点区域内的可用原始墙点 RMS。

`result.json` 给出全部状态、测区和数值。`Wxx/indices.npz` 保存 native_support 与 available，逐测区 CSV 保存 original_index、XYZ 和 signed_distance_mm。`report.docx` 汇总洞口候选、结构四角、房间尺寸、各类 RMS 和复核原因。没有真值时不输出虚假的误差或准确率。
