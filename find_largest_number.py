import pdfplumber
import re
import sys
import collections


''' 
Goal: Read the inputted pdf and extract the largest numerical value, ignoring specific units
Bonus Goal: Include consideration for natural language, and incorporate functionality for units such as "millions"
'''
NUMBER_REGEX = [
                r'(-?\d+(?:\.\d*)?)(?:\s*(million|billion|thousand|trillion)s?)?',
                r'((?<=\$)-?\d+(?:\.\d*)?)(?: *(M|B|T))'
                ]
NUMBERS_WITH_SUFFIXES = re.compile("|".join(NUMBER_REGEX))

TABLE_HEADERS = re.compile(r'$M|\(\$M\)|\$ millions|in millions|in thousands|\(\$\)|\(millions\)', re.IGNORECASE)

DATES = re.compile(r'FY\s*(?:19|20)\d\d')


TABLE_HEADERS_TO_NUMBERS = {
        "$m": 1_000_000,
        "($m)": 1_000_000,
        "$ millions": 1_000_000,
        "in millions": 1_000_000,
        "in thousands": 1_000,
        "($)": 1,
        "(millions)": 1_000_000
        }
SUFFIXES_TO_NUMBERS = {
        "thousand": 1_000,
        "million": 1_000_000,
        "m": 1_000_000,
        "billion": 1_000_000_000,
        "b": 1_000_000_000,
        "trillion": 1_000_000_000_000,
        "t": 1_000_000_000_000
        }

class RecognizedNumber:
    def __init__(self, raw_text, parsed_number, page_number):
        self.raw_text = raw_text
        self.parsed_number = parsed_number
        self.page_number = page_number
def parse_number(regex_groups, page_number):
    recognized_number = None
    if regex_groups[1] == '':
        # the number has no suffix; it's a literal
        recognized_number = RecognizedNumber(raw_text=regex_groups[0],
                                                     parsed_number=float(regex_groups[0]),
                                                     page_number=page_number)
    else:
        recognized_number = RecognizedNumber(raw_text=f"{regex_groups[0]} {regex_groups[1]}",
                                                     parsed_number=float(regex_groups[0])*SUFFIXES_TO_NUMBERS[regex_groups[1].lower()],
                                                     page_number=page_number)
    return recognized_number

