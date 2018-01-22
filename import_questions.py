import pandas as pd
import psycopg2
import urllib.request


class Indexed:
    def _get_index(self):
        return(self.__index)
    def _set_index(self, index):
        self.__index = int(index)
    index = property(_get_index, _set_index)


class Agent(Indexed):
    """Agent object for postgres DB."""
    def __init__(
        self,
        agent_name,
        sort_name=None,
        URL=None,
        description=None
    ):
        self.agent_name = agent_name
        self.sort_name = sort_name if sort_name else agent_name
        self.URL = URL if isinstance(URL, str) else None
        self.description = description if isinstance(
            description,
            str
        ) else None


class Instruction:
    """Instruction object for postgres DB."""
    def __init__(
        self,
        text_instruction=None,
        audio_instruction=None,
        image_instruction=None
    ):
        self.text_instruction = text_instruction
        self.audio_instruction = audio_instruction
        self.image_instruction = image_instruction


class Question(Indexed):
    """Question object for postgres DB."""
    def __init__(
        self,
        variable_name,
        activity_type,
        instruction,
        cursor
    ):
        self.variable_name = variable_name
        self.activity_type = lookup_key(
            cursor,
            table="activity_type",
            column="activity_type",
            value=activity_type,
            insert_command="INSERT INTO activity_type (activity_type)\n"
            "\tVALUES (\'{0}\');\n\n".format(
                activity_type
            )
        )
        self.instruction = instruction


class QuestionGroup(Indexed):
    """Question Group object for postgres DB."""
    def __init__(
        self,
        group_name,
        sort_name=None,
        instruction=None
    ):
        self.group_name = group_name
        self.sort_name = sort_name if sort_name else group_name
        self.instruction = instruction


class Questionnaire(Indexed):
    """Questionnaire object for postgres DB."""
    def __init__(
        self,
        questionnaire_name,
        sort_name
    ):
        self.questionnaire_name = questionnaire_name
        self.sort_name = sort_name if sort_name else questionnaire_name


class ResponseOption(Indexed):
    """Response Option object for postgres DB."""
    def __init__(
        self,
        option_type,
        option_text=None,
        option_audio=None,
        option_image=None,
        option_value=None
    ):
        self.option_type = option_type
        self.option_text = option_text
        self.option_audio = option_audio
        self.option_image = option_image
        self.option_value = option_value if option_value else option_text


class Rights(Indexed):
    """Rights object for postgres DB."""
    def __init__(
        self,
        long_name,
        short_name=None,
        URL=None,
        description=None
    ):
        self.long_name = long_name
        self.short_name = short_name if short_name else long_name
        self.URL = URL if isinstance(URL, str) else None
        self.description = description if isinstance(
            description,
            str
        ) else None


def connect_postgres(postgres_db, postgres_user, postgres_pass):
    """
    Function to connect to a specified postgres database

    Parameters
    ----------
    postgres_db: string
        name of postgres db

    postgres_user: string
        name of postgres user

    Returns
    -------
    cur: cursor
        cursor connected to postgres db

    conn: connection
        connection to postgres db (needed for closing)
    """
    conn = psycopg2.connect(
        "host=localhost dbname={0} user={1} password={2}".format(
            postgres_db,
            postgres_user,
            postgres_pass
        )
    )
    return(
        conn.cursor(),
        conn
    )


def define_values(value_list_string):
    """
    Parameter
    ---------
    value_list_strings: Series of strings

    Return
    ------
    value_dict: dictionary
        key:
            value_from_table: int

        value:
            value label: ResponseOption
    """
    value_dict = dict()
    value_list = value_list_string.split(
        "\n"
    ) if "\n" in value_list_string else value_list_string.split(
        ", "
    ) if ", " in value_list_string else value_list_string.split(
        ","
    )
    for value_string in value_list:
        v = value_string.split("=")
        value_key = v[0]
        try:
            value_keys = [vk.strip() for vk in value_key.split(",")]
        except:
            value_keys = [value_key]
        value_value = v[1].strip()
        for value_key in value_keys:
            value_dict[value_key] = value_value
    return(value_dict)


def disconnect_postgres(cur, conn, commit=True):
    """
    Function to disconnect from a specified connected postgres database

    Parameters
    ----------
    cur: cursor
        cursor connected to postgres db

    conn: connection
        connection to postgres db (needed for closing)

    commit: boolean, default True
        save changes?

    Returns
    -------
    None
    """
    conn.commit()
    cur.close()
    conn.close()


