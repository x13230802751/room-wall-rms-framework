// Run Schnabel's Efficient RANSAC with plane primitives and preserve original point indices.
#include <PointCloud.h>
#include <RansacShapeDetector.h>
#include <PlanePrimitiveShapeConstructor.h>
#include <PlanePrimitiveShape.h>
#include <fstream>
#include <iostream>
#include <iomanip>
#include <cstdlib>
int main(int argc,char** argv){
    if(argc!=4){std::cerr<<"input.xyzn output.txt seed\n";return 2;}
    PointCloud pc;std::ifstream in(argv[1]);float x,y,z,nx,ny,nz;
    Vec3f lo(1e30f,1e30f,1e30f),hi(-1e30f,-1e30f,-1e30f);
    while(in>>x>>y>>z>>nx>>ny>>nz){
        Point p(Vec3f(x,y,z),Vec3f(nx,ny,nz));p.index=pc.size();pc.push_back(p);
        for(int j=0;j<3;++j){lo[j]=std::min(lo[j],p.pos[j]);hi[j]=std::max(hi[j],p.pos[j]);}
    }
    if(pc.size()<500)return 3;pc.setBBox(lo,hi);
    // The patched two seed calls read this variable; the detector itself is unchanged.
    std::string env=std::string("RANSAC_BENCHMARK_SEED=")+argv[3];putenv(&env[0]);
    RansacShapeDetector::Options opt;
    opt.m_epsilon=.004f;opt.m_bitmapEpsilon=.03f;opt.m_normalThresh=.9f;
    opt.m_minSupport=500;opt.m_probability=.001f;
    RansacShapeDetector detector(opt);detector.Add(new PlanePrimitiveShapeConstructor());
    MiscLib::Vector<std::pair<MiscLib::RefCountPtr<PrimitiveShape>,size_t>> shapes;
    size_t left=detector.Detect(pc,0,pc.size(),&shapes);
    std::ofstream out(argv[2]);out<<std::setprecision(9)<<shapes.size()<<'\n';size_t end=pc.size();
    for(size_t k=0;k<shapes.size();++k){
        // The adapter refits planes in float64 later; a zero header is explicitly marked unused.
        out<<"0 0 0 0 0 0 "<<shapes[k].second<<'\n';
        size_t begin=end-shapes[k].second;
        for(size_t i=begin;i<end;++i)out<<pc[i].index<<' ';out<<'\n';end=begin;
    }
    std::cout<<"Points "<<pc.size()<<", planes "<<shapes.size()<<", unassigned "<<left<<'\n';
    return out.good()?0:4;
}
