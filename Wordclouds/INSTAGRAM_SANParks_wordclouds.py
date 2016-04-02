import os, random
from PIL import Image
import geopandas as gpd
import numpy as np
import matplotlib.pyplot as plt
from wordcloud import WordCloud, STOPWORDS, ImageColorGenerator
import sys
from fiona.crs import from_epsg
from rtree import index
from shapely.geometry import MultiPolygon
from shapely.ops import unary_union
from string import digits
from datetime import datetime
import pandas as pd
import re

def pointInPolygon(point_df, poly_df, poly_rtree, sourceColumn_in_poly, targetColumn_in_point, fast_search=True):
    """Iterates over points"""
    data = point_df
    data[targetColumn_in_point] = None
    data[targetColumn_in_point] = point_df.apply(querySpatialIndex, axis=1, poly_df=poly_df, poly_rtree=poly_rtree, source_column=sourceColumn_in_poly)
    return data

def querySpatialIndex(point, poly_df, poly_rtree, source_column):
    """Find poly containing the point"""
    point_coords = point['geometry'].coords[:][0]
    for idx_poly in poly_rtree.intersection( point_coords ):
        if poly_df['geometry'][idx_poly:idx_poly+1].values[0].contains(point['geometry']):
            return poly_df[source_column][idx_poly:idx_poly+1].values[0]
    return None

def buildRtree(polygon_df):
    idx = index.Index()
    for poly in polygon_df.iterrows():
        idx.insert(poly[0], poly[1]['geometry'].bounds)
    return idx

def convertWhiteToTransparent(png_fp):
    img = Image.open(png_fp)
    img = img.convert("RGBA")
    datas = img.getdata()
    newData = []
    # Convert white pixels (value 255 in every band) to transparent
    for item in datas:
        if item[0] == 255 and item[1] == 255 and item[2] == 255:
            newData.append((255, 255, 255, 0))
        else:
            newData.append(item)

    img.putdata(newData)
    img.save(png_fp, "PNG")

def grey_color_func(word, font_size, position, orientation, random_state=None, **kwargs):
    # Hue, saturation, light
    # http://www.december.com/html/spec/colorhsl.html
    
    # If you want to change the "root" color (e.g. from black to red) change the middle number in the tuple according to this color table
    # http://www.december.com/html/spec/colorcodes.html
    
    hsl = "hsl(0, 14%%, %d%%)" % random.randint(5, 55)
    return hsl


def createWordCloud(mask_filepath, df, label_col, label_name, text_name, outputname, suffix):
    # Read mask
    mask = np.array(Image.open(mask_filepath))

    # Ensure that all points has the same area identifier name
    if area_identifier == "Label":
        df[area_identifier] = df.ix[df[area_identifier].notnull()].copy().reset_index().loc[0, area_identifier].replace(' ', '')

    # Extract social media posts that are within the specified area
    posts = df.ix[df[label_col] == label_name]

    if area_identifier in ["SECTION", "REGION"]:
        posts[area_identifier] = posts.ix[posts[area_identifier].notnull()].copy().reset_index().loc[0, area_identifier].replace(' ', '')

    if len(posts) > 0:

        # Fill NaN
        posts[text_name].fillna("", inplace=True)
        
        # Combine posts texts to a single long string
        text = " ".join(posts[text_name]).lower()

        # Remove all digits from the text
        text = text.translate({ord(k): None for k in digits})

        # Remove stop words if they are used
        if len(STOP_WORDS) > 0:
            for stopwrd in STOP_WORDS:
                text = text.replace(stopwrd, '')

        # Remove lonely characters
        words = text.split(' ')
        cleaned = []
        
        # If text is only one character letter or otherwise nonsense, remove it
        # Notice: this will remove all Chinese/Japanese etc. words
        for word in words:
            letters = ['a', 'b', 'c', 'd', 'e', 'f', 'g', 'h', 'i', 'j', 'k', 'l', 'm', 'n', 'o', 'p', 'q', 'r', 's', 't', 'u', 'v', 'w', 'x', 'y', 'å', 'ä', '#', '_', '__', '___']
            if re.sub(r"[\W_]+", '', word) in letters:
                #print("Removed %s" % word)
                word = ""
            # Check Local
            if re.sub(r"[\W_]+", '', word, flags=re.LOCALE) in letters:
                #print("Removed %s" % word)
                word = ""
            # Check Unicode 
            if re.sub(r"[\W_]+", u'', word, flags=re.UNICODE) in letters:
                #print("Removed %s" % word)
                word = ""
            # Check
            if word.strip() in letters:
                word = ""
            cleaned.append(word)

        # Parse text again
        text = " ".join(cleaned) 

        if len(text) > 0:
            # Initialize WordCloud object
            if use_mask:
                wc = WordCloud(background_color=BACKGROUND_COLOR, max_words=WORD_COUNT, mask=mask,
                           max_font_size=MAX_FONTSIZE, random_state=1, width=WIDTH, height=HEIGHT, relative_scaling=RELATIVE_SCALING)
            else:
                wc = WordCloud(background_color=BACKGROUND_COLOR, max_words=WORD_COUNT,
                           max_font_size=MAX_FONTSIZE, random_state=1, width=WIDTH, height=HEIGHT, relative_scaling=RELATIVE_SCALING)
                
            # Generate word cloud
            wc.generate(text)

            # Create larger figure for better resolution
            plt.figure( figsize=(13,8), facecolor='k')

            # Default coloring
            #plt.imshow(mask, cmap=plt.cm.gray)

            # Gray coloring
            plt.imshow(wc.recolor(color_func=grey_color_func, random_state=3))
            plt.axis("off")
            plt.tight_layout(pad=0)

            # Create output name for Wordcloud image
            name = "Instagram_%s_%s_%s.png" % (outputname, year, suffix)
            outwc = os.path.join(wordcloud_dir, name)
                        
            plt.savefig(outwc, dpi=500, format='png')
            
            # Convert white to transparent
            if TRANSPARENT:
                convertWhiteToTransparent(outwc)
    



