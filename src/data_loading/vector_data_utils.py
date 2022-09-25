# Web scraping
from http.cookiejar import DefaultCookiePolicy
import requests
import urllib

# Handling geojson files
import geopandas as gpd

# Others
from typing import List
import zipfile
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
from data_loading.utils import *
from data_loading.tif_links_utils import 

def get_vector_data_links(hurricane_name = DEFAULT_HURRICANE, toprint = True) -> List:
    """
    Get a list of vector data links for the hurricane with hurricane_name
    The list must exist on github
    """
    filename = hurricane_name + FILE_LIST_SUFFIX
    file_list_path = FILE_LIST_PREFIX + filename
    response = requests.get(file_list_path)
    assert response.status_code == 200, f"Unsuccessful request! Status code: {response.status_code}"
    data = response.text 
    assert data != None, "No data!"
    L = data.split("\n")
    links = [link.strip() for link in L if ".zip" in link]
    print_message(toprint, f"There are in total {len(links)} links.")
    return links

def load_vector_data_link(vector_data_link, hurricane_name = DEFAULT_HURRICANE):
    """
    Given a link to the vector data, will download the (zip) file & extract it 
    Will save the file in the correct directory in /data
    """
    # Download and extract the zip file
    filename = vector_data_link.split("/")[-1] # name of the zip file
    destination_dir = os.path.join(PATH_TO_DATA_RAW, f"{hurricane_name}-vector-data")
    destination_path = os.path.join(destination_dir, filename[:-4]+"geojson")
    
    if not os.path.isdir(destination_dir):
        os.mkdir(destination_dir)
    if not os.path.isfile(filename):
        urllib.request.urlretrieve(vector_data_link, filename=filename)

    with zipfile.ZipFile(filename, 'r') as zip_ref:
        zip_ref.extractall(destination_path)

    # After extraction, delete the zip file
    os.remove(os.path.join(PATH_TO_DIR,filename))
    return destination_dir

def find_all_files_with_extension_in_dir(dirname, extension, files = []):
    """
    Given a directory, finds a list of paths to files with extension 
    
    EXAMPLE:
    --- 
    Using extension = ".geojson", will return a list of paths to all
    geojson files in the directory 
    """
    for name in os.scandir(dirname):
        if os.path.isdir(name):
            files = find_all_files_with_extension_in_dir(name.path, extension, files)
        else:
            if os.path.isfile(name):
                extension = os.path.splitext(name)[1]
                if extension==".geojson":
                    files.append(name.path)
    return files

def load_all_vector_data_for_hurricane(hurricane_name = DEFAULT_HURRICANE, toprint = True) -> List:
    """
    RETURNS
    ---
        geojson_files: a list of paths to all the geojson files related to hurricane_name
    """
    links = get_vector_data_links(hurricane_name, toprint)
    count = len(links)
    print_message(toprint, "Extracting files...")
    for (link, idx) in zip(links, list(range(count))):
        print_message(toprint, f"{idx+1}/{count}")
        destination_dir = load_vector_data_link(link, hurricane_name)
    print_message(toprint, f"Extracted files can be found in {destination_dir}")
    geojson_files = find_all_files_with_extension_in_dir(destination_dir, ".geojson")
    print_message(toprint, f"There are {len(geojson_files)} geojson files available")
    return geojson_files

def combine_all_vector_data_and_save_for_hurricane(hurricane_name = DEFAULT_HURRICANE, toprint = True):
    """
    Combines all geojson files for the hurricane into one geojson file
    The combined file will be saved in data/processed/geojson
    """
    print_message(toprint, f"Retrieving all geojson files for hurricane {hurricane_name}...")
    geojson_files = load_all_vector_data_for_hurricane(hurricane_name, toprint)
    assert len(geojson_files) > 0, f"No geojson files available for hurricane {hurricane_name}!"
    path = geojson_files.pop()
    res = gpd.read_file(path)
    while len(geojson_files) > 0:
        path = geojson_files.pop()
        res.append(gpd.read_file(path))
    # We only keep the points
    # for which we have image data
    print_message(toprint, f"There are {len(res)} buildings in total before trimming")


def trim_gdf(gdf: gpd.GeoDataFrame):
    """
    This trims down the geodataframe 
    We only keep the points that we have image for
    """

    