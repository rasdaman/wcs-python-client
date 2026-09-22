"""
Test the wcs.service module.
"""

from hashlib import sha256

from wcs.service import WebCoverageService


def get_checksum(response: bytes):
    hash_func = sha256()
    hash_func.update(response)
    return hash_func.hexdigest()


def test_list_coverages():
    service = WebCoverageService("https://ows.rasdaman.org/rasdaman/ows")
    coverages = service.list_coverages()
    cov = coverages['AvgLandTemp']
    expected = '''AvgLandTemp:
  subtype: ReferenceableGridCoverage
  crs: OGC:AnsiDate+EPSG:4326
  bbox:
    ansi:
      low: "2000-02-01"
      high: "2015-06-01"
      crs: OGC:AnsiDate
    Lat:
      low: -90
      high: 90
      crs: EPSG:4326
    Lon:
      low: -180
      high: 180
      crs: EPSG:4326
  WGS84 bbox:
    Lon:
      low: -180
      high: 180
      crs: EPSG:4326
    Lat:
      low: -90
      high: 90
      crs: EPSG:4326
  size in bytes: 4809618404'''
    assert str(cov) == expected
    assert cov.bbox.ansi.crs == 'https://www.opengis.net/def/crs/OGC/0/AnsiDate'


def test_list_coverages_only_local():
    service = WebCoverageService("https://ows.rasdaman.org/rasdaman/ows")
    coverages = service.list_coverages(only_local=True)
    assert all(cov.is_local() for k, cov in coverages.items())


def test_list_coverages_all():
    service = WebCoverageService("https://ows.rasdaman.org/rasdaman/ows")
    coverages = service.list_coverages()
    assert not all(cov.is_local() for k, cov in coverages.items())


# def test_list_coverages_readme():
#     service = WebCoverageService("https://ows.rasdaman.org/rasdaman/ows")
#     coverages = service.list_coverages()
#     cov = service.list_full_info('AvgLandTemp')
#     print(cov)


def test_list_full_info():
    service = WebCoverageService("https://ows.rasdaman.org/rasdaman/ows")
    cov = service.list_full_info('AvgLandTemp')
    expected = '''AvgLandTemp:
  crs: OGC:AnsiDate+EPSG:4326
  bbox:
    ansi:
      low: "2000-02-01"
      high: "2015-06-01"
      crs: OGC:AnsiDate
      uom: d
      type: irregular
      coefficients: ["2000-02-01", "2000-03-01", "2000-04-01", "2000-05-01", "2000-06-01", "2000-07-01", "2000-08-01",
                     "2000-09-01", "2000-10-01", "2000-11-01", "2000-12-01", "2001-01-01", "2001-02-01", "2001-03-01",
                     "2001-04-01", "2001-05-01", "2001-06-01", "2001-07-01", "2001-08-01", "2001-09-01", "2001-10-01",
                     "2001-11-01", "2001-12-01", "2002-01-01", "2002-02-01", "2002-03-01", "2002-04-01", "2002-05-01",
                     "2002-06-01", "2002-07-01", "2002-08-01", "2002-09-01", "2002-10-01", "2002-11-01", "2002-12-01",
                     "2003-01-01", "2003-02-01", "2003-03-01", "2003-04-01", "2003-05-01", "2003-06-01", "2003-07-01",
                     "2003-08-01", "2003-09-01", "2003-10-01", "2003-11-01", "2003-12-01", "2004-01-01", "2004-02-01",
                     "2004-03-01", "2004-04-01", "2004-05-01", "2004-06-01", "2004-07-01", "2004-08-01", "2004-09-01",
                     "2004-10-01", "2004-11-01", "2004-12-01", "2005-01-01", "2005-02-01", "2005-03-01", "2005-04-01",
                     "2005-05-01", "2005-06-01", "2005-07-01", "2005-08-01", "2005-09-01", "2005-10-01", "2005-11-01",
                     "2005-12-01", "2006-01-01", "2006-02-01", "2006-03-01", "2006-04-01", "2006-05-01", "2006-06-01",
                     "2006-07-01", "2006-08-01", "2006-09-01", "2006-10-01", "2006-11-01", "2006-12-01", "2007-01-01",
                     "2007-02-01", "2007-03-01", "2007-04-01", "2007-05-01", "2007-06-01", "2007-07-01", "2007-08-01",
                     "2007-09-01", "2007-10-01", "2007-11-01", "2007-12-01", "2008-01-01", "2008-02-01", "2008-03-01",
                     "2008-04-01", "2008-05-01", "2008-06-01", "2008-07-01", "2008-08-01", "2008-09-01", "2008-10-01",
                     "2008-11-01", "2008-12-01", "2009-01-01", "2009-02-01", "2009-03-01", "2009-04-01", "2009-05-01",
                     "2009-06-01", "2009-07-01", "2009-08-01", "2009-09-01", "2009-10-01", "2009-11-01", "2009-12-01",
                     "2010-01-01", "2010-02-01", "2010-03-01", "2010-04-01", "2010-05-01", "2010-06-01", "2010-07-01",
                     "2010-08-01", "2010-09-01", "2010-10-01", "2010-11-01", "2010-12-01", "2011-01-01", "2011-02-01",
                     "2011-03-01", "2011-04-01", "2011-05-01", "2011-06-01", "2011-07-01", "2011-08-01", "2011-09-01",
                     "2011-10-01", "2011-11-01", "2011-12-01", "2012-01-01", "2012-02-01", "2012-03-01", "2012-04-01",
                     "2012-05-01", "2012-06-01", "2012-07-01", "2012-08-01", "2012-09-01", "2012-10-01", "2012-11-01",
                     "2012-12-01", "2013-01-01", "2013-02-01", "2013-03-01", "2013-04-01", "2013-05-01", "2013-06-01",
                     "2013-07-01", "2013-08-01", "2013-09-01", "2013-10-01", "2013-11-01", "2013-12-01", "2014-01-01",
                     "2014-02-01", "2014-03-01", "2014-04-01", "2014-05-01", "2014-06-01", "2014-07-01", "2014-08-01",
                     "2014-09-01", "2014-10-01", "2014-11-01", "2014-12-01", "2015-01-01", "2015-02-01", "2015-03-01",
                     "2015-04-01", "2015-05-01", "2015-06-01"]
    Lat:
      low: -90
      high: 90
      crs: EPSG:4326
      uom: degree
      resolution: -0.1
      type: regular
    Lon:
      low: -180
      high: 180
      crs: EPSG:4326
      uom: degree
      resolution: 0.1
      type: regular
  grid_bbox:
    i:
      low: 0
      high: 184
      resolution: 1
      type: regular
    j:
      low: 0
      high: 1799
      resolution: 1
      type: regular
    k:
      low: 0
      high: 3599
      resolution: 1
      type: regular
  range_type:
    Gray:
      type: Quantity
      label: Gray
      definition: http://www.opengis.net/def/dataType/OGC/0/float32
      nil_values: 99999
      uom: 10^0
  metadata:
'''
    assert str(cov) == expected
    subset = cov.bbox.ansi["2006-08-01" : "2007-01-01"]
    assert len(subset) == 6
    assert cov.is_local()

