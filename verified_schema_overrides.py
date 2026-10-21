from __future__ import annotations

from copy import deepcopy
from datetime import date

from route_registry import DISCONTINUED_BY_ROUTE, SUPPRESSED_BY_ROUTE, normalize_operator

TTLINE_STANDARD_NOTE = (
    "Officiell TT-Line standardtidtabell 2026. "
    "Standardtidtabellen är en avgångsrekommendation; aktuell bindande tidtabell finns hos TT-Line Freight."
)

STENA_NYVE_NOTE = (
    "Verifierat 2026-05-30 mot Stena Line Freight LiveView route NYVE "
    "(Nynäshamn–Ventspils). Tiderna följer officiell per-dag-tidtabell från Stena."
)

FINNLINES_SWIMMA_NOTE = (
    "Verifierat 2026-05-20 mot Finnlines officiella ruttsida för Malmö–Świnoujście. "
    "Veckoschemat används som primärkälla eftersom Finnlines GraphQL-källan inte returnerar denna rutt."
)

POLSCA_TRELLEBORG_NOTE = (
    "Verifierat 2026-05-31 mot POL-AGENTs officiella POLSCA-tabell "
    "för Świnoujście–Trelleborg, giltig 2026-05-04 till 2026-06-20. "
    "Rader med Epsilon/Jantar följer tabellens jämn/udda vecka-markering."
)

POLSCA_GDANSK_KARLSHAMN_NOTE = (
    "Verifierat 2026-07-16 mot Polferries officiella tidtabell för Gdańsk–Karlshamn "
    "med publicerade avgångsdatum i juli/augusti 2026. Unity Line/POLSCA anger samma "
    "linje som giltig 2026-07-06 till 2026-08-16."
)

SUNDBUSSERNE_NOTE = (
    "Verifierat 2026-10-21 mot Sundbussernes officiella sejlplan-bild "
    "gällande från 2026-03-20. Restiden anges till cirka 18 minuter."
)

TTLINE_ROUTE_SOURCES = {
    ("Trelleborg", "Travemünde"): "https://www.ttline.com/globalassets/freight/images/pdf-timetable/standard-timetable-2026_tra.pdf",
    ("Travemünde", "Trelleborg"): "https://www.ttline.com/globalassets/freight/images/pdf-timetable/standard-timetable-2026_tra.pdf",
    ("Trelleborg", "Świnoujście"): "https://www.ttline.com/globalassets/freight/images/pdf-timetable/standard-timetable-2026_swi.pdf",
    ("Świnoujście", "Trelleborg"): "https://www.ttline.com/globalassets/freight/images/pdf-timetable/standard-timetable-2026_swi.pdf",
    ("Travemünde", "Karlshamn"): "https://www.ttline.com/globalassets/freight/images/pdf-timetable/standard-timetable-2026-karcon.pdf",
    ("Karlshamn", "Travemünde"): "https://www.ttline.com/globalassets/freight/images/pdf-timetable/standard-timetable-2026-karcon.pdf",
    ("Rostock", "Karlshamn"): "https://www.ttline.com/globalassets/freight/images/pdf-timetable/standard-timetable-2026-karcon.pdf",
}

TTLINE_ROUTE_VALIDITY = {
    ("Travemünde", "Karlshamn"): ("2026-01-01", "2026-12-31"),
    ("Karlshamn", "Travemünde"): ("2026-01-01", "2026-12-31"),
    ("Rostock", "Karlshamn"): ("2026-01-01", "2026-12-31"),
}

TTLINE_ROUTE_FLEETS = {
    ("Travemünde", "Trelleborg"): "Nils Holgersson / Nils Dacke / Peter Pan / Tom Sawyer / Tinker Bell / Huckleberry Finn / Robin Hood / Marco Polo",
    ("Trelleborg", "Travemünde"): "Nils Holgersson / Nils Dacke / Peter Pan / Tom Sawyer / Tinker Bell / Huckleberry Finn / Robin Hood / Marco Polo",
    ("Rostock", "Trelleborg"): "Huckleberry Finn / Peter Pan / Tom Sawyer / Tinker Bell / Nils Holgersson / Robin Hood / Nils Dacke / Marco Polo",
    ("Trelleborg", "Rostock"): "Huckleberry Finn / Peter Pan / Tom Sawyer / Tinker Bell / Nils Holgersson / Robin Hood / Nils Dacke / Marco Polo",
    ("Świnoujście", "Trelleborg"): "Tinker Bell / Tom Sawyer / Peter Pan / Huckleberry Finn / Robin Hood / Nils Dacke / Nils Holgersson",
    ("Trelleborg", "Świnoujście"): "Tinker Bell / Tom Sawyer / Peter Pan / Huckleberry Finn / Robin Hood / Nils Dacke / Nils Holgersson",
    ("Travemünde", "Karlshamn"): "Nils Dacke / Nils Holgersson / Robin Hood",
    ("Karlshamn", "Travemünde"): "Nils Dacke / Nils Holgersson / Robin Hood",
    ("Rostock", "Karlshamn"): "Nils Dacke / Nils Holgersson / Robin Hood",
}

