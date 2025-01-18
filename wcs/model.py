"""
Classes holding information about coverages on a WCS server.
"""

# postpone evaluations of type annotations
# https://stackoverflow.com/a/33533514
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Union, Optional
from urllib.parse import parse_qs, urlparse
import json
import textwrap

BoundType = Union[int, float, str, datetime]
"""Type for axis interval bounds."""

@dataclass
class BasicCoverage:
    """
    Holds basic coverage information extracted from the WCS GetCapabilities
    document, notably the WGS bounding box if provided.

    :param name: the coverage name.
    :param subtype: coverage subtype, e.g. 'ReferenceableGridCoverage'
    :param wgs84_bbox: a WGS84 bbox
    :param bbox: bounding box in native CRS
    :param size_bytes: coverage size in bytes; None if not reported by the server
    :param additional_params: additional key/value parameters
    """

    def __init__(self,
                 name: str,
                 subtype: str = None,
                 wgs84_bbox: WGS84BoundingBox = None,
                 bbox: BoundingBox = None,
                 size_bytes: int = None,
                 additional_params: dict[str, str] = None):
        self.name = name
        self.subtype = subtype
        self.wgs84_bbox = wgs84_bbox
        self.bbox = bbox
        self.size_bytes = size_bytes
        self.additional_params = additional_params

    def __str__(self):
        indent = '\n- '
        ret = self.name
        if self.subtype is not None:
            ret += f'{indent}subtype: {self.subtype}'
        if self.bbox is not None:
            ret += f'\n{self.bbox}'
        if self.wgs84_bbox is not None:
            ret += f'{indent}WGS84 bbox: {self.wgs84_bbox}'
        if self.size_bytes is not None:
            ret += f'{indent}size in bytes: {self.size_bytes}'
        if self.additional_params is not None and len(self.additional_params) > 0:
            ret += f'{indent}additional params: {self.additional_params}'
        return ret


@dataclass
class FullCoverage:
    """
    Holds full coverage information extracted from the WCS DescribeCoverage.

    :param name: the coverage name.
    :param bbox: bounding box in native CRS
    :param grid_bbox: grid bounding box
    :param range_type: coverage range type
    """

    def __init__(self,
                 name: str,
                 bbox: BoundingBox,
                 grid_bbox: GridBoundingBox,
                 range_type: RangeType,
                 metadata: dict = None):
        self.name = name
        self.bbox = bbox
        self.grid_bbox = grid_bbox
        self.range_type = range_type
        self.metadata = metadata or {}

    def __str__(self):
        ret = self.name + ':'
        if self.bbox is not None:
            ret += f'\n{self.bbox}'
        if self.grid_bbox is not None:
            ret += f'\n{self.grid_bbox}'
        if self.range_type is not None:
            ret += f'\n{self.range_type}'
        if len(self.metadata) > 0:
            metadata = json.dumps(self.metadata, indent=2)
            metadata = textwrap.indent(metadata, ' ' * 4)
            ret += f'\n  metadata:\n{metadata}'
        return ret


@dataclass
class Axis:
    """
    An axis with a name, low/upper bounds, a CRS, uom, resolution, coefficients.

    :param axis_name: Name of the axis.
    :param low: Lower bound of the axis.
    :param high: Upper bound of the axis.
    :param crs: Coordinate Reference System, e.g., "EPSG:4326".
    :param uom: Unit of measure, e.g., "degree".
    :param resolution: Axis resolution, for regular axes.
    :param is_regular: True if regularly gridded, False if irregular, None if unknown.
    :param coefficients: Axis coefficients for irregular axes.
    """
    axis_name: str
    low: BoundType
    high: BoundType
    crs: Optional[Crs] = None
    uom: Optional[str] = None
    resolution: Optional[BoundType] = None
    is_regular: Optional[bool] = None
    coefficients: Optional[list[BoundType]] = None

    def __str__(self):
        indent = '\n    '
        ret = f'{indent}{self.axis_name}:'
        indent += '  '
        ret += f'{indent}min: {_bound_to_str(self.low)}'
        ret += f'{indent}max: {_bound_to_str(self.high)}'
        if self.crs is not None:
            ret += f'{indent}crs: {self.crs}'
        if self.uom is not None:
            ret += f'{indent}uom: {self.uom}'
        if self.resolution is not None:
            ret += f'{indent}resolution: {self.resolution}'

        ret += f'{indent}type: {"regular" if self.is_regular else "irregular"}'

        if self.coefficients is not None:
            coefficients = ', '.join([_bound_to_str(c) for c in self.coefficients])
            coefficients = '[' + coefficients + ']'
            offset = ' ' * len('      coefficients: [')
            coefficients = textwrap.fill(coefficients, width=120, initial_indent=offset,
                                         subsequent_indent=offset, break_long_words=False)
            # remove the initial_indent which was added only to make sure the table width is consistent
            coefficients = coefficients.strip()
            ret += f'{indent}coefficients: {coefficients}'
        return ret


