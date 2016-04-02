import geopandas as gpd
import pandas as pd
import os
import matplotlib.pyplot as plt

# File paths
mask_fp = r"P:\h510\some\data\south-africa\gis_layers\national_park_regions\KNP\Kruger_Mask.shp"
sections_fp = r"C:\HY-Data\HENTENKA\AfricaNPs\gis_layers\Kruger\section_boundaries_2014.shp"
out_fold = r"C:\HY-Data\HENTENKA\AfricaNPs\gis_layers\Kruger\section_masks"
png_fold = r"C:\HY-Data\HENTENKA\AfricaNPs\gis_layers\Kruger\section_masks\PNG_no_color"

# Read data
mask = gpd.read_file(mask_fp)
sect = gpd.read_file(sections_fp)

# Iterate over sections and create mask with a whole that corresponds to section
# Masks are created to be able to produce PNG images of the sections with the terrain
for idx, value in sect.iterrows():
    # Create a GeoDataFrame for results
    #geo = gpd.GeoDataFrame(crs=sect.crs)
    # Create a whole to mask layer and set the output as 'geometry' of result GDF
    #geo['geometry'] = mask['geometry'].difference(value['geometry'])
    # Set name attribute to the mask file
    #geo['SECTION'] = value['SECTION']
    
    # Output name
    name = "%s_mask.shp" % value['SECTION'].replace(' ', '_').replace('-', '_').replace("'", '')
    output = os.path.join(out_fold, name)

    # Save data to disk
    #geo.to_file(output)

    # Save a simple png to disk
    pngname = "%s.png" % value['SECTION'].replace(' ', '_').replace('-', '_').replace("'", '')
    pngout = os.path.join(png_fold, pngname)
    png = gpd.GeoDataFrame(sect[idx:idx+1], geometry='geometry')

    # Create a plot out of the section
    png.plot()
    plt.axis("off")
    plt.savefig(pngout, dpi=300, alpha=False, bbox_inches='tight')
    plt.close()
    
    
    


