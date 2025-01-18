# Overview

The [OGC Web Coverage Service (WCS) standard](https://www.ogc.org/standards/wcs)
defines support for modeling and retrieval of geospatial data as coverages 
(e.g. sensor, image, or statistics data).

This Python library allows to extract information about WCS coverages from a
given WCS endpoint.

# Installation

    pip install wcs

# Examples

```python
from wcs.service import WebCoverageService

wcs_endpoint = "https://ows.rasdaman.org/rasdaman/ows"
service = WebCoverageService(wcs_endpoint)

# get a list of all coverages, with basic information such
# as a WGS 84 bounding box and a native bounding box
coverages = service.list_coverages()
avg_land_temp = coverages['AvgLandTemp']

# get full information for a particular coverage by
# parsing its DescribeCoverage document from the WCS server
full_avg_land_temp = service.list_full_info('AvgLandTemp')
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
