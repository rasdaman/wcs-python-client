import xml.etree.ElementTree as ET
from datetime import datetime

import pytest

from wcs.model import (WCSClientException, BoundingBox,
                       BasicCoverage, RangeType, Axis, Crs)
from wcs.parser import (parse_bound, parse_tag_name,
                        parse_bounds_list, parse_additional_parameters,
                        parse_bounding_box, parse_wgs84_bounding_box, parse_coverage_summary,
                        parse_coverage_summaries, parse_range_type, parse_domain_set, element_to_dict)


# ----------------------------------------------------------------------------
# parse_domain_set


def test_parse_domain_set_valid():
    xml_string = '''
    <DomainSet>
        <GeneralGrid srsName="https://www.opengis.net/def/crs-compound?1=https://www.opengis.net/def/crs/OGC/0/AnsiDate&amp;2=https://www.opengis.net/def/crs/EPSG/0/4326" axisLabels="ansi Lat Lon">
            <RegularAxis axisLabel="Lat" uomLabel="degree" lowerBound="-90" upperBound="90" resolution="-0.1"/>
            <RegularAxis axisLabel="Lon" uomLabel="degree" lowerBound="-180" upperBound="180" resolution="0.1"/>
            <IrregularAxis axisLabel="ansi" uomLabel="d">
                <C>"2000-02-01T00:00:00.000Z"</C>
                <C>"2000-03-01T00:00:00.000Z"</C>
            </IrregularAxis>
            <GridLimits srsName="http://www.opengis.net/def/crs/OGC/0/Index3D" axisLabels="i j k">
                <IndexAxis axisLabel="i" lowerBound="0" upperBound="184"/>
                <IndexAxis axisLabel="j" lowerBound="0" upperBound="1799"/>
                <IndexAxis axisLabel="k" lowerBound="0" upperBound="3599"/>
            </GridLimits>
        </GeneralGrid>
    </DomainSet>
    '''
    domain_set_element = ET.fromstring(xml_string)
    bounding_box, grid_bbox = parse_domain_set(domain_set_element)

    assert isinstance(bounding_box, BoundingBox)
    assert isinstance(grid_bbox, BoundingBox)

    assert len(bounding_box.axes) == 3
    assert len(grid_bbox.axes) == 3

    assert bounding_box.axes[0].name == 'ansi'
    assert bounding_box.axes[1].name == 'Lat'
    assert bounding_box.axes[2].name == 'Lon'

    assert grid_bbox.axes[0].name == 'i'
    assert grid_bbox.axes[1].name == 'j'
    assert grid_bbox.axes[2].name == 'k'


def test_parse_domain_set_none_input():
    assert parse_domain_set(None) == (None, None)


def test_parse_domain_set_invalid_tag():
    xml_string = '''
    <InvalidTag>
        <GeneralGrid srsName="https://www.opengis.net/def/crs-compound?1=https://www.opengis.net/def/crs/OGC/0/AnsiDate&amp;2=https://www.opengis.net/def/crs/EPSG/0/4326" axisLabels="ansi Lat Lon">
            <RegularAxis axisLabel="Lat" uomLabel="degree" lowerBound="-90" upperBound="90" resolution="-0.1"/>
        </GeneralGrid>
    </InvalidTag>
    '''
    domain_set_element = ET.fromstring(xml_string)
    with pytest.raises(WCSClientException, match="Expected a DomainSet element, but got InvalidTag"):
        parse_domain_set(domain_set_element)


def test_parse_domain_set_missing_general_grid():
    xml_string = '''
    <DomainSet>
        <RegularAxis axisLabel="Lat" uomLabel="degree" lowerBound="-90" upperBound="90" resolution="-0.1"/>
    </DomainSet>
    '''
    domain_set_element = ET.fromstring(xml_string)
    with pytest.raises(WCSClientException, match="Expected a GeneralGrid element"):
        parse_domain_set(domain_set_element)