TTLINE_ROUTE_TIMETABLES = {
    ("Trelleborg", "Travemünde"): {
        "Mån": [("16:00", "00:45+1"), ("22:00", "07:30+1")],
        "Tis": [("09:30", "20:15"), ("16:00", "00:45+1"), ("22:00", "07:00+1")],
        "Ons": [("06:30", "14:15"), ("09:30", "20:15"), ("13:00", "22:30"), ("16:00", "00:45+1"), ("22:00", "07:00+1")],
        "Tor": [("09:30", "20:15"), ("16:00", "01:00+1"), ("22:30", "07:15+1")],
        "Fre": [("09:30", "20:15"), ("16:00", "00:45+1"), ("22:00", "07:45+1")],
        "Lör": [("10:00", "20:00"), ("22:00", "08:15+1")],
        "Sön": [("16:00", "01:00+1"), ("23:15", "08:15+1")],
    },
    ("Travemünde", "Trelleborg"): {
        "Mån": [("03:00", "11:45"), ("10:30", "21:30"), ("22:00", "07:00+1")],
        "Tis": [("02:30", "11:15"), ("09:30", "19:30"), ("22:00", "07:00+1")],
        "Ons": [("02:30", "11:15"), ("09:30", "19:30"), ("15:30", "23:00"), ("22:00", "07:00+1")],
        "Tor": [("01:00", "14:40"), ("02:30", "11:15"), ("09:30", "19:30"), ("15:15", "22:45"), ("22:00", "07:00+1")],
        "Fre": [("03:00", "11:45"), ("09:30", "19:30"), ("22:30", "07:45+1")],
        "Lör": [("02:30", "11:15"), ("10:00", "20:00"), ("22:00", "09:15+1")],
        "Sön": [("01:00", "09:15"), ("21:30", "06:15+1")],
    },
    ("Trelleborg", "Świnoujście"): {
        "Mån": [("07:45", "14:00"), ("23:55", "07:00+1")],
        "Tis": [("07:00", "13:30"), ("16:30", "23:55")],
        "Ons": [("10:00", "16:00")],
        "Tor": [("02:30", "09:30"), ("22:00", "05:00+1")],
        "Fre": [("07:30", "14:00"), ("16:30", "23:10")],
        "Lör": [("09:00", "16:30")],
        "Sön": [("08:30", "14:30"), ("15:00", "23:15")],
    },
    ("Świnoujście", "Trelleborg"): {
        "Mån": [("01:00", "08:30"), ("16:00", "23:00")],
        "Tis": [("08:30", "15:00"), ("15:30", "22:30")],
        "Ons": [("02:00", "09:00"), ("18:05", "01:05+1")],
        "Tor": [("14:30", "20:30")],
        "Fre": [("06:30", "14:00"), ("15:00", "22:15")],
        "Lör": [("00:30", "07:45")],
        "Sön": [("00:30", "07:30"), ("16:00", "22:00")],
    },
    ("Travemünde", "Karlshamn"): {
        "Fre": [("22:20", "17:30+1")],
    },
    ("Karlshamn", "Travemünde"): {
        "Mån": [("07:30", "20:15")],
    },
    ("Rostock", "Karlshamn"): {
        "Fre": [("23:45", "17:30+1")],
    },
}

STENA_ROUTE_SOURCES = {
    ("Nynäshamn", "Ventspils"): "https://stenalinefreight.com/timetable/NYVE/",
    ("Ventspils", "Nynäshamn"): "https://stenalinefreight.com/timetable/NYVE/",
}

STENA_ROUTE_TIMETABLES = {
    ("Nynäshamn", "Ventspils"): {
        "Mån": [("21:15", "07:45+1")],
        "Tis": [("21:15", "07:45+1")],
        "Ons": [("21:15", "07:45+1")],
        "Tor": [("21:15", "07:45+1")],
        "Fre": [("21:15", "07:45+1")],
        "Lör": [("21:15", "07:45+1")],
        "Sön": [("21:15", "07:45+1")],
    },
    ("Ventspils", "Nynäshamn"): {
        "Mån": [("23:00", "07:30+1")],
        "Tis": [("23:00", "07:30+1")],
        "Ons": [("23:00", "07:30+1")],
        "Tor": [("22:45", "07:45+1")],
        "Fre": [("22:45", "07:45+1")],
        "Lör": [("22:45", "07:45+1")],
        "Sön": [("22:30", "07:30+1")],
    },
}

FINNLINES_ROUTE_SOURCES = {
    ("Malmö", "Świnoujście"): "https://www.finnlines.com/sv/rutter/malmo-swinoujscie/",
    ("Świnoujście", "Malmö"): "https://www.finnlines.com/sv/rutter/malmo-swinoujscie/",
    ("Malmö", "Travemünde"): "https://www.finnlines.com/sv/rutter/malmo-travemunde/",
    ("Travemünde", "Malmö"): "https://www.finnlines.com/sv/rutter/malmo-travemunde/",
    ("Kapellskär", "Naantali"): "https://www.finnlines.com/sv/rutter/kapellskar-langnas-nadendal/",
    ("Naantali", "Kapellskär"): "https://www.finnlines.com/sv/rutter/kapellskar-langnas-nadendal/",
}

