from dataclasses import dataclass


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


@dataclass
class DisplayFields:
    TITLE = "Title"
    ARTIST = "Artist"
    MEDIUM = "Medium"
    DATE = "Date"
    CULTURE = "Culture"
    DEPARTMENT = "Department"
    CLASSIFICATION = "Classification"

    FIELDS = (
        TITLE,
        ARTIST,
        MEDIUM,
        DATE,
        CULTURE,
        DEPARTMENT,
        CLASSIFICATION,
    )

    FIELDS_TO_OBJECT_FIELDS = {
        TITLE: ObjectFields.TITLE,
        ARTIST: ObjectFields.ARTIST_DISPLAY_NAME,
        MEDIUM: ObjectFields.MEDIUM,
        DATE: ObjectFields.OBJECT_DATE,
        CULTURE: ObjectFields.CULTURE,
        DEPARTMENT: ObjectFields.DEPARTMENT,
        CLASSIFICATION: ObjectFields.CLASSIFICATION,
    }

    OBJECT_FIELDS_TO_FIELDS = {
        ObjectFields.TITLE: TITLE,
        ObjectFields.ARTIST_DISPLAY_NAME: ARTIST,
        ObjectFields.MEDIUM: MEDIUM,
        ObjectFields.OBJECT_DATE: DATE,
        ObjectFields.CULTURE: CULTURE,
        ObjectFields.DEPARTMENT: DEPARTMENT,
        ObjectFields.CLASSIFICATION: CLASSIFICATION,
    }


@dataclass
class Requests:
    SECONDS = 60
    INTERVAL = 1000
    MAX_RESULTS = 80


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