def test_parse_domain_set_missing_axis_labels():
    xml_string = '''
    <DomainSet>
        <GeneralGrid srsName="https://www.opengis.net/def/crs-compound?
        1=https://www.opengis.net/def/crs/OGC/0/AnsiDate&amp;
        2=https://www.opengis.net/def/crs/EPSG/0/4326">
            <RegularAxis axisLabel="Lat" uomLabel="degree" lowerBound="-90" upperBound="90" resolution="-0.1"/>
            <RegularAxis axisLabel="Lon" uomLabel="degree" lowerBound="-180" upperBound="180" resolution="0.1"/>
        </GeneralGrid>
    </DomainSet>
    '''
    domain_set_element = ET.fromstring(xml_string)
    with pytest.raises(WCSClientException, match="GeneralGrid element missing axisLabels attribute."):
        parse_domain_set(domain_set_element)


def test_parse_domain_set_irregular_axis():
    xml_string = '''
    <DomainSet>
        <GeneralGrid srsName="https://www.opengis.net/def/crs-compound?
        1=https://www.opengis.net/def/crs/OGC/0/AnsiDate&amp;
        2=https://www.opengis.net/def/crs/EPSG/0/4326" axisLabels="ansi">
            <IrregularAxis axisLabel="ansi" uomLabel="d">
                <C>"2000-02-01T00:00:00.000Z"</C>
                <C>"2000-03-01T00:00:00.000Z"</C>
            </IrregularAxis>
        </GeneralGrid>
    </DomainSet>
    '''
    domain_set_element = ET.fromstring(xml_string)
    bounding_box, grid_bbox = parse_domain_set(domain_set_element)

    assert isinstance(bounding_box, BoundingBox)
    assert isinstance(grid_bbox, BoundingBox)

    assert len(bounding_box.axes) == 1
    assert len(grid_bbox.axes) == 0

    assert bounding_box.axes[0].name == 'ansi'
    assert bounding_box.axes[0].low.isoformat() == "2000-02-01T00:00:00+00:00"


# ----------------------------------------------------------------------------
# parse_coverage_summaries


def test_parse_range_type_valid_category():
    xml_string = '''
    <RangeType>
        <DataRecord>
            <field name="land_use">
                <Category definition="...">
                    <label>National Land Use Database</label>
                    <description>Land use classes</description>
                    <nilValues>
                        <NilValues>
                            <nilValue reason="">0</nilValue>
                        </NilValues>
                    </nilValues>
                    <codeSpace href="...."/>
                </Category>
            </field>
        </DataRecord>
    </RangeType>
    '''
    range_type_element = ET.fromstring(xml_string)
    range_type = parse_range_type(range_type_element)
    assert isinstance(range_type, RangeType)
    assert len(range_type.fields) == 1
    field = range_type['land_use']
    assert field.name == "land_use"
    assert field.is_quantity is False
    assert field.label == "National Land Use Database"
    assert field.description == "Land use classes"
    assert field.codespace == "...."
    assert field.nil_values[0].nil_value == "0"
    assert field.nil_values[0].reason == ""


def test_parse_range_type_valid_quantity():
    xml_string = '''
    <RangeType>
        <DataRecord>
            <field name="temperature">
                <Quantity definition="...">
                    <label>Monthly average air temperature</label>
                    <description>Monthly average air temperature in degree Celsius</description>
                    <nilValues>
                        <NilValues>
                            <nilValue reason="">-9999</nilValue>
                        </NilValues>
                    </nilValues>
                    <uom code="°C"/>
                </Quantity>
            </field>
        </DataRecord>
    </RangeType>
    '''
    range_type_element = ET.fromstring(xml_string)
    range_type = parse_range_type(range_type_element)
    assert isinstance(range_type, RangeType)
    assert len(range_type.fields) == 1
    field = range_type['temperature']
    assert field.name == "temperature"
    assert field.is_quantity is True
    assert field.label == "Monthly average air temperature"
    assert field.description == "Monthly average air temperature in degree Celsius"
    assert field.uom == "°C"
    assert field.nil_values[0].nil_value == "-9999"
    assert field.nil_values[0].reason == ""


def test_parse_range_type_none_input():
    assert parse_range_type(None) is None


def test_parse_range_type_invalid_tag():
    xml_string = '''
    <InvalidTag>
        <DataRecord>
            <field name="temperature">
                <Quantity definition="...">
                    <label>Temperature</label>
                </Quantity>
            </field>
        </DataRecord>
    </InvalidTag>
    '''
    range_type_element = ET.fromstring(xml_string)
    with pytest.raises(WCSClientException, match="Expected a RangeType element, but got InvalidTag"):
        parse_range_type(range_type_element)


