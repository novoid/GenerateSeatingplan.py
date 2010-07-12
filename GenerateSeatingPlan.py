#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Latest change: Mon Mar 08 11:49:34 CET 2010
"""
GenerateSeatingPlan.py
~~~~~~~~~~~~~~~~~~~~~~

:copyright: (c) 2010 by Karl Voit <Karl.Voit@IST.TUGraz.at>
:license: GPL v2 or any later version
:bugreports: <Karl.Voit@IST.TUGraz.at>

If you want access to the TU Graz SVN respository of this tool, send an email
to Karl.Voit@IST.TUGraz.at

See USAGE below for details!

FIXXME:
    * look for the string FIXXME to improve this script
    * Sanity checks all over (cmd line parameters, CSV file, ...)
    * implement GenerateTextfileSortedBySeat() and probably add a command line switch
    * probably: if -p is given, ask for proceeding after displaying ASCII seating plan

"""

## for general and jpilot reading:
import logging, os, re
from optparse import OptionParser

from random import *

## for CSV
import csv

## debugging:   for setting a breakpoint:  pdb.set_trace()
#import pdb

##        ===========================
##         How to add a lecture room
##        ===========================
##
##    Add a line below with following format:
##
##    NAME_OF_ROOM = { 'rows': NUMBER_OF_ROWS, 'columns': NUMBER_OF_SEATS_PER_ROW, 'name': "HUMAN READABLE NAME", 'seatstoomit': [ LIST OF SEATS THAT CAN NOT BE USED ] }
##
##    ... and ...
##
##    Add an entry to LIST_OF_LECTURE_ROOMS with:
##    { 'name': "SHORT_NAME_OF_ROOM", 'data': NAME_OF_ROOM }   ... with NAME_OF_ROOM is exactly the same name as above
##
## Details:
##
##  * General: avoid german umlauts due to character encoding issues
##        with LaTeX and ASCII output
##  * NUMBER_OF_ROWS: be careful: some lecture rooms have rows 
##        that can not be used for exam purposes. For example
##        some rooms do not provide a table for the very first
##        row
##  * "HUMAN READABLE NAME" will be used for printouts
##  * LIST OF SEATS THAT CAN NOT BE USED: some rooms have seats 
##        that can not be used because they do not exist or are
##        occupied with something else
##        Comma separated list elements look like: [ 3, 4 ] which 
##        means row three and seat four
##  * SHORT_NAME_OF_ROOM: is used for command line argument
##        Must not continue special characters nor spaces!
##  * NAME_OF_ROOM: is used for referring from LIST_OF_LECTURE_ROOMS 
##        to the detailed data sets. Please make sure, that they match
##        Must not continue special characters nor spaces!

HS_i7 = { 'rows': 15, 
        'columns': 16, 
        'name': "Hoersaal i7", 
        'seatstoomit': [ [1, 1], [1, 2], [2, 1] , [2, 2], [3, 1] , [3, 2], 
            [4, 1] , [4, 2], [5, 1] , [5, 2], [6, 1] , [6, 2], [7, 1] , [7, 2],
            [15, 11], [15,12], [15,13], [15,14]
            ] }

HS_i11 = { 'rows': 10, 
        'columns': 9, 
        'name': "Hoersaal i11", 
        'seatstoomit': [ [10, 4], [10, 5], [10, 6] ] }

HS_i12 = { 'rows': 10, 
        'columns': 13, 
        'name': "Hoersaal i12", 
        'seatstoomit': [ [10, 6], [10, 7], [10, 8], [10, 11], [10, 12], [10, 13] ] }

HS_i13 = { 'rows': 14, 
        'columns': 22, 
        'name': "Hoersaal i13", 
        'seatstoomit': [ [14, 10], [14, 11], [14, 12], [14, 13] ] }

HS_B = { 'rows': 10, 
        'columns': 16, 
        'name': "Hoersaal B", 
        'seatstoomit': [ ] }

HS_test1 = { 'rows': 4, 
        'columns': 7, 
        'name': "Test-Hoersaal", 
        'seatstoomit': [ [4, 1], [4, 2], [4, 3], [3,7] ] }