@dataclass
class WGS84BoundingBox:
    """
    Represents the WGS84 bounding box of a coverage.

    The WGS84BoundingBox defines the spatial extent of a coverage in terms of
    longitude and latitude, corresponding to the "WGS84BoundingBox" element in a
    GetCapabilities CoverageSummary. It contains the low/high limits of the
    longitude and latitude axes.

    Example XML structure for a WGS84BoundingBox:

    .. code:: xml

        <ows:WGS84BoundingBox>
            <ows:LowerCorner>-180 -90</ows:LowerCorner>
            <ows:UpperCorner>180 90</ows:UpperCorner>
        </ows:WGS84BoundingBox>

    :param lon: The :class:`Axis` object representing the longitude axis of the bounding box.
                It contains the lower and upper bounds for the longitude.
    :param lat: The :class:`Axis` object representing the latitude axis of the bounding box.
                It contains the lower and upper bounds for the latitude.
    """

    def __init__(self, lon: Axis, lat: Axis):
        self.lon = lon
        """The longitude axis of the bounding box, containing its lower and upper bounds."""
        self.lat = lat
        """The latitude axis of the bounding box, containing its lower and upper bounds."""

    def __str__(self):
        return f'[{self.lon}, {self.lat}]'


@dataclass
class BoundingBox:
    """
    The bounding box of a coverage, containing low/high limits of all its axes.
    Corresponds to the "BoundingBox" element in a GetCapabilities CoverageSummary, e.g.

    .. code:: xml

        <ows:BoundingBox
          crs="https://www.opengis.net/def/crs-compound?
          1=https://www.opengis.net/def/crs/OGC/0/AnsiDate&amp;
          2=https://www.opengis.net/def/crs/EPSG/0/4326" dimensions="3">
          <ows:LowerCorner>
            "2015-01-01T00:00:00.000Z" -90 -180
          </ows:LowerCorner>
          <ows:UpperCorner>
            "2015-05-01T00:00:00.000Z" 90 180
          </ows:UpperCorner>
        </ows:BoundingBox>

    :param crs: native CRS of the axis coordinates
    :param axes: a list of :class:`Axis` objects
    """

    def __init__(self, crs: Crs, axes: list[Axis]):
        self.crs = crs
        self.axes = axes
        # update the CRS of each axis properly
        crs_per_axis = crs.get_crs_per_axis()
        if len(self.axes) == len(crs_per_axis):
            for axis, axis_crs in zip(self.axes, crs_per_axis):
                axis.crs = Crs(axis_crs[0], axis_crs[1])

    def __str__(self):
        ret = f'  native CRS: {self.crs}\n'
        ret += f'  geo bbox:{_list_to_str(self.axes, "")}'
        return ret


@dataclass
class GridBoundingBox:
    """
    The grid bounding box of a coverage.

    It consists of grid integer low/high bounds for each axis.
    Unlike :class:`BoundingBox`, it is not geo-referenced so no CRS information is present.

    :param axes: a list of axes
    """

    def __init__(self, axes: list[Axis]):
        self.axes = axes

    def __str__(self):
        return f'  grid bbox:{_list_to_str(self.axes, "")}'


@dataclass
class Crs:
    """
    Handle coordinate reference system (CRS) identifiers.

    It stores a full CRS identifier and an optional shorthand CRS identifier.

    :param crs: The full coordinate reference system identifier.
                This is a complete URI or other identifier that specifies the
                spatial reference system used for the data.
    :param shorthand_crs: An optional shorthand identifier for the CRS, such as
                          an EPSG code (e.g., "EPSG:4326"). This provides a more
                          human-readable format.
    """

    def __init__(self, crs: str, shorthand_crs: str = None):
        self.crs = crs
        """The full CRS identifier."""
        self.shorthand_crs = shorthand_crs
        """A shorthand identifier for the CRS; defaults to None."""

    def __str__(self):
        return self.shorthand_crs if self.shorthand_crs else self.crs

    def get_crs_per_axis(self) -> list[tuple[str, str]]:
        """
        Expands the :attr:`crs` and :attr:`shorthand_crs` to individual pairs per axis.
        """
        crss = []
        if 'crs-compound' in self.crs:
            parsed_url = urlparse(self.crs)
            query_params = parse_qs(parsed_url.query)
            for _, value in query_params.items():
                for subcrs in value:
                    crss.append(subcrs)
        else:
            crss = [self.crs]

        if self.shorthand_crs is not None:
            shorthand_crss = self.shorthand_crs.split('+')
        else:
            shorthand_crss = [None] * len(crss)

        ret = []
        for crs, shorthand_crs in zip(crss, shorthand_crss):
            ret.append((crs, shorthand_crs))
            if 'EPSG' in crs:
                ret.append((crs, shorthand_crs))
        return ret

    def get_crs_for_axis(self, axis_index) -> tuple[str, str]:
        """
        :return: the (crs, shorthand_crs) for the given ``axis_index`` (0-based).
        """
        crs_per_axis = self.get_crs_per_axis()
        return crs_per_axis[axis_index]


