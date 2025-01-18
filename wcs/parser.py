"""
Utility methods for parsing XML into :mod:`wcs.model` objects.
"""
import xml.etree.ElementTree as ET
from collections import defaultdict
from datetime import datetime
from typing import Union, Optional
from urllib.parse import urlparse, parse_qs

from wcs.model import (BasicCoverage, WCSClientException,
                       BoundingBox, BoundType, Axis, FullCoverage,
                       RangeType, Field, NilValue)


# ---------------------------------------------------------------------------------------
# DescribeCoverage
# ---------------------------------------------------------------------------------------


def parse_describe_coverage(xml_string: Union[str, bytes]) -> FullCoverage:
    """
    Parses an XML string from a DescribeCoverage response into a :class:`wcs.model.FullCoverage`.

    It extracts essential information including the coverage name, metadata,
    domain set, and range type. The extracted data is used to construct and return
    a :class:`wcs.model.FullCoverage` object.

    :param xml_string: An XML string or bytes object containing the DescribeCoverage
        document. The XML should contain elements such as 'CoverageDescription',
        'Metadata', 'DomainSet', and 'RangeType'.

    :return: A :class:`wcs.model.FullCoverage` object constructed from the parsed XML data.

    :raises WCSClientException: If the XML does not contain a valid 'CoverageDescription'
        element or if the parsing process encounters any other issues.
    :raises ET.ParseError: If the XML string is malformed and cannot be parsed.
    """
    root = ET.fromstring(xml_string)
    cov_desc = None
    for child in root:
        if child.tag.endswith('CoverageDescription'):
            cov_desc = child
            break

    if cov_desc is None:
        raise WCSClientException("Invalid DescribeCoverage document: "
                                 "no CoverageDescription element found.")

    name = get_child(cov_desc, 'CoverageId').text
    metadata_element = get_child(cov_desc, 'Metadata', throw_if_not_found=False)
    domain_set_element = get_child(cov_desc, 'DomainSet')
    range_type_element = get_child(cov_desc, 'RangeType')

    geo_bbox, grid_bbox = parse_domain_set(domain_set_element)
    range_type = parse_range_type(range_type_element)
    metadata = parse_metadata(metadata_element)

    return FullCoverage(name, bbox=geo_bbox, grid_bbox=grid_bbox, range_type=range_type, metadata=metadata)


