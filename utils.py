import bpy
import numpy as np

def edgeMapping(edge):
    eps = 1e-6
    grading1 = True
    grading2 = True
    x1,x2 = edge['x1'], edge['x2']
    r1,r2 = edge['r1'], edge['r2']
    N, L = edge['N'], edge['L']

    def both(L,N,x1,x2,r1,r2,dx):
        n1 = np.log(dx/x1) / np.log(r1) + 1
        n2 = np.log(dx/x2) / np.log(r2) + 1
        l1 = x1*(1-r1**n1)/(1-r1)
        l2 = x2*(1-r2**n2)/(1-r2)
        Lapprox = l1 + l2 + (N - n1 - n2-1)*dx
        err = (L-Lapprox)
        return err,(n1,n2,l1,l2)

    def oneside(L,N,x,r,dx):
        n = np.log(dx/x) / np.log(r) + 1
        l = x*(1-r**n)/(1-r)
        Lapprox = l + (N - n)*dx
        err = (L-Lapprox)
        return err,(n,l)

    if abs(x1) < eps or (abs(r1) - 1) < eps:
        grading1 = False
    if abs(x2) < eps or (abs(r2) - 1) < eps:
        grading2 = False

    if not grading1 and not grading2:
        edge["l1"], edge["l2"] = 0,0
        edge["n1"], edge["n2"] = 0,0
        edge["ratio1"], edge["ratio2"] = 1,1
        edge["dL"], edge["nL"] = 1, N
        return edge

    elif grading1 and not grading2:
        l1 = x1*(1-r1**N)/(1-r1)
        if l1 < L:
            n1 = np.log(1-l1/x1*(1-r1))/np.log(r1)
            n1 += 1
            dx = x1*r1**n1
            edge["l1"], edge["l2"] = L,0
            edge["n1"], edge["n2"] = n1,0
            edge["ratio1"], edge["ratio2"] = dx/x1,1
            edge["dL"], edge["nL"] = 0, 0
            return edge
        approx = oneside
        x,r = x1,r1
        dx = L/N #initial guess
        parameters = [L,N,x,r,dx]
    elif not grading1 and grading2:
        l2 = x2*(1-r2**N)/(1-r2)
        if l2 < L:
            n2 = np.log(1-l2/x2*(1-r2))/np.log(r2)
            n2 += 1
            dx = x2*r2**n2
            edge["l1"], edge["l2"] = 0,L
            edge["n1"], edge["n2"] = 0,n2
            edge["ratio1"], edge["ratio2"] = 1,dx/x2
            edge["dL"], edge["nL"] = 0, 0
            return edge
        approx = oneside
        x,r = x2,r2
        dx = L/N
        parameters = [L,N,x,r,dx]
    else:
        n1 = (np.log(x2/x1)+N*np.log(r2))/np.log(r1*r2)
        n1 = int(n1+0.5)
        n2 = N-n1-1
        l1 = x1*((1-r1**n1)/(1-r1))
        l2 = x2*((1-r2**n2)/(1-r2))
        if (l1+l2) < L:
            n1 = np.log((L*(1-r1)*(1-r2)-x1-x2+x1*r2+x2*r1)/(-2*x1+x1*r1+x1*r2))/np.log(r1)
            n2 = np.log(x1/x2*r1**n1)/np.log(r2)
            l1 = x1*((1-r1**n1)/(1-r1))
            l2 = x2*((1-r2**n2)/(1-r2))
            dx = x1*r1**n1
            n1 += 1
            n2 += 1
            edge["l1"], edge["l2"] = l1,l2
            edge["n1"], edge["n2"] = n1,n2
            edge["ratio1"], edge["ratio2"] = dx/x1, dx/x2
            edge["dL"], edge["nL"] = 0, 0
            return edge
            # l2 = (x2-x1+L-L*r1)/(2-r2-r1)
            # l1 = L - l2
            # n1 = np.log(1-l1/x1*(1-r1))/np.log(r1)
            # n2 = N-n1
        approx = both
        dx = L/N
        parameters = [L,N,x1,x2,r1,r2,dx]


    Lapprox = 0.0
    err = 1.0
    count = 0

    err,pars=approx(*parameters)
    dx_old = dx
    err_old = err
    dx = dx*1.2*1e-10 # small perturbation
    parameters[-1] = dx
    err,pars=approx(*parameters)

    while abs(err)>1e-12 and count < 1000:
        dx_temp = dx
        derr = (err - err_old)/(dx - dx_old)
        dx = dx - err/derr
        dx_old = dx_temp
        err_old = err
        parameters[-1] = dx
        err, out = approx(*parameters)
        count = count+1

    if grading1 and not grading2:
        n1,l1 = out
        ratio1 = dx/x1
        n2,l2,ratio2 = 0,0,1
    elif not grading1 and grading2:
        n2,l2 = out
        ratio2 = dx/x2
        n1,l1,ratio1 = 0,0,1
    else:
        n1,n2,l1,l2 = out
        ratio1 = dx/x1
        ratio2 = dx/x2

    if (dx < x1 and abs(x1) > eps) or (dx < x2 and abs(x2) > eps):
        dx = x1
        l1, l2 = 0,0
        n1, n2 = 0,0
        ratio1, ratio2 = 1, 1

    dL = L-l1-l2
    nL = N-n1-n2
    dx = dL/nL
    edge['l1'], edge['l2'] = l1, l2
    edge['n1'], edge['n2'] = n1, n2
    edge['ratio1'], edge['ratio2'] = ratio1, ratio2
    edge['dL'], edge['nL'] = dL, nL
    return edge

