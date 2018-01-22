CREATE TABLE activity_type (
    key            serial primary key,
    activity_type  varchar(80)
);

CREATE TABLE agent (
    key            bigserial primary key,
    name           text,
    sort_name      text,
    URL            text,
    description    text
);

CREATE TABLE question (
    key            bigserial primary key,
    activity_type  int,
    variable_name  varchar(32),
    q_text         text,
    q_audio        bytea,
    q_image        bytea
);

CREATE TABLE question_group (
    key            bigserial primary key,
    qg_name        varchar(80),
    qg_sort        varchar(80),
    qg_text        text,
    qg_audio       bytea,
    qg_image       bytea
);

CREATE TABLE question_group_question (
    qg             bigint references question_group(key),
    qsn            int, -- question sequence number
    question       bigint references question(key),
    dependency     text
);

CREATE TABLE questionnaire (
    key            bigserial primary key,
    name           text,
    sort_name      text
);

CREATE TABLE questionnaire_sequence (
    questionnaire  bigint references questionnaire(key),
    qg_sequence    int,
    q_group        bigint references question_group(key),
    dependency     text
);

CREATE TABLE response_option (
    key            bigserial primary key,
    response_type  int,
    option_text    text,
    option_audio   bytea,
    option_image   bytea,
    option_value   text
);

CREATE TABLE question_response_sequence (
    question       bigint references question(key),
    option_number  int,
    option         bigint references response_option(key),
    dependency     text
);

CREATE TABLE response_type (
    key            int,
    response_type  text
);

CREATE TABLE rights (
    key             bigserial,
    name            text,
    short_name      varchar(80),
    URL             text,
    description     text
);

CREATE TABLE rights_holder (
    entity         varchar(80),
    entity_index   bigint,
    rights_index   bigint,
    rights_holder  bigint
);
