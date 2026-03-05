# Claude Knowledge base for JS (Job Search) project

## Goal 
Build a tool that will help search for open positions. 

I am currently looking for a new position.
I have a spreadsheet of companies I like and check if they have positions that match my desired job title.
I manually open the link and search for positions such as "QA Engineer, Test Automation Engineer, Software QA Tester" using the browser search or the search bar on the company page, if available. 
If I find a position on the company page, I make a note about it in my Spreadsheet.

This takes a lot of time and should be automated. 

Building proof of concept. 
Workflow logic
- Open File with companies
- Take the first link, open it
- Get position titles from the position titles file
- search for all titles in the company page
- If some title is matching, write to the console (Company name, link, and job Title that was matched)
- Move to the next company. and perform the same search and console notification. 

At the end, output in the console how many companies were searched, and how many titles were matched. 

- The app should intake two CSV files
  - companies.csv
  - titles.csv

Tack stack for proof of concept:
- No UI for now, only plain code and console output.
- The project should be built in Python with Python-related libraries. 
