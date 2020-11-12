import configparser
import os, sys
import glob

grass7bin = r'"C:\Program Files\GRASS GIS 7.8\grass78.bat"'
os.environ['GRASSBIN'] = grass7bin
os.environ['PATH'] += ';' + r"C:\Program Files\GRASS GIS 7.8\lib"

from grass_session import Session
from grass.script import core as gcore

CONFIG = configparser.ConfigParser()
CONFIG.read(os.path.join(os.path.dirname(__file__), 'script_config.ini'))
BASE_PATH = CONFIG['file_locations']['base_path']


# pathlist = glob.iglob(os.path.join(BASE_PATH, 'osgb_dem_5' + '/*.asc'))
# list_of_tiles = [p for p in pathlist]
# output_dir = os.path.abspath(os.path.join(BASE_PATH, 'viewshed_tiles'))
# if not os.path.exists(output_dir):
#     os.makedirs(output_dir)
# gis_path = os.path.join(output_dir, 'gisdb')

# with Session(gisdb=gis_path, location="location", create_opts="EPSG:27700"):
#     print(gcore.parse_command("g.gisenv", flags="s"))
#     for tile in list_of_tiles:
#         base, ext = os.path.splitext(os.path.split(tile)[1])
#         tile_name = "tile_%s" % base
#         tile = os.path.join('D:\Github\e3nb', tile[:-4])
#         print(tile)
#         gcore.run_command('r.import', input=tile, output=tile_name, overwrite=True)

#     rast_list = gcore.read_command('g.list', type='rast', pattern="tile_*", separator="comma").strip().split('\n')
#     gcore.run_command('g.region', rast=rast_list, flags='p')
#     gcore.run_command('r.patch', input=rast_list, output="all_tiles")
#     gcore.run_command('r.viewshed',flags='b',input=all_tiles, output="viewshed",
#         coordinates=[202699, 747787], overwrite=True)



# import grass.script as grass
filename = 'S004E026_AVE_DSM_projected.tif' #'S004E027_AVE_DSM.tif'
path = os.path.join(BASE_PATH, filename)
output_dir = os.path.join(BASE_PATH)
gis_path = os.path.join(BASE_PATH, 'test')
# list_of_tiles = ['data/S004E026_AVE_DSM.tif', 'data/S004E027_AVE_DSM.tif']
list_of_tiles = ['S004E027_AVE_DSM.tif', 'S004E026_AVE_DSM.tif']#,

with Session(gisdb=gis_path, location="location", create_opts="EPSG:3857"):

    print('parse command')
    print(gcore.parse_command("g.gisenv", flags="s", set="DEBUG=3"))

    print('r.external')
    # now link a GDAL supported raster file to a binary raster map layer,
    # from any GDAL supported raster map format, with an optional title.
    # The file is not imported but just registered as GRASS raster map.
    gcore.run_command('r.external', input=path, output='test_output', overwrite=True)

    print('r.external.out')
    #write out as geotiff
    gcore.run_command('r.external.out', directory=output_dir, format="GTiff")

    print('r.region')
    #manage the settings of the current geographic region
    gcore.run_command('g.region', raster='test_output')

    print('r.viewshed')
    gcore.run_command('r.viewshed',
            input='test_output',
            output='viewshed',
            coordinate= [2901221, -372990],#[27.5, -3.5],
            # obs_elev=1.75,
            # tgt_elev=0.0,
            # memory=4098,
            # overwrite=True,
            # quiet=True
            max_distance=0.5
    )


# def load_raster_files(list_of_tiles, output_dir, x_transmitter, y_transmitter):

#     #specify output path
#     gis_path = os.path.join(output_dir, 'gisdb')

#     #combine site coordinates
#     transmitter_coords = str(x_transmitter) + ',' + str(y_transmitter)

#     if not os.path.exists(output_dir):
#         os.makedirs(output_dir)

#     with Session(gisdb=gis_path, location="location", create_opts="EPSG:27700"):

#         print(gcore.parse_command("g.gisenv", flags="s"))

#         print('load tiles')
#         for tile in list_of_tiles:
#             base, ext = os.path.splitext(os.path.split(tile)[1])
#             tile_name = "tile_%s" % base
#             print(tile)
#             gcore.run_command('r.import', input=tile, output=tile_name, overwrite=True)

#         rast_list = gcore.read_command(
#             'g.list', type='rast', pattern="tile_*", separator="comma"
#             ).strip()

#         print(rast_list)
#         gcore.run_command('r.external.out', flags="r")

#         print('r.patch')
#         gcore.run_command('r.patch', input=rast_list, output="all_tiles", overwrite=True)

#         print('r.viewshed')
#         gcore.run_command(
#             'r.viewshed', flags='b', input="all_tiles", output="viewshed",
#             coordinates=[27.5, -3.5], overwrite=True,
#             )
#         gcore.run_command('r.external.out', flags="r")

#     return print('files loaded')


# if __name__ == '__main__':

#     # import grass.script as grass
#     # filename = 'S004E027_AVE_DSM.tif'
#     # path = os.path.join(BASE_PATH, filename)
#     output_dir = os.path.join(BASE_PATH)