def find_largest_number_in_pdf(pdf_path):
    with pdfplumber.open(pdf_path) as pdf:
        maximum_recognized_number = None
        for idx, page in enumerate(pdf.pages):
            page_max = None
            page_text = page.extract_text()
            tables = page.extract_tables()
            # first pass: search through the page text to identify numbers and update local page maximum
            matches = NUMBERS_WITH_SUFFIXES.findall(page_text)
            for match in matches:
                recognized_number = parse_number(match, idx)
                if page_max is None or page_max.parsed_number < recognized_number.parsed_number:
                    page_max = recognized_number
            # second pass: search through the tables, identify value-multiplying headers within the tables,
            # and update local page maximum
            table_column_multipliers = collections.defaultdict(lambda: 1)
            for table in tables:
                # by default, the multiplier for a given item in a table should be 1, 
                # unless we discover a column header that specifies otherwise.
                found_new_headers = False
                current_multipliers = collections.defaultdict(lambda: 1)
                if len(table) >= 3:
                    for header_row in table[:3]:
                        # check the first few rows to see if a header exists
                        # (in practice, a header tends to appear in either row 0 or row 1)
                        for col_idx, item in enumerate(header_row):
                            if item:
                                multipliers = TABLE_HEADERS.findall(item)
                                if multipliers and multipliers[0]:
                                    current_multipliers[col_idx] = TABLE_HEADERS_TO_NUMBERS[multipliers[0].lower()]
                                    found_new_headers = True
                    if found_new_headers:
                        table_column_multipliers = current_multipliers
                        # we will only update the multipliers for each iterated table in a page if 
                        # that table includes new unit headers. Otherwise, it is likely we're actually in a sub-table,                         # not a new table
                    for row in table[2:]:
                        # check the remaining rows, and generate a RecognizedNumber, taking
                        # the table header multiplier into consideration
                        for col_idx, item in enumerate(row):
                            if item:
                                numbers = NUMBERS_WITH_SUFFIXES.findall(item)
                                for number in numbers:
                                    if number[1] == '': # only apply the multiplier if the row item doesn't already have a unit suffix
                                        
                                        recognized_number = parse_number(regex_groups=number,
                                                                         page_number=idx)
                                        recognized_number.parsed_number *= table_column_multipliers[col_idx]
                                        if page_max is None or page_max.parsed_number < recognized_number.parsed_number:
                                            page_max = recognized_number
            # third pass: check for irregularly formatted tables that aren't detected by 
            # pdfplumber. we can try checking for these by scanning the first few text lines of the page,
            # and seeing if one of them contains one of the special headers, e.g. "(dollars in millions)", 
            # as seen on page 29. if so, we proceed similarly to pass 2, parsing numbers and applying the multiplier

            # one caveat is that, even though the page headers for these tables will state "dollars in millions",
            # there may be additional table text which specifies that values are actually just "dollars" or "dollars in thousands". In other words, it's not entirely reliable to proceed based on the header alone.
            
            # proposed solution: omit the third pass when certain conditions are met:
                # - if pdfplumber has already recognized a table on this page (i.e. then let the existing logic handle it)
                # - if multiple unit headers have been identified on the same page. since we can't parse the table,
                    # we won't know which units/multipliers belong to which values
            # if there is only one unit identified on the page, and we haven't already found an existing table,
            # then we will assume that we're dealing with an irregularly formed table, and apply the multiplier
            # found in the header

            if len(tables) == 0:
                text_lines = page_text.split("\n")
                page_multipliers = []
                if len(text_lines) >= 4:
                    for line_idx, line in enumerate(text_lines[:3]):
                        table_modifiers = TABLE_HEADERS.findall(line)
                        if table_modifiers:
                            for modifier in table_modifiers:
                                page_multipliers.append(TABLE_HEADERS_TO_NUMBERS[modifier.lower()])
                                #print("found a table modifier on page ", idx," and line ", line_idx, "with the string: ", modifier)
                                #print("Showing the full line: ", line)
                    if len(page_multipliers) == 1:
                        # if we've only found a single page multiplier towards the beginning of the page,
                        # then use it to modify the subsequent values we find on that same page, if they have
                        # no other suffix
                        for line_idx, line in enumerate(text_lines[3:]):
                            numbers = NUMBERS_WITH_SUFFIXES.findall(line)
                            for number in numbers:
                                if number[1] == '':
                                    # the number has no suffix
                                    #print("using primary suffix for non-standard table page: ", idx)
                                    #print("multiplier: ", page_multipliers[0])
                                    #print("number: ", number[0])
                                    recognized_number = parse_number(number, idx)
                                    recognized_number.parsed_number *= page_multipliers[0]
            if maximum_recognized_number is None:
                maximum_recognized_number = page_max
            elif page_max and maximum_recognized_number.parsed_number < page_max.parsed_number:
                maximum_recognized_number = page_max
    return maximum_recognized_number


if len(sys.argv) >= 3:
    print("Expected usage: python3 main.py or python3 main.py <path-to-file>")
    exit()
pdf_path = None
if len(sys.argv) == 2:
    pdf_path = sys.argv[1]
else:
    pdf_path = "./input.pdf"
print("Attempting to extract the largest numberical value for the PDF located at: ", pdf_path)
#try:
largest_number = find_largest_number_in_pdf(pdf_path)
if largest_number:
    print(f"Largest Number: {largest_number.parsed_number}")
    print(f"Found at Page: {largest_number.page_number}")
    print(f"Matching Text: {largest_number.raw_text}")
else:
    print("No numbers were found in the text.")
#except Exception as e:
#    print("ERROR: ", e)