boundaries_list = [r"Addo\\Boundaries\\Addo_NP_Boundaries.shp",
              r"Agulhas\\Boundaries\\Aghulhas_NP.shp",
              r"Augrabies\\Boundaries\\Augrabies_NP.shp",
              r"Bontebok\\Boundaries\\Bontebok_NP_2011.shp",
              r"Camdeboo\\Boundaries\\Camdeboo_NP.shp",
              r"Garden Route\\Boundaries\\Garden_Route_2012_04_11.shp",
              r"Golden Gate\\Boundaries\\GoldenGate_NP_Boundary.shp",
              r"iSimangaliso\\iSimangaliso_NP.shp",
              r"Kalahari\\Boundaries\\Kalahari_NP_boundary.shp",
              r"Karoo\\Boundaries\\Karoo_NP_boundary_2006-06-07.shp",
              r"KNP\\Kruger_NP_boundaries_2014.shp",
              r"Mapungubwe\\Boundaries\\Mapungubwe_NP_boundary.shp",
              r"Marakele\\Boundaries\\Marakele_NP_Boundary_2015.shp",
              r"Mokala\\Boundaries\\Mokala_NP.shp",
              r"Mountain Zebra\\Boundaries\\MountainZebra_NP_Boundaries.shp",
              r"Namaqua\\Boundaries\\Namaqua_NP.shp",
              r"Richtersveld\\Boundaries\\Richtersveld_NP.shp",
              r"Table Mountain\\Boundaries\\TableMountain_NP_2010_10_21.shp",
              r"Tankwa Karoo\\Boundaries\\TankwaKaroo_NP_Boundaries.shp",
              r"West Coast\\Boundaries\\WestCoast_NP.shp"
              ]

some_paths = [r"Instagram_Addo_2013-2015_October.shp",
              r"Instagram_Agulhas_2013-2015_October.shp",
              r"Instagram_AugrabiesFalls_2013-2015_October.shp",
              r"Instagram_Bontekok_2013-2015_October.shp",
              r"Instagram_Camdeboo_2013-2015_October.shp",
              r"Instagram_GardenRoute_2013-2015_October.shp",
              r"Instagram_GoldenGateHighlands_2013-2015_October.shp",
              r"Instagram_iSimangaliso_NP_Year_2014.shp",
              r"Instagram_KalahariGemsbok_2013-2015_October.shp",
              r"Instagram_Karoo_2013-2015_October.shp",
              r"Instagram_Kruger_2013-2015_October.shp",
              r"Instagram_Mapungubwe_2013-2015_October.shp",
              r"Instagram_Marakele_2013-2015_October.shp",
              r"Instagram_Mokala_2013-2015_October.shp",
              r"Instagram_MountainZebra_2013-2015_October.shp",
              r"Instagram_Namaqua_2013-2015_October.shp",
              r"Instagram_Richtersveld_2013-2015_October.shp",
              r"Instagram_TableMountain_2013-2015_October.shp",
              r"Instagram_TankwaKaroo_2013-2015_October.shp",
              r"Instagram_WestCoast_2013-2015_October.shp"
              ]

# KRUGER ONLY
# -----------
#boundaries_list = [r"KNP\\Kruger_NP_boundaries_2014.shp"]
#some_paths = [r"Instagram_Kruger_NP_Year_2014.shp"]

some_root = r"P:\h510\some\data\south-africa\social_media\instagram\geo_search_posts\SanParks\2013-2015\IndividualParks"
#some_root = r"P:\h510\some\data\south-africa\social_media\instagram\geo_search_posts\SanParks\2014"


# File paths
boundary_root = r"P:\h510\some\data\south-africa\gis_layers\national_park_regions"

mask_dir = r"P:\h510\some\data\south-africa\images\national_park_png"
wordcloud_dir = r"P:\h510\some\figures\Wordclouds\Instagram\2013-2015Oct\200Words"
circle_fp = r"P:\h510\some\data\south-africa\Content_analysis\word_clouds\wordcloud_circle.png"

# Parameters
# ----------

# Iterate areas / combine all areas 
iterate_areas = False #True #False

# Column name that identifies the area
area_identifier = "Label" #"SECTION" #"Label"

