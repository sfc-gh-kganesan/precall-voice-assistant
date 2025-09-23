-- initialize invoicestore sqlite database
-- database: invoicestore

create table if not exists submission (
    id integer primary key,
    created_at datetime default current_timestamp,
    lift_ticket text,
    file_ids text check (json_valid(file_ids)),
    status text not null
);

