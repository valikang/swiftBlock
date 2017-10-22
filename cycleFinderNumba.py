from numba import jit
import numpy as np

# @jit(nopython=True)
def still_coupling(dependent_edges):
    for es0 in range(len(dependent_edges)):
        edgeSet0 = dependent_edges[es0]
        for edge in edgeSet0:
            for es1 in range(len(dependent_edges)):
                edgeSet1 = dependent_edges[es1]
                if edge in edgeSet1 and es0 != es1:
                    for e in edgeSet0:
                        edgeSet1.append(e)
                    dependent_edges.pop(es0)
                    return True
    return False

def couple_edges(dependent_edges):
    while still_coupling(dependent_edges):
        pass

def cycleFinder(edges,verts):
    verticesId = np.array(verts)
    edges = np.array(edges)
    edgeVisited = np.zeros(len(edges), dtype=bool)
    faces = [-1] # For Numba the arrays have to contain element
    facesEdges = [-1]
    no_edges = 0

    # 50 is the limit of vertices in one edge. Should be enough, maybe too many?
    v_in_edge = np.ones((len(verticesId),50),dtype=int) * -1
    for v in verticesId:
        for eid, e in enumerate(edges):
            if v in e:
                v_in_edge[v][np.where(v_in_edge[v] == -1)[0][0]] = eid

    run(verticesId,edges,edgeVisited,faces,facesEdges,no_edges, v_in_edge)

    # Clean double faces
    faces = np.reshape(faces[1:],(-1,4))
    temp, u = np.unique(np.sort(faces), axis=0, return_index=True)
    faces = faces[u]
    facesP = [list(map(np.asscalar,f)) for f in faces]

    facesEdges = np.reshape(facesEdges[1:],(-1,4))
    facesEdges = facesEdges[u]
    facesEdgesP = [list(map(np.asscalar,f)) for f in facesEdges]

    return facesP, facesEdgesP

@jit(nopython=True)
def run(verticesId,edges,edgeVisited,faces,facesEdges,no_edges, v_in_edge):
    for v in verticesId:
        currentCycle = [v]
        currentCycleEdges = [-1]
        buildFourEdgeFaces(v, edgeVisited, edges, no_edges, currentCycle, currentCycleEdges, faces, facesEdges, v_in_edge, first=True)

@jit(nopython=True)
def buildFourEdgeFaces(v, edgeVisited, edges, no_edges, currentCycle, currentCycleEdges, faces, facesEdges, v_in_edge, first=False):
    for eid in v_in_edge[v]:
        if eid == -1:
            break
        e = edges[eid]
        if v == e[0]:
            opposite_v = e[1]
        elif v == e[1]:
            opposite_v = e[0]
        else:
            continue
        if not edgeVisited[eid]:
            no_edges += 1
            edgeVisited[eid] = True
            currentCycle.append(opposite_v)
            if first:
                currentCycleEdges[0] = eid
                first = False
            else:
                currentCycleEdges.append(eid)
            if currentCycle[0] == currentCycle[-1]: # First equals last -> we have a face
                # we are only interested in quads
                if len(currentCycle) == 5:
                    faces.extend(currentCycle[0:4])
                    facesEdges.extend(currentCycleEdges[0:4])
            else:
                if no_edges < 4:
                    buildFourEdgeFaces(opposite_v, edgeVisited, edges, no_edges, currentCycle, currentCycleEdges, faces, facesEdges, v_in_edge)
            no_edges -= 1
            currentCycle.pop()
            currentCycleEdges.pop()
            edgeVisited[eid] = False