FINNLINES_ROUTE_TIMETABLES = {
    ("Malmö", "Travemünde"): {
        "Mån": [("16:00", "00:45+1"), ("22:00", "07:00+1")],
        "Tis": [("10:00", "19:15"), ("16:00", "00:45+1"), ("22:00", "07:00+1")],
        "Ons": [("10:00", "19:15"), ("16:00", "00:45+1"), ("22:00", "07:15+1")],
        "Tor": [("10:00", "19:15"), ("16:00", "00:45+1"), ("22:00", "07:15+1")],
        "Fre": [("10:00", "21:00"), ("16:00", "00:45+1"), ("22:00", "07:00+1")],
        "Lör": [("10:00", "19:15"), ("13:30", "23:00"), ("22:30", "08:30+1")],
        "Sön": [("16:00", "01:15+1"), ("22:00", "07:15+1")],
    },
    ("Travemünde", "Malmö"): {
        "Mån": [("03:00", "11:45"), ("22:00", "07:15+1")],
        "Tis": [("03:00", "11:45"), ("10:00", "19:15"), ("21:45", "07:15+1")],
        "Ons": [("03:00", "11:45"), ("10:00", "19:15"), ("21:45", "07:15+1")],
        "Tor": [("03:00", "11:45"), ("10:00", "19:15"), ("22:00", "07:15+1")],
        "Fre": [("03:00", "11:45"), ("10:00", "19:15"), ("22:00", "07:15+1")],
        "Lör": [("03:00", "12:00"), ("11:00", "20:00"), ("22:00", "07:30+1")],
        "Sön": [("01:00", "10:30"), ("22:00", "07:30+1")],
    },
    ("Kapellskär", "Naantali"): {
        day: [("10:30" if day in {"Mån", "Tis"} else "10:45", "19:55" if day in {"Mån", "Tis"} else "20:10"),
              ("21:45", "07:15+1")]
        for day in ("Mån", "Tis", "Ons", "Tor", "Fre", "Lör", "Sön")
    },
    ("Naantali", "Kapellskär"): {
        day: [("10:45" if day in {"Mån", "Tis"} else "10:00", "18:30" if day in {"Mån", "Tis"} else "17:45"),
              ("22:45", "06:30+1" if day in {"Fre", "Lör"} else "06:15+1")]
        for day in ("Mån", "Tis", "Ons", "Tor", "Fre", "Lör", "Sön")
    },
    ("Malmö", "Świnoujście"): {
        "Mån": [("10:15", "19:15")],
        "Tis": [("11:00", "19:15")],
        "Ons": [("11:00", "19:15")],
        "Tor": [("11:00", "19:15")],
        "Fre": [("11:00", "19:15")],
        "Lör": [("11:00", "19:15")],
        "Sön": [("10:15", "19:15")],
    },
    ("Świnoujście", "Malmö"): {
        "Mån": [("21:30", "06:45+1")],
        "Tis": [("21:30", "06:45+1")],
        "Ons": [("21:30", "06:45+1")],
        "Tor": [("21:30", "06:45+1")],
        "Fre": [("21:30", "06:45+1")],
        "Lör": [("21:30", "06:45+1")],
        "Sön": [("21:30", "06:45+1")],
    },
}

POLSCA_TRELLEBORG_SOURCE = "https://polagent.com/en/sailing-schedule/"
POLSCA_TRELLEBORG_VALID_FROM = "2026-05-04"
POLSCA_TRELLEBORG_VALID_TO = "2026-06-20"
POLSCA_GDANSK_KARLSHAMN_SOURCE = "https://polferries.com/prices-i-timetable/ferries-to-sweden-timetable.html?code=gh"
SUNDBUSSERNE_SOURCE = "https://sundbusserne.dk/fartplan/"

