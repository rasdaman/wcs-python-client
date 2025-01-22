# Overview

The [OGC Web Coverage Service (WCS) standard](https://www.ogc.org/standards/wcs)
defines support for modeling and retrieval of geospatial data as coverages 
(e.g. sensor, image, or statistics data).

This Python library allows to extract information about WCS coverages from a
given WCS endpoint.

Note that downloading raster data is not supported. This can be done with
the [WCPS Python Client](https://rasdaman.github.io/wcps-python-client/).

# Installation

    pip install wcs

# Examples

## List Coverages

The example below illustrates how to get a list of 
[BasicCoverage](https://rasdaman.github.io/wcs-python-client/autoapi/wcs/model/index.html#wcs.model.BasicCoverage)
objects for all coverages (datacubes) on the server, and extract various details
for a particular coverage.

First we need to create a
[WebCoverageService](https://rasdaman.github.io/wcs-python-client/autoapi/wcs/service/index.html#wcs.service.WebCoverageService)
object. Optionally, a username and a password may be specified, if the endpoint requires them.

```python
from wcs.service import WebCoverageService

wcs_endpoint = "https://fairicube.rasdaman.com/rasdaman/ows"
service = WebCoverageService(wcs_endpoint)

# or with credentials:
# service = WebCoverageService(wcs_endpoint,
#                              username=..., password=...)
```

With the `service` object we can get a map of all coverages
(coverage name -> [BasicCoverage](https://rasdaman.github.io/wcs-python-client/autoapi/wcs/model/index.html#wcs.model.BasicCoverage)), 
with basic information such as a WGS 84 bounding box and a native bounding box:

```python
coverages = service.list_coverages()
```

Let's print information of a single coverage with name `dominant_leaf_type_20m`:

```python
cov = coverages['dominant_leaf_type_20m']

print(cov)
```
```yaml
dominant_leaf_type_20m:
  subtype: ReferenceableGridCoverage
  native CRS: OGC:AnsiDate+EPSG:3035
  geo bbox:
    time:
      min: "2012-01-01"
      max: "2015-01-01"
      crs: OGC:AnsiDate
    Y:
      min: 900000
      max: 5500000
      crs: EPSG:3035
    X:
      min: 900000
      max: 7400000
      crs: EPSG:3035
  lon/lat bbox:
    Lon:
      min: -56.50514190170437
      max: 72.9061049341568
      crs: EPSG:4326
    Lat:
      min: 24.28417068794856
      max: 72.66326966834436
      crs: EPSG:4326
  size in bytes: 113000000001
  additional params:
    title: Dominant Leaf Type (2012-2015)
    sizeInBytesWithPyramidLevels: "113000000001"
```

Examples for extracting individual details of the coverage:

```python
# coverage subtype

print(cov.subtype)

# ReferenceableGridCoverage

# coverage bounding box, containing the CRS and axes

bbox = cov.bbox

# full coverage crs identifier

print(bbox.crs)

# https://www.opengis.net/def/crs-compound?
# 1=https://www.opengis.net/def/crs/OGC/0/AnsiDate?axis-label="time"&
# 2=https://www.opengis.net/def/crs/EPSG/0/3035

# coverage crs identifier in shorthand notation

from wcs.model import Crs

print(Crs.to_short_notation(bbox.crs))

# OGC:AnsiDate+EPSG:3035

# get information for the first axis; as it is a temporal axis,
# the lower_bound and upper_bound are datetime.datetime objects.

axis = bbox.time

# note that these are all equivalent:
# axis = bbox['time']
# axis = bbox[0]

name = axis.name
lower_bound = axis.low
upper_bound = axis.high
print(f'{name}({lower_bound} - {upper_bound})')
# time(2012-01-01 00:00:00+00:00 - 2015-01-01 00:00:00+00:00)

# get size in bytes if available

if cov.size_bytes is not None:
    print(cov.size_bytes)
    # 113000000001
```

## Full Coverage Information

The previous example gets basic information about the coverage
through what is published in the WCS *GetCapabilities* response.

More detailed information can be retrieved with the 
`service.list_full_info` method, which parses the corresponding *DescribeCoverage* document and returns a
[FullCoverage](https://rasdaman.github.io/wcs-python-client/autoapi/wcs/model/index.html#wcs.model.FullCoverage)
object:

```python
cov = service.list_full_info('dominant_leaf_type_20m')

# print all information

print(cov)
```
```yaml
dominant_leaf_type_20m:
  native CRS: OGC:AnsiDate+EPSG:3035
  geo bbox:
    time:
      min: 2012-01-01
      max: 2015-01-01
      crs: OGC:AnsiDate
      uom: d
      type: irregular
      coefficients:
        - 2012-01-01
        - 2015-01-01
    Y:
      min: 900000
      max: 5500000
      crs: EPSG:3035
      uom: metre
      resolution: -20
      type: regular
    X:
      min: 900000
      max: 7400000
      crs: EPSG:3035
      uom: metre
      resolution: 20
      type: regular
  grid bbox:
    i:
      min: 0
      max: 1
      resolution: 1
      type: regular
    j:
      min: -125000
      max: 104999
      resolution: 1
      type: regular
    k:
      min: 0
      max: 324999
      resolution: 1
      type: regular
  range type fields:
    dlt:
      type: Category
      label: dominant leaf type map of Europe
      description: >
        raster coding (thematic pixel values): 
        0: all non-tree covered areas; 
        1: broadleaved trees; 
        2: coniferous trees; 
        254: unclassifiable (no satellite image available, or clouds, shadows, or snow); 
        255: outside area
      definition: https://land.copernicus.eu/en/technical-library/hrl-forest-2012-2015/@@download/file
      nil values: 250
  metadata:
    covMetadata:
      axes:
        time:
          areasOfValidity:
            area:
              - 
                "@start": 2011-01-01T00:00:00.000Z
                "@end": 2013-12-31T23:59:59.999Z
              - 
                "@start": 2014-01-01T00:00:00.000Z
                "@end": 2016-12-31T23:59:59.999Z
    rasdamanCoverageMetadata:
      catalog:
        title: Dominant Leaf Type (2012-2015)
        thumbnail: https://fairicube.rasdaman.com/rasdaman/ows/coverage/thumbnail?COVERAGEID=dominant_leaf_type_20m
        description: Provides at pan-European level in the spatial resolution of 20 m information on the dominant leaf type (broadleaved or coniferous).
        provenance:
          "@sourceUrl": https://land.copernicus.eu/en/products/high-resolution-layer-dominant-leaf-type
          "@providerName": Copernicus
          "@termsUrl": https://land.copernicus.eu/en/data-policy
        ourTerms: https://fairicube.rasdaman.com/#terms
    fairicubeMetadata:
      "@role": https://codelists.fairicube.eu/metadata/MetadataCatalogLink
      "@title": Metadata in the FAIRiCUBE Catalog
      "@href": https://stacapi.eoxhub.fairicube.eu/collections/index/items/dominant_leaf_type_20m
```

In addition to the geo `bbox` in native CRS, the 
`FullCoverage` object also has a `grid_bbox` attribute, which contains 
the integer grid axis bounds of the coverage. This is the same 
type of 
[BoundingBox](https://rasdaman.github.io/wcs-python-client/autoapi/wcs/model/index.html#wcs.model.BoundingBox)
object, except its `crs` attribute is `None`.

```python
print(cov.grid_bbox)
```

The `range_type` attribute indicates the structure of the cell values
of the coverage. It contains a `fields` attribute, which is
a list of
[Field](https://rasdaman.github.io/wcs-python-client/autoapi/wcs/model/index.html#wcs.model.Field)
objects corresponding to the bands of the 
coverage. Check the documentation of
[RangeType](https://rasdaman.github.io/wcs-python-client/autoapi/wcs/model/index.html#wcs.model.RangeType)
for full details.

```python
range_type = cov.range_type
all_fields = range_type.fields
dlt = range_type.dlt

# note that these are all equivalent:
# field = range_type['dlt']
# field = range_type[0]

# get all properties of the field

label = dlt.label
description = dlt.description
definition = dlt.definition
nil_values = dlt.nil_values
if dlt.is_quantity:
    uom = dlt.uom
else:
    codespace = dlt.codespace
```

Finally, any coverage metadata is available from the `metadata` attribute,
which is a nested dict mirroring the XML structure in the *DescribeCoverage* document.
E.g. to get the link to the FAIRiCUBE catalog entry for this coverage:

```python
catalog_link = cov.metadata['fairicubeMetadata']['@href']
```

# Contributing

The directory structure is as follows:

- `wcs` - the main library code
- `tests` - testing code
- `docs` - documentation in reStructuredText format

The `./pylint.sh` script should be executed before committing code changes.

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


# Acknowledgments

Created in project [EU FAIRiCUBE](https://fairicube.nilu.no/), with funding from the 
Horizon Europe programme under grant agreement No 101059238.
