const express = require('express');
const router = express.Router();
const mongoose = require('mongoose');
const bcrypt = require('bcryptjs');
const passport = require('passport');

//Load User Model
require('../models/Users');
const User = mongoose.model('users');

//USER LOGIN ROUTE
router.get('/login', (request, response) => {
  response.render("users/login");
});

//USER REGISTER ROUTE
router.get('/request-access', (request, response) => {
  response.render("users/request-access");
});

//SET PASSWORD ROUTE
router.get('/register', (request, response) => {
  response.render("users/register");
});

//LOGIN POST REQUEST
router.post('/login', (request, response, next) => {
  passport.authenticate('local', {
    successRedirect: '/datasets',
    failureRedirect: '/users/login',
    failureFlash: true
  })(request, response, next);
});

//REGISTER REQUEST

router.post('/register', (request, response) => {
  let errors = [];
  //Password validation
  if(request.body.password != request.body.passwordConf){
    errors.push({text: 'Passwords do not match.'});
  };
  if(request.body.password.length < 8){
    errors.push({text: 'Passwords must be at least 8 chracters in length.'});
  };
  if (errors.length > 0){
    response.render('users/register', {
      errors: errors,
      name: request.body.name,
      email: request.body.email
    });
  } else {
    //Check if user exists
    User.findOne({email: request.body.email})
    .then(user => {
      if(user){
        request.flash('error_msg', "Email already registered");
        response.redirect('/users/register');
      } else {
        //Register new user
        var newUser = new User({
          name: request.body.name,
          email: request.body.email,
          password: request.body.password
        });
        //Encrypt password
        bcrypt.genSalt(10, (err, salt) =>{
          bcrypt.hash(newUser.password, salt, (err, hash) => {
            if (err) throw (err);
            newUser.password = hash;
            newUser.save()
            .then(user => {
              request.flash('success_msg', "You're now registered and can login");
              response.redirect('users/login');
            })
            .catch(err => {
              console.log(err);
              return;
            })
          })
        })
      }
    });

  }
});

router.get('/logout', (request, response) => {
  request.logout();
  request.flash('success_msg', "You have been logged out");
  response.render('users/login');
})

module.exports = router;