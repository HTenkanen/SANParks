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


def createWordCloud(mask_filepath, df, label_col, label_name, text_name, suffix):
    # Read mask
    mask = np.array(Image.open(mask_filepath))

    # Extract social media posts that are within the section
    posts = df.ix[df[label_col] == label_name]

    # Remove rows where there is no text
    posts = posts.ix[posts[text_name].notnull()]

    if len(posts) > 0:

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
        
        # If text is only one characters long, remove it
        for word in words:
            if len(word.replace(' ', '')) < 2:
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
            name = "Flickr_%s_%s_%s.png" % (label_name, year, suffix)
            outwc = os.path.join(wordcloud_dir, name)
            
            plt.savefig(outwc, dpi=500, format='png')
            
            # Convert white to transparent
            convertWhiteToTransparent(outwc)
    

# File paths
boundary_root = r"P:\h510\some\data\south-africa\gis_layers\national_park_regions"

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

some_root = r"P:\h510\some\data\south-africa\social_media\flickr\2008_2016"

some_paths = [r"Flickr_Addo_2008-2016_Feb.shp",
              r"Flickr_Aghulhas_2008-2016_Feb.shp",
              r"Flickr_Augrabies_2008-2016_Feb.shp",
              r"Flickr_Bontebok_2008-2016_Feb.shp",
              r"Flickr_Camdeboo_2008-2016_Feb.shp",
              r"Flickr_GardenRoute_2008-2016_Feb.shp",
              r"Flickr_GoldenGate_2008-2016_Feb.shp",
              r"Flickr_iSimangaliso_2008-2016_Feb.shp",
              r"Flickr_Kalahari_2008-2016_Feb.shp",
              r"Flickr_Karoo_2008-2016_Feb.shp",
              r"Flickr_Kruger_2008-2016_Feb.shp",
              r"Flickr_Mapungubwe_2008-2016_Feb.shp",
              r"Flickr_Marakele_2008-2016_Feb.shp",
              r"Flickr_Mokala_2008-2016_Feb.shp",
              r"Flickr_MountainZebra_2008-2016_Feb.shp",
              r"Flickr_Namaqua_2008-2016_Feb.shp",
              r"Flickr_Richtersveld_2008-2016_Feb.shp",
              r"Flickr_TableMountain_2008-2016_Feb.shp",
              r"Flickr_TankwaKaroo_2008-2016_Feb.shp",
              r"Flickr_WestCoast_2008-2016_Feb.shp"
              ]

mask_dir = r"P:\h510\some\data\south-africa\images\national_park_png"
wordcloud_dir = r"P:\h510\some\figures\Wordclouds\Flickr\2008-2015"
circle_fp = r"P:\h510\some\data\south-africa\Content_analysis\word_clouds\wordcloud_circle.png"

# Parameters
# ----------

# Time window
start_date, end_date = datetime(2008,1,1,0,0,0), datetime(2015,1,1,0,0,0)

# Year
year = "2008-2015" #start_date.year

# Flag for using simple circle mask (determine path to circle_fp variable above)
circle_mask = True

# Flag for not using the mask and going by default settings
use_mask = True

# Irrelevant or too obvious words that should be excluded 
STOP_WORDS = ['national park', 'nationalpark', 'national', 'southern', 'southafrica', 'south',
              'africana', 'african', 'eastern', 'east', 'western', 'west', 'northern', 'north', 'africa', 'hello', 'selfie', 'instalike', 'instagood', 'instagram', 'insta', 'nofilter', 'iphoneonly',
              'photograph', 'photo', 'img_cr2', 'img_', 'img', 'dsc_', 'dsc', 'jdw_', 'jdw', 'sdc_', 'sdc', 'jpg', '_mg_', '_lutz', '_t', '_cp', '_sa', '_cr', 'jga']

# Suffix for result file
SUFFIX = 'removedStopwords'

# Maximum amount of words to include in the WordCloud
WORD_COUNT = 500

# The size of the image
HEIGHT, WIDTH = 400, 400

# Background color
BACKGROUND_COLOR = "white"

# Relative scaling of the popularity 
RELATIVE_SCALING = 0.15

# Maximum font size in the figure (if there are not enough words to fill the image, use larger font size to fill the area)
MAX_FONTSIZE = 120

# Iterate areas / combine all areas 
iterate_areas = False

for idx, boundary in enumerate(boundaries_list):
    # Parse file path
    boundary_fp = os.path.join(boundary_root, boundary)
    # Read data
    boundaries = gpd.read_file(boundary_fp)

    # Parse some file path
    some_fp = os.path.join(some_root, some_paths[idx])
    some = gpd.read_file(some_fp)

    # Create datetime index from timestamps
    some = some.sort_values(by='time_local')
    some = some.reset_index(drop=True)
    some['time'] = pd.to_datetime(some['time_local'])
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
    some = pointInPolygon(some, boundaries, rtree, 'Label', 'Label')

    # Ensure that all points has same label name
    some['Label'] = some.ix[some['Label'].notnull()].copy().reset_index().loc[0, 'Label'].replace(' ', '')

    # Iterate over sections
    if iterate_areas:
        for idx, row in boundaries.iterrows():
            print("Processing section: %s" % row['Label'])
            # Parse the path of corresponding mask png file
            label = row['Label'].replace(' ', '_').replace('-', '_').replace("'", '')
            name = "%s.png" % label
            if circle_mask:
                mask_fp = circle_fp                
            else:
                mask_fp = os.path.join(mask_dir, name)

            # Create mask PNG file
            png = gpd.GeoDataFrame(sect[idx:idx+1], geometry='geometry')
            # Create a plot out of the section
            png.plot()
            plt.axis("off")
            plt.savefig(mask_fp, dpi=500, alpha=False, bbox_inches='tight')
            plt.close()

            # Create Wordclouds
            createWordCloud(mask_filepath=mask_fp, label_col='Label', df=some, label_name=label, text_name='text', suffix=SUFFIX)

            
    else:
        print("Processing: %s" % os.path.basename(boundary_fp))
        # Create GeoDataFrame for boundaries
        geo = gpd.GeoDataFrame(crs=boundaries.crs)

        # Create MultiPolygon of all areas
        multipoly = unary_union(list(MultiPolygon(list(boundaries['geometry']))))
        # Insert MultiPolygon to DataFrame
        geo['geometry'] = [multipoly]
        # Insert Label name
        label = boundaries.ix[boundaries['Label'].notnull()].copy().loc[0, 'Label'].replace(' ', '')
        geo['Label'] = label
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
        createWordCloud(mask_filepath=mask_fp, label_col='Label', df=some, label_name=label, text_name='text', suffix=SUFFIX)

    
    
    
                
            
