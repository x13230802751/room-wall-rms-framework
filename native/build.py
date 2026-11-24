# 编译原版 Efficient RANSAC 和仅用于完整点云法向估计的辅助程序，保存构建来源。
from pathlib import Path
import argparse
import hashlib
import json
import subprocess

ROOT=Path(__file__).resolve().parent
COMMITS={'EfficientRANSAC':'6e8b3633c1cca8ba1cd1d36169e44d1e88dbf75b',
         'PlaneDetection':'85a64ac8584c0a870dd61973228e186885c0cda2'}


def main():
    ap=argparse.ArgumentParser();ap.add_argument('--source-root',required=True);args=ap.parse_args()
    source=Path(args.source_root).resolve();build=ROOT/'build';binary=ROOT/'bin'
    build.mkdir(exist_ok=True);binary.mkdir(exist_ok=True)
    for name,commit in COMMITS.items():
        path=source/name
        actual=subprocess.check_output(['git','-c',f'safe.directory={path.as_posix()}','-C',str(path),'rev-parse','HEAD'],text=True).strip()
        dirty=subprocess.check_output(['git','-c',f'safe.directory={path.as_posix()}','-C',str(path),'status','--porcelain'],text=True).strip()
        if actual!=commit or dirty:raise ValueError(f'Source must be clean at pinned commit: {name}')
    src=source/'EfficientRANSAC';original=(src/'RansacShapeDetector.cpp').read_text()
    patched=original.replace('srand((unsigned int)time(NULL));','srand((unsigned int)atoi(getenv("RANSAC_BENCHMARK_SEED")));').replace('rn_setseed((size_t)time(NULL));','rn_setseed((size_t)atoi(getenv("RANSAC_BENCHMARK_SEED")));')
    if patched==original:raise ValueError('Seed patch did not apply')
    seedfile=build/'RansacShapeDetector_seed.cpp';seedfile.write_text(patched)
    files=[str(p) for p in src.glob('*.cpp') if p.name not in ['main.cpp','RansacShapeDetector.cpp']]+[str(p) for p in (src/'MiscLib').glob('*.cpp')]
    er=['g++','-O3','-std=gnu++11','-fpermissive','-w','-UWIN32','-DPOINTSWITHINDEX','-include',str(ROOT/'mingw_compat.h'),'-I',str(src),'-I',str(src/'MiscLib'),*files,str(seedfile),str(ROOT/'eransac_main.cpp'),'-o',str(binary/'eransac.exe')]
    ns=source/'PlaneDetection';cpp=ns/'CommandLine/src'
    normals=['g++','-O3','-std=c++11','-w','-I',str(cpp),'-I',str(ns/'eigen3'),str(cpp/'connectivitygraph.cpp'),str(ROOT/'normals_main.cpp'),'-o',str(binary/'normals.exe')]
    commands=[]
    for name,cmd in [('normals',normals),('eransac',er)]:
        p=subprocess.run(cmd,cwd=ROOT,capture_output=True,text=True)
        (build/f'{name}.log').write_text(p.stdout+p.stderr,encoding='utf-8')
        if p.returncode:raise RuntimeError(f'{name} build failed: '+p.stderr[-3000:])
        commands.append(cmd);print(f'Built {name}',flush=True)
    sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
    manifest=dict(source_commits=COMMITS,commands=commands,
        compiler=subprocess.check_output(['g++','--version'],text=True).splitlines()[0],
        binaries={p.name:sha(p) for p in binary.glob('*.exe')},
        adapters={p.name:sha(p) for p in [ROOT/'eransac_main.cpp',ROOT/'normals_main.cpp',ROOT/'mingw_compat.h',Path(__file__)]},
        seed_patch_sha256=sha(seedfile))
    (binary/'manifest.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8')


if __name__=='__main__':main()
