drop table if exists workflow;
create table workflow (
  id integer primary key,
  name text not null,
  mermaid text
);

drop table if exists execution;
create table execution (
  id integer primary key,
  start_ts text not null,
  end_ts text,
  status text not null
);