def test_parse_range_type_missing_data_record():
    xml_string = '''
    <RangeType>
        <field name="temperature">
            <Quantity definition="...">
                <label>Temperature</label>
            </Quantity>
        </field>
    </RangeType>
    '''
    range_type_element = ET.fromstring(xml_string)
    with pytest.raises(WCSClientException, match="Expected a DataRecord element, but got field"):
        parse_range_type(range_type_element)


# ----------------------------------------------------------------------------
# parse_coverage_summaries


def test_parse_coverage_summaries_valid():
    xml_string = '''
    <Capabilities>
        <Contents>
            <CoverageSummary>
                <CoverageId>Coverage1</CoverageId>
                <CoverageSubtype>GridCoverage</CoverageSubtype>
                <WGS84BoundingBox>
                    <LowerCorner>-180 -90</LowerCorner>
                    <UpperCorner>180 90</UpperCorner>
                </WGS84BoundingBox>
                <BoundingBox crs="EPSG:4326" dimensions="2">
                    <LowerCorner>-180 -90</LowerCorner>
                    <UpperCorner>180 90</UpperCorner>
                </BoundingBox>
                <AdditionalParameters>
                    <AdditionalParameter>
                        <Name>sizeInBytes</Name>
                        <Value>1000</Value>
                    </AdditionalParameter>
                </AdditionalParameters>
            </CoverageSummary>
            <CoverageSummary>
                <CoverageId>Coverage2</CoverageId>
                <CoverageSubtype>GridCoverage</CoverageSubtype>
            </CoverageSummary>
        </Contents>
    </Capabilities>
    '''
    coverages = parse_coverage_summaries(xml_string)
    assert len(coverages) == 2
    assert coverages[0].name == "Coverage1"
    assert coverages[0].size_bytes == 1000
    assert coverages[1].name == "Coverage2"
    assert coverages[1].size_bytes is None  # No sizeInBytes parameter in Coverage2


def test_parse_coverage_summaries_missing_contents():
    xml_string = '''
    <Capabilities>
        <SomeOtherElement>
            <CoverageSummary>
                <CoverageId>Coverage1</CoverageId>
            </CoverageSummary>
        </SomeOtherElement>
    </Capabilities>
    '''
    with pytest.raises(WCSClientException, match="Invalid GetCapabilities document: no Contents element found."):
        parse_coverage_summaries(xml_string)


def test_parse_coverage_summaries_bytes_input():
    xml_string = b'''
    <Capabilities>
        <Contents>
            <CoverageSummary>
                <CoverageId>Coverage1</CoverageId>
                <CoverageSubtype>GridCoverage</CoverageSubtype>
            </CoverageSummary>
        </Contents>
    </Capabilities>
    '''
    coverages = parse_coverage_summaries(xml_string)
    assert len(coverages) == 1
    assert coverages[0].name == "Coverage1"


def test_parse_coverage_summaries_empty_contents():
    xml_string = '''
    <Capabilities>
        <Contents>
        </Contents>
    </Capabilities>
    '''
    coverages = parse_coverage_summaries(xml_string)
    assert len(coverages) == 0


def test_parse_coverage_summaries_no_coverage_summaries():
    xml_string = '''
    <Capabilities>
        <Contents>
            <SomeOtherElement/>
        </Contents>
    </Capabilities>
    '''
    with pytest.raises(WCSClientException, match="Expected a CoverageSummary element, but got SomeOtherElement"):
        parse_coverage_summaries(xml_string)


# ----------------------------------------------------------------------------
# parse_coverage_summary

