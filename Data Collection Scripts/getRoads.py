import geopandas as gpd
import pandas as pd

def fixRoads(road_path, output_path):
    """

    Args:
        path_to_roads (_type_): _description_
        output_path (_type_): _description_
    """
    roads = gpd.read_file(road_path)
    roads['tag']=roads.highway
    roads.to_file(output_path)

remove_roads_list = ['service'
                     ,'construction'
                     ,'living_street'
                     ,'passing_place'
                     ,'planned'
                     ,'platform'
                     ,'proposed'
                     ,'rest area'
                     ,'service'
                     ,'services'
                     ,'living_street'
                     ,'corridor'
                     ,'raceway'
                    ]

def findNewTypes(roads, road_costs_master):
    """_summary_

    Args:
        roads (_type_): _description_
        road_costs_master (_type_): _description_
    """
    road_costs = pd.read_csv(road_costs_master)
    roads = gpd.read_file(roads)
    road_costs['Road type'] = road_costs['Road type'].apply(lambda x: str(x).replace(u'\xa0', u''))
    newTypes = []
    countnewTypes = 0
    for roadtype in roads.highway.unique():
        if roadtype not in [known for known in road_costs['Road type']]:
            if roadtype not in remove_roads_list:
                countnewTypes+=1
                newTypes.append(roadtype)
    print(f'Found {countnewTypes} new road types:' )
    [print(f'{newType}') for newType in newTypes]

def saveRoadCosts(road_costs, roads, road_costs_path):
    road_costs = pd.read_csv(road_costs)
    roads = gpd.read_file(roads)
    road_costs[road_costs['Road type'].isin(roads.highway.unique())].to_csv(road_costs_path)