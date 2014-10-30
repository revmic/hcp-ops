drop table if exists restrictedaccess;
create table restrictedaccess (
    id integer primary key autoincrement,
    firstname text not null,
    lastname text not null,
    email text not null,
    login text not null,
    other_accounts boolean,
    email_matches text,
    status text,
    status_updated datetime,
    notes text
);

drop table if exists access_stats;
create table access_stats (
    id integer primary key autoincrement,
    shortname text not null,
    longname text,
    count integer,
    last_updated datetime
);
