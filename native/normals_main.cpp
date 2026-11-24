// Estimate original k=30 normals only; no RSPD plane detection is executed.
#include <pointcloudio.hpp>
#include <planedetector.h>
#include <normalestimator.h>
#include <boundaryvolumehierarchy.h>
#include <connectivitygraph.h>
#include <fstream>
#include <iostream>
#include <iomanip>
#include <chrono>
int main(int argc,char** argv) {
    if(argc!=3) {std::cerr<<"input.xyz normals.xyzn\n";return 2;}
    PointCloudIO io;
    PointCloud3d* pc=io.loadFromXYZ(argv[1]);
    if(!pc || pc->size()<30) return 3;
    Octree octree(pc);octree.partition(10,30);
    ConnectivityGraph* graph=new ConnectivityGraph(pc->size());pc->connectivity(graph);
    NormalEstimator3d est(&octree,30,NormalEstimator3d::QUICK);
    std::ofstream normals(argv[2]);normals<<std::setprecision(9);
    for(size_t i=0;i<pc->size();++i){
        auto n=est.estimate(i);graph->addNode(i,n.neighbors);
        (*pc)[i].normal(n.normal);(*pc)[i].normalConfidence(n.confidence);(*pc)[i].curvature(n.curvature);
        const auto& p=(*pc)[i].position();
        normals<<p[0]<<' '<<p[1]<<' '<<p[2]<<' '<<n.normal[0]<<' '<<n.normal[1]<<' '<<n.normal[2]<<'\n';
    }
    normals.close();std::cout<<"Normals complete: "<<pc->size()<<std::endl;
    delete pc;return normals.good()?0:4;
}