POLSCA_TRELLEBORG_ROWS = [
    ("Mån", "Copernicus", None, "02:00", "09:00", "15:00", "22:15"),
    ("Mån", "Epsilon", "even", "10:00", "17:00", "", ""),
    ("Mån", "Jantar Unity", "odd", "10:00", "17:00", "", ""),
    ("Mån", "Jantar Unity", "even", "20:30", "03:00+1", "10:15", "16:30"),
    ("Mån", "Epsilon", "odd", "20:30", "03:00+1", "10:15", "16:30"),
    ("Tis", "Epsilon", "even", "", "", "01:30", "09:45"),
    ("Tis", "Jantar Unity", "odd", "", "", "01:30", "09:45"),
    ("Tis", "Copernicus", None, "02:00", "09:00", "15:00", "22:15"),
    ("Tis", "Epsilon", "even", "14:00", "21:00", "10:15", "16:30"),
    ("Tis", "Jantar Unity", "odd", "14:00", "21:00", "10:15", "16:30"),
    ("Tis", "Jantar Unity", "even", "20:30", "03:00+1", "24:00", "07:00+1"),
    ("Tis", "Epsilon", "odd", "20:30", "03:00+1", "24:00", "07:00+1"),
    ("Ons", "Copernicus", None, "02:00", "09:00", "15:00", "22:15"),
    ("Ons", "Epsilon", "even", "10:30", "17:30", "22:30", "07:00+1"),
    ("Ons", "Jantar Unity", "odd", "10:30", "17:30", "22:30", "07:00+1"),
    ("Ons", "Jantar Unity", "even", "20:30", "03:00+1", "10:15", "16:30"),
    ("Ons", "Jantar Unity", "odd", "20:30", "03:00+1", "10:15", "16:30"),
    ("Tor", "Copernicus", None, "02:00", "09:00", "15:00", "22:15"),
    ("Tor", "Epsilon", "even", "09:00", "16:00", "23:55", "07:15+1"),
    ("Tor", "Jantar Unity", "odd", "09:00", "16:00", "23:55", "07:15+1"),
    ("Tor", "Jantar Unity", "even", "20:30", "03:00+1", "10:00", "16:30"),
    ("Tor", "Epsilon", "odd", "20:30", "03:00+1", "10:00", "16:30"),
    ("Fre", "Copernicus", None, "02:00", "09:00", "13:30", "21:15"),
    ("Fre", "Epsilon", "even", "09:00", "15:30", "22:45", "05:15+1"),
    ("Fre", "Jantar Unity", "odd", "09:00", "15:30", "22:45", "05:15+1"),
    ("Fre", "Jantar Unity", "even", "13:30", "21:15", "17:55", "01:00+1"),
    ("Fre", "Epsilon", "odd", "13:30", "21:15", "17:55", "01:00+1"),
    ("Lör", "Copernicus", None, "02:00", "09:30", "12:45", "20:15"),
    ("Sön", "Jantar Unity", "even", "10:00", "17:00", "22:30", "05:30+1"),
    ("Sön", "Epsilon", "odd", "10:00", "17:00", "22:30", "05:30+1"),
    ("Sön", "Epsilon", "even", "20:30", "03:00+1", "", ""),
    ("Sön", "Jantar Unity", "odd", "20:30", "03:00+1", "", ""),
]

