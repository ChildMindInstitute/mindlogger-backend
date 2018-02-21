import AWS from 'aws-sdk';

// credentials saved in ~/.aws/credentials
// [MindloggerAdmin]
// aws_access_key_id = **KEY ID**
// aws_secret_access_key = **SECRET KEY**
var credentials = new AWS.SharedIniFileCredentials({profile: 'MindloggerAdmin'});
var s3config = new AWS.Config({
  credentials: credentials,
  region: 'us-east-1'
});
var s3 = new AWS.S3({});


// Create the parameters for calling createBucket
var bucketParams = {
   Bucket : 'mindloggerimages',    // S3 bucket name
   ServerSideEncryption: 'AES256'  // encryption
};


// Create image if not exists with verbose callback
function newImage(path, image, created) {
  var imageParams = bucketParams;
  imageParams.Key = path;   // path/to/image in S3 bucket
  imageParams.Body = image; // binary
  checkPath(imageParams.Key, function(exists){
    if (exists) {
      created(path + " already exists!");
    } else {
      s3.putObject(imageParams, function(err, data) {
        if (err) created(err, err.stack); // an error occurred
        else     {                        // successful response
          created(path + " created successfully!");
        };
      });
    }
  });
}


// Create folder if not exists with verbose callback
function newFolder(folder, created) {
  var folderParams = bucketParams;
  folderParams.Key = folder + "/";
  checkPath(folderParams.Key, function(exists){

    if (exists) {
      created(folder + " already exists!");
    } else {
      s3.putObject(folderParams, function(err, data) {
        if (err) created(err, err.stack); // an error occurred
        else     {                        // successful response
          created(folder + " created successfully!");
        };
      });
    }
  });
}


// Check if file or folder exists with Boolean callback
function checkPath(path, inBucket) {
  var pathParams = new Object;
  pathParams.Bucket = bucketParams.Bucket;
  var pathInBucket = false;
  s3.listObjects(pathParams, function(err, data) {
    if (err) console.log(err, err.stack); // an error occurred
    else {                                // successful response
      var listContents = data.Contents;
      var iLC = 0;
      for (iLC = 0; iLC < listContents.length; iLC++) {
        if(listContents[iLC].Key == path){
          pathInBucket = true;
        };
      }
    };
    inBucket(pathInBucket);
  });
}
