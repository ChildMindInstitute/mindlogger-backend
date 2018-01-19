import pandas as pd
import psycopg2


class Agent:
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
        self.URL = URL
        self.description = description


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


class Question:
    """Question object for postgres DB."""
    def __init__(
        self,
        activity_type,
        instruction
    ):
        self.activity_type = activity_type
        self.instruction = instruction


class QuestionGroup:
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


class Questionnaire:
    """Questionnaire object for postgres DB."""
    def __init__(
        self,
        questionnaire_name,
        sort_name
    ):
        self.questionnaire_name = questionnaire_name
        self.sort_name = sort_name if sort_name else questionnaire_name


class ResponseOption:
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


class Rights:
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
        self.URL = URL
        self.description = description


def add_question(
    q_group,
    q,
    sequence_no=None,
    dependency=None
):
    """

    Parameters
    ----------
    q_group: QuestionGroup

    q: Question

    sequence_no: int, optional

    dependency: string, optional

    Returns
    -------
    q_index: int
        index of question
    """
    pass


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


def generate_sql(cur, row):
    """
    Parameters
    ----------
    cur: cursor
        cursor connected to postgres db

    row: Series
        row[1] from DataFrame.iterrows()

    Returns
    -------
    sql_commands: list
        list of SQL strings
    """
    sql_commands = list()
    questionnaires = set()
    question_groups = set()
    questions = set()
    questionnaire = Questionnaire(
        row["Questionnaire"],
        row["Questionnaire Sort Name"]
    ) if row["Questionnaire Sort Name"] else Questionnaire(
        row["Questionnaire"]
    )
    question_group_sequence = row["Question Group Sequence"]
    question_group = QuestionGroup(
        row["Question Group"],
        instruction=row["Question Group Instruction"]
    ) if row["Question Group Instruction"] else QuestionGroup(
        row["Question Group"]
    )
    question_sequence = row["Question Sequence"]
    question = Question(
        row["Activity Type"],
        row["Question"]
    )
    responses = define_values(
        row["Value Labels"]
    ) if row["Activity Type"] in ["Choice", "Multiple"] else None
    vrange = row["Values"].split("-") if isinstance(
        row["Values"],
        str
    ) else None
    if vrange:
        for v in range(
            int(vrange[0]),
            int(vrange[1])
        ):
            if v not in responses:
                responses[v] = v
    questionnaire_index = lookup_key(
        cur,
        "questionnaire",
        "name",
        questionnaire.questionnaire_name
    )
    if not questionnaire_index:
        cur.execute(
            "INSERT INTO questionnaire\n"
            "\t(name, sort_name)\n"
            "\tVALUES\n"
            "\t(\'{0}\', \'{1}\');\n\n".format(
                questionnaire.questionnaire_name,
                questionnaire.sort_name
            )
        )
        questionnaire_index = lookup_key(
            cur,
            "questionnaire",
            "name",
            questionnaire.questionnaire_name
        )
    return([str(questionnaire_index)])


def lookup_key(cur, table, column, value, key_column="key"):
    """
    Function to lookup a key for a specified object.

    Parameters
    ----------
    cur: cursor
        cursor connected to postgres db

    table: str
        name of db table to lookup in

    column: str
        name of table column to lookup in

    value: str
        value to lookup

    key_column: str, default "key"
        name of key column

    Returns
    -------
    key: str, int, float or None
        first result of lookup
    """
    cur.execute(
        "SELECT {3} FROM\n"
        "\t{1}\n"
        "\tWHERE {2}='{0}'".format(
            value,
            table,
            column,
            key_column
        )
    )
    key = cur.fetchone()
    return(key[0] if key else None)

def main():
    cur, conn = connect_postgres(
        "hbnqdb",
        "jclucas",
        "postgres"
    )
    sql_commands = list()
    for spreadsheet in [
        "nonproprietary.csv"
    ]:
        sheet = pd.read_csv(spreadsheet)
        for row in sheet.iterrows():
            sql_commands = [
                *sql_commands,
                *generate_sql(
                    cur,
                    row[1]
                )
            ]
    print(
        ";\n\n".join(sql_commands),
        end=";\n\n")
    disconnect_postgres(cur, conn)


if __name__ == "__main__":
    main()