def test_parse_coverage_summary_valid():
    xml_string = '''
    <CoverageSummary>
        <CoverageId>AverageChloroColorScaled</CoverageId>
        <CoverageSubtype>ReferenceableGridCoverage</CoverageSubtype>
        <WGS84BoundingBox>
            <LowerCorner>-180 -90</LowerCorner>
            <UpperCorner>180 90</UpperCorner>
        </WGS84BoundingBox>
        <BoundingBox crs="https://www.opengis.net/def/crs-compound?1=https://www.opengis.net/def/crs/OGC/0/AnsiDate&amp;2=https://www.opengis.net/def/crs/EPSG/0/4326" dimensions="3">
            <LowerCorner>"2002-07-01T00:00:00.000Z" -90 -180</LowerCorner>
            <UpperCorner>"2015-05-01T00:00:00.000Z" 90 180</UpperCorner>
        </BoundingBox>
        <AdditionalParameters>
            <AdditionalParameter>
                <Name>sizeInBytes</Name>
                <Value>188325000</Value>
            </AdditionalParameter>
            <AdditionalParameter>
                <Name>axisList</Name>
                <Value>ansi,Lat,Lon</Value>
            </AdditionalParameter>
        </AdditionalParameters>
    </CoverageSummary>
    '''
    element = ET.fromstring(xml_string)
    coverage = parse_coverage_summary(element)
    assert isinstance(coverage, BasicCoverage)
    assert coverage.name == "AverageChloroColorScaled"
    assert coverage.subtype == "ReferenceableGridCoverage"
    assert coverage.size_bytes == 188325000
    assert coverage.additional_params == {}
    assert coverage.lon is not None
    assert coverage.lat is not None
    assert coverage.bbox is not None
    assert coverage.bbox.axes[0].name == 'ansi'
    assert coverage.bbox.axes[1].name == 'Lat'
    assert coverage.bbox.axes[2].name == 'Lon'


def test_parse_coverage_summary_none():
    assert parse_coverage_summary(None) is None


def test_parse_coverage_summary_invalid_tag():
    xml_string = '''
    <InvalidTag>
        <CoverageId>AverageChloroColorScaled</CoverageId>
    </InvalidTag>
    '''
    element = ET.fromstring(xml_string)
    with pytest.raises(WCSClientException, match="Expected a CoverageSummary element, but got InvalidTag"):
        parse_coverage_summary(element)


def test_parse_coverage_summary_missing_coverage_id():
    xml_string = '''
    <CoverageSummary>
        <CoverageSubtype>ReferenceableGridCoverage</CoverageSubtype>
    </CoverageSummary>
    '''
    element = ET.fromstring(xml_string)
    with pytest.raises(WCSClientException, match="CoverageSummary is missing required CoverageId child element."):
        parse_coverage_summary(element)


def test_parse_coverage_summary_no_axis_list():
    xml_string = '''
    <CoverageSummary>
        <CoverageId>AverageChloroColorScaled</CoverageId>
        <CoverageSubtype>ReferenceableGridCoverage</CoverageSubtype>
        <WGS84BoundingBox>
            <LowerCorner>-180 -90</LowerCorner>
            <UpperCorner>180 90</UpperCorner>
        </WGS84BoundingBox>
        <BoundingBox crs="https://www.opengis.net/def/crs-compound?1=https://www.opengis.net/def/crs/OGC/0/AnsiDate&amp;2=https://www.opengis.net/def/crs/EPSG/0/4326" dimensions="3">
            <LowerCorner>"2002-07-01T00:00:00.000Z" -90 -180</LowerCorner>
            <UpperCorner>"2015-05-01T00:00:00.000Z" 90 180</UpperCorner>
        </BoundingBox>
    </CoverageSummary>
    '''
    element = ET.fromstring(xml_string)
    coverage = parse_coverage_summary(element)
    assert coverage.bbox is not None
    assert coverage.bbox.axes[0].name == ''
    assert coverage.bbox.axes[1].name == ''
    assert coverage.bbox.axes[2].name == ''


# ----------------------------------------------------------------------------
# parse_wgs84_bounding_box

def test_parse_wgs84_bounding_box_valid():
    xml_string = '''
    <WGS84BoundingBox>
        <LowerCorner>-180 -90</LowerCorner>
        <UpperCorner>180 90</UpperCorner>
    </WGS84BoundingBox>
    '''
    bbox_element = ET.fromstring(xml_string)
    lon, lat = parse_wgs84_bounding_box(bbox_element)
    assert isinstance(lon, Axis)
    assert isinstance(lat, Axis)
    assert lon.name == 'Lon'
    assert lat.name == 'Lat'
    assert lon.low == -180
    assert lon.high == 180
    assert lat.low == -90
    assert lat.high == 90