def generate_rights(cur, row):
    """
    Function to generate and execute queries to port intellectual property
    rights information from CSV tables to postgres db.

    Parameters
    ----------
    cur: cursor
        cursor connected to postgres db

    row: Series
        row[1] from DataFrame.iterrows()

    Returns
    -------
    None
    """
    # Read from spreadsheet
    rights = Rights(
        long_name=row["Rights Long"],
        short_name=row["Rights Short"],
        URL=row["Rights URL"],
        description=row["Rights Description"]
    )
    agent = Agent(
        agent_name = row["Rights Holder Name"],
        sort_name = row["Rights Holder Sort Name"],
        URL = row["Rights Holder URL"],
        description = row["Rights Holder Description"]
    )
    # Agent
    agent.index = lookup_key(
        cur,
        "agent",
        "sort_name",
        agent.sort_name,
        "INSERT INTO agent (name, sort_name, URL, description)\n"
        "\tVALUES (\'{0}\', \'{1}\', \'{2}\', \'{3}\');\n\n".format(
            agent.agent_name.replace("'", "''"),
            agent.sort_name.replace("'", "''"),
            str(agent.URL).replace("'", "''"),
            str(agent.description).replace("'", "''")
        ) if (
            agent.URL and agent.description
        ) else "INSERT INTO agent (name, sort_name, URL)\n"
        "\tVALUES (\'{0}\', \'{1}\', \'{2}\');\n\n".format(
            agent.agent_name.replace("'", "''"),
            agent.sort_name.replace("'", "''"),
            str(agent.URL).replace("'", "''")
        ) if (
            agent.URL
        ) else "INSERT INTO agent (name, sort_name, description)\n"
        "\tVALUES (\'{0}\', \'{1}\', \'{2}\');\n\n".format(
            agent.agent_name.replace("'", "''"),
            agent.sort_name.replace("'", "''"),
            str(agent.description).replace("'", "''")
        ) if (
            agent.description
        ) else "INSERT INTO agent (name, sort_name)\n"
        "\tVALUES (\'{0}\', \'{1}\');\n\n".format(
            agent.agent_name.replace("'", "''"),
            agent.sort_name.replace("'", "''")
        )
    )
    # Rights
    rights.index = lookup_key(
        cur,
        "rights",
        "short_name",
        rights.short_name,
        "INSERT INTO rights (name, short_name, URL, description)\n"
        "\tVALUES (\'{0}\', \'{1}\', \'{2}\', \'{3}\');\n\n".format(
            rights.long_name.replace("'", "''"),
            rights.short_name.replace("'", "''"),
            str(rights.URL).replace("'", "''"),
            str(rights.description).replace("'", "''")
        ) if (
            rights.URL and rights.description
        ) else "INSERT INTO rights (name, short_name, URL)\n"
        "\tVALUES (\'{0}\', \'{1}\', \'{2}\');\n\n".format(
            rights.long_name.replace("'", "''"),
            rights.short_name.replace("'", "''"),
            str(rights.URL).replace("'", "''")
        ) if (
            rights.URL
        ) else "INSERT INTO rights (name, short_name, description)\n"
        "\tVALUES (\'{0}\', \'{1}\', \'{2}\');\n\n".format(
            rights.long_name.replace("'", "''"),
            rights.short_name.replace("'", "''"),
            str(rights.description).replace("'", "''")
        ) if (
            rights.description
        ) else "INSERT INTO rights (name, short_name)\n"
        "\tVALUES (\'{0}\', \'{1}\');\n\n".format(
            rights.long_name.replace("'", "''"),
            rights.short_name.replace("'", "''")
        )
    )
    # Rights Holder
    lookup_key(
        cur,
        "rights_holder",
        [
            "entity",
            "entity_index",
            "rights_index",
            "rights_holder"
        ],
        [
             row["Entity Table"],
             lookup_key(
                 cur,
                 row["Entity Table"],
                 row["Entity Column"],
                 row["Entity"]
             ),
             rights.index,
             agent.index
        ],
        key_column=[
            "entity",
            "entity_index",
            "rights_index",
            "rights_holder"
        ],
        insert_command="INSERT INTO rights_holder "
        "(entity, entity_index, rights_index, rights_holder)\n"
        "\tVALUES (\'{0}\', {1}, {2}, {3});\n\n".format(
            row["Entity Table"],
            lookup_key(
                cur,
                row["Entity Table"],
                row["Entity Column"],
                row["Entity"]
            ),
            rights.index,
            agent.index
        )
    )
    return