def test_list_full_info2():
    service = WebCoverageService("https://ows.rasdaman.org/rasdaman/ows")
    cov = service.list_full_info('Germany_DTM')
    descr = cov.metadata['covMetadata']['description']
    assert descr == "Digital terrain model of Germany, values represent terrain height in meters."

def test_to_short_str():
    service = WebCoverageService("https://ows.rasdaman.org/rasdaman/ows")
    cov = service.list_full_info('AvgLandTemp')
    expected = '''AvgLandTemp:
  crs: OGC:AnsiDate+EPSG:4326
  bbox:
    ansi("2000-02-01":"2015-06-01") -- irregular axis with 185 slices at "2000-02-01", "2000-03-01", "2000-04-01", ..., "2015-04-01", "2015-05-01", "2015-06-01"
    Lat(-90:90) -- regular axis with resolution of -0.1 degree (1800 grid points)
    Lon(-180:180) -- regular axis with resolution of 0.1 degree (3600 grid points)
  grid_bbox:
    ansi:"CRS:1"(0:184)
    Lat:"CRS:1"(0:1799)
    Lon:"CRS:1"(0:3599)
  range_type (bands):
    Gray: float, nodata 99999
'''
    print(cov.to_short_str())
    assert cov.to_short_str() == expected

def test_to_short_str2():
    service = WebCoverageService("https://ows.rasdaman.org/rasdaman/ows")
    cov = service.list_full_info('Temperature4D')
    expected = '''Temperature4D:
  crs: OGC:AnsiDate+OGC:Index1D+EPSG:4326
  bbox:
    ansi("2010-01-01":"2010-12-01") -- irregular axis with 12 slices at "2010-01-01", "2010-02-01", "2010-03-01", ..., "2010-10-01", "2010-11-01", "2010-12-01"
    elev(0:400) -- irregular axis with 5 slices at 0, 100, 200, 300, 400
    Lat(-90:90) -- regular axis with resolution of -0.1 degree (1800 grid points)
    Lon(-180:180) -- regular axis with resolution of 0.1 degree (3600 grid points)
  grid_bbox:
    ansi:"CRS:1"(0:11)
    elev:"CRS:1"(0:4)
    Lat:"CRS:1"(0:1799)
    Lon:"CRS:1"(0:3599)
  range_type (bands):
    red: unsigned char [0,255] -- red channel
    green: unsigned char [0,255] -- green channel
    blue: unsigned char [0,255] -- blue channel
  metadata:
    covMetadata:
      bands:
        red:
          valid_min: 0
          valid_max: 255
          grid_mapping: crs
          units: 10^0
        green:
          valid_min: 0
          valid_max: 255
          grid_mapping: crs
          units: 10^0
        blue:
          valid_min: 0
          valid_max: 255
          grid_mapping: crs
          units: 10^0
      grid_mapping:
        identifier: crs
        grid_mapping_name: latitude_longitude
        long_name: CRS definition
        longitude_of_prime_meridian: 0.0
        semi_major_axis: 6378137.0
        inverse_flattening: 298.257223563
        crs_wkt: GEOGCS["WGS 84",DATUM["WGS_1984",SPHEROID["WGS 84",6378137,298.257223563,AUTHORITY["EPSG","7030"]],AUTHORITY["EPSG","6326"]],PRIMEM["Greenwich",0,AUTHORITY["EPSG","8901"]],UNIT["degree",0.0174532925199433,AUTHORITY["EPSG","9122"]],AXIS["Latitude",NORTH],AXIS["Longitude",EAST],AUTHORITY["EPSG","4326"]]
      description: World temperature 4D coverage.
'''
    print(cov.to_short_str())
    assert cov.to_short_str() == expected