LIST_OF_LECTURE_ROOMS = [ \
        { 'name': "HS_i7", 'data': HS_i7 }, \
        { 'name': "HS_i11", 'data': HS_i11 }, \
        { 'name': "HS_i12", 'data': HS_i12 }, \
        { 'name': "HS_i13", 'data': HS_i13 }, \
        { 'name': "HS_B", 'data': HS_B }, \
        { 'name': "test1", 'data': HS_test1 } \
        ]

NAME_OF_PDF_FILE_WITHOUT_EXTENSION = "Seating_Plan"
NAME_OF_TXT_FILE_WITHOUT_EXTENSION = "Seating_Plan"


## ======================================================================= ##
##                                                                         ##
##         You should NOT need to modify anything below this line!         ##
##                                                                         ##
## ======================================================================= ##

TEMP_FILENAME_STUDENTS_TEXFILE = "temp_students_by_lastname.tex"

LECTURE_ROOM_DEFAULT_VALUE = HS_i13
LECTURE_ROOM = LECTURE_ROOM_DEFAULT_VALUE

string_of_all_known_lecture_room_names = ""
for room in LIST_OF_LECTURE_ROOMS:
    string_of_all_known_lecture_room_names += room['name']+" "

## 1 ... one student, one free seat, one student, ...
## 2 ... two students, one free seat, two students, ...
SEATS_WITH_STUDENTS_BEFORE_FREE_SEAT_DEFAULT_VALUE = 1
SEATS_WITH_STUDENTS_BEFORE_FREE_SEAT = SEATS_WITH_STUDENTS_BEFORE_FREE_SEAT_DEFAULT_VALUE

## 1 ... one row with students, one empty row, one row with students, ...
## 2 ... two rows with students, one empty row, two rows with students, ...
ROWS_WITH_STUDENTS_TO_KEEP_TOGETHER_DEFAULT_VALUE = 1
ROWS_WITH_STUDENTS_TO_KEEP_TOGETHER = ROWS_WITH_STUDENTS_TO_KEEP_TOGETHER_DEFAULT_VALUE

NUM_FREE_SEATS_DEFAULT_VALUE = 1
NUM_FREE_SEATS = NUM_FREE_SEATS_DEFAULT_VALUE

NUM_FREE_ROWS_DEFAULT_VALUE = 1
NUM_FREE_ROWS = NUM_FREE_ROWS_DEFAULT_VALUE


USAGE = "\n\
         %prog --lr KNOWN_ROOM STUDENTS.csv\n\
\n\
GenerateSeatingPlan.py takes a TUGrazOnline CSV file including the students\n\
attending an exam and generates a randomized seating plan for a specific\n\
lecture room.\n\
\n\
Several things can be manipulated according to your needs. \n\
\n\
  :copyright:  (c) 2010 by Karl Voit <Karl.Voit@IST.TUGraz.at>\n\
  :license:    GPL v2 or any later version\n\
  :bugreports: <Karl.Voit@IST.TUGraz.at>\n\
\n\
If you want write access to the TU Graz SVN respository of this tool, send \n\
an email to Karl.Voit@IST.TUGraz.at\n\
\n\
Run %prog --help for usage hints\n"


parser = OptionParser(usage=USAGE)

parser.add_option("-c", "--csvfile", dest="students_csv_file",
                  help="CSV file of students in TUGrazOnline format. You can add columns but original header line is required.", metavar="FILE")

parser.add_option("--lr", "--lecture-room", dest="lecture_room",
                help="the short name of a known lecture room. so far, following lecture rooms are supported: "+str(string_of_all_known_lecture_room_names), metavar="NAME")

parser.add_option("--sa", "--students_adjoined", dest="students_side_by_side",
                  help="that many students are sitting right beneath each other before the next empty seat(s)", metavar="INT")

parser.add_option("--ra", "--filled_rows_adjoined", dest="occupied_row_before_empty_line",
                  help="that many rows are being filled with students before the next empty row(s)", metavar="INT")

