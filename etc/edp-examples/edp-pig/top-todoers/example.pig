input_lines = LOAD '$INPUT' AS (line:chararray);

-- filter out any lines that are not with TODO
todo_lines = FILTER input_lines BY line MATCHES '.*TODO\\s*\\(\\w+\\)+.*';
ids = FOREACH todo_lines GENERATE FLATTEN(REGEX_EXTRACT($0, '(.*)\\((.*)\\)(.*)', 2));

-- create a group for each word
id_groups = GROUP ids BY $0;

-- count the entries in each group
atc_count = FOREACH id_groups GENERATE COUNT(ids) AS count, group AS atc;

-- order the records by count
result = ORDER atc_count BY count DESC;
result = FOREACH result GENERATE count, CONCAT('https://launchpad.net/~', atc);

STORE result INTO '$OUTPUT' USING PigStorage();
