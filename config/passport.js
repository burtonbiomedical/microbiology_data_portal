//This is where we define our passport strategy
const LocalStrategy = require('passport-local').Strategy;
const mongoose = require('mongoose');
const bcrypt = require('bcryptjs');
const User = mongoose.model('users');

module.exports = function(passport){
  passport.use(new LocalStrategy({usernameField: 'email'}, (email, password, done) => {
    //Query user and check if exists
    User.findOne({email})
    .then(user => {
      if(!user){
        return done(null, false, {message: `No user ${email} found.`});
      };
      //Match password using bcrypt
      bcrypt.compare(password, user.password, (err, isMatch) => {
        if(err) throw err;
        if(isMatch){
          return done(null, user);
        } else {
          return done(null, false, {message: 'Incorrect password'})
        }
      })
    })
  }));

  /*When a user logs in, that users information is only transmitted once, and if the login is successful
  a session is established. The user information will be serialised and stored within a cookie in the users browser
  that identifies that particular session. So we need to define a serialise and deserialise function*/
  passport.serializeUser((user, done) => {
    done(null, user.id);
  });
  passport.deserializeUser((id, done) => {
    User.findById(id, (err, user) => {
      done(err, user);
    });
  });
};