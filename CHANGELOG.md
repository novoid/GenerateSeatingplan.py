Changelog:
==========
* 2018-02-16 by Christian Schindler
  - Added CHANGELOG.md (this) file to get an idea what was changed. 
  - UTF-8 support: csv export from TUG-Online must be utf-8. Now umlauts and special characters are possible
  - HTML-Seating Plan:
    - Names in the HTML seating plan are truncated (with trailing horizontal ellipsis) when longer than 10 characters 
    - Row and column numbering on all sides of the seating plan
    - Turning table (-u opton for lecturer view) now browser independent 
  - Fixed latex source: usepackage utf8x; all generated pdfs correctyl display  umlauts and special characters in names
  - Fixed latex source: intendation removed of first line in first paragraph in Students_Checklist_by_Seat.pdf 
* 2017-06-02 by Christian Schindler
  - Deal with student IDs with 8 digits
  - Added new lecture hall HS_I Rechbauerstr. 12, 8010 Graz (basement)
* 2017-01-31 by Christian Schindler
  - New Option: filling seats from front
  - Excluded seats for disabled in HS_P1 - last row 12|13, 14|15