# Time window
start_date, end_date = datetime(2008,1,1,0,0,0), datetime(2016,1,1,0,0,0)

# Year
year = "2008-2015" #start_date.year

# Flag for using simple circle mask (determine path to circle_fp variable above)
# If flag is False, the image will be the shape of the national park boundaries
circle_mask = True #False

# Flag for not using the mask and going by default settings
use_mask = True

# Irrelevant or too obvious words that should be excluded 
STOP_WORDS = ['national park', 'nationalpark', 'national', 'southern', 'southafrica', 'south',
              'africana', 'african', 'africa', 'eastern', 'east', 'western', 'west', 'northern', 'north', 'hello', 'selfie', 'instalike', 'instagood', 'instagram', 'insta', 'nofilter', 'iphoneonly',
              'photograph', 'photo', 'img_cr2', 'img_', 'img', 'dsc_', 'dsc', 'jdw_', 'jdw', 'sdc_', 'sdc', 'jpg', '_mg_', '_lutz', '_t', '_cp', '_sa', '_cr', 'jga', '*', '_', ':', ';']

# Suffix for result file
SUFFIX = '200WORDS_removedStopwords'

# Maximum amount of words to include in the WordCloud
WORD_COUNT = 200

# The size of the image
HEIGHT, WIDTH = 400, 400

# Background color
BACKGROUND_COLOR = "white"

# Use transparent background
TRANSPARENT = True

# Relative scaling of the popularity 
RELATIVE_SCALING = 0.15

# Maximum font size in the figure (if there are not enough words to fill the image, use larger font size to fill the area)
MAX_FONTSIZE = 300

for idx, boundary in enumerate(boundaries_list):
    # Parse file path
    boundary_fp = os.path.join(boundary_root, boundary)
    # Read data
    boundaries = gpd.read_file(boundary_fp)

    # Parse some file path
    some_fp = os.path.join(some_root, some_paths[idx])
    some = gpd.read_file(some_fp)

    # Create datetime index from timestamps
    try:
        some = some.sort_values(by='time_local')
        some = some.reset_index(drop=True)
        some['time'] = pd.to_datetime(some['time_local'])
        some = some.set_index(pd.DatetimeIndex(some['time']))
    except:
        some = some.sort_values(by='timestamp')
        some = some.reset_index(drop=True)
        some['time'] = pd.to_datetime(some['timestamp'])
        some = some.set_index(pd.DatetimeIndex(some['time']))

    # Take a selection
    some = some[start_date:end_date]

    # Process
    # --------

    # Ensure that the data is in same projection
    some['geometry'] = some['geometry'].to_crs(crs=boundaries.crs)

    # Create Rtree out of boundaries (for fast lookups)
    rtree = buildRtree(boundaries)

    # Make a spatial query to set the Label name for some points
    some = pointInPolygon(some, boundaries, rtree, area_identifier, area_identifier)

    # Iterate over sections
    if iterate_areas:
        for idx, row in boundaries.iterrows():
            print("Processing section: %s" % row[area_identifier])
            # Parse the path of corresponding mask png file
            area_name = row[area_identifier]
            png_name = row[area_identifier].replace(' ', '_').replace('-', '_').replace("'", '')
            name = "%s.png" % png_name
            if circle_mask:
                mask_fp = circle_fp                
            else:
                mask_fp = os.path.join(mask_dir, name)

            # Create mask PNG file
            png = gpd.GeoDataFrame(boundaries[idx:idx+1], geometry='geometry')
            # Create a plot out of the section
            png.plot()
            plt.axis("off")
            plt.savefig(mask_fp, dpi=500, alpha=False, bbox_inches='tight')
            plt.close()

            # Create Wordclouds
            posts = createWordCloud(mask_filepath=mask_fp, label_col=area_identifier, df=some, label_name=area_name, outputname=png_name, text_name='text', suffix=SUFFIX)

            
    else:
        print("Processing: %s" % os.path.basename(boundary_fp))
        # Create GeoDataFrame for boundaries
        geo = gpd.GeoDataFrame(crs=boundaries.crs)

        # Create MultiPolygon of all areas
        multipoly = unary_union(list(MultiPolygon(list(boundaries['geometry']))))
        # Insert MultiPolygon to DataFrame
        geo['geometry'] = [multipoly]
        # Insert Label name
        label = boundaries.ix[boundaries[area_identifier].notnull()].copy().loc[0, area_identifier].replace(' ', '')
        geo[area_identifier] = label
        # Save PNG
        # --------
        
        # Parse the path of corresponding mask png file
        name = "%s.png" % label
        if circle_mask:
            mask_fp = circle_fp                
        else:
            mask_fp = os.path.join(mask_dir, name)
            # Create a plot out of the section
            geo.plot()
            plt.axis("off")
            plt.savefig(mask_fp, dpi=500, alpha=False, bbox_inches='tight')
            plt.close()

        # Create Wordcloud
        createWordCloud(mask_filepath=mask_fp, label_col=area_identifier, df=some, label_name=label, outputname=label, text_name='text', suffix=SUFFIX)

    
    
    
                
            