POLSCA_GDANSK_KARLSHAMN_ROWS = [
    ("2026-07-06", "Gdańsk", "Karlshamn", "21:00", "11:30+1", "Copernicus"),
    ("2026-07-08", "Gdańsk", "Karlshamn", "21:00", "11:30+1", "Skania"),
    ("2026-07-08", "Karlshamn", "Gdańsk", "18:00", "08:00+1", "Copernicus"),
    ("2026-07-09", "Karlshamn", "Gdańsk", "17:00", "08:00+1", "Skania"),
    ("2026-07-10", "Gdańsk", "Karlshamn", "07:30", "20:00", "Copernicus"),
    ("2026-07-10", "Gdańsk", "Karlshamn", "21:00", "11:30+1", "Skania"),
    ("2026-07-10", "Karlshamn", "Gdańsk", "22:00", "10:30+1", "Copernicus"),
    ("2026-07-12", "Gdańsk", "Karlshamn", "21:00", "10:30+1", "Copernicus"),
    ("2026-07-12", "Karlshamn", "Gdańsk", "17:30", "08:00+1", "Skania"),
    ("2026-07-13", "Gdańsk", "Karlshamn", "21:00", "11:30+1", "Skania"),
    ("2026-07-13", "Karlshamn", "Gdańsk", "18:00", "08:00+1", "Copernicus"),
    ("2026-07-14", "Gdańsk", "Karlshamn", "21:00", "10:30+1", "Copernicus"),
    ("2026-07-14", "Karlshamn", "Gdańsk", "17:00", "08:00+1", "Skania"),
    ("2026-07-15", "Gdańsk", "Karlshamn", "21:00", "11:30+1", "Skania"),
    ("2026-07-15", "Karlshamn", "Gdańsk", "18:00", "08:00+1", "Copernicus"),
    ("2026-07-16", "Karlshamn", "Gdańsk", "17:00", "08:00+1", "Skania"),
    ("2026-07-17", "Gdańsk", "Karlshamn", "07:30", "20:00", "Copernicus"),
    ("2026-07-17", "Gdańsk", "Karlshamn", "21:00", "11:30+1", "Skania"),
    ("2026-07-17", "Karlshamn", "Gdańsk", "22:00", "10:30+1", "Copernicus"),
    ("2026-07-19", "Gdańsk", "Karlshamn", "21:00", "10:30+1", "Copernicus"),
    ("2026-07-19", "Karlshamn", "Gdańsk", "17:30", "08:00+1", "Skania"),
    ("2026-07-20", "Gdańsk", "Karlshamn", "21:00", "11:30+1", "Skania"),
    ("2026-07-20", "Karlshamn", "Gdańsk", "18:00", "08:00+1", "Copernicus"),
    ("2026-07-21", "Gdańsk", "Karlshamn", "21:00", "10:30+1", "Copernicus"),
    ("2026-07-21", "Karlshamn", "Gdańsk", "17:00", "08:00+1", "Skania"),
    ("2026-07-22", "Gdańsk", "Karlshamn", "21:00", "11:30+1", "Skania"),
    ("2026-07-22", "Karlshamn", "Gdańsk", "18:00", "08:00+1", "Copernicus"),
    ("2026-07-23", "Karlshamn", "Gdańsk", "17:00", "08:00+1", "Skania"),
    ("2026-07-24", "Gdańsk", "Karlshamn", "07:30", "20:00", "Copernicus"),
    ("2026-07-24", "Gdańsk", "Karlshamn", "21:00", "11:30+1", "Skania"),
    ("2026-07-24", "Karlshamn", "Gdańsk", "22:00", "10:30+1", "Copernicus"),
    ("2026-07-26", "Gdańsk", "Karlshamn", "21:00", "10:30+1", "Copernicus"),
    ("2026-07-26", "Karlshamn", "Gdańsk", "17:30", "08:00+1", "Skania"),
    ("2026-07-27", "Gdańsk", "Karlshamn", "21:00", "11:30+1", "Skania"),
    ("2026-07-27", "Karlshamn", "Gdańsk", "18:00", "08:00+1", "Copernicus"),
    ("2026-07-28", "Gdańsk", "Karlshamn", "21:00", "10:30+1", "Copernicus"),
    ("2026-07-28", "Karlshamn", "Gdańsk", "17:00", "08:00+1", "Skania"),
    ("2026-07-29", "Gdańsk", "Karlshamn", "21:00", "11:30+1", "Skania"),
    ("2026-07-29", "Karlshamn", "Gdańsk", "18:00", "08:00+1", "Copernicus"),
    ("2026-07-30", "Karlshamn", "Gdańsk", "17:00", "08:00+1", "Skania"),
    ("2026-07-31", "Gdańsk", "Karlshamn", "07:30", "20:00", "Copernicus"),
    ("2026-07-31", "Gdańsk", "Karlshamn", "21:00", "11:30+1", "Skania"),
    ("2026-07-31", "Karlshamn", "Gdańsk", "22:00", "10:30+1", "Copernicus"),
    ("2026-08-02", "Gdańsk", "Karlshamn", "21:00", "10:30+1", "Copernicus"),
    ("2026-08-02", "Karlshamn", "Gdańsk", "17:30", "08:00+1", "Skania"),
    ("2026-08-03", "Gdańsk", "Karlshamn", "21:00", "11:30+1", "Skania"),
    ("2026-08-03", "Karlshamn", "Gdańsk", "18:00", "08:00+1", "Copernicus"),
    ("2026-08-04", "Gdańsk", "Karlshamn", "21:00", "10:30+1", "Copernicus"),
    ("2026-08-04", "Karlshamn", "Gdańsk", "17:00", "08:00+1", "Skania"),
    ("2026-08-05", "Gdańsk", "Karlshamn", "21:00", "11:30+1", "Skania"),
    ("2026-08-05", "Karlshamn", "Gdańsk", "18:00", "08:00+1", "Copernicus"),
    ("2026-08-06", "Karlshamn", "Gdańsk", "17:00", "08:00+1", "Skania"),
    ("2026-08-07", "Gdańsk", "Karlshamn", "07:30", "20:00", "Copernicus"),
    ("2026-08-07", "Gdańsk", "Karlshamn", "21:00", "11:30+1", "Skania"),
    ("2026-08-07", "Karlshamn", "Gdańsk", "22:00", "10:30+1", "Copernicus"),
    ("2026-08-09", "Gdańsk", "Karlshamn", "21:00", "10:30+1", "Copernicus"),
    ("2026-08-09", "Karlshamn", "Gdańsk", "17:30", "08:00+1", "Skania"),
    ("2026-08-10", "Gdańsk", "Karlshamn", "21:00", "11:30+1", "Skania"),
    ("2026-08-10", "Karlshamn", "Gdańsk", "18:00", "08:00+1", "Copernicus"),
    ("2026-08-11", "Gdańsk", "Karlshamn", "21:00", "10:30+1", "Copernicus"),
    ("2026-08-11", "Karlshamn", "Gdańsk", "17:00", "08:00+1", "Skania"),
    ("2026-08-12", "Gdańsk", "Karlshamn", "21:00", "11:30+1", "Skania"),
    ("2026-08-12", "Karlshamn", "Gdańsk", "18:00", "08:00+1", "Copernicus"),
    ("2026-08-13", "Karlshamn", "Gdańsk", "17:00", "08:00+1", "Skania"),
    ("2026-08-14", "Gdańsk", "Karlshamn", "07:30", "20:00", "Copernicus"),
    ("2026-08-14", "Gdańsk", "Karlshamn", "21:00", "11:30+1", "Skania"),
    ("2026-08-14", "Karlshamn", "Gdańsk", "22:00", "10:30+1", "Copernicus"),
    ("2026-08-16", "Gdańsk", "Karlshamn", "21:00", "10:30+1", "Copernicus"),
    ("2026-08-16", "Karlshamn", "Gdańsk", "17:30", "08:00+1", "Skania"),
]