parser.add_option("--fs", "--free_seats_to_seperate", dest="num_free_seats",
                  help="that many seats are empty before the next student sits", metavar="INT")

parser.add_option("--fr", "--free_rows_to_seperate", dest="num_free_rows",
                  help="that many rows are empty before the next row is filled", metavar="INT")

parser.add_option("-p", "--pdf", dest="pdf", action="store_true",
                  help="generates a PDF file with alphabetical student names and seating (requires pdflatex with savetrees, longtable, hyperref, and KOMA)")

parser.add_option("-v", "--verbose", dest="verbose", action="store_true",
                  help="enable verbose mode")

parser.add_option("-q", "--quiet", dest="quiet", action="store_true",
                  help="do not output anything but just errors on console")


(options, args) = parser.parse_args()

class vk_FileNotFoundException(Exception):
    def __init__(self, value):
        self.value = value
    def __str__(self):
        return repr(self.value)

def handle_logging():
    """Log handling and configuration"""

    if options.verbose:
        FORMAT = "%(levelname)-8s %(asctime)-15s %(message)s"
        logging.basicConfig(level=logging.DEBUG, format=FORMAT)
    elif options.quiet:
        FORMAT = "%(levelname)-8s %(message)s"
        logging.basicConfig(level=logging.CRITICAL, format=FORMAT)
    else:
        FORMAT = "%(message)s"
        logging.basicConfig(level=logging.INFO, format=FORMAT)

def ReadInStudentsFromCsv(csvfilename):

    csvReader = csv.DictReader(open(csvfilename), delimiter=';', quotechar='"')
    students_list = []

    for row in csvReader:
        students_list.append(row)

    return students_list

def PrintOutSeats(lecture_room, list_of_seats):
    """Plot an ASCII graph of the lecture room with all potential used seats (to show seating scheme)"""

    linestring = ""
    if len(list_of_seats) < 1:
        logging.warning("list_of_seats is empty, so no seat is occupied. looks like internal error.")
    ## logging.debug("number of seats in list_of_seats: %s" % str(len(list_of_seats)) )

    print "\nLegend:   #  ... potential seat      -  ... empty seat"
    print   "          S  ... student sitting     X  ... seat not available"
    print   "      row 1  ... first row near blackboard"

    print "\n------    Seating Scheme for Lecture Room \"" + lecture_room['name'] + "\"   ------\n"
    print   "              --Front--"

    for currentrow in range(1, lecture_room['rows']+1):

        linestring = "   row " + str(currentrow).rjust(2)+":  "

        for currentseat in range(1, lecture_room['columns']+1):
            if [currentrow, currentseat] in lecture_room['seatstoomit']:
                linestring += "X "
            elif [currentrow, currentseat] in list_of_seats:
                linestring += "# "
            else:
                linestring += "- "

        print linestring
        linestring = ''

def PrintOutSeatsWithStudents(lecture_room, list_of_students):
    """Plot an ASCII graph of the lecture room with all seated students marked"""

    linestring = ""
    if len(list_of_students) < 1:
        logging.warning("list_of_seats is empty, so no seat is occupied. looks like internal error.")

    print "\n------    Seating Plan with students for Lecture Room \"" + lecture_room['name'] + "\"   ------\n"
    print   "              --Front--"

    for currentrow in range(1, lecture_room['rows']+1):

        linestring = "   row " + str(currentrow).rjust(2) + ":  "

        for currentseat in range(1, lecture_room['columns']+1):

            seat_is_defined = False

            if [currentrow, currentseat] in lecture_room['seatstoomit']:
                linestring += "X "
                seat_is_defined = True
                continue

            ## pretty dumb "brute force" search for a student, sitting on current seat
            for student in list_of_students:
                if student['seat'] == [ currentrow, currentseat]:
                    linestring += "S "
                    seat_is_defined = True

            if not seat_is_defined:
                linestring += "- "

        print linestring
        linestring = ''
    print ## one final line to seperate