def parse_domain_set(domain_set_element: Optional[ET]) -> tuple[Optional[BoundingBox], Optional[BoundingBox]]:
    """
    Parses an XML element representing a DomainSet into corresponding objects.

    It extracts information about spatio-temporal regular/irregular axes, and constructs
    geo and grid :class:`wcs.model.BoundingBox` objects. Example XML structure:

    .. code:: xml

        <cis11:DomainSet>
          <cis11:GeneralGrid
            srsName="https://www.opengis.net/def/crs-compound?
            1=https://www.opengis.net/def/crs/OGC/0/AnsiDate&amp;
            2=https://www.opengis.net/def/crs/EPSG/0/4326"
            axisLabels="ansi Lat Lon">
            <cis11:RegularAxis axisLabel="Lat" uomLabel="degree"
              lowerBound="-90" upperBound="90" resolution="-0.1"/>
            <cis11:RegularAxis axisLabel="Lon" uomLabel="degree"
              lowerBound="-180" upperBound="180" resolution="0.1"/>
            <cis11:IrregularAxis axisLabel="ansi" uomLabel="d">
              <cis11:C>"2000-02-01T00:00:00.000Z"</cis11:C>
              <cis11:C>"2000-03-01T00:00:00.000Z"</cis11:C>
            </cis11:IrregularAxis>
            <cis11:GridLimits
              srsName="http://www.opengis.net/def/crs/OGC/0/Index3D"
              axisLabels="i j k">
              <cis11:IndexAxis axisLabel="i"
                lowerBound="0" upperBound="184"/>
              <cis11:IndexAxis axisLabel="j"
                lowerBound="0" upperBound="1799"/>
              <cis11:IndexAxis axisLabel="k"
                lowerBound="0" upperBound="3599"/>
            </cis11:GridLimits>
          </cis11:GeneralGrid>
        </cis11:DomainSet>

    :param domain_set_element: An XML element representing the DomainSet
        structure. It should contain one or more 'cis11:GeneralGrid' elements,
        which in turn include 'cis11:RegularAxis' or 'cis11:IrregularAxis' elements,
        and a 'cis11:GridLimits' element.

    :return: A tuple containing geo and grid :class:`BoundingBox` objects.
        If the input is None, the function returns (None, None).

    :raises WCSClientException: If the provided XML does not conform to the expected structure.
    """
    if domain_set_element is None:
        return None, None
    validate_tag_name(domain_set_element, 'DomainSet')

    geo_axes = []
    grid_axes = []

    general_grid = first_child(domain_set_element, 'GeneralGrid')
    crs = general_grid.get('srsName')

    for axis_element in general_grid:
        tag = parse_tag_name(axis_element)
        name = axis_element.get('axisLabel')

        if tag == 'RegularAxis':
            resolution = axis_element.get('resolution')
            try:
                resolution = float(resolution)
            except ValueError:
                # it may be a datetime resolution which is not a number
                pass

            geo_axes.append(Axis(name,
                                 low=parse_bound(axis_element.get('lowerBound')),
                                 high=parse_bound(axis_element.get('upperBound')),
                                 uom=axis_element.get('uomLabel'),
                                 resolution=resolution))

        elif tag == 'IrregularAxis':
            coefficients = [parse_bound(c.text) for c in axis_element]
            geo_axes.append(Axis(name, low=coefficients[0], high=coefficients[-1],
                                 uom=axis_element.get('uomLabel'),
                                 coefficients=coefficients))

        elif tag == 'GridLimits':
            for index_axis in axis_element:
                grid_axes.append(Axis(index_axis.get('axisLabel'),
                                      low=parse_bound(index_axis.get('lowerBound')),
                                      high=parse_bound(index_axis.get('upperBound')),
                                      resolution=1))

    # sort the geo_axes to match the order of axis_labels
    axis_labels = general_grid.get('axisLabels')
    if axis_labels is None:
        raise WCSClientException("GeneralGrid element missing axisLabels attribute.")
    name_to_index = {name: index for index, name in enumerate(axis_labels.split())}
    geo_axes = sorted(geo_axes, key=lambda axis: name_to_index[axis.name])

    # set axis CRS
    for axis, axis_crs in zip(geo_axes, crs_to_crs_per_axis(crs)):
        axis.crs = axis_crs

    return BoundingBox(geo_axes, crs), BoundingBox(grid_axes, None)


