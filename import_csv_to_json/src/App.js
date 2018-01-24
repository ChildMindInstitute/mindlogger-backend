import React, { Component } from 'react';
import logo from './logo.svg';
import './App.css';
import Papa from 'papaparse';

class App extends Component {
  render() {
    return (
      <div className="App">
        <header className="App-header">
          <img src={logo} className="App-logo" alt="logo" />
          <h1 className="App-title">Welcome to React</h1>
        </header>
        <p className="App-intro">
          To get started, edit <code>src/App.js</code> and save to reload.
        </p>
      </div>
    );
  }
}

export default App;

var question_types = {
  "Choice": "single_sel",
  "Image": "image_sel",
  "Multiple": "multi_sel",
  "Text": "text",
};

function questionnaire_exists(questionnaire_array){
  return(this === questionnaire_array["title"]);
}

function questions_responses(test, question_title, question_types, file_json_array_i, response_json){
  return(
    test ? [
      {
        "title": question_title,
        "type": question_types[file_json_array_i["Activity Type"]],
        "rows": response_json,
        "variable name": file_json_array_i["Variable Name"],
      }
    ] : [
      {
        "title": question_title,
        "type": question_types[file_json_array_i["Activity Type"]],
        "variable name": file_json_array_i["Variable Name"],
      }
    ]
  )
}

function json_restructure(file_json_array) {
  var dbs_json = [];
  for (var i=0; i<file_json_array.length; i++){
    var questionnaire_title = file_json_array[i]["Questionnaire"] === file_json_array[i]["Questionnaire Sort Name"] ? file_json_array[i]["Questionnaire"] : file_json_array[i]["Questionnaire Sort Name"] + " (" + file_json_array[i]["Questionnaire"] + ")";
    var responses = [];
    if (file_json_array[i]["Activity Type"] !== "Text"){
      responses = file_json_array[i]["Value Labels"].split("\n");
      if (responses.length < 2){
        responses = file_json_array[i]["Value Labels"].split(",");
      };
      var response_json = [];
      for (var j=0; j<responses.length; j++){
        var response_value = responses[j].split("=");
        response_json.push(
          {
            "text": response_value[1].trim(),
            "value": response_value[0].trim(),
          }
        )
      }
    };
    var question_title = file_json_array[i]["Question"].trim();
    if (file_json_array[i]["Question Group Instruction"].trim().length > 0){
      question_title = file_json_array[i]["Question Group Instruction"].trim() + ": " + question_title;
    };
    var existing_questionnaire = dbs_json.find(questionnaire_exists, questionnaire_title);
    if (existing_questionnaire) {
      existing_questionnaire["questions"].push(questions_responses(responses.length, question_title, question_types, file_json_array[i], response_json));
      existing_questionnaire["updated_at"] = Date.now();
    } else {
      dbs_json.push(
        {
        "activity_type": "survey",
        "title": questionnaire_title,
        "date": Date.now(),
        "updated_at": Date.now(),
        "questions": questions_responses(responses.length, question_title, question_types, file_json_array[i], response_json),
        }
      );
    };
    //if file_json_array[i]);
  };
  return(dbs_json);
}

var control = document.getElementById("your-files-selector");
control.addEventListener("change", function(event) {

  // When the control has changed, there are new files

  var i = 0,
    files = control.files,
    len = files.length;

  for (; i < len; i++){
    console.log("Filename: " + files[i].name);
    console.log("Type: " + files[i].type);
    console.log("Size: " + files[i].size + " bytes");
    Papa.parse(files[i], {
    	complete: function(results) {
    		console.log(json_restructure(results.data));
    	},
      header: true,
      skipEmptyLines: true,
    });
  }

}, false);
