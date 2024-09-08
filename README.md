# Largest Number Finder

A program to find the largest numerical value in a PDF

## Setup

1. Clone the repository to your directory of choice.
2. Ensure that Python3/pip are installed in your environment.
3. Create a virtual environment using `python3 -m venv <env_name>`
4. Activate the environment via `source <path_to_env>/bin/activate`
5. Install dependencies via `pip install -r requirements.txt`

## Usage

Ensure that your virtual environment is activated and that dependencies have been installed,
and run either of the following:

`python3 find_largest_number.py` --> this will search the current directory for a file named `input.pdf` and run the program using that pdf
`python3 find_largest_number.py <path_to_pdf>` --> this will run the program with the specified pdf

The program will output the largest number found in float form, the page number on which it was found, and the originaltext that was used to recognize that number.

## Program Structure

The program uses a three-pass structure for each page in the pdf, in order of ascending complexity:

-   First, the program checks for standalone numerical values. These values are identified using regex, and consist of a number (a sequence of digits, followed by an optional decimal point and additional digits), followed by an optional value-modifying suffix such as "thousands" "billions" and so on. If such a suffix exists, the program will multiply the original numerical value accordingly.
-   Next, the program checks for numerical values within recognized tables. If a table has been identified (using the `pdfplumber` library), column headers are used to identify value multipliers, and multipliers are applied accordingly when identifying numbers
-   Lastly, the program checks for "irregular" tables, which aren't recognized by `pdfplumber`'s table detection algorithm. In such cases, value multipliers are still identified and used, but only under certain conditions. This works by searching for a table header term (ex. "\_ in thousands") at the top of a page, and applying it to numerical values on that page, if no other headers exist and no tables have been identified on this page already.

The program will output the largest number found in float form, the page on which it was found, and the text that was used to recognize the number.

## TODOs:

-   Since the third pass in particular may be prone to error/false positives, add a pass parameter to the program inputs, which allows the user to specify the maximum number of passes (1, 2, or 3).
-   Add additional number format specifiers, and/or recognized table headers/units (ex. comma-separated numbers, dot-separated numbers)