def generate_sql(cur, row):
    """
    Function to generate and execute queries to port questionnaires from
    CSV tables to postgres db.

    Parameters
    ----------
    cur: cursor
        cursor connected to postgres db

    row: Series
        row[1] from DataFrame.iterrows()

    Returns
    -------
    None
    """
    # Setup variables
    has_options = ["Choice", "Multiple"]
    # Read from spreadsheet
    questionnaire = Questionnaire(
        row["Questionnaire"].strip(),
        row["Questionnaire Sort Name"].strip()
    ) if row["Questionnaire Sort Name"] else Questionnaire(
        row["Questionnaire"].strip()
    )
    question_group = QuestionGroup(
        row["Question Group"][:80],
        sort_name=": ".join([
            questionnaire.sort_name,
            row["Question Group"].strip()
        ])[:80],
        instruction=str(row["Question Group Instruction"]).strip()
    ) if row["Question Group Instruction"] else QuestionGroup(
        str(row["Question Group"]).strip()
    )
    question = Question(
        variable_name=row["Variable Name"].strip(),
        activity_type=row["Activity Type"].strip(),
        instruction=row["Question"].strip(),
        cursor=cur
    )
    responses = define_values(
        row["Value Labels"].strip()
    ) if row["Activity Type"] in has_options else None
    vrange = row["Values"].split("-") if isinstance(
        row["Values"],
        str
    ) else None
    if vrange:
        for v in range(
            int(vrange[0]),
            int(vrange[1])
        ):
            if str(v) not in responses:
                responses[str(v)] = v
    # Questionnaire
    questionnaire.index = lookup_key(
        cur,
        "questionnaire",
        "name",
        questionnaire.questionnaire_name,
        "INSERT INTO questionnaire (name, sort_name)\n"
        "\tVALUES (\'{0}\', \'{1}\');\n\n".format(
            questionnaire.questionnaire_name.replace("'", "''"),
            questionnaire.sort_name.replace("'", "''")
        )
    )
    # Question Group
    question_group.index = lookup_key(
        cur,
        "question_group",
        "qg_sort",
        question_group.sort_name,
        "INSERT INTO question_group (qg_name, qg_sort, qg_text)\n"
        "\tVALUES (\'{0}\', \'{1}\', \'{2}\');\n\n".format(
            question_group.group_name.replace("'", "''"),
            question_group.sort_name.replace("'", "''"),
            str(question_group.instruction).replace("'", "''")
        )
    )
    # Question
    question.index = lookup_key(
        cur,
        "question",
        "variable_name",
        question.variable_name,
        "INSERT INTO question (activity_type, variable_name, q_text)\n"
        "\tVALUES ({0}, \'{1}\', \'{2}\');\n\n".format(
            question.activity_type,
            question.variable_name.replace("'", "''"),
            question.instruction.replace("'", "''")
        )
    )
    # Question Response Sequence
    if row["Activity Type"] in has_options:
        response_number = 1
        for response in responses:
            response_option = ResponseOption(
                option_type=0,
                option_text=responses[response],
                option_value=response
            )
            response_option.index = lookup_key(
                cur,
                "response_option",
                [
                    "option_text",
                    "option_value"
                ],
                [
                    response_option.option_text,
                    response_option.option_value
                ],
                "INSERT INTO response_option (option_text, option_value)\n"
                "\tVALUES\n\t(\'{0}\', {1});\n\n".format(
                    str(response_option.option_text).replace("'", "''"),
                    str(response_option.option_value).replace("'", "''")
                )
            )
            lookup_key(
                cur,
                "question_response_sequence",
                [
                    "question",
                    "option_number"
                ],
                [
                    question.index,
                    response_number
                ],
                key_column=[
                    "question",
                    "option_number"
                ],
                insert_command="INSERT INTO question_response_sequence "
                "(question, option_number, option)\n\tVALUES\n"
                "\t({0}, {1}, {2});\n\n".format(
                    question.index,
                    response_number,
                    response_option.index
                )
            )
            response_number = response_number + 1
    # Question Group Questions Sequence
    lookup_key(
        cur,
        "question_group_question",
        [
            "qg",
            "qsn"
        ],
        [
            question_group.index,
            int(row["Question Sequence"])
        ],
        key_column=[
           "qg",
           "qsn"
        ],
        insert_command="INSERT INTO question_group_question "
        "(qg, qsn, question)\n\tVALUES\n"
        "\t({0}, {1}, {2});\n\n".format(
            question_group.index,
            int(row["Question Sequence"]),
            question.index
        )
    )
    # Questionnaire Question Group Sequence
    lookup_key(
        cur,
        "questionnaire_sequence",
        [
            "questionnaire",
            "qg_sequence"
        ],
        [
            questionnaire.index,
            row["Question Group Sequence"]
        ],
        key_column=[
            "questionnaire",
            "qg_sequence"
        ],
        insert_command="INSERT INTO questionnaire_sequence "
        "(questionnaire, qg_sequence, q_group)\n\tVALUES\n"
        "\t({0}, {1}, {2});\n\n".format(
            questionnaire.index,
            row["Question Group Sequence"],
            question_group.index
        )
    )
    return