def getNodes(x1,x2,r1,r2,L,dx):
    n1 = np.log(dx/x1)/np.log(r1) + 1
    n2 = np.log(dx/x1)/np.log(r1) + 1
    l1 = x1*(1-r1**n1)/(1-r1)
    l2 = x2*(1-r2**n2)/(1-r2)
    if (l1+l2) > L:
        n1 = np.log((L*(1-r1)*(1-r2)-x1-x2+x1*r2+x2*r1)/(-2*x1+x1*r1+x1*r2))/np.log(r1)
        n1 = int(n1+0.5)+1
        n2 = np.log(x1/x2*r1**n1)/np.log(r2)
        n2 = int(n2+0.5)
        l1 = x1*((1-r1**n1)/(1-r1))
        l2 = x2*((1-r2**n2)/(1-r2))
        dx = x1*r1**n1
        return n1+n2
    else:
        return n1+n2+(L-l1-l2)/dx

def edge(e0, e1):
    return [min(e0,e1), max(e0,e1)]

def findFace(faces, vl):
    for fid, f in enumerate(faces):
        if vl[0] in f and vl[1] in f and vl[2] in f and vl[3] in f:
            return fid, f
    return -1, []


# No comments. Just works.
def getEdgeDirections(block_print_out, dependent_edges):
    edgeDirections = [set() for i in dependent_edges]
    positiveBlockEdges = [[(0,1),(3,2),(7,6),(4,5)],[(0,3),(1,2),(5,6),(4,7)],[(0,4),(1,5),(2,6),(3,7)]]
    for i in range(1000):
        ready = True
        for ed, de in zip(edgeDirections,dependent_edges):
            if not len(ed)==len(de):
                ready = False
        if ready:
            break
        for bid, vl in enumerate(block_print_out):
            for es, edgeSet in enumerate(dependent_edges):
                for direction in range(3):
                    if edge(vl[positiveBlockEdges[direction][0][0]],vl[positiveBlockEdges[direction][0][1]]) in edgeSet:
                        if not edgeDirections[es]:
                            edgeDirections[es] = set([(vl[e[0]],vl[e[1]]) for e in positiveBlockEdges[direction]])
                        else:
                            simedges = edgeDirections[es].intersection([(vl[e[0]],vl[e[1]]) for e in positiveBlockEdges[direction]])
                            if simedges:
                                edgeDirections[es] |= set([(vl[e[0]],vl[e[1]]) for e in positiveBlockEdges[direction]])
                            else:
                                asimedges= set(edgeDirections[es]).intersection([(vl[e[1]],vl[e[0]]) for e in positiveBlockEdges[direction]])
                                if asimedges:
                                    edgeDirections[es] |= set([(vl[e[1]],vl[e[0]]) for e in positiveBlockEdges[direction]])

    return edgeDirections

