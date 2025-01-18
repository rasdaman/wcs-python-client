from docutils.nodes import description

# Overview

The [OGC Web Coverage Service (WCS) standard](https://www.ogc.org/standards/wcs)
defines support for modeling and retrieval of geospatial data as coverages 
(e.g. sensor, image, or statistics data).

This Python library allows to extract information about WCS coverages from a
given WCS endpoint.

# Installation

    pip install wcs

# Examples

The example below illustrates how to get a list of 
[BasicCoverage](autoapi/wcs/model/index.html#wcs.model.BasicCoverage)
objects for all coverages on the server, and extract various details
for a particular coverage.

```python
from wcs.service import WebCoverageService
from wcs.model import Crs

wcs_endpoint = "https://ows.rasdaman.org/rasdaman/ows"
service = WebCoverageService(wcs_endpoint)

# get a list of all coverages, with basic information such
# as a WGS 84 bounding box and a native bounding box
coverages = service.list_coverages()

# get the AvgLandTemp coverage object, see BasicCoverage
# in the API reference
avg_land_temp = coverages['AvgLandTemp']

# print all information
print(avg_land_temp)

# AvgLandTemp:
#   subtype: ReferenceableGridCoverage
#   native CRS: OGC:AnsiDate+EPSG:4326
#   geo bbox:
#     ansi:
#       min: "2000-02-01"
#       max: "2015-06-01"
#       crs: OGC:AnsiDate
#     Lat:
#       min: -90
#       max: 90
#       crs: EPSG:4326
#     Lon:
#       min: -180
#       max: 180
#       crs: EPSG:4326
#   lon/lat bbox:
#     Lon:
#       min: -180
#       max: 180
#       crs: EPSG:4326
#     Lat:
#       min: -90
#       max: 90
#       crs: EPSG:4326
#   size in bytes: 4809618404

# coverage subtype
print(avg_land_temp.subtype)
# ReferenceableGridCoverage

# coverage bounding box, containing the CRS and axes
bbox = avg_land_temp.bbox

# full coverage crs identifier
print(bbox.crs)
# https://www.opengis.net/def/crs-compound?
# 1=https://www.opengis.net/def/crs/OGC/0/AnsiDate&
# 2=https://www.opengis.net/def/crs/EPSG/0/4326

# coverage crs identifier in shorthand notation
print(Crs.to_short_notation(bbox.crs))
# OGC:AnsiDate+EPSG:4326

# get information for the first axis; as it is a temporal axis,
# the lower_bound and upper_bound are datetime.datetime objects.
axis = bbox[0]
name = axis.name
lower_bound = axis.low
upper_bound = axis.high
print(f'{name}({lower_bound} - {upper_bound})')
# ansi(2000-02-01 00:00:00+00:00 - 2015-06-01 00:00:00+00:00)

# get information for the Lat axis
axis = bbox['Lat']
print(axis.name)
# Lat

# get size in bytes if available
if avg_land_temp.size_bytes is not None:
    print(avg_land_temp.size_bytes)
    # 4809618404

```

The above example gets basic information about the coverage
through what is published in the WCS GetCapabilities response.
More detailed information can be retrieved with the 
`list_full_info` method, which returns a
[FullCoverage](autoapi/wcs/model/index.html#wcs.model.FullCoverage)
object.

```python
from wcs.service import WebCoverageService

wcs_endpoint = "https://ows.rasdaman.org/rasdaman/ows"
service = WebCoverageService(wcs_endpoint)

# get full information for a particular coverage by
# parsing its DescribeCoverage document from the WCS server
full_avg_land_temp = service.list_full_info('AvgLandTemp')

# print all information
print(full_avg_land_temp)

# AvgLandTemp:
#   native CRS: OGC:AnsiDate+EPSG:4326
#   geo bbox:
#     ansi:
#       min: "2000-02-01"
#       max: "2015-06-01"
#       crs: OGC:AnsiDate
#       uom: d
#       type: irregular
#       coefficients: ["2000-02-01", "2000-03-01", ...
#                      "2015-05-01", "2015-06-01"]
#     Lat:
#       min: -90
#       max: 90
#       crs: EPSG:4326
#       uom: degree
#       resolution: -0.1
#       type: regular
#     Lon:
#       min: -180
#       max: 180
#       crs: EPSG:4326
#       uom: degree
#       resolution: 0.1
#       type: regular
#   grid bbox:
#     i:
#       min: 0
#       max: 184
#       resolution: 1
#       type: regular
#     j:
#       min: 0
#       max: 1799
#       resolution: 1
#       type: regular
#     k:
#       min: 0
#       max: 3599
#       resolution: 1
#       type: regular
#   range type fields:
#     Gray:
#       type: Quantity
#       label: Gray
#       definition: http://www.opengis.net/def/dataType/OGC/0/float32
#       nil values: 99999
#       uom: 10^0
#   metadata:
#     {
#       "covMetadata": null
#     }


# In addition to the geo bounding box in native CRS, the 
# `FullCoverage` object also has a `grid_bbox`, which contains 
# the integer grid axis bounds of the coverage. This is the same 
# type of `BoundingBox` object, except the `crs` is None.
print(full_avg_land_temp.grid_bbox)

# The range_type indicates the structure of the cell values
# of the coverage. It contains a `fields` attribute, which is
# a list of `Field` object corresponding to the bands of the 
# coverage. Check the documentation of RangeType for full details.
range_type = full_avg_land_temp.range_type
all_fields = range_type.fields
field = range_type['Gray']  # or range_type[0]

# get all properties of the field
label = field.label
description = field.description
definition = field.definition
nil_values = field.nil_values
if field.is_quantity:
  uom = field.uom
else:
  codespace = field.codespace
```



# Contributing

The directory structure is as follows:

- `wcs` - the main library code
- `tests` - testing code
- `docs` - documentation in reStructuredText format

## Tests

To run the tests:

```
# install dependencies
pip install wcs[tests]

pytest
```

## Documentation

To build the documentation:

```
# install dependencies
pip install wcs[docs]

cd docs
make html
```

The built documentation can be found in the `docs/_build/html/` subdir.
