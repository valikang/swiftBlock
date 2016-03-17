import tempfile
import os
import numpy as np
import bpy
import subprocess
import shutil
import itertools
class PreviewMesh():
    def __init__(self, tempdir=None):
        if not shutil.which('blockMesh'):
            raise RuntimeError('ERROR: No BlockMesh Found!')
        if tempdir:
            self.tempdir = tempdir
        else:
            self.tempdir = tempfile.mkdtemp()
            os.mkdir(self.tempdir+'/constant')
            os.mkdir(self.tempdir+'/constant/polyMesh')
            os.mkdir(self.tempdir+'/system')
            os.mkdir(self.tempdir+'/0')
            cd = open(self.tempdir+'/system/controlDict','w')
            cd.write(self.header())

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
            bcifaces = []
            bcfaces=[]
            for bc in sorted(fields, key=lambda k: k['startFace']):
                bcfaces.extend(faces[bc['startFace']:bc['startFace']+bc['nFaces']])
            bcifaces = np.array(bcfaces,dtype=int)
            bcifaces = np.unique(bcifaces.ravel(),return_inverse=True)[1].reshape(bcifaces.shape)
            bcifaces = bcifaces.astype(int).tolist()
        return bcfaces,bcifaces

    def runBlockMesh(self):
        subprocess.call(['blockMesh','-case',self.tempdir])#,stdout=subprocess.PIPE)

    def generateMesh(self,runBlockMesh=True,internalCells=False):
        if runBlockMesh:
            self.runBlockMesh()
        faces, bcifaces=self.getBCFaces(internalCells)
        points=self.getPoints(faces)
        blocking=bpy.context.active_object
        blocking.hide = True
        blocking.select = False
        mesh_data = bpy.data.meshes.new("swiftBlockMesh")
        self.previewMesh = bpy.data.objects.new('swiftBlockObj', mesh_data)
        self.previewMesh['swiftBlockObj'] = bpy.context.active_object.name
        scn = bpy.context.scene
        scn.objects.link(self.previewMesh)
        scn.objects.active = self.previewMesh
        self.previewMesh.select = True
        mesh_data.from_pydata(points, [],bcifaces)
        mesh_data.update()
        shutil.rmtree(self.tempdir)

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
