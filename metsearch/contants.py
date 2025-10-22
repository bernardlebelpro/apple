from dataclasses import dataclass


MAX_RESULTS = 80


@dataclass
class Endpoints:
    BASE = "https://collectionapi.metmuseum.org/public/collection/v1"
    OBJECTS = "/objects"
    SEARCH = "/search"


@dataclass
class ObjectFields:
    ARTIST_DISPLAY_NAME = "artistDisplayName"
    CLASSIFICATION = "classification"
    CULTURE = "culture"
    DEPARTMENT = "department"
    MEDIUM = "medium"
    OBJECT_DATE = "objectDate"
    OBJECT_ID = "objectID"
    PRIMARY_IMAGE = "primaryImage"
    TITLE = "title"

    # Map field display names to the object's fields
    DISPLAY_FIELDS = (
        (TITLE, "Title"),
        (ARTIST_DISPLAY_NAME, "Artist"),
        (MEDIUM, "Medium"),
        (OBJECT_DATE, "Date"),
        (CULTURE, "Culture"),
        (DEPARTMENT, "Department"),
        (CLASSIFICATION, "Classification"),
    )


@dataclass
class ResponseFields:
    OBJECT_IDS = "objectIDs"
    TOTAL = "total"


@dataclass
class SearchKeywords:
    ARTIST_OR_CULTURE = "artistOrCulture"
    DEPARTMENT_ID = "departmentID"
    GEO_LOCATION = "geoLocation"
    HAS_IMAGES = "hasImages"
    MEDIUM = "medium"
    Q = "q"
    TITLE = "title"