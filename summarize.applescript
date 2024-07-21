on run {input, parameters}
	set summaryCommand to "summarize"

	tell application "Path Finder" to activate
	delay 0.5 -- Give Path Finder time to become active

	tell application "System Events"
		tell process "Path Finder"
			click menu item "Unix" of menu 1 of menu item "Copy Path" of menu 1 of menu bar item "Edit" of menu bar 1
		end tell
	end tell

	delay 0.2

	-- Get the copied path from the clipboard
	set fullPath to (the clipboard as text)

	if fullPath starts with "file://" then
		set fullPath to text 7 thru -1 of fullPath
	end if

	if fullPath is "" then
		display dialog "Unable to get the current path from Path Finder." buttons {"OK"} default button "OK"
		return
	end if

	-- Check if the path ends with a file extension
	set isFile to fullPath contains "." and (offset of "." in (reverse of characters of fullPath as string)) ≤ 5

	-- Set the directory path
	if isFile then
		-- Extract only the directory path
		set AppleScript's text item delimiters to "/"
		set pathItems to text items of fullPath
		set directoryPath to (items 1 thru -2 of pathItems as text)
		set AppleScript's text item delimiters to "/"
	else
		-- Use the full path as it's already a directory
		set directoryPath to fullPath
	end if

	tell application "Terminal"
		activate
		do script "cd " & quoted form of directoryPath & " && " & summaryCommand & " && exit"
	end tell
end run