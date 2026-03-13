# ToDo

List of planned work

## To Do

✅ Mach output
- Add functionality to store matching found positions to the CSV file.
- csv file should be stored in `output_data/match.csv`
- The name for this output file should be set by config in the `config.json`
- If the file is not present, it should be created; if the file is present, information should be updated.  
- CSV file should have these columns: id, company_name, match_position_url, time_found, received, comment.
- `time_found` should be in ISO 8601 format `2026-04-10 17:25:00`
- `company_name` should be the same as in the input CSV.  
    
✅ Check match output
- Add functionality to check if the found match was already added to the output CSV. 
- This functionality should check the current match URL with the URLs in the `match_position_url` column. Most URLs are unique and can be used as a unique identifier.
- If the found match URL is not present in the CSV, it should be upended in a new row, and the fields `company_name, match_position_url, and time_found should be filled out. 
    - for this scenario, console output should be changed to:
        ```txt
        🔎  Scanning : Amount - https://job-boards.greenhouse.io/amount/
        ✅  Match for: [Automation Engineer] https://job-boards.greenhouse.io/amount/jobs/5058090007
        🟢 added to output file
        ```
    - If the found URL is already in the output file, than app should skip adding it and write in the console output:
        ```txt
        🔎  Scanning : Amount - https://job-boards.greenhouse.io/amount/
        🟡  No new matches found
        ```

[] Slack notification for the new 
- Add functionality to send a Slack message if the new matches were found
- Store webhook in the `.env` file under `SLACK_WEBHOOK`
- When a new match found, it should be posted to the Slack in this format:
```txt
🥳 New match found: [company_name] - [title]
[match_position_url]
```

[] Add scheduler
    - Add scheduler functionality to run the app on a schedule. 
    - `config.json` should keep the time when the schedule will run. There should be an option to set multiple times.
    - Set scheduler to run at `8:08`, `13:13`, and `18:18`.

[] Add batter handling to the missing input files. 
    - Add infrastructure checks before running main.
    - Add notification for the missing input files.

[] Add Google Spreadsheet API helper
- Documentation
    - Document how to set up Spreadsheet files
    - Document how to get API keys and add them to the app.
- Develop Google Spreadsheet API helper
    - Make a config switch to switch between CSV file and Google Spreadsheet API
    - CSV file will be defoult settings
    - When the config is set to the Google Spreadsheet API app shouldn't use CSV at all and should use spreadhseet
    - Add the console output to show what input/output media app is using.
    - Add Proper error handlers if the API is not set up correctly or is not accessible.
    - App will get companies and titles from the Spreadsheet and write results to the match spreadsheet. 
      
    
    
