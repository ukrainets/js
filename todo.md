# ToDo

List of planned work

## To Do

[x] Mach otput
- Add functionality to store matching found positions to the csv file.
- csv file should be stored in `output_data/match.csv`
- the name for this output file should be set by config in the `config.json`
- If file not present it should be created, if file present information should be upended.  
- csv file should have this columns `id, company_name, match_position_url, time_found, revieved, comment`
- `time_found` should be in ISO 8601 format `2026-04-10 17:25:00`
- `company_name` should be the same as in input CSV.  
    
[X] Check match output
- Add functionality to check if found match was already added to the output csv. 
- This functionality should check current match URL witht the URLs in the `match_position_url` column. Most URLs are unique and and can be used as a unique identifier.
- If the found match URL is not present in the CSV, it should upended in a new row, and fields `company_name, match_position_url, time_found,` should be filled out. 
    - for this scenario console output shuld be changed to:
        ```txt
        🔎  Scanning : Amount - https://job-boards.greenhouse.io/amount/
        ✅  Match for: [Automation Engineer] https://job-boards.greenhouse.io/amount/jobs/5058090007
        🟢 added to output file
        ```
    - If the found URL already in the output file, than app should skipp adding it and write in the console output:
        ```txt
        🔎  Scanning : Amount - https://job-boards.greenhouse.io/amount/
        🟡  No new matches found
        ```

[] Slack notification for the new 
- Add functionality to send a Slack message if the new maches were found
- Store webhook in the `.env` file under `SLACK_WEBHOOK`
- When new match found it should be posted to the salck in this format:
```txt
🥳 New match found: [company_name] - [title]
[match_position_url]
```

[] Add schaduler
    - Add shcaduler functionality to run the app on the schadule. 
    - `config.json` should keep the time when schadule will run. There should be option to set multipel times.
    - Set schaduler to run at `8:08`, `13:13`, and `18:18`.