def override_route_keys() -> set[tuple[str, str, str]]:
    route_keys = {("TT-Line", avghamn, ankhamn) for avghamn, ankhamn in TTLINE_ROUTE_TIMETABLES}
    route_keys.update({("Stena Line", avghamn, ankhamn) for avghamn, ankhamn in STENA_ROUTE_TIMETABLES})
    route_keys.update({("Finnlines", avghamn, ankhamn) for avghamn, ankhamn in FINNLINES_ROUTE_TIMETABLES})
    route_keys.update({
        ("Wasaline", "Umeå", "Vasa"), ("Wasaline", "Vasa", "Umeå"),
        ("Eckerö Linjen", "Grisslehamn", "Eckerö"), ("Eckerö Linjen", "Eckerö", "Grisslehamn"),
        ("Sundbusserne", "Helsingborg", "Helsingør"),
        ("Sundbusserne", "Helsingør", "Helsingborg"),
    })
    route_keys.update({
        ("Polferries (POLSCA)", "Świnoujście", "Trelleborg"),
        ("Polferries (POLSCA)", "Trelleborg", "Świnoujście"),
        ("Polferries (POLSCA)", "Gdańsk", "Karlshamn"),
        ("Polferries (POLSCA)", "Karlshamn", "Gdańsk"),
    })
    return route_keys


def _add_minutes(time_text: str, minutes: int) -> str:
    hour, minute = [int(part) for part in time_text.split(":", 1)]
    total = hour * 60 + minute + minutes
    return f"{(total // 60) % 24:02d}:{total % 60:02d}"


def _half_hour_times(start: str, end: str) -> list[str]:
    current_h, current_m = [int(part) for part in start.split(":", 1)]
    end_h, end_m = [int(part) for part in end.split(":", 1)]
    current = current_h * 60 + current_m
    end_minutes = end_h * 60 + end_m
    values: list[str] = []
    while current <= end_minutes:
        values.append(f"{current // 60:02d}:{current % 60:02d}")
        current += 30
    return values


def _make_row(
    rederi: str,
    avghamn: str,
    ankhamn: str,
    veckodag: str,
    avgtid: str,
    anktid: str,
    source_url: str,
    note: str,
    *,
    fartyg: str = "",
    giltig_from: str = "",
    giltig_to: str = "",
    iso_week_parity: str = "",
    source_detail: str = "",
) -> dict:
    row = {
        "id": 0,
        "kategori": "Passagerare",
        "rederi": rederi,
        "rutt": f"{avghamn}–{ankhamn}",
        "avghamn": avghamn,
        "ankhamn": ankhamn,
        "veckodag": veckodag,
        "avgtid": avgtid,
        "avgtid_raw": avgtid,
        "anktid": anktid,
        "nasta_dag": "+1" in anktid,
        "mot_sverige": ankhamn in {"Trelleborg", "Karlshamn", "Göteborg", "Malmö", "Ystad", "Nynäshamn", "Kapellskär", "Karlskrona", "Stockholm", "Umeå", "Grisslehamn"},
        "fran_sverige": avghamn in {"Trelleborg", "Karlshamn", "Göteborg", "Malmö", "Ystad", "Nynäshamn", "Kapellskär", "Karlskrona", "Stockholm", "Umeå", "Grisslehamn"},
        "anmarkning": note,
        "verifiering": "Verifierad",
        "kalla": source_url,
    }
    if fartyg:
        row["fartyg"] = fartyg
    if giltig_from:
        row["giltig_from"] = giltig_from
    if giltig_to:
        row["giltig_to"] = giltig_to
    if iso_week_parity:
        row["iso_week_parity"] = iso_week_parity
    if source_detail:
        row["source_detail"] = source_detail
    return row


def _build_ttline_rows() -> list[dict]:
    rows: list[dict] = []
    for (avghamn, ankhamn), weekday_map in TTLINE_ROUTE_TIMETABLES.items():
        source_url = TTLINE_ROUTE_SOURCES[(avghamn, ankhamn)]
        validity = TTLINE_ROUTE_VALIDITY.get((avghamn, ankhamn), ("", ""))
        source_detail = "TT-Line Standard Timetable 2026 Karlshamn Routes" if validity[0] else ""
        fleet = TTLINE_ROUTE_FLEETS.get((avghamn, ankhamn), "")
        for veckodag, sailings in weekday_map.items():
            for avgtid, anktid in sailings:
                rows.append(_make_row(
                    "TT-Line",
                    avghamn,
                    ankhamn,
                    veckodag,
                    avgtid,
                    anktid,
                    source_url,
                    TTLINE_STANDARD_NOTE,
                    fartyg=fleet,
                    giltig_from=validity[0],
                    giltig_to=validity[1],
                    source_detail=source_detail,
                ))
    return rows


def _build_stena_rows() -> list[dict]:
    rows: list[dict] = []
    for (avghamn, ankhamn), weekday_map in STENA_ROUTE_TIMETABLES.items():
        source_url = STENA_ROUTE_SOURCES[(avghamn, ankhamn)]
        for veckodag, sailings in weekday_map.items():
            for avgtid, anktid in sailings:
                rows.append(_make_row("Stena Line", avghamn, ankhamn, veckodag, avgtid, anktid, source_url, STENA_NYVE_NOTE))
    return rows


def _build_finnlines_rows() -> list[dict]:
    rows: list[dict] = []
    for (avghamn, ankhamn), weekday_map in FINNLINES_ROUTE_TIMETABLES.items():
        source_url = FINNLINES_ROUTE_SOURCES[(avghamn, ankhamn)]
        for veckodag, sailings in weekday_map.items():
            for avgtid, anktid in sailings:
                rows.append(_make_row("Finnlines", avghamn, ankhamn, veckodag, avgtid, anktid, source_url,
                    "Officiell ruttsidas veckotidtabell kontrollerad 2026-10-21. Alla tider lokala. Helgavvikelser kan förekomma; kontrollera rederiets bokning."))
    return rows