def parse_range_type(range_type_element: Optional[ET]) -> Optional[RangeType]:
    """
    Parses an XML element representing a RangeType into a :class:`wcs.model.RangeType` object.

    This function processes an XML element handling either
    'swe:Category' or 'swe:Quantity' fields within a 'swe:DataRecord'.
    It extracts fields information such as field name, definition, label,
    description, codespace, unit of measurement, and nil values,
    constructing a list of :class:`wcs.model.Field` objects that are then encapsulated within
    a :class:`wcs.model.RangeType` object.

    Supported XML structures:

    1. **swe:Category field**:

       .. code:: xml

            <cis11:RangeType>
              <swe:DataRecord>
                <swe:field name="land_use">
                  <swe:Category definition="...">
                    <swe:label>National Land Use</swe:label>
                    <swe:description>description text</swe:description>
                    <swe:nilValues>
                      <swe:NilValues>
                        <swe:nilValue reason="">0</swe:nilValue>
                      </swe:NilValues>
                    </swe:nilValues>
                    <swe:codeSpace xlink:href="...."/>
                  </swe:Category>
                </swe:field>
              </swe:DataRecord>
            </cis11:RangeType>

    2. **swe:Quantity field**:

       .. code:: xml

            <cis11:RangeType>
              <swe:DataRecord>
                <swe:field name="temperature">
                  <swe:Quantity definition="...">
                    <swe:label>Monthly temperature</swe:label>
                    <swe:description>description text</swe:description>
                    <swe:nilValues>
                      <swe:NilValues>
                        <swe:nilValue reason="">-9999</swe:nilValue>
                      </swe:NilValues>
                    </swe:nilValues>
                    <swe:uom code="°C"/>
                  </swe:Quantity>
                </swe:field>
              </swe:DataRecord>
            </cis11:RangeType>

    :param range_type_element: An XML element representing the RangeType
        structure. It should contain one or more 'swe:DataRecord' elements,
        each with 'swe:field' elements that can be either 'swe:Category' or
        'swe:Quantity'.

    :return: A RangeType object containing a list of Field objects. Each Field
        object represents either a 'swe:Category' or 'swe:Quantity' extracted
        from the XML, with associated metadata. If the input is None, then
        None is returned.

    :raises WCSClientException: If the provided XML does not conform to the expected structure.
    """
    if range_type_element is None:
        return None
    validate_tag_name(range_type_element, 'RangeType')

    fields: list[Field] = []
    data_record = first_child(range_type_element, 'DataRecord')

    for field_element in data_record:
        name = field_element.get('name')
        field = Field(name)

        child = first_child(field_element)
        # child = swe:Quantity or swe:Category
        field.is_quantity = parse_tag_name(child) == 'Quantity'
        field.definition = child.get('definition')
        for c in child:
            tag = parse_tag_name(c)
            if tag == 'label':
                field.label = c.text
            elif tag == 'description':
                field.description = c.text
            elif tag == 'codeSpace':
                field.codespace = c.get('href')
            elif tag == 'uom':
                field.uom = c.get('code')
            elif tag == 'nilValues':
                field.nil_values = []
                nil_values_element = first_child(c)
                if parse_tag_name(nil_values_element) == 'NilValues':
                    for nil_value in nil_values_element:
                        value = nil_value.text
                        reason = nil_value.get('reason')
                        field.nil_values.append(NilValue(nil_value=value, reason=reason))

        fields.append(field)

    return RangeType(fields)


def parse_metadata(metadata_element: Optional[ET]) -> dict:
    """
    Parse an XML Metadata element into a dictionary. Example XML structure:

    .. code:: xml

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
              <thumbnail>https://localhost/thumbnail.png</thumbnail>
              <description>Description.</description>
              <provenance sourceUrl="https://localhost"
                providerName="P" termsUrl="http://localhost"/>
              <ourTerms>https://localhost/#terms</ourTerms>
            </catalog>
          </rasdamanCoverageMetadata>
          <otherMetadata role="https://codelists" title="Catalog"
            href="https://localhost"/>
        </Metadata>

    :param metadata_element: An XML element containing metadata information.
        This element is expected to have the tag 'Metadata'.

    :return: A dictionary representation of the metadata contained within the
        XML element. Nested elements are converted to nested dicts. Element attributes
        convert to key names starting with '@'.
        If the input is ``None`` or an empty XML element, an empty dictionary is returned.

    :raises WCSClientException: If the root tag of ``metadata_element`` is not 'Metadata'.
    """
    if metadata_element is None:
        return {}
    validate_tag_name(metadata_element, 'Metadata')
    ret = element_to_dict(metadata_element)
    ret = ret.get('Metadata', ret)
    if isinstance(ret, str):
        if ret == '':
            # empty <Metadata/> element
            return {}

    return ret


# ---------------------------------------------------------------------------------------
# GetCapabilities
# ---------------------------------------------------------------------------------------

def parse_coverage_summaries(xml_string: Union[str, bytes]) -> list[BasicCoverage]:
    """
    Parses CoverageSummary XML elements from a GetCapabilities XML string.

    This function takes an XML string representing a GetCapabilities response,
    searches for the 'Contents' element, and extracts all 'CoverageSummary'
    elements within it. Each 'CoverageSummary' element is parsed into a
    :class:`wcs.model.BasicCoverage` object using the
    :meth:`parse_coverage_summary` function.

    :param xml_string: A GetCapabilities XML string, provided as either a
                       string or bytes object.
    :return: A list of BasicCoverage objects, each representing a parsed
             CoverageSummary element from the XML.
    :raises WCSClientException: If the XML does not contain a 'Contents'
                                element, indicating an invalid GetCapabilities
                                document.
    """
    root = ET.fromstring(xml_string)
    contents = None
    for child in root:
        if child.tag.endswith('Contents'):
            contents = child
            break

    if contents is None:
        raise WCSClientException("Invalid GetCapabilities document: "
                                 "no Contents element found.")

    ret = []

    for coverage_summary in contents:
        ret.append(parse_coverage_summary(coverage_summary))

    return ret


