import tempfile
import os
import numpy as np
import subprocess
import shutil
import itertools
import glob
from . import utils
class PreviewMesh():
    def __init__(self, blockMeshDictPath=None):
        if not shutil.which('blockMesh'):
            raise RuntimeError('ERROR: No BlockMesh Found!')
            # openfoams = glob.glob('/opt/openfoam*')
            # for of in openfoams:
                # try:
                    # ofdir = glob.glob(of+'/platforms/*')[0]
                    # self.blockMeshbin = ofdir + '/bin/blockMesh'
                    # os.environ["LD_LIBRARY_PATH"] = ofdir+'/lib/:'
                    # os.environ["LD_LIBRARY_PATH"] += ofdir+'/lib/openmpi-system/:'
                    # os.environ["LD_LIBRARY_PATH"] += ofdir+'/lib/dymmy/:'
                    # print (os.environ["LD_LIBRARY_PATH"])
                # except e:
        else:
            self.blockMeshbin = 'blockMesh'
        if blockMeshDictPath:
            self.blockMeshDictPath = blockMeshDictPath
        else:
            self.tempdir = tempfile.mkdtemp()
            self.blockMeshDictPath = self.tempdir+"/system/blockMeshDict"
            os.mkdir(self.tempdir+'/constant')
            os.mkdir(self.tempdir+'/constant/polyMesh')
            os.mkdir(self.tempdir+'/system')
            os.mkdir(self.tempdir+'/0')
            cd = open(self.tempdir+'/system/controlDict','w')
            cd.write(self.header())
            print('OpenFOAM temp directory: {}'.format(self.tempdir))

    def writeBlockMeshDict(self, verts, convertToMeters, patchnames, polyLines, edgeInfo, blockNames, blocks, dependent_edges, block_faces):
        patchfaces = []
        for pn in patchnames:
            for vl in pn[2]:
                patchfaces.append(vl)
        bmFile = open(self.blockMeshDictPath,'w')
        bmFile.write(self.header())
        bmFile.write("\nconvertToMeters " + str(convertToMeters) + ";\n\nvertices\n(\n")

        for v in verts:
            bmFile.write('    ({} {} {})\n'.format(*v))
        bmFile.write(");\nblocks\n(\n")
        NoCells = 0

        edge = lambda e0,e1: [min(e0,e1), max(e0,e1)]

        for bid, (vl, blockName) in enumerate(zip(blocks, blockNames)):
            # blockName = ''
            # for name in reversed(vertexNames):
                # if all( v in name[1] for v in vl ):
                    # blockName = name[0]
            edges = [(vl[e[0]],vl[e[1]]) for e in [(0,1),(3,2),(7,6),(4,5),(0,3),(1,2),(5,6),(4,7),(0,4),(1,5),(2,6),(3,7)]]
            gradingStr = ""
            for ei in edges:
                e = edgeInfo[ei]
                gradingStr+='\n(\n ({:.6g} {:.6g} {:.6g}) ({:.6g} {:.6g} {:.6g}) ({:.6g} {:.6g} {:.6g}) '.format(
                e["l1"],e["n1"],e["ratio1"],\
                e["dL"],e["nL"],1,\
                e["l2"],e["n2"],1/e["ratio2"]) + '\n)'
            ires = edgeInfo[edges[0]]["N"]
            jres = edgeInfo[edges[4]]["N"]
            kres = edgeInfo[edges[8]]["N"]

            NoCells += ires*jres*kres
            bmFile.write('// block id {} \nhex ({} {} {} {} {} {} {} {}) '.format(bid,*vl) \
                       + blockName + ' ({} {} {}) '.format(ires,jres,kres)\
                       + 'edgeGrading (' + gradingStr + '\n)\n' )
        bmFile.write(');\n\npatches\n(\n')
        for pn in patchnames:
            if not len(pn[2]) == 0:
                bmFile.write('    {} {}\n    (\n'.format(pn[0],pn[1]))
                for pl in pn[2]:
                    # fid, tmp = utils.findFace(block_faces, pl)
                    # if fid >= 0:
                        # if (len(face_info[fid]['neg']) + len(face_info[fid]['pos'])) == 1: #avoid printing internal faces and patches in non-identified blocks as patch
                            # bmFile.write('        ({} {} {} {})\n'.format(*pl))
                    bmFile.write('        ({} {} {} {})\n'.format(*pl))
                bmFile.write('    )\n')

        bmFile.write(');\n\nedges\n(\n')
        for pl in polyLines:
            bmFile.write(pl)
        bmFile.write(');')
        bmFile.close()
        return NoCells


    def readHeader(self,dicfile):
        numberOfFields = 0
        startLine = False
        with open(dicfile) as fin:
            for lidx,line in enumerate(fin):
                if not numberOfFields:
                    try:
                        numberOfFields = int(line)
                    except ValueError:
                        pass
                if '(' in line:
                    startLine = lidx + 1
                    break
        return startLine, numberOfFields

    def readBoundaries(self,files):
        data = []
        readingField = False
        for line in files:
            if not line.strip():
                continue
            if not readingField and line.strip() == '{':
                readingField = True
            elif not readingField:
                temp = dict()
                temp['name']= line.strip()
            elif readingField and 'type' in line:
                temp['type'] = line.strip().split()[1][:-1]
            elif readingField and 'nFaces' in line:
                temp['nFaces'] = int(line.strip().split()[1][:-1])
            elif readingField and 'startFace' in line:
                temp['startFace'] = int(line.strip().split()[1][:-1])
            elif readingField and line.strip() == '}':
                data.append(temp)
                readingField = False
            elif not readingField and line.strip() == ')':
                break
        return data

    def getPoints(self,faces=None):
        pointsFile = self.tempdir +'/constant/polyMesh/points'
        startLine, numberofLines = self.readHeader(pointsFile)
        convertfnc1 = lambda x: float(x[1:])
        convertfnc2 = lambda x:float(x[:-1])
        with open(pointsFile,'rb') as fin:
            points = np.genfromtxt(itertools.islice(fin,startLine,startLine+numberofLines),\
                converters={0:convertfnc1,2:convertfnc2},dtype=float)
        if faces!=None:
            pidxs = np.unique(np.ravel(faces))
            points = points[pidxs]
        points=points.tolist()
        return points

    def getFaces(self):
        facesFile = self.tempdir +'/constant/polyMesh/faces'
        startLine, numberofLines = self.readHeader(facesFile)
        convertfnc1 = lambda x: int(x[2:])
        convertfnc2 = lambda x: int(x[:-1])
        with open(facesFile,'rb') as fin:
            faces = np.genfromtxt(itertools.islice(fin,startLine,startLine+numberofLines),\
                converters={0:convertfnc1,3:convertfnc2},dtype=int)
        faces = faces.tolist()
        return faces

    def getBCFaces(self,internalCells):
        faces = self.getFaces()
        bcifaces = faces
        bcfaces = faces
        if not internalCells:
            boundaryFile = self.tempdir + '/constant/polyMesh/boundary'
            startLine, boundaries = self.readHeader(boundaryFile)
            with open(boundaryFile) as fin:
                fields = self.readBoundaries(itertools.islice(fin,startLine,None))
            self.fields = fields
            bcifaces = []
            bcfaces=[]
            for bc in sorted(fields, key=lambda k: k['startFace']):
                bcfaces.extend(faces[bc['startFace']:bc['startFace']+bc['nFaces']])
            bcifaces = np.array(bcfaces,dtype=int)
            bcifaces = np.unique(bcifaces.ravel(),return_inverse=True)[1].reshape(bcifaces.shape)
            bcifaces = bcifaces.astype(int).tolist()
        return bcfaces,bcifaces

