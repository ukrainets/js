# LinkedIn Contacts Companies

This is a submodule that helps gather more companies from the LinkedIn contacts. 

## Getting Data from LinkedIn (manual export)
- Go to LinkedIn settings -> Data Privacy (or open https://www.linkedin.com/mypreferences/d/categories/privacy)
- In "How LinkedIn uses your data" section, click "Download your data"
- Click the "Download archive" button. and download it to your computer. 
- Unzip the downloaded archive and copy `Connections.csv` to the `linked/input_data` directory.
- Open `Connections.csv` file with the text editor and remove the note on top of the table
- Use AI to find companies websites
```txt
I need you to create a new table from the companies in connections2.csv, and find and add all companies' websites to it.

Parse the given CSV file and extract the company names from the "Company" column. 
Create a new table with the columns [company, website, comment] 
Copy company names from the table. 
Search the internet for each company name and find the company website. 
Skip the company if you can't find the company's website.
Make the table available in both Markdown and CSV formats. 

Analyze the given information and ask me clarifying questions until you have enough missing data to complete this task correctly.
```

Manual Export — Go to Settings → Data Privacy → Get a copy of your data → select "Connections." You'll get a CSV with names, companies, positions, and connection dates. This is the easiest path.