@dataclass
class RangeType:
    """
    Represents the range type of a coverage, indicating the structure of the data.

    The range type consists of a list of field types (:class:`Field`).

    :param fields: A list of :class:`Field` objects describing the fields (also
                   known as bands or channels) of a coverage. Each field is
                   initialized based on its name, ensuring a unique mapping.
    """

    def __init__(self, fields):
        self.fields: dict[str, Field] = dict(zip([f.name for f in fields], fields))
        """
        A dictionary mapping field names to their corresponding :class:`Field` objects.
        """

    def __str__(self):
        fields = ''.join([str(f) for _, f in self.fields.items()])
        ret = f'  range type fields:{fields}'
        return ret


@dataclass
class Field:
    """
    A field (also known as band, or channel) in a coverage range type (:class:`RangeType`)

    It can be either a quantity or a category. It includes information about the
    field's name, definition, label, description, codespace (only Category),
    unit of measure (only Quantity), and any nil values.

    :param name: The name of the field. This can be used to subset bands in
        WCS GetCoverage requests or WCPS queries.
    :param is_quantity: Indicates whether this field is a Quantity (:code:`True`)
        or a Category (:code:`False`). Defaults to :code:`True`.
    :param definition: A URI that can be resolved to the complete human-readable
        definition of the property that is represented by the data component.
    :param label: Short human-readable information about the data component.
    :param description: A human-readable description of the data.
    :param codespace: A URL to an external dictionary, taxonomy, or ontology
        representing the code space. This attribute is only set for category data,
        i.e., when :attr:`is_quantity` is :code:`False`.
    :param uom: The unit of measure for this data.
    :param nil_values: A list of nil values associated with this field.
    """
    name: str
    """Field name that can be used to subset bands in WCS GetCoverage or WCPS queries."""
    is_quantity: bool = True
    """True if this field is a Quantity, False if it's a Category."""
    definition: str = None
    """A URI that can be resolved to the complete human readable definition of the
    property that is represented by the data component."""
    label: str = None
    """Short human readable information about the data component."""
    description: str = None
    """Human-readable description of the data."""
    codespace: str = None
    """
    URL to an external dictionary, taxonomy or ontology representing the code space.
    Only set for category data, i.e. :attr:`is_quantity` is False."""
    uom: str = None
    """Unit of measure for this data."""
    nil_values: list[NilValue] = None
    """A list of nil values."""

    def __str__(self):
        indent = '\n    '
        ret = f'{indent}{self.name}:'
        indent += '  '
        ret += f'{indent}type: ' + 'Quantity' if self.is_quantity else 'Category'
        if self.label is not None:
            ret += f'{indent}label: {self.label}'
        if self.description is not None:
            ret += f'{indent}description: {self.description}'
        if self.definition is not None:
            ret += f'{indent}definition: {self.definition}'
        if self.nil_values is not None and len(self.nil_values) > 0:
            ret += f'{indent}nil values: {_list_to_str(self.nil_values, ",")}'
        if self.codespace is not None:
            ret += f'{indent}codespace: {self.codespace}'
        if self.uom is not None:
            ret += f'{indent}uom: {self.uom}'
        return ret


@dataclass
class NilValue:
    """
    Represents a null value with an optional reason.

    :param nil_value: The null value itself, represented as a string.
    :param reason: An optional explanation for why the value is null.
        This is useful for providing context or documentation about the null
        value.
    """
    nil_value: str
    reason: Optional[str]

    def __str__(self):
        ret = self.nil_value
        if self.reason is not None and len(self.reason) > 0:
            ret += ': ' + self.reason
        return ret


class WCSClientException(Exception):
    """
    An exception thrown by this library.
    """


def _bound_to_str(bound: BoundType) -> str:
    """
    Convert an interval bound to its string representation.

    If the bound is a `datetime` object, the function formats
    it as an ISO 8601 string, potentially simplifying the format if the time
    components are zero. All other types are converted to strings directly.

    :param bound: The interval bound to convert.

    :return: A string representation of the bound. For `datetime` objects, the
             string is enquoted and formatted according to ISO 8601.

    :meta private:

    .. note::
        This function is intended for internal use within modules where interval
        bounds need to be serialized to strings.
    """
    if isinstance(bound, datetime):
        if bound.hour == 0 and bound.minute == 0 and bound.second == 0:
            ret = bound.strftime("%Y-%m-%d")
        else:
            ret = bound.isoformat()
        return '"' + ret + '"'

    return str(bound)


def _list_to_str(lst: list, sep: str) -> str:
    """
    Convert a list of items into a single string. Each item is converted to a string
    and separated by a specified separator in the result.

    :param lst: The list of items to be joined into a string. Each item in the list
                will be converted to a string before joining.
    :param sep: The separator to use between each item in the resulting string.

    :return: A single string containing all items from the list, separated by the
             specified separator.
    """
    return sep.join([str(item) for item in lst])