def parse_coverage_summary(element: Optional[ET]) -> Optional[BasicCoverage]:
    """
    Parses an XML element representing a Coverage Summary into a BasicCoverage object.
    Example XML structure:

    .. code:: xml

        <wcs20:CoverageSummary>
          <wcs20:CoverageId>AverageChloroColorScaled</wcs20:CoverageId>
          <wcs20:CoverageSubtype>ReferenceableGridCoverage
          </wcs20:CoverageSubtype>
          <ows:WGS84BoundingBox>
            <ows:LowerCorner>-180 -90</ows:LowerCorner>
            <ows:UpperCorner>180 90</ows:UpperCorner>
          </ows:WGS84BoundingBox>
          <ows:BoundingBox
            crs="https://www.opengis.net/def/crs-compound?
            1=https://www.opengis.net/def/crs/OGC/0/AnsiDate&amp;
            2=https://www.opengis.net/def/crs/EPSG/0/4326"
            dimensions="3">
            <ows:LowerCorner>
                "2002-07-01T00:00:00.000Z" -90 -180
            </ows:LowerCorner>
            <ows:UpperCorner>
                "2015-05-01T00:00:00.000Z" 90 180
            </ows:UpperCorner>
          </ows:BoundingBox>
          <ows:AdditionalParameters>
            <ows:AdditionalParameter>
              <ows:Name>sizeInBytes</ows:Name>
              <ows:Value>188325000</ows:Value>
            </ows:AdditionalParameter>
            <ows:AdditionalParameter>
              <ows:Name>axisList</ows:Name>
              <ows:Value>ansi,Lat,Lon</ows:Value>
            </ows:AdditionalParameter>
          </ows:AdditionalParameters>
        </wcs20:CoverageSummary>


    :param element: An XML element representing a CoverageSummary.
        it should contain 'CoverageId' and a 'CoverageSubtype', and optionally
        'WGS84BoundingBox', 'BoundingBox', and 'AdditionalParameters'.
    :return: A BasicCoverage object containing coverage information extracted from the XML,
        or None if ``element`` is None.
    :raises WCSClientException: If the coverage_summary_element does not have the
                                expected tag, or is missing a 'CoverageId' element.
    """
    if element is None:
        return None
    validate_tag_name(element, 'CoverageSummary')

    name, subtype, lon, lat, bbox = None, None, None, None, None
    params = {}

    for e in element:
        tag = parse_tag_name(e)
        if tag == 'CoverageId':
            name = e.text
        elif tag == 'CoverageSubtype':
            subtype = e.text
        elif tag == 'WGS84BoundingBox':
            lon, lat = parse_wgs84_bounding_box(e)
        elif tag == 'BoundingBox':
            bbox = parse_bounding_box(e)
        elif tag == 'AdditionalParameters':
            params = parse_additional_parameters(e)

    if name is None:
        raise WCSClientException("CoverageSummary is missing required CoverageId child element.")

    size_bytes, axis_list = None, None
    for key, value in params.items():
        if key == 'sizeInBytes':
            size_bytes = int(value)
        if key == 'axisList':
            axis_list = value.split(',')

    params.pop('sizeInBytes', None)
    params.pop('axisList', None)

    if axis_list is not None and bbox is not None:
        for axis_name, axis in zip(axis_list, bbox.axes):
            axis.name = axis_name

    return BasicCoverage(name,
                         subtype=subtype,
                         lon_lat=(lon, lat),
                         bbox=bbox,
                         size_bytes=size_bytes,
                         additional_params=params)


