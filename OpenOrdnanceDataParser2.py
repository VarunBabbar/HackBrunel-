import bs4
import convertbng.util
import networkx as nx
import sys
from Density_Map_Traffic_Data import accident_density_mapg
import numpy as np
import geocoder

sys.setrecursionlimit(50000)
with open("OSOpenRoads_SM.gml", 'r') as fp:
    sp = bs4.BeautifulSoup(fp.read(), 'xml')

road_links = sp.select('road|RoadLink')
road_nodes = sp.select('road|RoadNode')


def location_of_node(node):
    EN = node.pos.text.split(' ')
    long_lat = (0,0)
    
    a = convertbng.util.convert_lonlat(float(EN[0]), float(EN[1]))
    long_lat = (a[0][0], a[1][0])
    return long_lat

location_to_node = {location_of_node(road_node) : road_node for road_node in road_nodes}

node_to_id = {}
G = nx.MultiGraph()
#n = 0
for rd_node in road_nodes:
    G.add_node(location_of_node(rd_node))
    
#    node_to_id[rd_node] = n
    
#    n += 1
c = 0
for rd_link in road_links:
    poss = [float( s) for s in rd_link.posList.text.split(' ')]

    long_lats = convertbng.util.convert_lonlat( poss[0::2], poss[1::2] )

    path = [(long_lats[0][i], long_lats[1][i]) for i in range(len(long_lats))]
    
    _length = int(rd_link.length.text)
    
    try:
        if location_of_node(rd_link.startNode) == path[0]:
            if c > 100:
                break
            c += 1
            print('good')
    except:
        pass

    if path[0] in G.nodes:
        node1 = path[0]
    else:
        G.add_node(path[0])
        node1 = path[0]


    if path[-1] in G.nodes:
        node2 = path[-1]
    else:
        G.add_node(path[-1])
        node2 = path[-1]
    G.add_edge(node1, node2, points=path, length = _length)

def distance(pt_1, pt_2):
    pt_1 = np.array((pt_1[0], pt_1[1]))
    pt_2 = np.array((pt_2[0], pt_2[1]))
    return np.linalg.norm(pt_1-pt_2)

def closest_node(node, nodes):
    pt = []
    dist = 9999999
    for n in nodes:
        if distance(node, n) <= dist:
            dist = distance(node, n)
            pt = n
    return pt

def risk_dictionary(nodal_data):
    original_dictionary = nodal_data
    risk_dictionary = {}
    grad, latitude_matrix,longitude_matrix,unrolled_latitude,unrolled_longitude, unrolled_density = accident_density_mapg()
    coordinates = list(zip(unrolled_longitude, unrolled_latitude))
    compilation = list(zip(coordinates, unrolled_density))
    nodal_data = list(nodal_data.values())
    risk_function = {}

    for i in range(len(nodal_data)):
        point1 = nodal_data[i][0]
        point2 = nodal_data[i][1]
        close_point1 = closest_node(point1, coordinates)
        idx1 = coordinates.index(close_point1)
        density1 = compilation[idx1][1]
        close_point2 = closest_node(point2, coordinates)
        idx2 = coordinates.index(close_point2)
        density2 = compilation[idx2][1]
        density = 0.5*(density1+density2)
        risk_function[tuple(nodal_data[i])] = density

    risk_of_edge = {}
    for edge in G.edges:
        pts = original_dictionary[edge]
        sum = 0
        for i in range(len(pts)-1):
            sum += risk_function[(pts[i], pts[i+1])]

        avg = sum / (len(pts) -1)

        risk_of_edge[edge] = avg

    return risk_of_edge


nodal_data = nx.get_edge_attributes(G,'points')
risks = risk_dictionary(nodal_data)
# print(a)




def ReturnOptimalPath(_start_lon_lat, _end_lon_lat, _L, risks):
    nodes = list(G.nodes)
    edges = G.edges


    start_lon_lat = _start_lon_lat
    end_lon_lat   = _end_lon_lat

    L = _L

    def distance(x, y):
        return (x[0] - y[0])*(x[0] - y[0]) + (x[1] - y[1])*(x[1] - y[1])

    i_min = 0
    min_value = distance(start_lon_lat, nodes[0])

    for i in range(len(nodes)):
        #if distance(start_lon_lat, nodes[i]) < min_value:
        if distance(start_lon_lat, nodes[i]):
            i_min = i
            min_value = distance(start_lon_lat, nodes[i])

    start_node = nodes[i_min]

    i_min = 0
    min_value = distance(end_lon_lat, nodes[0])

    for i in range(len(nodes)):
        #if distance(start_lon_lat, nodes[i]) < min_value:
        if distance(end_lon_lat, nodes[i]):
            i_min = i
            min_value = distance(end_lon_lat, nodes[i])

    end_node = nodes[i_min]

    lengths_dict = nx.get_edge_attributes(G, 'length')

    M = max(list(lengths_dict.values()))
    lengths = { edge : lengths_dict[edge]/M for edge in edges }

    weights = { edge : (L * risks[edge]) + lengths[edge] for edge in edges }


    H = nx.Graph()
    H.add_nodes_from(G)

    min_weight_for_nodes = {}

    for edge in G.edges:
        u = edge[0]
        v = edge[1]

        if (u, v) in min_weight_for_nodes:
            min_weight_for_nodes[(u, v)] = min( min_weight_for_nodes[(u, v)], weights[edge] )
        else:
            min_weight_for_nodes[(u, v)] = weights[edge]

    for key in min_weight_for_nodes.keys():
        H.add_edge(key[0], key[1], weight=min_weight_for_nodes[key])

    shortest_path = [(start_node[0]/2 + end_node[0]/2, start_node[1]/2 + end_node[1]/2)]

    grad, latitude_matrix,longitude_matrix,unrolled_latitude,unrolled_longitude, unrolled_density = accident_density_mapg()
    gradmax = np.amax(grad)

    result = np.where(grad == gradmax)
    result = (result[0][0], result[1][0])

    longitude = longitude_matrix(result[0],result[1])
    latitude = latitude_matrix(result[0],result[1])
    vector = [longitude-shortest_path[0][0], latitude - shortest_path[0][1]] - shortest_path;
    shortest_path = [shortest_path[0][0]+(_L**(1/2))*vector[0], shortest_path[0][1]+(_L**(1/2))*vector[1]]

    i_min = 0
    min_value = distance(start_lon_lat, nodes[0])

    for i in range(len(nodes)):
        if distance(start_lon_lat, nodes[i]) < min_value:
            #if distance(start_lon_lat, nodes[i]):
            i_min = i
            min_value = distance(start_lon_lat, nodes[i])

    outpt = nodes[i_min]

    return [start_lon_lat] + [nx.shortest_path(H, start_node, end_node)[0]] + [end_lon_lat]

g = geocoder.ipinfo('me')
input_latitude = g.latlng[0]
input_longitude = g.latlng[1]

print(ReturnOptimalPath((-5.2886835,51.87768652),(-5.269568,51.885629),0, risk_dictionary(nodal_data)))