def FillRowWithStudentsOrLeaveEmpty(lecture_room, currentrow, list_of_occupied_seats):

    ## initialize things before filling a row with students:
    current_num_of_students_close_together = 0
    current_num_of_empty_seats = 0
    filling_seats = True

    ## iterate over the seats in a row:
    for currentseat in range(1, lecture_room['columns']+1):

        #logging.debug("---row %s seat %s stud_close %s" % ( str(currentrow), str(currentseat), str(current_num_of_students_close_together) )   )

        ## filling_seats means that there are not too many students right beneath each other:
        if filling_seats:

            #logging.debug("o  row %s seat %s occupied" % ( str(currentrow), str(currentseat)) )
            list_of_occupied_seats.append( [ currentrow, currentseat ] )
            current_num_of_students_close_together += 1

            ## if enough students are seated beneath each other, continue next time with empty seats:
            if current_num_of_students_close_together >= SEATS_WITH_STUDENTS_BEFORE_FREE_SEAT:
                current_num_of_students_close_together=0
                if NUM_FREE_SEATS > 0:
                    filling_seats = False
                    current_num_of_empty_seats = 0

        else:  ## not filling seats, generate empty seats between students

            current_num_of_empty_seats += 1

            ## continue with seating students again
            if current_num_of_empty_seats == NUM_FREE_SEATS:
                current_num_of_empty_seats = 0
                current_num_of_students_close_together=0
                filling_seats = True
                continue ## with next seat

            ## not enough free seats, continue with empty seats
            elif current_num_of_empty_seats < NUM_FREE_SEATS:
                continue ## with next seat

    return list_of_occupied_seats


def GenerateListOfAllSeats(lecture_room):
    """Generates a (dumb) list of all seats *not* considering seats to omit"""

    logging.debug("seats per row:  %s" % str(lecture_room['columns']) )
    logging.debug("number of rows: %s" % str(lecture_room['rows']) )
    logging.debug("number of students sitting right beneath each other:  %s" % str(SEATS_WITH_STUDENTS_BEFORE_FREE_SEAT) )
    logging.debug("number of rows filled with students before empty row: %s" % str(ROWS_WITH_STUDENTS_TO_KEEP_TOGETHER) )

    current_num_of_filled_rows = 0
    current_num_of_empty_rows = 0
    filling_row = True
    list_of_occupied_seats = []

    ## iterate over the rows:
    for currentrow in range(1, lecture_room['rows']+1):

        #logging.debug("r  starting now in row %s" % str(currentrow) )

        ## filling_row == True if currentrow should be filled with students
        if filling_row:

            current_num_of_filled_rows += 1

            ## fill me the row:
            list_of_occupied_seats = FillRowWithStudentsOrLeaveEmpty(lecture_room, currentrow, list_of_occupied_seats) 

            if current_num_of_filled_rows == ROWS_WITH_STUDENTS_TO_KEEP_TOGETHER:
                ## next row should be an empty one

                current_num_of_filled_rows = 0
                if NUM_FREE_ROWS > 0:
                    filling_row = False
                #logging.debug("skipping row %s" % str(currentrow) )
                continue ## in next row

        ## not filling rows: keep row empty
        else:

            current_num_of_empty_rows += 1

            ## next row should be filled with students again
            if current_num_of_empty_rows == NUM_FREE_ROWS:
                current_num_of_empty_rows = 0
                filling_row = True
                continue ## in next row

            ## keep on with empty rows
            elif current_num_of_empty_rows <= NUM_FREE_ROWS:
                continue ## in next row

    logging.debug("number of (dumb) seats not considered seats to omit: %s" % str(len(list_of_occupied_seats)) )
    ## print str(list_of_occupied_seats)

    return list_of_occupied_seats

def SelectRandomListElementAndRemoveItFromList(list):
    if list != []:
        list_element_index = randrange( len(list) )
        list_element = list[list_element_index]
        list[list_element_index] = list[-1]
        del list[-1]
        return list_element
    else:
        return None


