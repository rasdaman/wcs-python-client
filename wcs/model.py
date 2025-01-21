"""
Classes holding information about coverages on a WCS server.
"""

# postpone evaluations of type annotations
# https://stackoverflow.com/a/33533514
from __future__ import annotations

import json
import textwrap
from dataclasses import dataclass
from datetime import datetime
from typing import Union, Optional
from urllib.parse import parse_qs, urlparse

BoundType = Union[int, float, str, datetime]
"""Type for axis interval bounds."""


@dataclass
class BasicCoverage:
    """
    Holds basic coverage information extracted from the WCS GetCapabilities
    document, notably the WGS bounding box if provided.

    :param name: the coverage name.
    :param subtype: coverage subtype, e.g. 'ReferenceableGridCoverage'
    :param bbox: bounding box in native CRS
    :param lon_lat: a tuple of longitude / latitude axes respresenting the
        WGS84 bounding box of the coverage
    :param size_bytes: coverage size in bytes; None if not reported by the server
    :param additional_params: additional key/value parameters
    """

    def __init__(self,
                 name: str,
                 subtype: str = None,
                 bbox: BoundingBox = None,
                 lon_lat: tuple[Axis, Axis] = None,
                 size_bytes: int = None,
                 additional_params: dict[str, str] = None):
        self.name = name
        """Coverage name"""
        self.subtype = subtype
        """Coverage subtype, e.g. ReferenceableGridCoverage"""
        self.bbox = bbox
        """Bounding box of all coverage axes in native CRS"""
        self.lon, self.lat = lon_lat or (None, None)
        """Longitude / Latitude axes describing the WGS84 bounding box of the coverage"""
        self.size_bytes = size_bytes
        """Coverage size in bytes; None if not reported by the server"""
        self.additional_params = additional_params
        """A dictionary of additional key/value parameters if reported by the server"""

    def __str__(self):
        ret = self.name + ':'
        if self.subtype is not None:
            ret += f'\n  subtype: {self.subtype}'
        if self.bbox is not None:
            ret += f'\n{self.bbox}'
        if self.lon is not None:
            ret += f'\n  lon/lat bbox:{self.lon}{self.lat}'
        if self.size_bytes is not None:
            ret += f'\n  size in bytes: {self.size_bytes}'
        if self.additional_params is not None and len(self.additional_params) > 0:
            ret += f'\n  additional params: {self.additional_params}'
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
                 grid_bbox: BoundingBox,
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

    A subset of the coefficients (axis coordinates) can be retrieved with the [] operator,
    e.g. for an irregular temporal axis: axis["2024-01-01" : "2024-01-31"].
    See :meth:`__getitem__` for more details.

    :param name: Name of the axis.
    :param low: Lower bound of the axis.
    :param high: Upper bound of the axis.
    :param crs: Coordinate Reference System, e.g., "EPSG:4326".
    :param uom: Unit of measure, e.g., "degree".
    :param resolution: Axis resolution, for regular axes.
    :param coefficients: Axis coefficients for irregular axes.
    """
    name: str
    low: BoundType
    high: BoundType
    crs: Optional[str] = None
    uom: Optional[str] = None
    resolution: Optional[BoundType] = None
    coefficients: Optional[list[BoundType]] = None

    def __str__(self):
        indent = '\n    '
        ret = f'{indent}{self.name}:'
        indent += '  '
        ret += f'{indent}min: {_bound_to_str(self.low)}'
        ret += f'{indent}max: {_bound_to_str(self.high)}'
        if self.crs is not None:
            ret += f'{indent}crs: {Crs.to_short_notation(self.crs)}'
        if self.uom is not None:
            ret += f'{indent}uom: {self.uom}'
        if self.resolution is not None:
            ret += f'{indent}resolution: {self.resolution}'

        if self.resolution is not None:
            ret += f'{indent}type: regular'
        if self.coefficients is not None:
            ret += f'{indent}type: irregular'

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

    def is_temporal(self) -> bool:
        """
        Returns: True if this axis is a temporal axis (e.g. ansi), False otherwise.
        """
        return isinstance(self.low, datetime)

    def is_spatial(self) -> bool:
        """
        Returns: True if this axis is a spatial axis (e.g. Lat, Lon, E, N), False otherwise.
        """
        return not self.is_temporal()

    def is_irregular(self) -> bool:
        """
        Returns: True if this axis is an irregular axis, False otherwise.
        """
        return self.coefficients is not None and len(self.coefficients) > 0

    def is_regular(self) -> bool:
        """
        Returns: True if this axis is a regular axis, False otherwise.
        """
        return self.resolution is not None

    def __getitem__(self, item) -> list[BoundType]:
        """
        - If :attr:`coefficients` is not None, then they are subsetted according to ``item``
        - Otherwise, a list of coefficients is generated according to the :attr:`resolution`,
          between the start and stop provided by the item slice.

        :param item: must be a :class:`slice` object with a start and stop set;
            the step is ignored. The start and stop must be valid coordinates in the
            axis :attr:`crs` and within the :attr:`low` / :attr:`high` bounds of this object.

        :raises WCSClientException:
            - if :attr:`coefficients` and :attr:`resolution` are both None.
            - if ``item`` is not a slice object
            - if the start / stop of ``item`` are invalid coordinates
        """
        if not isinstance(item, slice):
            raise WCSClientException(f"Invalid coordinates provided for operator [] "
                                     f"on axis {self.name}, expected a slice of the form start:stop.")
        if item.stop is None:
            raise WCSClientException(f"No upper limit provided for operator [] on axis {self.name}.")

        temporal = self.is_temporal()
        regular = self.is_regular()
        irregular = self.is_irregular()

        if not regular and not irregular:
            raise WCSClientException(f"operator [] is inapplicable to axis {self.name} "
                                     f"without a resolution or coefficients.")
        if temporal and not irregular:
            raise WCSClientException(f"operator [] is inapplicable to regular "
                                     f"temporal axis {self.name}.")

        start = item.start
        stop = item.stop

        # parse string datetime to datetimes if needed, and make sure all datetime have the same tzinfo
        if temporal:
            tz = self.coefficients[0].tzinfo
            if isinstance(start, str):
                start = datetime.fromisoformat(start)
            elif not isinstance(start, datetime):
                raise WCSClientException(f"Invalid type of start coordinate provided for operator [] "
                                         f"on axis {self.name}, expected either a string or a datetime.")
            if isinstance(stop, str):
                stop = datetime.fromisoformat(stop).replace(tzinfo=tz)
            elif not isinstance(stop, datetime):
                raise WCSClientException(f"Invalid type of stop coordinate provided for operator [] "
                                         f"on axis {self.name}, expected either a string or a datetime.")
            start = start.replace(tzinfo=tz)
            stop = stop.replace(tzinfo=tz)

        coefficients = self.get_coefficients()
        return [c for c in coefficients if start <= c <= stop]

    def get_coefficients(self) -> list[BoundType]:
        """
        :return: a list of coefficients, automatically generated if this
            is a regular axis.
        """
        if self.is_irregular():
            return self.coefficients
        if not self.is_regular():
            raise WCSClientException(f"{self.name} is not a regular or irregular "
                                     f"axis, cannot calculate coefficients.")

        ret = []
        current = self.low
        while current <= self.high:
            ret.append(current)
            current += self.resolution
        return ret


@dataclass
class BoundingBox:
    """
    The bounding box of a coverage, containing low/high limits of all its axes.

    The axes can be accessed through the :attr:`axes` attribute, or through
    the subscript operator, e.g.

    .. code:: python

        bbox[1]      # get the second axis
        bbox['Lat']  # get the axis with name Lat

    :param crs: native CRS of the axis coordinates
    :param axes: a list of :class:`Axis` objects
    """

    def __init__(self, axes: list[Axis], crs: Optional[str]):
        self.axes = axes
        self.crs = crs

    def __str__(self):
        bbox_type = 'grid'
        ret = ''
        if self.crs is not None:
            ret += f'  native CRS: {Crs.to_short_notation(self.crs)}\n'
            bbox_type = 'geo'
        ret += f'  {bbox_type} bbox:{_list_to_str(self.axes, "")}'
        return ret

    def __getitem__(self, index: Union[int, str]) -> Axis:
        """
        Get the :class:`Axis` object from the :attr:`axes` list
        according to the specified ``index``. The ``index`` can be an
        axis name, or an index of the axes list.
        :raise KeyError: if the axis name is not found, the axis index
            is out of bounds, or the ``index`` is not an int or string.
        """
        if isinstance(index, int):
            return self.axes[index]
        if isinstance(index, str):
            for axis in self.axes:
                if axis.name == index:
                    return axis

            axis_names = ', '.join([axis.name for axis in self.axes])
            raise KeyError(f"Axis '{index}' not found in the BoundingBox axes: {axis_names}")

        raise KeyError(f"Axis index has an invalid type {index.__class__},"
                       f"expected a string or int.")

    def __getattr__(self, item):
        """
        Get the :class:`Axis` object from the :attr:`axes` list
        according to the specified ``item``. The ``item`` can be an
        axis name, or an index of the axes list.
        :raise KeyError: if the axis name is not found, the axis index
            is out of bounds, or the ``item`` is not an int or string.
        """
        return self.__getitem__(item)


@dataclass
class RangeType:
    """
    Represents the range type of a coverage, indicating the structure of the data.

    The range type consists of a list of field types (:class:`Field`).
    The fields can be accessed through the :attr:`fields` attribute, or through
    the subscript operator, e.g.

    .. code:: python

        range_type[1]      # get the second field
        range_type['blue']  # get the field with name blue

    :param fields: A list of :class:`Field` objects describing the fields (also
                   known as bands or channels) of a coverage.
    """

    def __init__(self, fields):
        self.fields: list[Field] = fields
        """
        A list of :class:`Field` objects corresponding to the bands of the coverage.
        """

    def __str__(self):
        fields = _list_to_str(self.fields, '')
        ret = f'  range type fields:{fields}'
        return ret

    def __getitem__(self, index: Union[int, str]) -> Field:
        """
        Get the :class:`Field` object from the :attr:`fields` list
        according to the specified ``index``. The ``index`` can be a
        field (band) name, or an index of the fields list.
        :raise KeyError: if the field name is not found, the fields index
            is out of bounds, or the ``index`` is not an int or string.
        """
        if isinstance(index, int):
            return self.fields[index]
        if isinstance(index, str):
            for field in self.fields:
                if field.name == index:
                    return field

            names = ', '.join([field.name for field in self.fields])
            raise KeyError(f"Field '{index}' not found in the RangeType fields: {names}")

        raise KeyError(f"Field index has an invalid type {index.__class__},"
                       f"expected a string or int.")

    def __getattr__(self, item):
        """
        Get the :class:`Field` object from the :attr:`fields` list
        according to the specified ``item``. The ``item`` can be a
        field (band) name, or an index of the fields list.
        :raise KeyError: if the field name is not found, the fields index
            is out of bounds, or the ``item`` is not an int or string.
        """
        return self.__getitem__(item)


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


class Crs:
    """Utility class for handling CRS."""

    @staticmethod
    def to_short_notation(url: Optional[str]) -> Optional[str]:
        """
        Parse CRS identifiers in `this notation
        <https://doc.rasdaman.org/05_geo-services-guide.html#crs-notation>`_.

        :param url: a CRS identifier, e.g.

            - http://localhost:8080/rasdaman/def/crs/EPSG/0/4326
            - EPSG/0/4326
            - EPSG:4326

        :return: Short CRS notation, e.g. EPSG:4326; None if input is None or the method
            fails to parse the url.
        """
        if url is None:
            return None

        # handle "EPSG:4326"
        if not '/' in url:
            return url

        parsed_url = urlparse(url)
        path = parsed_url.path.strip('/')

        # compound urls, e.g. "https://www.opengis.net/def/crs-compound?1=..."
        if '/crs-compound' in url:
            query_params = parse_qs(parsed_url.query)
            ret = []
            for _, value in query_params.items():
                for subcrs in value:
                    ret.append(Crs.to_short_notation(subcrs))
            return '+'.join(ret)

        # url == "https://www.opengis.net/def/crs/EPSG/0/4326"
        parts = path.split('/')
        if len(parts) > 2:
            authority = parts[-3]
            version = parts[-2]
            code = parts[-1]
            if version == "0":
                return f'{authority}:{code}'
            return f'{authority}:{version}:{code}'

        return None


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