def parse_wgs84_bounding_box(element: Optional[ET]) -> Optional[tuple[Axis, Axis]]:
    """
    Parses an XML element representing a WGS84 bounding box into a tuple of lon/lat
    :class:`wcs.model.Axis` objects. Example XML structure:

    .. code:: xml

        <ows:WGS84BoundingBox>
            <ows:LowerCorner>-180 -90</ows:LowerCorner>
            <ows:UpperCorner>180 90</ows:UpperCorner>
        </ows:WGS84BoundingBox>

    :param element: A 'WGS84BoundingBox' XML element containing
        'LowerCorner' and 'UpperCorner' elements.
    :return: a tuple of lon/lat :class:`wcs.model.Axis` objects, or None if the input element is None.
    :raises WCSClientException: If the element tag is not 'WGS84BoundingBox'.
    """
    if element is None:
        return None
    validate_tag_name(element, 'WGS84BoundingBox')

    bbox = parse_bounding_box(element, crs='EPSG:4326')
    axes = bbox.axes
    if len(axes) != 2:
        raise WCSClientException(f"Expected a WGS84BoundingBox element bounds for lon/lat axes, "
                                 f"but got {len(axes)} bounds")
    axes[0].name = 'Lon'
    axes[1].name = 'Lat'
    return axes[0], axes[1]


def parse_bounding_box(bbox_element: Optional[ET], crs: str = None) -> Optional[BoundingBox]:
    """
    Parses an XML element representing a bounding box into a BoundingBox object.
    Example XML structure:

    .. code:: xml

        <ows:BoundingBox
          crs="https://www.opengis.net/def/crs-compound?
          1=https://www.opengis.net/def/crs/OGC/0/AnsiDate&amp;
          2=https://www.opengis.net/def/crs/EPSG/0/4326" dimensions="3">
          <ows:LowerCorner>
            "2002-07-01T00:00:00.000Z" -90 -180
          </ows:LowerCorner>
          <ows:UpperCorner>
            "2015-05-01T00:00:00.000Z" 90 180
          </ows:UpperCorner>
        </ows:BoundingBox>

    :param bbox_element: An XML element representing the bounding box. It should
                         contain 'LowerCorner' and 'UpperCorner' child elements.
    :param crs: An optional CRS identifier string. If not provided, the CRS is
                inferred from the 'crs' attribute of the bbox_element.
    :return: A :class:`wcs.model.BoundingBox` object containing the parsed CRS and axis
        lower/upper bounds.
    :raises WCSClientException: If the parsing of 'LowerCorner' or 'UpperCorner' elements fails.
    """
    if bbox_element is None:
        return None

    tag = parse_tag_name(bbox_element)
    ll, ur = None, None
    for e in bbox_element:
        tag = parse_tag_name(e)
        if tag == 'LowerCorner':
            ll = parse_bounds_list(e.text)
        elif tag == 'UpperCorner':
            ur = parse_bounds_list(e.text)

    if ll is None:
        raise WCSClientException(f"Failed parsing {tag}/LowerCorner element.")
    if ur is None:
        raise WCSClientException(f"Failed parsing {tag}/UpperCorner element.")

    if crs is None:
        crs = bbox_element.get('crs')
    if crs is None:
        raise WCSClientException(f"Failed parsing CRS from XML element:\n"
                                 f"{element_to_string(bbox_element)}")

    axis_crss = crs_to_crs_per_axis(crs)
    axes = []
    for low, high, axis_crs in zip(ll, ur, axis_crss):
        axes.append(Axis('', low, high, crs=axis_crs))

    return BoundingBox(axes, crs)


