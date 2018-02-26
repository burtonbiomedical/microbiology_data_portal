//THIS FILE CONTAINS ALL ROUTES RELATED TO THE CREATION AND MANAGEMENT OF IDEAS
const express = require('express');
const router = express.Router();
const MongoClient = require('mongodb').MongoClient;
const ObjectID = require('mongodb').ObjectId;
const db = require('../config/database');
const PythonShell = require('python-shell');
const spawn = require('child_process').spawn
const pythonFile = '/home/rossco/Documents/Data Science Portfolio/vitek_project/MIC Data Exploration Tools/MIC_Data_Exploration_Tools.py'
const fs = require('fs');

var options = {
  mode: 'text',
  pythonPath: '/usr/bin/python',
  pythonOptions: ['-u'],
  scriptPath: '/home/rossco/Documents/Data Science Portfolio/vitek_project/MIC Data Exploration Tools/',
  args: ''
}


//LOAD HELPER
const {ensureAuthenticated} = require('../helpers/auth');

router.get('/', (request, response) => {
  MongoClient.connect(db.mongoURL, (err, client) => {
    if (err) throw err;
    const db = client.db('vitekAlpha');
    db.collection('reference_data').find().toArray((err, docs) => {
      if (err) throw err;
      var orgs = docs[0]['organisms'];
      var drugs = docs[0]['drugs'];
      var compare = (a,b) => {
        if (a.name < b.name)
          return -1;
        if (a.name > b.name)
          return 1;
        return 0;
      };
      response.render('vitek',{orgs: orgs.sort(compare), drugs: drugs.sort(compare)});
    });
    client.close();
  });
});


router.post('/organism', (request, response) => {
  var startDate = request.body['start-date'];
  var endDate = request.body['end-date'];
  var bug = request.body.selectOrg;
  if (startDate && endDate){
    var args = [{
      'dbname': 'vitekAlpha',
      'start_date': startDate,
      'end_date': endDate,
      'userID': 'Testing',
      'bug':bug
    }];
  } else {
    var args = [{
      'dbname': 'vitekAlpha',
      'userID': 'Testing',
      'bug':bug
    }];
  };

  options.args = JSON.stringify(args);

  console.log(options)
  
  PythonShell.run('MIC_Data_Exploration_Tools.py', options, (err, results) => {
    if (err) throw err;

    MongoClient.connect(db.mongoURL, (err, client) => {
      if (err) throw err;
      const db = client.db('vitekAlpha');
      db.collection('reference_data').find().toArray((err, docs) => {
        if (err) throw err;
        var drugs = docs[0]['drugs'];
        var compare = (a,b) => {
          if (a.name < b.name)
            return -1;
          if (a.name > b.name)
            return 1;
          return 0;
        };
        var allDrugs = drugs.sort(compare);

        result_paths = JSON.parse(results[0])
        console.log(result_paths)
        response.render('search_results/organism', {
          result_paths: result_paths, 
          bug: bug, 
          start_date: startDate, 
          end_date: endDate, 
          userID:args['userID'],
          allDrugs: allDrugs
        });
      });
      client.close();
  })
});
});

router.post('/antibiotic', (request, response) => {
  if (request.body.start_date && request.body.end_date){
    var args = [{
      'dbname': 'vitekAlpha',
      'start_date': request.body.start_date,
      'end_date': request.body.end_date,
      'userID': 'Testing',
      'bug':request.body.bug,
      'antibiotic': request.body.selectDrug
    }];
  } else {
    var args = [{
      'dbname': 'vitekAlpha',
      'userID': 'Testing',
      'bug':request.body.bug,
      'antibiotic': request.body.selectDrug
    }];
  };
  options.args = JSON.stringify(args);
  PythonShell.run('MIC_Data_Exploration_Tools.py', options, (err, results) => {
    if (err) throw err;
    result = JSON.parse(results[0])
    console.log(result)
    // var stats;
    // fs.readFile(result.descriptive_stats, 'utf8', (err, data) => {
    //   if (err) throw err;
    //   stats = JSON.parse(data);
    // });
    // console.log(stats)
    response.render('search_results/antibiotic', {
      result: result, 
      bug: request.body.bug,
      drug: request.body.selectDrug,
      start_date: request.body.startDate, 
      end_date: request.body.endDate, 
      userID: args['userID']
    });
  });
  console.log(request.body)
});

router.get('/download/:userID', (req, res) => {
  console.log(req.params)
  //res.download(__dirname + '/user_data/');
  res.end();
});

module.exports = router;