#this is faster
    def getBCFaces2(self,internalCells):
        facesFile = self.tempdir +'/constant/polyMesh/faces'
        startLine, numberofLines = self.readHeader(facesFile)
        faces = open(facesFile).readlines()
        faces = faces[startLine:startLine+numberofLines]
        subs = lambda s: list(map(int,s.__getitem__(slice(2,-2)).split()))
        faces = list(map(subs, faces))
        boundaryFile = self.tempdir + '/constant/polyMesh/boundary'
        startLine, boundaries = self.readHeader(boundaryFile)
        with open(boundaryFile) as fin:
            fields = self.readBoundaries(itertools.islice(fin,startLine,None))
        self.fields = fields
        bcifaces = []
        bcfaces=[]
        for bc in sorted(fields, key=lambda k: k['startFace']):
            bcfaces.extend(faces[bc['startFace']:bc['startFace']+bc['nFaces']])
        bcifaces = np.array(bcfaces,dtype=int)
        bcifaces = np.unique(bcifaces.ravel(),return_inverse=True)[1].reshape(bcifaces.shape)
        bcifaces = bcifaces.astype(int).tolist()
        return bcfaces,bcifaces

    def runBlockMesh(self):
        subprocess.call([self.blockMeshbin,'-case',self.tempdir],stdout=subprocess.PIPE)

    def runMesh(self,runBlockMesh=True,internalCells=False):
        print('running blockmesh')
        if runBlockMesh:
            self.runBlockMesh()
        faces, bcifaces=self.getBCFaces2(internalCells)
        points=self.getPoints(faces)
        # shutil.rmtree(self.tempdir)
        return points, bcifaces

    def header(self):
        return \
        '''
/*--------------------------------*- C++ -*----------------------------------*/

// File was generated by SwiftBlock, a Blender 3D addon.

FoamFile
{
    version     2.0;
    format      ascii;
    class       dictionary;
    object      blockMeshDict;
}
// * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * //


deltaT          1;

writeInterval   1;



// ************************************************************************* //

'''
