
# # Windows
# # grass7path = r'C:\OSGeo4W64\apps\grass\grass-7.8.dev'
# grass7bin_win =
# # Linux
# grass7bin_lin = 'grass78'
# # MacOSX
# grass7bin_mac = '/Applications/GRASS/GRASS-7.8.app/'

myepsg = '4326'
#myfile = '/home/neteler/markus_repo/books/kluwerbook/data3rd/lidar/lidar_raleigh_nc_spm.shp'
myfile = r'C:\Users\edwar\Desktop\S004E027_AVE_DSM.tif'
#myfile = r'C:\Dati\Padergnone\square_p95.tif'

###########
import os
import sys
import subprocess
import shutil
import binascii
import tempfile

########### SOFTWARE
grass7bin = r'C:\Program Files\GRASS GIS 7.8\grass78.bat'

startcmd = grass7bin + ' --config path'
print(startcmd)
p = subprocess.Popen(startcmd, shell=True,
					 stdout=subprocess.PIPE, stderr=subprocess.PIPE)
out, err = p.communicate()

if p.returncode != 0:
    print(sys.stderr, 'ERROR: %s' % err)
    print(sys.stderr, "ERROR: Cannot find GRASS GIS 7 start script (%s)" % startcmd)
    sys.exit(-1)
    if out.find(b"OSGEO4W home is") != -1:
        gisbase = out.strip().split('\n')[1]
    else:
        gisbase = str(out).strip('\n')
os.environ['GRASS_SH'] = os.path.join(gisbase, 'msys', 'bin', 'sh.exe')

# Set GISBASE environment variable
os.environ['GISBASE'] = gisbase
# define GRASS-Python environment
gpydir = os.path.join(gisbase, "etc", "python")
sys.path.append(gpydir)
########
# define GRASS DATABASE
if sys.platform.startswith('win'):
    gisdb = os.path.join(os.getenv('APPDATA', 'grassdata'))
else:
    gisdb = os.path.join(os.getenv('HOME', 'grassdata'))

# override for now with TEMP dir
gisdb = os.path.join(tempfile.gettempdir(), 'grassdata')
try:
    os.stat(gisdb)
except:
    os.mkdir(gisdb)

# location/mapset: use random names for batch jobs
string_length = 16
location = binascii.hexlify(os.urandom(string_length))

mapset   = 'PERMANENT'
location_path = os.path.join(gisdb, str(location))

# Create new location (we assume that grass7bin is in the PATH)
#  from EPSG code:
startcmd = grass7bin + ' -c epsg:' + myepsg + ' -e ' + location_path
#  from SHAPE or GeoTIFF file
#startcmd = grass7bin + ' -c ' + myfile + ' -e ' + location_path

print(startcmd)
p = subprocess.Popen(startcmd, shell=True,
                     stdout=subprocess.PIPE, stderr=subprocess.PIPE)
out, err = p.communicate()
if p.returncode != 0:
    print(sys.stderr, 'ERROR: %s' % err)
    print(sys.stderr, 'ERROR: Cannot generate location (%s)' % startcmd)
    sys.exit(-1)
else:
    print('Created location %s' % location_path)

# Now the location with PERMANENT mapset exists.

########
# Now we can use PyGRASS or GRASS Scripting library etc. after
# having started the session with gsetup.init() etc

# Set GISDBASE environment variable
os.environ['GISDBASE'] = gisdb

# Linux: Set path to GRASS libs (TODO: NEEDED?)
path = os.getenv('LD_LIBRARY_PATH')
dir  = os.path.join(gisbase, 'lib')
if path:
    path = dir + os.pathsep + path
else:
    path = dir
os.environ['LD_LIBRARY_PATH'] = path

# language
os.environ['LANG'] = 'en_US'
os.environ['LOCALE'] = 'C'

# Windows: NEEDED?
#path = os.getenv('PYTHONPATH')
#dirr = os.path.join(gisbase, 'etc', 'python')
#if path:
#    path = dirr + os.pathsep + path
#else:
#    path = dirr
#os.environ['PYTHONPATH'] = path

#print os.environ

## Import GRASS Python bindings
import grass.script as grass
import grass.script.setup as gsetup

###########
# Launch session and do something
gsetup.init(gisbase, gisdb, location, mapset)

# say hello
grass.message('--- GRASS GIS 7: Current GRASS GIS 7 environment:')
print(grass.gisenv())

# do something in GRASS now...

grass.message('--- GRASS GIS 7: Checking projection info:')
in_proj = grass.read_command('g.proj', flags = 'jf')

# selective proj parameter printing
kv = grass.parse_key_val(in_proj)
print(kv)
print(kv['+proj'])

# print full proj parameter printing
in_proj = in_proj.strip()
grass.message("--- Found projection parameters: '%s'" % in_proj)

# show current region:
grass.message('--- GRASS GIS 7: Checking computational region info:')
in_region = grass.region()
grass.message("--- Computational region: '%s'" % in_region)

# do something else: r.mapcalc, v.rectify, ...

# Finally remove the temporary batch location from disk
print('Removing location %s' % location_path)
shutil.rmtree(location_path)

sys.exit(0)