def parse_additional_parameters(element: ET) -> dict[str, str]:
    """
    Parses additional parameters from an XML element into a dict of key/value strings.
    Example XML structure:

    .. code:: xml

        <ows:AdditionalParameters>
            <ows:AdditionalParameter>
                <ows:Name>sizeInBytes</ows:Name>
                <ows:Value>188325000</ows:Value>
            </ows:AdditionalParameter>
            <ows:AdditionalParameter>
                <ows:Name>axisList</ows:Name>
                <ows:Value>ansi,Lat,Lon</ows:Value>
            </ows:AdditionalParameter>
        </ows:AdditionalParameters>

    :param element: An XML element containing 'AdditionalParameter' child elements.
                    Each 'AdditionalParameter' element is expected to contain a 'Name'
                    and a 'Value' sub-element.
    :return: A dictionary mapping parameter names to their values.
    :raises WCSClientException: If an unexpected element is found,
                                or if 'Name' or 'Value' elements are missing.
    """
    ret = {}
    if element is None:
        return ret
    validate_tag_name(element, 'AdditionalParameters')
    for param in element:
        tag = parse_tag_name(param)
        if tag != 'AdditionalParameter':
            raise WCSClientException(f"Unexpected child element of AdditionalParameters: {tag}")

        name, value = None, None
        for child in param:
            tag = parse_tag_name(child)
            if tag == 'Name':
                name = child.text
            elif tag == 'Value':
                value = child.text
            else:
                raise WCSClientException(f"Unexpected child element of AdditionalParameter: {tag}")

        if name is None:
            raise WCSClientException("AdditionalParameter element missing a Name child element.")
        if value is None:
            raise WCSClientException("AdditionalParameter element missing a Value child element.")

        ret[name] = value

    return ret


def parse_bounds_list(element_text: Optional[str]) -> list[BoundType]:
    """
    Parses a space-separated string of axis bounds into a list of properly
    typed bound values. Each string bound is parsed with :meth:`parse_bound`.

    :param element_text: A space-separated string containing bound values.
    :return: A list of parsed bounds, where each bound is of type :attr:`BoundType`.
    :raises WCSClientException: If any bound in the list cannot be parsed into
                                a supported type by :meth:`parse_bound`.
    """
    if element_text is None:
        return []
    bounds = element_text.split()
    ret = [parse_bound(bnd) for bnd in bounds]
    return ret


def parse_bound(bound: Optional[str]) -> Optional[BoundType]:
    """
    Parses a given axis bound string into its appropriate data type.

    The method attempts to interpret the input ``bound`` in several formats:

    - A string representing a datetime in ISO 8601 format.
    - A raw string if it starts with a " but failed to parse as a datetime.
    - A string representing an integer.
    - A string representing a float.

    :param bound: A string representing the bound value to be parsed. It can be
                  a string datetime in ISO 8601 format (optionally in double quotes),
                  an integer, or a float.
    :return: The parsed bound in its appropriate data type.
             Returns `None`` if the input is `None``.
    :raises WCSClientException: If the `bound`` cannot be parsed into any of the supported types.
    """
    if bound is None:
        return None

    is_string = bound.startswith('"')
    bound = bound.strip('"')

    # attempt to parse as a datetime
    try:
        return datetime.fromisoformat(bound)
    except ValueError:
        pass

    if is_string:
        return bound

    # attempt to parse as an integer
    try:
        return int(bound)
    except ValueError:
        pass

    # attempt to parse as a float
    try:
        return float(bound)
    except ValueError:
        pass

    raise WCSClientException(f"Failed parsing bound '{bound}'")


def crs_to_crs_per_axis(crs: str) -> list[str]:
    """
    Convert a single CRS to a list of CRS per axis.
    If ``crs`` contains crs-compound, i.e. it is a compund CRS, then it is split first
    into it's component CRS. For each crs then,
    - it is added twice into the result list if 'EPSG' is contained in it
    - otherwise, it is added once into the result list

    :return: a list of CRS per axis, or an empty list if crs is None.
    """
    if crs is None:
        return []
    crss = []
    if 'crs-compound' in crs:
        parsed_url = urlparse(crs)
        query_params = parse_qs(parsed_url.query)
        for _, value in query_params.items():
            for subcrs in value:
                crss.append(subcrs)
    else:
        crss = [crs]

    ret = []
    for axis_crs in crss:
        ret.append(axis_crs)
        if 'EPSG' in axis_crs:
            ret.append(axis_crs)
    return ret


# ---------------------------------------------------------------------------------------
# XML
# ---------------------------------------------------------------------------------------