def _build_polsca_trelleborg_rows() -> list[dict]:
    rows: list[dict] = []
    for veckodag, fartyg, parity, swi_dep, tre_arr, tre_dep, swi_arr in POLSCA_TRELLEBORG_ROWS:
        common = {
            "fartyg": fartyg,
            "giltig_from": POLSCA_TRELLEBORG_VALID_FROM,
            "giltig_to": POLSCA_TRELLEBORG_VALID_TO,
            "iso_week_parity": parity or "",
            "source_detail": "POL-AGENT POLSCA sailing schedule",
        }
        if swi_dep and tre_arr:
            rows.append(_make_row(
                "Polferries (POLSCA)",
                "Świnoujście",
                "Trelleborg",
                veckodag,
                swi_dep,
                tre_arr,
                POLSCA_TRELLEBORG_SOURCE,
                POLSCA_TRELLEBORG_NOTE,
                **common,
            ))
        if tre_dep and swi_arr:
            rows.append(_make_row(
                "Polferries (POLSCA)",
                "Trelleborg",
                "Świnoujście",
                veckodag,
                tre_dep,
                swi_arr,
                POLSCA_TRELLEBORG_SOURCE,
                POLSCA_TRELLEBORG_NOTE,
                **common,
            ))
    return rows


def _build_polsca_gdansk_karlshamn_rows() -> list[dict]:
    rows: list[dict] = []
    for dep_date, avghamn, ankhamn, avgtid, anktid, fartyg in POLSCA_GDANSK_KARLSHAMN_ROWS:
        weekday = ["Mån", "Tis", "Ons", "Tor", "Fre", "Lör", "Sön"][date.fromisoformat(dep_date).weekday()]
        rows.append(_make_row(
            "Polferries (POLSCA)",
            avghamn,
            ankhamn,
            weekday,
            avgtid,
            anktid,
            POLSCA_GDANSK_KARLSHAMN_SOURCE,
            POLSCA_GDANSK_KARLSHAMN_NOTE,
            fartyg=fartyg,
            giltig_from=dep_date,
            giltig_to=dep_date,
            source_detail="Polferries Gdańsk-Karlshamn timetable",
        ))
    return rows


def _build_sundbusserne_rows() -> list[dict]:
    rows: list[dict] = []
    weekday_times = {
        "Mån": _half_hour_times("10:00", "18:30"),
        "Tis": _half_hour_times("10:00", "18:30"),
        "Ons": _half_hour_times("10:00", "18:30"),
        "Tor": _half_hour_times("10:00", "18:30"),
        "Fre": _half_hour_times("10:00", "20:30"),
        "Lör": _half_hour_times("10:00", "20:30"),
        "Sön": _half_hour_times("10:00", "17:30"),
    }
    for avghamn, ankhamn, first_vessel in [
        ("Helsingborg", "Helsingør", "Pernille"),
        ("Helsingør", "Helsingborg", "Jeppe"),
    ]:
        for veckodag, times in weekday_times.items():
            for idx, avgtid in enumerate(times):
                if first_vessel == "Pernille":
                    vessel = "Pernille" if idx % 2 == 0 else "Jeppe"
                else:
                    vessel = "Jeppe" if idx % 2 == 0 else "Pernille"
                rows.append(_make_row(
                    "Sundbusserne",
                    avghamn,
                    ankhamn,
                    veckodag,
                    avgtid,
                    _add_minutes(avgtid, 18),
                    SUNDBUSSERNE_SOURCE,
                    SUNDBUSSERNE_NOTE,
                    fartyg=vessel,
                    source_detail="Sundbusserne sejlplan 2026-03-20",
                ))
    return rows


