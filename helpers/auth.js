//THIS HELPER FUNCTION WILL CHECK FOR AUTHENTICATION ALLOWING ACCESS CONTROL FOR MY VIEWS
module.exports = {
  ensureAuthenticated: function(request, response, next){
    if(request.isAuthenticated()){
      //If isAuthenticated returns true, then we just want to call next(), so we just want to call the next function or next bit of middleware
      return next();
    } else {
      request.flash('error_msg', 'Not Authorised')
      response.redirect('/users/login');
    }
  }
}