def sortEdges(edges):
    sorted=[]
    # Find out if the edges form a loop
    edges1D=np.ravel(edges)
    occ=np.bincount(edges1D)
    # This is a loop, let's just start sorting anywhere (from first element here)
    if len(np.where(occ==1)[0])==0:
        sorted.append(edges[0][0])
    # This is not a loop, let's find the first or last element
    else:
        # Find a vertex which occurs only 1 and then it's place in 2D list
        firstidx1D=np.where(edges1D==np.where(occ==1)[0][0])[0][0]
        if firstidx1D % 2 == 0:
            sorted.append(edges[int(firstidx1D/2)][0])
        else:
            sorted.append(edges[int((firstidx1D-1)/2)][1])
    edgesTemp = []
    vertids = []
    for e in edges:
        vertids.append(e[0])
        vertids.append(e[1])
    vertids = list(set(vertids))
    vertid=sorted[0]
    edgesTemp=edges[:]
    for i in range(len(vertids)):
        for eid, e in enumerate(edgesTemp):
            if vertid in e:
                if e[0] == vertid:
                    sorted.append(e[1])
                else:
                    sorted.append(e[0])
                edgesTemp.pop(eid)
                vertid = sorted[-1]
                break
    return sorted

def obFromStructuredMesh(verts, dim, objName):
    context = bpy.context
    nx, ny, nz = dim
    edges = []
    faces = []
    boundary_verts = []
    boundary_mes = []
    boundary_verts.append(list(verts[0:nx*ny]))
    boundary_verts.append(verts[nx*ny*nz-nx*ny:])
    boundary_verts.append(verts[::nx])
    boundary_verts.append(verts[nx-1::nx])
    boundary_verts.append([])

    for sverts in range(0,nx*ny*nz,nx*ny):
        boundary_verts[-1].extend(verts[sverts:sverts+nx])

    boundary_verts.append([])
    for sverts in range(nx*ny-nx,nx*ny*nz,nx*ny):
        boundary_verts[-1].extend(verts[sverts:sverts+nx])

    verts = [v for bv in boundary_verts for v in bv]
    boundary_faces = []
    boundary_ij = [[nx,ny], [ny,nz], [nx,nz]]
    vert_idx = 0
    # With Numpy slicing?
    for ni, nj in boundary_ij:
        bf = []
        for j in range(nj-1):
            for i in range(ni-1):
                bf.append((i+j*ni,1+i+j*ni,1+i+(1+j)*ni,i+(1+j)*ni))

        boundary_faces.append(bf)
        boundary_faces.append(bf)
        # Blender face arrays do not work with np.ints
        faces.extend((np.array(bf)+vert_idx).tolist())
        vert_idx += ni*nj

        faces.extend((np.array(bf)+vert_idx).tolist())
        vert_idx += ni*nj


    boundary_mes = [bpy.data.meshes.new('boundary_%s'%i) for i in range(6)]
    for bm, bv, bf in zip(boundary_mes, boundary_verts, boundary_faces):
        bm.from_pydata(bv, [], bf)

    vol_me=bpy.data.meshes.new('internal')
    vol_me.from_pydata(verts, edges,faces) 
    vol_me.update()

    ob = bpy.data.objects.new(objName,vol_me)
    context.scene.objects.link(ob)
    boundary_obs = []
    for i, bm in enumerate(boundary_mes):
        boundary_ob = bpy.data.objects.new(objName+ '_{}'.format(i), bm)
        boundary_ob.parent = ob
        # boundary_ob.show_all_edges = True
        # boundary_ob.show_wire = True
        context.scene.objects.link(boundary_ob)
        boundary_obs.append(boundary_ob)
    return ob


def getBlockFaces(verts):
    fids = [(0,1,5,4),(0,3,2,1),(3,7,6,2),(4,5,6,7),(0,4,7,3),(1,2,6,5)]
    faces = [(verts[f[0]],verts[f[1]],verts[f[2]],verts[f[3]]) for f in fids]
    return faces



