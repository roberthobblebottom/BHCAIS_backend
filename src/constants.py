print_headers = [
    "Continuous S/N no.",
    "UID",
    "Album no.",
    "Object Condition (QC1)",
    "Album Information (OLD)",
    "Album Information (New)",
    "Photograph Information",
    "Main Category",
    "Collector's Name",
    "Day",
    "Month",
    "Year",
    "Country",
    "Locality",
    "GPS Coordinates",
    "Taxonomy",
    "Common Name",
    "Fieldnotes",
    "Keywords",
    "Location in LKCNHM",
    "Catalogued by",
    "Date catalogued",
    "Access status",
    "Remarks",
    "Negative (Y/N)",
    "Batch no.",
    "Sign-Out Date",
    "Sign-In Date",
    "Date of QC",
    "Checked by",
    "Object Condition (QC2)",
]
print_headers = str([col.strip().lower() for col in print_headers])
oral_histories_headers = [
    "S/N",
    "Name of Interviewee",
    "Name of Interviewee (2)",
    "Recording Date (DD/MM/YYYY)",
    "Track Number",
    "Total Tracks",
    "Running Time",
    "File name",
    "Format (Original File)",
    "Access Conditions",
    "Access Remarks",
    "Transcription Status",
    "Editing Remarks",
    "Vetted for Access?",
    "Accession Status",
    "Languages",
    "Keywords",
    "Interview Location",
    "Interviewers",
    "Associated Materials",
    "Catalogued By",
    "Catalogue Date",
    "Comments",
]

oral_histories_headers = str([col.strip().lower() for col in oral_histories_headers])
negative_headers = [
    "S/N no.",
    "UID",
    "Ziplock bag no.",
    "Object Condition (QC1)",
    "Ziplock Bag Information",
    "Negative Information",
    "Main Category",
    "Collector's Name",
    "Day",
    "Month",
    "Year",
    "Country",
    "Locality",
    "GPS Coordinates",
    "Taxonomy",
    "Common Name",
    "Fieldnotes",
    "Keywords",
    "Location stored",
    "Catalogued by",
    "Date catalogued",
    "Access status",
    "Remarks",
    "Prints (Y/N)",
    "Batch no.",
    "Sign-Out Date",
    "Sign-In Date",
    "Date of QC",
    "Checked by",
    "Object Condition (QC2)",
]

negative_headers = str([col.strip().lower() for col in negative_headers])
slides_headers = [
    "S/N no.",
    "UID",
    "Box no.",
    "Object Condition (QC1)",
    "Box Information (OLD)",
    "Box Information (New)",
    "Divider 1",
    "Divider 2",
    "Divider 3",
    "Slides Information",
    "Main Category",
    "Collector's Name",
    "Day",
    "Month",
    "Year",
    "Country",
    "Locality",
    "GPS Coordinates",
    "Taxonomy",
    "Common Name",
    "Fieldnotes",
    "Keywords",
    "Location in LKCNHM",
    "Catalogued by",
    "Date catalogued",
    "Access status",
    "Remarks",
    "Batch no.",
    "Sign-Out Date",
    "Sign-In Date",
    "Date of QC",
    "Checked by",
    "Object Condition (QC2)",
    "",
    "Data Tier (2 or 3)",
]

slides_headers = str([col.strip().lower() for col in slides_headers])
library_and_archives_header = [
    "S/N",
    "Category",
    "Subcategory",
    "Catalog Number",
    "Object Status",
    "Location (in Museum)",
    "Material Type",
    "Subject",
    "Shelving Location",
    "Condition",
    "Number of copies",
    "Full Title",
    "Journal/Conference/Report/Workshop Name",
    "Edition Number",
    "Volume Number",
    "Issue Number",
    "Pages",
    "Author",
    "From Year",
    "From Month",
    "From Date",
    "To Year",
    "To Month",
    "To Date",
    "ISBN/ISSN Number",
    "Language",
    "Country",
    "Publisher",
    "Organisation",
    "Collection Name",
    "Physical Description",
    "Abstract",
    "Keywords",
    "Remarks",
    "Recorded by",
    "Recorded year",
    "Scan file media",
    "Transcription file media",
]

library_and_archives_header = str(
    [col.strip().lower() for col in library_and_archives_header]
)

if __name__ == "__main__":
    print(
        print_headers.replace("[", "")
        .replace("]", "")
        .replace("(", "")
        .replace(")", "")
        .replace("/", "")
        .replace("-", "_")
        .replace(", ", ",")
        .replace(" ", "_"),
        "\n",
        oral_histories_headers.replace("[", "")
        .replace("]", "")
        .replace("(", "")
        .replace(")", "")
        .replace("/", "")
        .replace("-", "_")
        .replace(", ", ",")
        .replace(" ", "_"),
        "\n",
        slides_headers.replace("[", "")
        .replace("]", "")
        .replace("(", "")
        .replace(")", "")
        .replace("/", "")
        .replace("-", "_")
        .replace(", ", ",")
        .replace(" ", "_"),
        "\n",
        library_and_archives_header.replace("[", "")
        .replace("]", "")
        .replace("(", "")
        .replace(")", "")
        .replace("/", "")
        .replace("-", "_")
        .replace(", ", ",")
        .replace(" ", "_"),
        "\n",
        negative_headers.replace("[", "")
        .replace("]", "")
        .replace("(", "")
        .replace(")", "")
        .replace("/", "")
        .replace("-", "_")
        .replace(", ", ",")
        .replace(" ", "_"),
        "\n",
    )
