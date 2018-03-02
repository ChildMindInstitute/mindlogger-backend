import AWS from 'aws-sdk';
import multer from 'multer';
import path from 'path';
import multerS3 from 'multer-s3';
import config from '../config';

// credentials saved in ~/.aws/credentials
// [MindloggerAdmin]
// aws_access_key_id = **KEY ID**
// aws_secret_access_key = **SECRET KEY**
var credentials = new AWS.SharedIniFileCredentials({profile: 'default'});
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

const audioBucket = 'cmi-dataapp'


// Create image if not exists with verbose callback
export function newImage(path, image) {
  return new Promise((resolve, reject) => {
    var imageParams = bucketParams;
    imageParams.Key = path;   // path/to/image in S3 bucket
    imageParams.Body = image; // binary
    checkPath(imageParams.Key, function(exists){
      if (exists) {
        reject(new Error(path + " already exists!"));
      } else {
        s3.putObject(imageParams, function(err, data) {
          if (err) 
            reject(err); // an error occurred
          else     {                        // successful response
            resolve(data);
          }
        });
      }
    });
  });
}


// Create folder if not exists with verbose callback
export function newFolder(folder) {
  return new Promise((resolve, reject) => {
    var folderParams = bucketParams;
    folderParams.Key = folder + "/";
    checkPath(folderParams.Key, function(exists){
      if (exists) {
        reject(new Error(folder + " already exists!"));
      } else {
        s3.putObject(folderParams, function(err, data) {
          if (err) 
            reject(err); // an error occurred
          else {                        // successful response
            resolve(data)
          };
        });
      }
    });
  })
  
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

export function listPath(path) {
  return new Promise((resolve, reject) => {
    var pathParams = new Object;
    pathParams.Bucket = bucketParams.Bucket;
    pathParams.Prefix = path
    var pathInBucket = false;
    return s3.listObjects(pathParams, function(err, data) {
      if (err) {
        console.log(err, err.stack); // an error occurred
        reject(err)
      } else {                           // successful response
        var listContents = data.Contents;
        console.log(listContents)
        resolve(listContents)
      };
      //inBucket(pathInBucket);
    });
  })
}

export function uploadImage() {
  let storage = multerS3({
    s3: s3,
    bucket: bucketParams.Bucket,
    metadata: function(req,file,cb) {
      cb(null, {fieldName: file.fieldname});
    },
    key: function(req,file, callback) {
      callback(null,`${req.bodyData.path}${req.bodyData.filename+path.extname(file.originalname).toLowerCase()}`);
    }
  });
  return multer({
    storage,
    limits: {
    fieldSize: 1000000
    }
  });
}

export function uploadAudio() {
  let storage = multerS3({
    s3: s3,
    bucket: audioBucket,
    metadata: function(req,file,cb) {
      cb(null, {fieldName: file.fieldname});
    },
    key: function(req,file, callback) {
      callback(null,`${req.bodyData.path}${req.bodyData.filename+path.extname(file.originalname).toLowerCase()}`);
    }
  });
  return multer({
    storage,
    limits: {
    fieldSize: 1000000
    }
  });
}