def GenerateRandomizedSeatingPlan(list_of_students, list_of_available_seats):

    ## randomize students over all seats:
    for student in list_of_students:
        student['seat'] = SelectRandomListElementAndRemoveItFromList(list_of_available_seats)

    ## randomize over all students, beginning to fill seats from first row upward:
    ## FIXXME: to be done
    ##     idea: iterate over seats and assign random student to it

    return list_of_students


def GenerateTextfileSortedByStudentLastname(lecture_room, list_of_students_with_seats):

    file = open(NAME_OF_TXT_FILE_WITHOUT_EXTENSION + '.txt', 'w')

    file.write( "               Seating plan     " + lecture_room['name'] + "      by last name\n\n")

    for student in list_of_students_with_seats:
        file.write( student['FAMILY_NAME_OF_STUDENT'].ljust(25, '.') + \
            student['FIRST_NAME_OF_STUDENT'].ljust(20, '.') + \
            student['REGISTRATION_NUMBER'].ljust(10, '.') + \
            "  row " + str(student['seat'][0]).rjust(3) + "/" + str(chr(64 + student['seat'][0] )) + \
            "  seat " + str(student['seat'][1] ).rjust(3) + "\n\n" )
            

def GenerateLatexfileSortedByStudentLastname(lecture_room, list_of_students_with_seats):

    file = open(TEMP_FILENAME_STUDENTS_TEXFILE, 'w')

    for student in list_of_students_with_seats:
        file.write( "\\vkExamStudent{" + student['FAMILY_NAME_OF_STUDENT'] + '}{' + \
            student['FIRST_NAME_OF_STUDENT'] + '}{' + \
            student['REGISTRATION_NUMBER'] + '}{' + \
            str(student['seat'][0]) + '}{' + \
            str(chr(64 + student['seat'][0] )) + '}{' + \
            str(student['seat'][1] ) + '}' + "\n" )
    file.flush() 
    os.fsync(file.fileno())
            

def GenerateTextfileSortedBySeat(lecture_room, list_of_students_with_seats):

    pass
    ## FIXXME

def GenerateLatexMainFile(lecture_room):

    content = '''\\documentclass[%
14pt,%
a4paper,%
oneside,%
headinclude,%
footexclude,%
openright%
]{scrartcl}

%% encoding:
\\usepackage[ansinew]{inputenc}
\\usepackage{ucs}
%\\usepackage[utf8x]{inputenc}  %% Sorry, problems with Umlauts in CSV forced me to stay at ansinew

%% use up as much space as possible:
\\usepackage{savetrees}

%% using a loooong table possible over several pages:
\\usepackage{longtable}

\\pdfcompresslevel=9

\\usepackage[%
  pdftitle={Seating Plan}, %
  pdfauthor={}, %
  pdfsubject={Exam}, %
  pdfcreator={Accomplished with LaTeX2e and pdfLaTeX with hyperref-package under Debian GNU/Linux. No anmimals, MS-EULA or BSA-rules were harmed.},
  pdfproducer={GenerateSeatingPlan.py by Karl Voit},
  pdfkeywords={Seating Plan, Exam},
  a4paper=true, %
  pdftex=true, %
  bookmarks=false, %
  bookmarksopen=false, % when starting with AcrobatReader, the Bookmarkcolumn is opened
  pdfpagemode=None,% None, UseOutlines, UseThumbs, FullScreen
  plainpages=false, % correct, if pdflatex complains: ``destination with same identifier already exists''
  colorlinks=false % turn off colored links (better for printout versions)
]{hyperref}

%% header and footer:
\\usepackage{scrpage2}
\\pagestyle{scrheadings}
\\clearscrheadings
\\clearscrplain
\\ifoot{\\scriptsize{}page~\\pagemark}
\\ofoot{\\tiny{}Generated using GenerateSeatingPlan.py by Karl Voit}

\\begin{document}

\\newcommand{\\vkExamStudent}[6]{%%
    #1 & #2 & #3 & #4 & #6  \\\\[0.5em] 
}%%

\\sffamily
\\newcommand{\\vkHeaderSettings}{\\bf\\large }

\\begin{longtable}{lllrr}
\\multicolumn{5}{c}{\\scshape\\Large Seating Plan ''' + lecture_room['name'] + '''} \\\\[5pt]
\\multicolumn{2}{c}{\\vkHeaderSettings Name} & {\\vkHeaderSettings Matr.} & \\multicolumn{1}{c}{\\vkHeaderSettings Row} & {\\vkHeaderSettings Seat}  \\\\[5pt]
\\hline
\\hline \\\\[-5pt]
\\endhead
\\input{''' + TEMP_FILENAME_STUDENTS_TEXFILE + '''}
\\hline
\\end{longtable}

\\end{document}
%% end
'''

    file = open(NAME_OF_PDF_FILE_WITHOUT_EXTENSION+'.tex', 'w')

    file.write( content )
    file.flush() 
    os.fsync(file.fileno())


