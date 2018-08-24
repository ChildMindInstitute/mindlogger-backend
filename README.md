[![CircleCI](https://circleci.com/gh/ChildMindInstitute/mindlogger-app-backend/tree/mongo.svg?style=svg)](https://circleci.com/gh/ChildMindInstitute/mindlogger-app-backend/tree/mongo) [![Python coverage](.circleci/python-coverage.svg)](https://circleci.com/gh/ChildMindInstitute/mindlogger-app-backend/tree/mongo)
[![ReadTheDocs](https://readthedocs.org/projects/mindlogger-app-backend/badge/?version=mongo)](https://mindlogger-app-backend.readthedocs.io/en/girder-dev/?badge=mongo)

# App_ModularDataCollection_Backend
This backend serves as an administration console for customizing and storing data from the modular data collection app.

---
# Mindlogger Girder DB (Live Link)
[🔗 Mindlogger Girder Database](http://mindlogger-girder-atlas.a4vwd5q7ib.us-east-1.elasticbeanstalk.com)

---
# Girder Structure

## Collections

### Volumes

The **Volumes** Collection includes a Folder for each Mindlogger **Volume**.

#### [Volume].meta

##### consent

API string of this Volume's consent Activity in a JSON-LD object's "@id" or `null` if no consent Activity.

##### information

API string of this Volume's information Activity in a JSON-LD object's "@id" or `null` if no information Activity.

##### members

Object with "editors", "managers", "users", and "viewers" keys.

###### editors

Array of strings, Girder_ids of Editors of this Volume.

###### managers

Array of strings, Girder_ids of Managers of this Volume.

###### users

Array of strings, Girder_ids of Users of this Volume.

###### viewers

Array of objects: keys are Girder_ids of Viewers of this Volume; values are Arrays of Girder_ids of Users that the keyed Viewer has permissions to view.

##### shortName

Display name for this Volume in navbar.

#### Activities

Each [**Volume**].**Activities** Folder is organized into a Folder for each [**Activity**].

##### [Activity]

Each [**Volume**].**Activities**.[**Activity**] Folder contains an Item for each [**Version**] of that [**Activity**].

###### [Version]
Each **Activities**.[**Activity**].[**Version**] Folder contains JSON-LD metadata and Items for new Screens.

###### *meta.instructions*

API string of this Activity's instructions Activity in a JSON-LD object's "@id" or `null` if no instructions Activity.

###### *meta.shortName*

String abbreviation for this [**Activity**].[**Version**] (not necessarily unique).

###### *meta.schema:name*

JSON-LD object with optional **@language** and **@value** strings.

###### *meta.progressBar*

Boolean

###### *meta.respondent*

String (for now) indicating the intended respondent in relationship to the target individual (eg, "Self", "Parent", "Teacher", "Peer").

###### *meta.resume*

String

###### *meta.reverseNavigable*

Boolean

###### *meta.screens*

JSON-LD array (ordered) of **Screens** to display, in sequence, for this [**Activity**].[**Version**]. This sequence is the default order that will be presented if the **User** chooses "Skip" on every **Screen**.

###### __*@id*__

Each object in a **meta.screens** array contains an **@id** key with a string value that resolves to a Mindlogger **Screen** in the Girder API.

###### *meta.skippable*
Boolean

###### *meta.userDeleteable*
Boolean

###### *meta.userFontSize*
Boolean

###### *meta.userNotifications*
Object with the following keys:
    - `scheduleType`
		   Object with the following keys:
			    - `calendar`: Array
					- `monthly`: Array
					- `weekly`: Array
					- `userCanReset`: boolean
		- `timeOfDay`: Object with the following keys:
		    - `times`: Array of Objects with the following keys:
				    - `scheduled`: time
						- `random`: Object with `start` and `stop` times
				- `userCanReset`: boolean
		- `reminders`: Object with the following keys:
		    - `advanceNotification`: integer (minutes) or `null`
				- `reminderDays`: integer (days) or `null`
				- `userCanReset`: boolean

###### *meta.status*

String: "active" or "inactive".

###### *[Screen]*

Each [**Screen**] Item contains JSON-LD metadata, including **@context**, **schema:name**, **options**, **question_image**, **question_text**, **response_type** and any relevant media (images, audio, and/or video files).

###### *__meta.audio__*
Object with boolean `autoplay`, `play`, and `playbackIcon` keys and a `files` key with a value of an Array of strings, each of which resolves to an audio file URL through the Mindlogger Girder API.

###### *__meta.bgcolor__*
String, background color.

###### *__meta.maximumAttempts__*
Object with an integer `attempts` and boolean `enforce`.

###### *__meta.schema:name__*

JSON-LD object with optional **@language** and **@value** strings.

###### *__meta.options__*

JSON-LD array of objects (ordered).

###### - [option]

Each [**Screen**].**meta.options**.[**option**] contains a stimulus to be presented to the **User** (eg, an **optionText** object JSON-LD object with **@language** and **@value** strings) and a **value** string to be stored / used for scoring if that response **[option]** is chosen.

###### *__meta.pictureVideo__*
Object with boolean `autoplay`, `display`, and `playbackIcon` keys and a `files` key with a value of an Array of strings, each of which resolves to an Image or Video URL through the Mindlogger Girder API.

###### - @id
A string in the format "file/[girder_id]".

###### *__meta.questionText__*

JSON-LD object with optional **@language** and **@value** strings.

###### *__meta.responseDelay__*
Object with an integer `seconds` and boolean `delay`.

###### *__meta.responseType__*

String.

###### *__meta.rows__*

Array of Objects. rows[0] contains header info; each subsequent Object is a table row.

###### *__meta.select__*
Object with an integer `min` and integer `max` (if a selection-response screen).

###### *__meta.skippable__*
Boolean

###### *__meta.sliderBar__*
Object with the following keys:
    - `orientation`
	      "vertical" or "horizontal"
	  - `increments`
	      "discrete" or "smooth"
	  - `tickmarks`
	      Array of Objects with the following keys:
				  - `label`
					- `nextScreen`
	  - `between` (if `increments`=="smooth")
	      Array of Objects with `nextScreen` keys.


###### *__meta.textEntryBox__*
Object with a boolean `display` and JSON-LD Object `textAbove`.

###### *__meta.timer__*
Object with boolean `display`, `hideNavigation`, and `timer` keys and an integer `seconds`.

## Users

**User** objects contain [**Volume**] Folders.

### [Volume]

[**Volume**] Folders contain **Schedules** Folders [of **Activities**] and **Responses** Folders [of that User's previously completed **Activities**].

#### Responses

[**User**].[**Volume**].**Responses** Folders each contain a Folder for each **Activity** the parent **User** has completed in that **Volume**.

##### [Activity]

Each [**User**].[**Volume**].**Responses**.[**Activity**] Folder contains a Folder for each version of that **Activity** the **User** has completed.

###### [Version]
Each [**User**].[**Volume**].**Responses**.[**Activity**].[**Version**] Folder contains an Item for each **Completed Activity** instance for that relative (**User** + **Activity**.**Version**) combination.

###### *[Completed Activity]*
Each [**User**].[**Volume**].**Responses**.[**Activity**].[**Version**].**Completed Activity** Item contains JSON-LD metadata, including context, os, and responses.

#### Schedules

Each [**User**].[**Volume**].**Schedules** Folder contains a **Schedule** Item for each **Volume**.

##### [Schedule]

Each [**User**].[**Volume**].**Schedules**.[**Schedule**] contains JSON-LD metadata, including context and an array of **Activity** objects.

###### activities

Each object in a [**User**].[**Volume**].**Schedules**.[**Schedule**].activities array includes an **@id** and a **name**.

###### *@id*
A string in the format "item/[girder_id]"

###### *name*
A string to show in the **User**'s app for this **Schedule**.

## Groups

### Editors

**Editors** can create **Screens**, **Activities** and **Schedules**.

### Managers

**Managers** can assign **Viewers** and **Activities** to **Users**.

### Users

**Users** can perform **Activities** assigned to them by **Managers**.

### Viewers

**Viewers** can view data from **Users** as assigned by **Managers**.
