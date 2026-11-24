# 命令行入口：读取完整房间或已审计目录，运行五接口框架并生成统一结果。
import argparse
import json
from pathlib import Path
import sys
from .pipeline import run
from .segmentation import from_catalog


def main():
    ap=argparse.ArgumentParser(description='Full cloud -> Efficient RANSAC -> room framework -> RMS, no filtering')
    source=ap.add_mutually_exclusive_group(required=True);source.add_argument('--cloud');source.add_argument('--catalog')
    ap.add_argument('--unit',choices=['m','mm']);ap.add_argument('--up',nargs=3,type=float,default=[0,0,1])
    ap.add_argument('--out',required=True);ap.add_argument('--annotations');ap.add_argument('--json-only',action='store_true')
    args=ap.parse_args()
    if args.cloud and args.unit is None:ap.error('--unit is required with --cloud')
    try:
        annotations=None if not args.annotations else json.loads(Path(args.annotations).read_text(encoding='utf-8-sig'))
        room=from_catalog(args.catalog) if args.catalog else None
        result=run(args.cloud,args.unit or 'm',args.up,args.out,annotations=annotations,room=room,write_docx=not args.json_only)
        print(json.dumps(dict(out=str(Path(args.out).resolve()),n_wall_candidates=result['n_wall_candidates'],
            structural_status=result['structural']['status'],walls=[dict(wall=w['wall_id'],support_rms_mm=w['support_rms'].get('rms_mm'),
            local_status=w['local_rms']['status'],opening_candidates=len(w['openings'])) for w in result['walls']]),ensure_ascii=True))
        return 0
    except (ValueError,OSError,KeyError,TypeError) as e:print('ERROR:',e,file=sys.stderr);return 2


if __name__=='__main__':sys.exit(main())
