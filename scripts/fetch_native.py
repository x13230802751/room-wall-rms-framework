# 下载固定版本的原始算法依赖，已存在的目录只核验不覆盖。
from pathlib import Path
import subprocess

ROOT=Path(__file__).resolve().parents[1]
SOURCES=[('EfficientRANSAC','https://github.com/alessandro-gentilini/Efficient-RANSAC-for-Point-Cloud-Shape-Detection.git','6e8b3633c1cca8ba1cd1d36169e44d1e88dbf75b'),
         ('PlaneDetection','https://github.com/abner-math/PlaneDetection.git','85a64ac8584c0a870dd61973228e186885c0cda2')]


def main():
    root=ROOT/'native/sources';root.mkdir(exist_ok=True)
    for name,url,commit in SOURCES:
        target=root/name
        if not target.exists():
            subprocess.run(['git','clone',url,str(target)],check=True)
            subprocess.run(['git','-C',str(target),'checkout',commit],check=True)
        head=subprocess.check_output(['git','-C',str(target),'rev-parse','HEAD'],text=True).strip()
        if head!=commit:raise SystemExit(f'{name} is at another commit; existing source was not modified')
        print(name,head)


if __name__=='__main__':main()