def test_parse_wgs84_bounding_box_none():
    assert parse_wgs84_bounding_box(None) is None


def test_parse_wgs84_bounding_box_invalid_tag():
    xml_string = '''
    <InvalidTag>
        <LowerCorner>-180 -90</LowerCorner>
        <UpperCorner>180 90</UpperCorner>
    </InvalidTag>
    '''
    bbox_element = ET.fromstring(xml_string)
    with pytest.raises(WCSClientException, match="Expected a WGS84BoundingBox element, "
                                                 "but got InvalidTag"):
        parse_wgs84_bounding_box(bbox_element)


def test_parse_wgs84_bounding_box_missing_bound():
    xml_string = '''
    <WGS84BoundingBox>
        <LowerCorner>-180</LowerCorner>
        <UpperCorner>180</UpperCorner>
    </WGS84BoundingBox>
    '''
    bbox_element = ET.fromstring(xml_string)
    with pytest.raises(WCSClientException, match="Expected a WGS84BoundingBox element "
                                                 "bounds for lon/lat axes, but got 1 bounds"):
        parse_wgs84_bounding_box(bbox_element)


# ----------------------------------------------------------------------------
# parse_bounding_box

def test_parse_bounding_box_valid():
    xml_string = '''
    <BoundingBox crs="http://www.opengis.net/def/crs/EPSG/0/4326" dimensions="2">
        <LowerCorner>-90 -180</LowerCorner>
        <UpperCorner>90 180</UpperCorner>
    </BoundingBox>
    '''
    bbox_element = ET.fromstring(xml_string)
    bbox = parse_bounding_box(bbox_element)
    assert isinstance(bbox, BoundingBox)
    assert bbox.crs == "http://www.opengis.net/def/crs/EPSG/0/4326"
    assert len(bbox.axes) == 2
    assert bbox.axes[0].low == -90 and bbox.axes[0].high == 90
    assert bbox.axes[1].low == -180 and bbox.axes[1].high == 180


def test_parse_bounding_box_none_crs():
    xml_string = '''
    <BoundingBox dimensions="2">
        <LowerCorner>-90 -180</LowerCorner>
        <UpperCorner>90 180</UpperCorner>
    </BoundingBox>
    '''
    bbox_element = ET.fromstring(xml_string)
    with pytest.raises(WCSClientException, match="Failed parsing CRS from XML element"):
        parse_bounding_box(bbox_element)


def test_parse_bounding_box_missing_corners():
    xml_string = '''
    <BoundingBox crs="http://www.opengis.net/def/crs/EPSG/0/4326" dimensions="2">
        <LowerCorner>-90 -180</LowerCorner>
    </BoundingBox>
    '''
    bbox_element = ET.fromstring(xml_string)
    with pytest.raises(WCSClientException, match="Failed parsing .*UpperCorner element"):
        parse_bounding_box(bbox_element)


def test_parse_bounding_box_none_element():
    assert parse_bounding_box(None) is None


def test_parse_bounding_box_empty_string():
    xml_string = '<BoundingBox></BoundingBox>'
    bbox_element = ET.fromstring(xml_string)
    with pytest.raises(WCSClientException, match="Failed parsing .*LowerCorner element"):
        parse_bounding_box(bbox_element)


def test_parse_bounding_box_invalid_crs():
    xml_string = '''
    <BoundingBox crs="http://example.com/invalid/crs" dimensions="2">
        <LowerCorner>-90 -180</LowerCorner>
        <UpperCorner>90 180</UpperCorner>
    </BoundingBox>
    '''
    bbox_element = ET.fromstring(xml_string)
    bbox = parse_bounding_box(bbox_element)
    assert isinstance(bbox, BoundingBox)


def test_parse_bounding_box_compound_crs():
    xml_string = '''
    <BoundingBox crs="https://www.opengis.net/def/crs-compound?1=http://www.opengis.net/def/crs/EPSG/0/4326&amp;2=http://www.opengis.net/def/crs/EPSG/0/3857" dimensions="2">
        <LowerCorner>-90 -180</LowerCorner>
        <UpperCorner>90 180</UpperCorner>
    </BoundingBox>
    '''
    bbox_element = ET.fromstring(xml_string)
    bbox = parse_bounding_box(bbox_element)
    assert isinstance(bbox, BoundingBox)
    assert bbox.crs == "https://www.opengis.net/def/crs-compound?" + \
                       "1=http://www.opengis.net/def/crs/EPSG/0/4326&" + \
                       "2=http://www.opengis.net/def/crs/EPSG/0/3857"


