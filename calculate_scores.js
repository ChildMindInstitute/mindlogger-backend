/**
 * Function to look up score label
 * @param {(Number|string)} score_value - value from scoring function
 * @param {Object} score_key_i - score key definitions with score-range or single-score keys and label values
 * @param {function(string)} score_label - a callback to run whose signature is a string, zero or more labels based on scores
 */
function score_label_lookup(score_value, score_key_i, score_label){
  label_for_score = ""
  for (var label_range in score_key_i.values){
    if label_range.includes("-"){
      var l_range = label_range.split("-");
      if (score_value >= Number(l_range[0]) && score_value <= Number(l_range[1])){
        if (label_for_score.length){
          label_for_score += (", " + score_key_i.values[label_range]);
        } else {
          label_for_score = score_key_i.values[label_range];
        }
      }
    } else {
      if(score_value == label_range){
        if (label_for_score.length){
          label_for_score += (", " + score_key_i.values[label_range]);
        } else {
          label_for_score = score_key_i.values[label_range];
        }
      }
    }
  }
  score_label(label_for_score);
}

/**
 * Function to calculate scores
 * @param {Object} score_key - Mindlogger-formatted score key JSON object
 * @param {Object} answers - Mindlogger-formatted activity response
 * @param {function(Object[])} score_results - a callback to run whose signature is an array of Objects with "value" and "label" keys
 * @param {(Number|string)} score_results[].value - score calculated from answers by method defined in score_key
 * @param {string} score_results[].label - label(s) for score as defined in score_key
 */
function calculate_score(score_key, answers, score_results){
  var score_i=0;
  var all_scores=new Array;
  for (score_i=0; score_i<score_key.scores.length; score_i++){
    eval(score_key.scores[score_i].formula);
    var final_score = new Number();
    eval(score_key.scores[score_i].short_label)(answers, function(final_score) {
      var score_value = final_score;
      score_label_lookup(score_value, score_key.scores[score_i], function(score_label) {
        score_results({"value": score_value, "label": score_label});
      });
    });
  }
}