#     # list_of_tiles = ['data/S004E026_AVE_DSM.tif', 'data/S004E027_AVE_DSM.tif']
#     # list_of_tiles = ['data/S004E027_AVE_DSM.tif', 'data/S004E026_AVE_DSM.tif']#,
#     list_of_tiles = [r'D:\Github\e3nb\data\osgb_dem_5\NN04NE.asc', r'D:\Github\e3nb\data\osgb_dem_5\NN04NW.asc']

#     pathlist = glob.iglob(os.path.join(BASE_PATH, 'osgb_dem_5' + '/*.asc'))
#     pathlist = [p for p in pathlist]

#     print('Loading raster files')
#     load_raster_files(pathlist, output_dir, 202699, 747787) #27.5, -3.5)



# def generate_viewshed(x_transmitter, y_transmitter, output_dir, filename, tile_path):

#     if not os.path.exists(output_dir):
#         os.makedirs(output_dir)

#     gis_path = os.path.join(output_dir, 'gisdb')

#     output_filename = '{}-viewshed.tif'.format(filename)

#     transmitter_coords = str(x_transmitter) + ',' + str(y_transmitter)

#     with Session(gisdb=gis_path, location="location", create_opts="EPSG:27700"):

#         gcore.run_command('r.external', input=tile_path, output=filename, overwrite=True)
#         # gcore.run_command('r.external.out', directory=output_dir, format="GTiff")
#         # gcore.run_command('g.region', raster=filename)
#         # gcore.run_command(
#         #     'r.viewshed', flags='b', input=filename, output=output_filename,
#         #     coordinates=transmitter_coords, overwrite=True
#         #     )
#         # gcore.run_command('r.external.out', flags="r")

# if __name__ == '__main__':

#     output_dir = os.path.join(BASE_PATH, 'test2')
#     filename = 'NN04NE.asc'
#     tile_path = os.path.join(BASE_PATH, 'osgb_dem_5')#'D:\Github\e3nb\data\osgb_dem_5'

#     generate_viewshed(202699, 747787, output_dir, filename, tile_path)











# list_of_tiles = ['S004E026_AVE_DSM_projected.tif']#['NN05NE.asc']#,
# output_dir = os.path.join(BASE_PATH, 'test')
# tile_path = os.path.join(BASE_PATH, list_of_tiles[0])
# # pathlist = glob.iglob(os.path.join(BASE_PATH + '/*'))

# # for tile_id in pathlist:
# #     print(tile_id)

# filename = list_of_tiles[0]
# gis_path = os.path.join(output_dir, 'gisdb')
# output_filename = '{}-viewshed.tif'.format(filename)
# transmitter_coords = str(2902614) + ',' + str(-371418)#str(26.500) + ',' + str(-3.500) #str(206311) + ',' + str(756691) #

# with Session(gisdb=gis_path, location="location", create_opts="EPSG:3857"):

#     print(gcore.parse_command("g.gisenv", flags="s", set="DEBUG=3"))

#     # now link a GDAL supported raster file to a binary raster map layer,
#     # from any GDAL supported raster map format, with an optional title.
#     # The file is not imported but just registered as GRASS raster map.
#     gcore.run_command('r.external', input=tile_path, output=filename, overwrite=True)

#     #write out as geotiff
#     gcore.run_command('r.external.out', directory=output_dir, format="GTiff")

#     #manage the settings of the current geographic region
#     gcore.run_command('g.region', raster=filename)

#     #
#     gcore.run_command('r.viewshed',flags='b',input=filename,output=output_filename,
#         coordinates=transmitter_coords, overwrite=True, max_distance=1000)

#     gcore.run_command('r.external.out', flags="r")




# def load_raster_files(list_of_tiles, output_dir, x_transmitter, y_transmitter):

#     print('Specifying output path')
#     gis_path = os.path.join(output_dir, 'gisdb')

#     print('Combining site coordinates')
#     transmitter_coords = str(x_transmitter) + ',' + str(y_transmitter)

#     if not os.path.exists(output_dir):
#         os.makedirs(output_dir)

#     print('Starting Session')
#     with Session(gisdb=gis_path, location="location", create_opts="EPSG:4326"):

#         print(gcore.parse_command("g.gisenv", flags="s"))

#         # for tile in list_of_tiles:
#         #     base, ext = os.path.splitext(os.path.split(tile)[1])
#         #     tile_name = "tile_%s" % base
#         #     gcore.run_command('r.import', input=tile, output=tile_name, overwrite=True)

#         gcore.run_command('r.import', input=list_of_tiles[0], output=tile_name, overwrite=True)

#         rast_list = gcore.read_command(
#             'g.list', type='rast', pattern="tile_*", separator="comma"
#             ).strip()

#         gcore.run_command('r.external.out', flags="r")

#         gcore.run_command('r.patch', input=rast_list, output="all_tiles", overwrite=True)
#         gcore.run_command(
#             'r.viewshed',flags='b',input="all_tiles", output="viewshed",
#             coordinates=transmitter_coords, overwrite=True
#             )
#         gcore.run_command('r.external.out', flags="r")

#     return print('files loaded')


# if __name__ == '__main__':

#     list_of_tiles = ['data/S004E026_AVE_DSM.tif', 'data/S004E027_AVE_DSM.tif']
#     # list_of_tiles = ['S004E026_AVE_DSM.tif']#, 'S004E027_AVE_DSM.tif']
#     output_dir = os.path.join(BASE_PATH, 'test')

#     print('Loading raster files')
#     load_raster_files(list_of_tiles, output_dir, 27.5, -3.5)
