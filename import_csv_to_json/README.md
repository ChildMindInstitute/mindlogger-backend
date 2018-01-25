This project was bootstrapped with [Create React App](https://github.com/facebookincubator/create-react-app).

[Try it!](http://68.66.205.123:5000)

#### How to use this page
This webapp converts CSV files from [a templated format](https://docs.google.com/spreadsheets/d/1Jh0t6_TVLR59DZvZepSaxbb1E4ZHib3BzZVbHLZXTQc/export?gid=1911345128&format=csv) into a JSON format usable by AB2CD.

The fields in the spreadsheet are described here:

##### Questionnaire
Full, human-readable name of a questionnaire, eg `Physical Activity Questionnaire for Adolescents`.

##### Questionnaire Sort Name
Initialism, acronym or other standard abbreviation for questionnaire, eg `PAQ-A`.

##### Question Group Sequence
Integer indicating where in sequence the current question group belongs in the questionnaire, eg, `1` for the first question group.

##### Question Group
Name or description of the question group to which the current question belongs, eg `Physical activity in your spare time.`.

##### Question Group Instruction
Text instruction to precede each question in the current question group, to be given to a questionnaire-taker, eg `Physical activity in your spare time. Have you done any of the following activities in the past 7 days (last week)? If yes, how many times? (Mark only one circle per row)`

##### Question
Text instruction or question to be asked of a questionnaire-taker, eg `Skipping`.

##### Question Sequence
Integer indicating where in sequence the current question belongs in its question group, eg, `1` for the first question in a group.

##### Variable Name
Name or label for tracking a specific embedding of a question, eg `PAQ_A_01a`.

##### Activity Type
One of the following:

- `Choice`: the questionnaire-taker can choose one option from a given set.
- `Multiple`: the questionnaire-taker can choose zero or more options from a given set.
- `Text`: the questionnaire-taker enters free text.

##### Values
If `Activity Type` is `Choice` or `Multiple`, the range of values expected for the choices, eg `1-5`.

##### Value Labels
Within a single cell, values and labels connected with `=` and separated with newlines, eg
```
1=No

2=1-2

3=3-4

4=5-6

5=7 or more times
```

[Download CSV template here](https://docs.google.com/spreadsheets/d/1Jh0t6_TVLR59DZvZepSaxbb1E4ZHib3BzZVbHLZXTQc/export?gid=1911345128&format=csv).

Save your file(s) in CSV format.

#### What you get from this app
If your CSV adheres to [the template](https://docs.google.com/spreadsheets/d/1Jh0t6_TVLR59DZvZepSaxbb1E4ZHib3BzZVbHLZXTQc/export?gid=1911345128&format=csv), you'll get one JSON file per questionnaire. You can include one or more questionnaires in a CSV, and you can load one or more CSVs at a time into the app. Don't split a questionnaire across CSVs.
