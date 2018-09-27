# Mindlogger Backend
This repository documents setup and management of Mindlogger's Girder API backend.

## Data concepts

### Structures

**Activities** are a series of interactive **screens** that **Users** perform according to a **notification schedule**. **Activities** are bundled in **Activity Sets**.

### Roles
These roles are defined at the **Activity Set** level.

#### Public
Anyone not logged in is **Public** can see things set to be publicly visible.

#### Owner
The creator of an **Activity Set** is that **Activity Set**'s initial **Owner**. Each **Activity Set** must have at least one **Owner**, and ownership is shareable, separable, and transferrable. **Owners** can assign and remove **Managers** to/from their **Activity Sets**.

#### Manager
**Manangers** can assign/remove **Editors**, **Managers**, and **Users** to/from **Activity Sets** and can assign **Viewers** and **Users** to one another within the **Activity Sets** they manage.

#### Editor
**Editors** can create and edit **Activities** and **Screens** within assigned **Activity Sets**.

#### User
**Users** can perform all **Activities** in each **Activity Set** to which they are assigned.

#### Viewer
**Viewers** can view the responses and scores from **Activities** completed by the **Users** assigned to them, as permitted per **Activity Set**.

## Data structure

Within Girder, data objects are `Collections`, `Groups`, and `Users` at the highest level. More thorough documentation and examples of the Girder structure vis-à-vis the web app interface can be found on the [admin panel wiki](https://github.com/ChildMindInstitute/mindlogger-app-admin-panel/wiki/Figma-Vis-%C3%A0-Vis-Girder)

### Collections

In the Collections, we only have the **Activity Sets** (currently named "[Volumes](http://mindlogger-girder-atlas.a4vwd5q7ib.us-east-1.elasticbeanstalk.com/#collection/5b634d590fc13a0df633b1c6)") Collection.

In the **Activity Sets** Collection, each **Activity Set** has its own Folder.

Each **Activity Set** Folder has the following metadata.

  - metadata (Object)
    - description (string): default=""
    - members (Object)
      - editors (string Array)
        - editors[] (string): User_id of each **Editor** for this **Activity Set**
      - managers (string Array)
        - managers[] (string): User_id of each **Manager** for this **Activity Set**
      - owners (string Array)
        - owners[] (string): User_id of each **Owner** for this **Activity Set**
      - users (string Array)
        - users[] (string): User_id of each **User** for this **Activity Set**
      - viewers (Object Array)
        - viewers[].key (string): User_id of each **Viewer** for this **Activity Set** || "group/{Group_id}" for a group of **Viewers** for this **Activity Set**
        - viewers[].value (string Array)
          - viewers[].value[] (string): User_id of each **User** for whom the **Viewer** keyed here has permission to see data for this **Activity Set** || "folder/{Activity Set_id}" to allow the keyed **Viewer** to view data for all **Users** of this **Activity Set**.
    - respondent (string): default="self"
    - shortName (string): default={Activity Set name}

Each **Activity Set** Folder also contains an **Activities** Folder. That **Activities** Folder contains a Folder for each **Activity** in that **Activity Set**. Each of these Folders contains a Folder for each Version of that **Activity** (for version control). The most recent Activity Version Folder is the only version that is currently accessible through Mindlogger's interfaces, though older versions are retained for reference and future features. Each most recent Activity Version Folder has the following metadata:

  - abbreviation (string): default={Activity name}
  - description (string): default=""
  - userNotifications (Object)
    - scheduleType (Object)
      - weekly (string Array): default=[]
        - weekly[]: "Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"
      - monthly (integer Array): default=[]
        - monthly[]: 1‒28
      - calendar (Date Array): default=[]
        - calendar[]: Date Objects (time portions ignored)
      -userCanReset (boolean): default=false
    - timeOfDay (Object Array)
      - times (Object Array)
        - times[].key (string): "scheduled" or "random"
        - times[]scheduled.value (string): time in "HH:MM AM/PM" format
        - times[]random".value (Object):
          - random.start (string): time in "HH:MM AM/PM" format
          - random.stop (string): time in "HH:MM AM/PM" format
      - userCanReset (boolean): default=false
    - reminders (Object)
      - advanceNotification (integer): number of minutes, default=null
      - reminderDays (integer): number of days, default=null
      - userCanReset (boolean): default=false
  - screens (Object Array): the default sequence of screens
    - screens[].@id (string): API IRI suffix

Each **Activity** Version Folder also contains an Item for each **Screen** that is accessible in that **Activity**. The `screens` metadata Array lists the default sequence (if the **User** skips every **Screen**, the order in which that **User** would see the **Screens**). Each other **Screen** should be referenced in a `nextScreen` property.

When a **User** performs an **Activtiy**, each **Screen** will be in one of 4 Arrays as that **User** progresses:

- Previously displayed
- Currently displayed
- Queued
- Extra

**Screens** can move between adjacent Arrays conditionally but never exist in more than one Array at a time. (For a lengthy discussion of the mechanism, see [#36](https://github.com/ChildMindInstitute/mindlogger-app-backend/issues/36) and [#68](https://github.com/ChildMindInstitute/mindlogger-app-backend/issues/68).)

### Users

- Each `User` object in Girder should have a `Responses` Folder.

- Within each User's `Responses` Folder should be an Activity Set Folder for each Activity Set to which that User is assigned. This folder should be created when a Manager assigns a User to an Activity in the admin panel, and the permissions (view rights to Users and Groups as assigned by Managers) should be updated according to changes Managers make in the admin panel.

- Within each Activity Set Folder should be an Item for each time a User has submitted an Activity.
  - The naming convention for these Items is `YYYY-MM-DD Activity Name`, eg, `2018-09-25 Medications`

- Each Response Item should include at least the following as a JSON Object in the Item's metadata field:
  - If the user was notified, and if so, when.
  - If the user was reminded, and if so, when.
  - When the user completed the Activity.
  - The IRI of the Activity Version completed.
  - Device details.
  - The text (URL for web version of non-text prompts and options) of each prompt and option as presented.
  - Each selected / entered response.
  - Any user-submitted media (images / audio) should be stored in the Item for which that file is a part of.
  - Any additional configuration/settings options (eg, timer) should also be noted in the response data.
  - For example, if I answered "N/A" to [EMA: Parent/Medications](http://mindlogger-girder-atlas.a4vwd5q7ib.us-east-1.elasticbeanstalk.com/#folder/5ba515810a76ac049becd555) just a few minutes ago on my iPhone SE, the following JSON Object should be saved to my `User/Responses/EMA: Parent` Folder in a `2018-09-25 Medications` Item's metadata Object:
    ```json
    {  
      "activity":{  
        "@id":"folder/5ba515810a76ac049becd555",
        "name":"Medications"
      },
      "devices:os":"devices:iOS",
      "devices:osversion":"iOS 12.0",
      "deviceModel":"MLME22L/A",
      "responses":[  
        {  
          "questionText":{  
            "@language":"en-US",
            "@value":"What daily medications does your child take (include name and dosage)?"
          },
          "response":{  
            "textEntry":"N/A"
          }
        }
      ],
      "notificationTime":null,
      "reminderTimes":[  

      ],
      "responseTime":1537910311217
    }
    ```

### Groups

Groups are used for 2 purposes: to associate **Activity Sets** with any number of **Organizations** for searchability and to group **Viewrs** to reduce overhead for **Managers** updating data view permissions to a group of **Viewers** en masse.

## Network Diagram
In the following diagram, the filled components represent our current setup. The unfilled components that share a lane with a component we are using are interchangeable alternatives.

![network diagram: endpoint, gateway, Girder, Mongo, storage](assets/img/network.png)
([Dia](http://live.gnome.org/Dia)-formatted diagram source file: [`assets/img/network.dia`](assets/img/network.dia))

## Mindlogger Girder DB Interactive Endpoint (Live Link)
[🔗 Mindlogger Girder Database](http://mindlogger-girder-atlas.a4vwd5q7ib.us-east-1.elasticbeanstalk.com)