def google_sheet(docid, gid=None):
    """
    Function to download and use shared Google Sheet

    Parameters
    ---------
    docid: str
        Google Sheet document identifier string

    gid: str
        Google Sheet sheet identifier string

    Returns
    -------
    sheet: csv file
        Google sheet downloaded as csv
    """
    return(urllib.request.urlopen(
        "https://docs.google.com/spreadsheets/d/{0}/export"
        "?format=csv{1}".format(
            docid,
            "&gid={0}".format(
                gid
            ) if gid else ""
        )
    ))


def lookup_key(
    cur,
    table,
    column,
    value,
    insert_command=None,
    key_column="key"
):
    """
    Function to lookup a key for a specified object.

    Parameters
    ----------
    cur: cursor
        cursor connected to postgres db

    table: str
        name of db table to lookup in

    column: str or list
        name(s) of table column(s) to lookup in

    value: str or list
        value(s) to lookup
        if a list, must be the same length as column or will search for each
        value in each column

    insert_command: SQL str
        command to insert missing entity into relevant table

    key_column: str or list, default "key"
        name of key column

    Returns
    -------
    key: str, int, float, list or None
        first result of lookup
    """
    insert_command = insert_command if insert_command else "INSERT INTO {0}\n"
    "\t({1})\n\tVALUES\n\t(\'{2}\');\n\n".format(
        table,
        column,
        value
    )
    key_column = ", ".join(
        key_column
    ) if isinstance(
        key_column,
        list
    ) else key_column
    if isinstance(column, list):
        if len(column) == len(value):
            parameters = " AND ".join([
                "{0}=\'{1}\'".format(
                    column[x],
                    str(value[x]).replace("'", "''")
                ) for x in range(
                    len(column)
                )
            ])
        else:
            parameters = " AND ".join([
                "{0}=\'{1}\'".format(
                    column[x],
                    value[y]
                ) for x in range(
                    len(column)
                ) for y in range(
                    len(value)
                )
            ])
    else:
        parameters = "{0}=\'{1}\'".format(
            column,
            str(value).replace("'", "''")
        )
    cur.execute(
        "SELECT {2} FROM\n"
        "\t{1}\n"
        "\tWHERE {0};\n\n".format(
            parameters,
            table,
            key_column
        )
    )
    key = cur.fetchone()
    if key:
        try:
            return(int(key[0]))
        except:
            return(key[0])
    else:
        print(insert_command)
        cur.execute(insert_command)
        return(lookup_key(
            cur,
            table,
            column,
            value,
            insert_command,
            key_column
        ))


def main():
    cur, conn = connect_postgres(
        "hbnqdb",
        "jclucas",
        "postgres"
    )
    sql_commands = list()
    for spreadsheet in [
        google_sheet(
            "1nT03l7oDWKcfA20x3R8zvtG1w2TvKmrwaD1s5uM9tPw",
            "1911345128"
        )
    ]:
        sheet = pd.read_csv(spreadsheet)
        for row in sheet.iterrows():
            generate_sql(
                cur,
                row[1]
            )
    for spreadsheet in [
        google_sheet(
            "1nT03l7oDWKcfA20x3R8zvtG1w2TvKmrwaD1s5uM9tPw",
            "444712839"
        )
    ]:
        sheet = pd.read_csv(spreadsheet)
        for row in sheet.iterrows():
            generate_rights(
                cur,
                row[1]
            )
    disconnect_postgres(cur, conn)


if __name__ == "__main__":
    main()