def InvokeLaTeX():

    ## FIXXME: implement a test, if pdflatex is found in path like:
    ## if not py.path.local.sysfind("pdflatex"):
    ##     logging.critical("ERROR: pdflatex could not be found on your system!")
    ##     os.sys.exit(7)

    ## for latexiterations in range(2):
    ##     os.execlp('pdflatex', 'pdflatex', NAME_OF_PDF_FILE_WITHOUT_EXTENSION+'.tex')
    if (os.system('pdflatex ' + NAME_OF_PDF_FILE_WITHOUT_EXTENSION + '.tex') or
        os.system('pdflatex ' + NAME_OF_PDF_FILE_WITHOUT_EXTENSION + '.tex')):
        logging.critical("ERROR: pdflatex returned with an error.")
        logging.critical("You can try manually by invoking \"pdflatex " + NAME_OF_PDF_FILE_WITHOUT_EXTENSION + ".tex\"")
        os.sys.exit(8)


def DeleteTempLaTeXFiles():

    ## FIXXME: check at tool start, if files with these names
    ##   are already in current directory and issue a warning
    ##   that these files will be deleted!

    logging.info("deleting temporary LaTeX files ...")
    os.remove(NAME_OF_PDF_FILE_WITHOUT_EXTENSION+'.tex')
    os.remove(NAME_OF_PDF_FILE_WITHOUT_EXTENSION+'.log')
    os.remove(NAME_OF_PDF_FILE_WITHOUT_EXTENSION+'.aux')
    os.remove(TEMP_FILENAME_STUDENTS_TEXFILE)
    logging.info("deleting temporary LaTeX files finished")
    


