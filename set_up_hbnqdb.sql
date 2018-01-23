CREATE TABLE activity_type (
    key            SERIAL PRIMARY KEY,
    activity_type  VARCHAR(80)
);

CREATE TABLE agent (
    key            BIGSERIAL PRIMARY KEY,
    name           TEXT,
    sort_name      TEXT,
    URL            TEXT,
    description    TEXT
);

CREATE TABLE instruction_type (
    key            SERIAL PRIMARY KEY,
    type           VARCHAR(80)
);

CREATE TABLE instruction (
    key            BIGSERIAL PRIMARY KEY,
    type           INT REFERENCES instruction_type(key),
    language       VARCHAR(8),
    content        TEXT
);

CREATE TABLE question (
    key            BIGSERIAL PRIMARY KEY,
    activity_type  INT,
    variable_name  VARCHAR(32)
);

CREATE TABLE question_instruction (
    question       BIGINT REFERENCES question(key),
    instruction    BIGINT REFERENCES instruction(key),
    PRIMARY KEY(question, instruction)
);

CREATE TABLE question_group (
    key            BIGSERIAL PRIMARY KEY,
    qg_name        VARCHAR(80),
    qg_sort        VARCHAR(80)
);

CREATE TABLE question_group_instruction (
    qg             BIGINT REFERENCES question_group(key),
    instruction    BIGINT REFERENCES instruction(key),
    PRIMARY KEY(qg, instruction)
);

CREATE TABLE question_group_question (
    qg             BIGINT REFERENCES question_group(key),
    qsn            INT, -- question sequence number
    question       BIGINT REFERENCES question(key),
    dependency     TEXT,
    PRIMARY KEY(qg, qsn)
);

CREATE TABLE questionnaire (
    key            BIGSERIAL PRIMARY KEY,
    name           TEXT,
    sort_name      TEXT
);

CREATE TABLE questionnaire_sequence (
    questionnaire  BIGINT REFERENCES questionnaire(key),
    qg_sequence    INT,
    q_group        BIGINT REFERENCES question_group(key),
    dependency     TEXT,
    PRIMARY KEY(questionnaire, qg_sequence)
);

CREATE TABLE response_option (
    key            BIGSERIAL PRIMARY KEY,
    response_type  INT,
    option_value   TEXT
);

CREATE TABLE response_option_instruction (
    option         BIGINT REFERENCES response_option(key),
    instruction    BIGINT REFERENCES instruction(key),
    PRIMARY KEY(option, instruction)
);

CREATE TABLE question_response_sequence (
    question       BIGINT REFERENCES question(key),
    option_number  INT,
    option         BIGINT REFERENCES response_option(key),
    dependency     TEXT,
    PRIMARY KEY(question, option_number)
);

CREATE TABLE response_type (
    key            SERIAL PRIMARY KEY,
    response_type  TEXT
);

CREATE TABLE rights (
    key             BIGSERIAL PRIMARY KEY,
    name            TEXT,
    short_name      VARCHAR(80),
    URL             TEXT,
    description     TEXT
);

CREATE TABLE rights_holder (
    entity         VARCHAR(80),
    entity_index   BIGINT,
    rights_index   BIGINT,
    rights_holder  BIGINT,
    PRIMARY KEY(entity, entity_index, rights_index, rights_holder)
);
