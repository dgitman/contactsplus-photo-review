on run argv
    if (count argv) is not 6 then error "Required: contact ID, TIFF path, backup path, first name, last name, email"
    set targetID to item 1 of argv
    set photoPath to item 2 of argv
    set backupPath to item 3 of argv
    set photoData to read POSIX file photoPath as TIFF picture
    tell application "Contacts"
        set matches to every person whose id is targetID
        if (count matches) is not 1 then error "Expected exactly one contact"
        set p to item 1 of matches
        if first name of p is not (item 4 of argv) or last name of p is not (item 5 of argv) then error "Name mismatch"
        if (item 6 of argv) is not in (value of every email of p) then error "Email mismatch"
        if image of p is not missing value then error "Existing photo; refusing replacement"
        set originalNote to note of p
        set originalCard to vcard of p
    end tell
    set backupFile to open for access POSIX file backupPath with write permission
    try
        set eof backupFile to 0
        write originalCard to backupFile as «class utf8»
        close access backupFile
    on error errorText number errorNumber
        close access backupFile
        error errorText number errorNumber
    end try
    tell application "Contacts"
        set image of p to photoData
        save
        if note of p is not originalNote then error "Note verification failed"
        if image of p is missing value then error "Photo verification failed"
        return "Photo saved; note unchanged"
    end tell
end run