def main():
    """Main function [make pylint happy :)]"""

    print "   GenerateSeatingPlan.py - generating random seating plans for exams\n"
    print "          (c) 2010 by Karl Voit <Karl.Voit@IST.TUGraz.at>"
    print "              GPL v2 or any later version\n"

    handle_logging()

    if not options.students_csv_file:
        logging.critical("ERROR: No students CSV file given")
        os.sys.exit(1)

    if not os.path.isfile( options.students_csv_file ):
        logging.critical("ERROR: Students CSV file could not be found")
        os.sys.exit(2)

    ## FIXXME: implement additional command line parameter checks

    global ROWS_WITH_STUDENTS_TO_KEEP_TOGETHER
    if options.occupied_row_before_empty_line:
        logging.debug("default value of ROWS_WITH_STUDENTS_TO_KEEP_TOGETHER: %s" % ROWS_WITH_STUDENTS_TO_KEEP_TOGETHER) 
        ROWS_WITH_STUDENTS_TO_KEEP_TOGETHER = int(options.occupied_row_before_empty_line)
        logging.debug("ROWS_WITH_STUDENTS_TO_KEEP_TOGETHER " +
            "is overwritten by command line parameter: %s" % ROWS_WITH_STUDENTS_TO_KEEP_TOGETHER) 

    global SEATS_WITH_STUDENTS_BEFORE_FREE_SEAT
    if options.students_side_by_side:
        logging.debug("default value of SEATS_WITH_STUDENTS_BEFORE_FREE_SEAT: %s" % SEATS_WITH_STUDENTS_BEFORE_FREE_SEAT) 
        SEATS_WITH_STUDENTS_BEFORE_FREE_SEAT = int(options.students_side_by_side)
        logging.debug("SEATS_WITH_STUDENTS_BEFORE_FREE_SEAT " +
            "is overwritten by command line parameter: %s" % SEATS_WITH_STUDENTS_BEFORE_FREE_SEAT) 

    global NUM_FREE_SEATS
    if options.num_free_seats:
        logging.debug("default value of NUM_FREE_SEATS: %s" % NUM_FREE_SEATS) 
        NUM_FREE_SEATS = int(options.num_free_seats)
        logging.debug("NUM_FREE_SEATS " +
            "is overwritten by command line parameter: %s" % NUM_FREE_SEATS) 

    global NUM_FREE_ROWS
    if options.num_free_rows:
        logging.debug("default value of NUM_FREE_ROWS: %s" % NUM_FREE_ROWS) 
        NUM_FREE_ROWS = int(options.num_free_rows)
        logging.debug("NUM_FREE_ROWS " +
            "is overwritten by command line parameter: %s" % NUM_FREE_ROWS) 


    global LECTURE_ROOM
    if options.lecture_room:
        logging.debug("default value of LECTURE_ROOM: %s" % LECTURE_ROOM['name']) 
        LECTURE_ROOM = ""
        for room in LIST_OF_LECTURE_ROOMS:
            ## search for matching known lecture room
            if room['name'] == options.lecture_room:
                LECTURE_ROOM = room['data']
        if LECTURE_ROOM == "":
            logging.critical("ERROR: Sorry, lecture room \"%s\" is not recognised yet." % options.lecture_room ) 
            logging.critical("Known rooms are: %s" % string_of_all_known_lecture_room_names )
            os.sys.exit(4)

        logging.debug("LECTURE_ROOM is overwritten by command line parameter: %s" % LECTURE_ROOM['name']) 


    logging.debug("Student CSV file found")

    list_of_students = ReadInStudentsFromCsv( options.students_csv_file )

    logging.info("Number of students:  %s" % str(len(list_of_students)) ) 

    ## generate list of all seats and remove seats to omit from lecture room:
    list_of_available_seats = [ x for x in GenerateListOfAllSeats(LECTURE_ROOM) if x not in LECTURE_ROOM['seatstoomit'] ]

    logging.info("Number of seats:     %s   (using current seating scheme)" % str(len(list_of_available_seats)) ) 

    ## just the potential seating plan (without students)
    PrintOutSeats(LECTURE_ROOM, list_of_available_seats)

    missing_seats = len(list_of_students) - len(list_of_available_seats)
    if missing_seats > 0:
        logging.critical("\nERROR: With current seating scheme, there are %s seats missing!\n" % str(missing_seats) )
        logging.critical("Tip: try higher values for \"--students_adjoined\", \"--filled_rows_adjoined\",")
        logging.critical("     or lower values for \"--free_seats_to_seperate\", \"--free_rows_to_seperate\".")
        os.sys.exit(3)

    logging.info("(Unused seats: %s)" % str(len(list_of_available_seats) - len(list_of_students)) )

    list_of_students_with_seats = GenerateRandomizedSeatingPlan(list_of_students, list_of_available_seats)

    ## the seating plan (showing the students)
    PrintOutSeatsWithStudents(LECTURE_ROOM, list_of_students_with_seats)

    GenerateTextfileSortedByStudentLastname(LECTURE_ROOM, list_of_students_with_seats)

    ## not implemented yet:
    #GenerateTextfileSortedBySeat(LECTURE_ROOM, list_of_students_with_seats)

    if options.pdf:
       GenerateLatexfileSortedByStudentLastname(LECTURE_ROOM, list_of_students_with_seats)
       GenerateLatexMainFile(LECTURE_ROOM)
       InvokeLaTeX()
       DeleteTempLaTeXFiles()

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        logging.info("Received KeyboardInterrupt")

## END OF FILE #################################################################
# vim:foldmethod=indent expandtab ai ft=python tw=120 fileencoding=utf-8 shiftwidth=4
