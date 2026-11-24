# 生成不含课程原始资料的四墙合成房间，可用于独立安装后的端到端演示。
from pathlib import Path
import argparse
import numpy as np


def main():
    ap=argparse.ArgumentParser();ap.add_argument('--out',default='outputs/demo.csv');args=ap.parse_args()
    rng=np.random.default_rng(7023);parts=[];step=.02
    for axis,value,length in [(0,0,3),(0,4,3),(1,0,4),(1,3,4)]:
        a,z=np.meshgrid(np.arange(.01,length,step),np.arange(.01,2.6,step))
        p=np.c_[np.full(a.size,value),a.ravel(),z.ravel()] if axis==0 else np.c_[a.ravel(),np.full(a.size,value),z.ravel()]
        if axis==1 and value==0:p=p[~((p[:,0]>1)&(p[:,0]<1.9)&(p[:,2]<2.05))]
        p[:,axis]+=.001*np.sin(p[:,2]*4)+rng.normal(0,.0002,len(p));parts.append(p)
    x,y=np.meshgrid(np.arange(.01,4,step),np.arange(.01,3,step))
    for height in [0,2.6]:parts.append(np.c_[x.ravel(),y.ravel(),np.full(x.size,height)])
    path=Path(args.out);path.parent.mkdir(parents=True,exist_ok=True)
    if path.exists():raise ValueError('Refusing to overwrite demo data')
    np.savetxt(path,np.vstack(parts),delimiter=',',header='x,y,z',comments='',fmt='%.9g')
    print(path)


if __name__=='__main__':main()