def get_child(element: ET, tag: str, throw_if_not_found=True) -> Optional[ET]:
    """
    Retrieve a child element matching a given ``tag`` from an XML element.

    :param element: The XML element to search for a child with the specified tag.
        The tags of child elements are parsed to remove namespaces before comparison
        with the :meth:`parse_parse_tag_name` method.
    :param tag: The tag name of the child element to search for; it should not
        include any namespaces.
    :param throw_if_not_found: If True, raises an exception when no matching child is found.
                               If False, returns None instead.

    :return: The first child element with the specified tag, or None if not found
             ``throw_if_not_found`` is False.

    :raises WCSClientException: If no child with the specified tag is found and
                                ``throw_if_not_found`` is True.
    """
    for child in element:
        child_tag = parse_tag_name(child)
        if child_tag == tag:
            return child

    if throw_if_not_found:
        raise WCSClientException(f'No element {tag} found under element {parse_tag_name(element)}')

    return None


def first_child(element: ET, expected_tag: str = None) -> Optional[ET]:
    """
    Retrieve the first child element of an XML element.

    Optionally, it can validate the tag of the first child against an expected
    tag (without any namespaces). If no children are present, it raises a
    :class:`wcs.model.WCSClientException`.

    :param element: The XML element whose first child is to be retrieved.
    :param expected_tag: The expected tag name of the first child element.
                         If provided, the function will validate the tag of the first child.

    :return: The first child element of the given XML element.

    :raises WCSClientException: If the element has no children or if the tag of the
                                first child does not match the expected tag.
    """
    for c in element:
        if expected_tag is not None:
            validate_tag_name(c, expected_tag)
        return c
    raise WCSClientException(f'Element {parse_tag_name(element)} has no child element.')


def parse_tag_name(element: ET) -> str:
    """
    Extract just the tag name of an XML element, removing namespace components.
    Example: "{http://www.example.com}root" -> "root"

    :param element: An XML element from which to extract the tag name.
    :return: The tag name of the element.
    """
    return element.tag.split('}')[-1]


def validate_tag_name(element: ET, expected_tag: str):
    """
    Validate the tag name of an XML element against an expected tag.

    This function checks if the tag name of the given XML element matches the
    expected tag. It uses the :meth:`parse_tag_name` function to remove any
    namespaces in the tag name. If the tag names do not match, it raises a
    :class:`wcs.model.WCSClientException`.

    :param element: The XML element whose tag name is to be validated.
    :param expected_tag: The expected tag name to validate against.

    :raises WCSClientException: If the tag name of the ``element`` does not match the
                                expected tag.
    """
    tag = parse_tag_name(element)
    if tag != expected_tag:
        raise WCSClientException(f"Expected a {expected_tag} element, but got {tag}")


def element_to_string(element: ET) -> str:
    """
    Serialize an XML element to a string.

    :param element: The XML element to serialize.
    :return: A Unicode string representation of the XML element.
    """
    return ET.tostring(element, encoding='unicode', method='xml')


def element_to_dict(t: ET) -> dict:
    """
    Convert an XML element into a nested dictionary.

    This function recursively converts an XML element and its children into a
    nested dictionary. The keys of the dictionary are the tag names of the XML
    elements. Attributes of the XML elements are prefixed with '@' in the
    dictionary keys, and text content is stored under a '#text' key.

    :param t: The XML element to convert.
    :return: A nested dictionary representing the structure and content of the XML element.

    :note:
        - Elements with multiple children having the same tag name are converted into lists.
        - Text content is only added to the dictionary if the element has children
          or attributes, to avoid overwriting important data with whitespace.
    """
    tag = parse_tag_name(t)
    d = {tag: {} if t.attrib else None}
    children = list(t)
    if children:
        dd = defaultdict(list)
        for dc in map(element_to_dict, children):
            for k, v in dc.items():
                dd[k].append(v)
        d = {tag: {k: v[0] if len(v) == 1 else v for k, v in dd.items()}}
    if t.attrib:
        d[tag].update(('@' + k, v) for k, v in t.attrib.items())
    if t.text:
        text = t.text.strip()
        if children or t.attrib:
            if text:
                d[tag]['#text'] = text
        else:
            d[tag] = text
    return d