def _build_wasaline_rows() -> list[dict]:
    """Officiella säsongsperioder kontrollerade 2026-10-21 (uppdaterade 13/10)."""
    source = "https://www.wasaline.com/en/timetable/"
    weekdays = ["Mån", "Tis", "Ons", "Tor", "Fre", "Lör", "Sön"]
    # (weekday indices, departure port, departure, arrival). All times local.
    base = [
        ([0], "Umeå", "11:30", "17:00"), ([0], "Vasa", "20:00", "23:15"),
        ([1], "Umeå", "08:00", "13:00"), ([1], "Vasa", "14:00", "17:15"),
        ([1], "Umeå", "18:15", "23:00"), ([1], "Vasa", "23:45", "06:00+1"),
        ([2], "Umeå", "08:00", "13:00"), ([2], "Vasa", "14:30", "17:30"),
        ([2], "Umeå", "19:00", "00:00+1"),
        ([6], "Vasa", "08:00", "11:15"), ([6], "Umeå", "13:00", "18:15"),
        ([6], "Vasa", "20:00", "23:00"),
    ]
    def late_week(days):
        return [(days, "Vasa", "08:00", "10:30"), (days, "Umeå", "11:15", "16:00"),
                (days, "Vasa", "16:45", "19:15"), (days, "Umeå", "20:15", "01:00+1")]
    saturday = [([5], "Vasa", "09:00", "12:00"), ([5], "Umeå", "17:00", "22:00")]
    january = base + [
        ([3], "Vasa", "08:00", "10:45"), ([3], "Umeå", "11:15", "16:30"),
        ([3], "Vasa", "17:00", "20:00"), ([3], "Umeå", "20:45", "02:00+1"),
        ([4], "Vasa", "16:00", "18:45"), ([4], "Umeå", "19:30", "00:30+1"),
        ([5], "Vasa", "09:00", "12:15"), ([5], "Umeå", "17:00", "22:15"),
    ]
    periods = [
        ("2026-09-01", "2026-11-08", base + late_week([3, 4]) + saturday),
        ("2026-11-09", "2026-12-18", base + late_week([3, 4, 5])),
        ("2026-12-19", "2026-12-23", [(list(range(7)), "Vasa", "09:00", "12:15"), (list(range(7)), "Umeå", "17:00", "22:15")]),
        ("2026-12-26", "2026-12-30", [(list(range(7)), "Vasa", "09:00", "12:15"), (list(range(7)), "Umeå", "17:00", "22:15")]),
        ("2026-12-31", "2026-12-31", [([3], "Vasa", "17:00", "20:00"), ([3], "Umeå", "20:30", "01:30+1")]),
        ("2027-01-01", "2027-01-01", [([4], "Vasa", "11:00", "14:15"), ([4], "Umeå", "15:00", "20:15")]),
        ("2027-01-02", "2027-03-25", january),
    ]
    rows = []
    for start, end, entries in periods:
        for days, departure, dep, arr in entries:
            for weekday in days:
                rows.append(_make_row("Wasaline", departure, "Vasa" if departure == "Umeå" else "Umeå",
                    weekdays[weekday], dep, arr, source,
                    "Officiell säsongstidtabell kontrollerad 2026-10-21. Alla tider är lokala; ingen trafik 24–25/12.",
                    fartyg="Aurora Botnia", giltig_from=start, giltig_to=end))
    return rows


def _build_eckero_rows() -> list[dict]:
    """Två timmars överfart och korrekt lokal ankomsttid (+1 timme i Finland)."""
    source = "https://www.eckerolinjen.se/en/timetable"
    full = [
        ("Grisslehamn", "Eckerö", "10:00", "13:00"),
        ("Grisslehamn", "Eckerö", "15:00", "18:00"),
        ("Grisslehamn", "Eckerö", "20:00", "23:00"),
        ("Eckerö", "Grisslehamn", "08:00", "09:00"),
        ("Eckerö", "Grisslehamn", "13:30", "14:30"),
        ("Eckerö", "Grisslehamn", "18:30", "19:30"),
    ]
    periods = [
        ("2026-09-01", "2026-12-23", full),
        ("2026-12-26", "2026-12-31", full),
        ("2027-01-01", "2027-01-01", [row for row in full if row[2] not in {"08:00", "10:00"}]),
        ("2027-01-02", "2027-01-06", full),
        ("2027-01-29", "2027-03-31", full),
    ]
    rows = []
    for start, end, entries in periods:
        for origin, destination, dep, arr in entries:
            for weekday in ["Mån", "Tis", "Ons", "Tor", "Fre", "Lör", "Sön"]:
                rows.append(_make_row("Eckerö Linjen", origin, destination, weekday, dep, arr, source,
                    "Officiell tidtabell kontrollerad 2026-10-21. Lokala tider. Ingen trafik 24–25/12 2026 eller 7–28/1 2027 (dockning).",
                    fartyg="Eckerö", giltig_from=start, giltig_to=end))
    return rows


def _is_removed_legacy_schema_row(row: dict) -> bool:
    rederi = normalize_operator(row.get("rederi"))
    avghamn = str(row.get("avghamn") or "").strip()
    ankhamn = str(row.get("ankhamn") or "").strip()
    avgtid = str(row.get("avgtid_raw") or row.get("avgtid") or "").strip()
    return (
        rederi == "Polferries (POLSCA)"
        and avghamn == "Świnoujście"
        and ankhamn == "Ystad"
        and avgtid == "22:55"
    )


def apply_verified_schema_overrides(schema: list[dict]) -> list[dict]:
    route_keys = override_route_keys()
    preserved = [
        deepcopy(row)
        for row in schema
        if not _is_removed_legacy_schema_row(row)
        and (row.get("rederi"), row.get("avghamn"), row.get("ankhamn")) not in route_keys
        and (normalize_operator(row.get("rederi")), row.get("avghamn"), row.get("ankhamn")) not in DISCONTINUED_BY_ROUTE
        and (normalize_operator(row.get("rederi")), row.get("avghamn"), row.get("ankhamn")) not in SUPPRESSED_BY_ROUTE
    ]
    merged = (
        preserved
        + _build_ttline_rows()
        + _build_stena_rows()
        + _build_finnlines_rows()
        + _build_polsca_trelleborg_rows()
        + _build_polsca_gdansk_karlshamn_rows()
        + _build_sundbusserne_rows()
        + _build_wasaline_rows()
        + _build_eckero_rows()
    )
    for idx, row in enumerate(merged, start=1):
        row["id"] = idx
        row["avgtid_raw"] = row.get("avgtid_raw") or row.get("avgtid") or ""
    return merged
