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
      console.log(Papa.parse(files[i], {
      	complete: function(results) {
      		console.log("Finished:", results.data);
      	},
        header: true,
        skipEmptyLines: true,
      }));
    }

}, false);