# ----------------------------------------------------------------------------
# parse_additional_parameters

def test_parse_additional_parameters_valid():
    xml_string = '''
    <AdditionalParameters>
        <AdditionalParameter>
            <Name>param1</Name>
            <Value>value1</Value>
        </AdditionalParameter>
        <AdditionalParameter>
            <Name>param2</Name>
            <Value>value2</Value>
        </AdditionalParameter>
    </AdditionalParameters>
    '''
    element = ET.fromstring(xml_string)
    expected = {'param1': 'value1', 'param2': 'value2'}
    assert parse_additional_parameters(element) == expected


def test_parse_additional_parameters_missing_name():
    xml_string = '''
    <AdditionalParameters>
        <AdditionalParameter>
            <Value>value1</Value>
        </AdditionalParameter>
    </AdditionalParameters>
    '''
    element = ET.fromstring(xml_string)
    with pytest.raises(WCSClientException, match="missing a Name child element"):
        parse_additional_parameters(element)


def test_parse_additional_parameters_missing_value():
    xml_string = '''
    <AdditionalParameters>
        <AdditionalParameter>
            <Name>param1</Name>
        </AdditionalParameter>
    </AdditionalParameters>
    '''
    element = ET.fromstring(xml_string)
    with pytest.raises(WCSClientException, match="missing a Value child element"):
        parse_additional_parameters(element)


def test_parse_additional_parameters_unexpected_child():
    xml_string = '''
    <AdditionalParameters>
        <UnexpectedElement>
            <Name>param1</Name>
            <Value>value1</Value>
        </UnexpectedElement>
    </AdditionalParameters>
    '''
    element = ET.fromstring(xml_string)
    with pytest.raises(WCSClientException, match="Unexpected child element of AdditionalParameters"):
        parse_additional_parameters(element)


def test_parse_additional_parameters_invalid_name_value():
    xml_string = '''
    <AdditionalParameters>
        <AdditionalParameter>
            <Name></Name>
            <Value>value1</Value>
        </AdditionalParameter>
    </AdditionalParameters>
    '''
    element = ET.fromstring(xml_string)
    with pytest.raises(WCSClientException, match="missing a Name child element"):
        parse_additional_parameters(element)


def test_parse_additional_parameters_empty():
    xml_string = '<AdditionalParameters></AdditionalParameters>'
    element = ET.fromstring(xml_string)
    assert not parse_additional_parameters(element)


def test_parse_additional_parameters_none():
    element = None
    assert not parse_additional_parameters(element)


# ----------------------------------------------------------------------------
# parse_bounds_list


def test_parse_bounds_list_none():
    assert parse_bounds_list(None) == []
    assert parse_bounds_list("") == []


def test_parse_bounds_list_mixed_types():
    input_string = '"2023-10-04T14:48:00Z" 42 3.14 "hello"'
    expected = [
        datetime.fromisoformat("2023-10-04T14:48:00+00:00"),
        42,
        3.14,
        "hello"
    ]
    assert parse_bounds_list(input_string) == expected


def test_parse_bounds_list_invalid():
    input_string = "42 invalid 3.14"
    with pytest.raises(WCSClientException):
        parse_bounds_list(input_string)


# ----------------------------------------------------------------------------
# parse_bound

def test_parse_bound_none():
    assert parse_bound(None) is None


def test_parse_bound_datetime():
    bound = '"2023-10-04T14:48:00Z"'
    expected = datetime.fromisoformat("2023-10-04T14:48:00+00:00")
    assert parse_bound(bound) == expected
    assert parse_bound(bound.strip('"')) == expected


def test_parse_bound_integer():
    bound = "42"
    assert parse_bound(bound) == 42


def test_parse_bound_float():
    bound = "3.14"
    assert parse_bound(bound) == 3.14


def test_parse_bound_string():
    bound = '"hello"'
    assert parse_bound(bound) == "hello"


