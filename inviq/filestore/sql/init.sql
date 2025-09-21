-- initialize filestore sqlite database
-- database: filestore

create table if not exists file (
    id text primary key,
    created_at datetime default current_timestamp,
    sha256 text not null,
    path text not null,
    namespace text not null
);

-- create indexes for better query performance
create index if not exists idx_files_sha256 on file(sha256);
create index if not exists idx_files_namespace on file(namespace);
create index if not exists idx_files_created_at on file(created_at);