def test_parse_bound_invalid():
    with pytest.raises(WCSClientException):
        parse_bound("invalid-bound")


# ----------------------------------------------------------------------------
# Crs.to_short_notation

def test_none_input():
    assert Crs.to_short_notation(None) is None


def test_short_notation():
    assert Crs.to_short_notation("EPSG:4326") == "EPSG:4326"
    assert Crs.to_short_notation("EPSG:1:4326") == "EPSG:1:4326"


def test_path_notation():
    assert Crs.to_short_notation("EPSG/0/4326") == "EPSG:4326"


def test_full_url_notation():
    assert Crs.to_short_notation("http://localhost:8080/rasdaman/def/crs/EPSG/0/4326") == "EPSG:4326"


def test_full_url_with_version_notation():
    assert Crs.to_short_notation("http://localhost:8080/rasdaman/def/crs/EPSG/1/4326") == "EPSG:1:4326"


def test_compound_url_notation():
    url = ("https://www.opengis.net/def/crs-compound?"
           "1=http://localhost:8080/rasdaman/def/crs/EPSG/0/4326&"
           "2=http://localhost:8080/rasdaman/def/crs/EPSG/0/3857")
    expected = "EPSG:4326+EPSG:3857"
    assert Crs.to_short_notation(url) == expected


def test_compound_url_with_version_notation():
    url = ("https://www.opengis.net/def/crs-compound?"
           "1=http://localhost:8080/rasdaman/def/crs/EPSG/1/4326&"
           "2=http://localhost:8080/rasdaman/def/crs/EPSG/0/3857")
    expected = "EPSG:1:4326+EPSG:3857"
    assert Crs.to_short_notation(url) == expected


def test_unrecognized_url():
    assert Crs.to_short_notation("http://example.com/unknown") is None


# ----------------------------------------------------------------------------
# parse_tag_name

def test_parse_tag_name_with_namespace():
    element = ET.Element("{http://www.example.com}root")
    assert parse_tag_name(element) == "root"


def test_parse_tag_name_without_namespace():
    element = ET.Element("root")
    assert parse_tag_name(element) == "root"


def test_parse_tag_name_empty_namespace():
    element = ET.Element("{ }root")
    assert parse_tag_name(element) == "root"


# ----------------------------------------------------------------------------
# element_to_dict


def test_element_to_dict():
    xml_string = '''
    <Metadata>
        <covMetadata>
            <title>Temperature</title>
            <abstract>Monthly average air temperature.</abstract>
            <description>Description.</description>
            <keywords>climate, temperature</keywords>
        </covMetadata>
        <rasdamanCoverageMetadata>
            <catalog>
                <title>Temperature</title>
                <thumbnail>https://localhost:8080/rasdaman/ows/coverage/Temperature</thumbnail>
                <description>Description.</description>
                <provenance sourceUrl="https://localhost" providerName="P" termsUrl="http://localhost"/>
                <ourTerms>https://localhost/#terms</ourTerms>
            </catalog>
        </rasdamanCoverageMetadata>
        <otherMetadata role="https://codelists" title="Catalog" href="https://localhost"/>
    </Metadata>
    '''
    t = ET.fromstring(xml_string)
    d = element_to_dict(t)['Metadata']
    expected = {
        'covMetadata': {
            'abstract': 'Monthly average air temperature.',
            'description': 'Description.',
            'keywords': 'climate, temperature',
            'title': 'Temperature'
        },
        'otherMetadata': {
            '@href': 'https://localhost', '@role': 'https://codelists', '@title': 'Catalog'
        },
        'rasdamanCoverageMetadata': {
            'catalog': {
                'description': 'Description.',
                'ourTerms': 'https://localhost/#terms',
                'provenance': {'@providerName': 'P', '@sourceUrl': 'https://localhost',
                               '@termsUrl': 'http://localhost'},
                'thumbnail': 'https://localhost:8080/rasdaman/ows/coverage/Temperature',
                'title': 'Temperature'
            }
        }
    }
    assert d == expected


def test_element_to_dict_empty():
    xml_string = '''
    <Metadata>
    </Metadata>
    '''
    t = ET.fromstring(xml_string)
    d = element_to_dict(t)['Metadata']
    expected = ''
    assert d == expected
