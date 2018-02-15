//DEPENDENCIES
const express = require('express');
const exphbs = require('express-handlebars');
const mongoose = require('mongoose');
const bodyParser = require('body-parser');
const methodOverride = require('method-override');
const flash = require('connect-flash');
const session = require('express-session');
const passport = require('passport');
const path = require('path');

//Express app init
const app = express();

//MIDDLEWARE
app.engine('handlebars', exphbs({
  defaultLayout: 'main'
}));
app.set('view engine', 'handlebars');

app.use(bodyParser.urlencoded({encoded: false}));
app.use(bodyParser.json());

app.use(session({
  secret: 'secret',
  resave: false,
  saveUninitialized: true
}));
app.use(flash());

app.use(passport.initialize());
app.use(passport.session());
require('./config/passport')(passport);

//Set static folder
app.use(express.static(path.join(__dirname, 'public')));


//ROUTES
//Index
app.get('/', (request, response) => {
  const title = "Welcome"
  response.render('index', {
    title: title
  });
})
//About route
app.get('/about', (request, response) => {
  response.render("about");
});
//Vitek
const vitek = require('./routes/vitek');
app.use('/vitek', vitek);
//User
const users = require('./routes/users');
app.use('/users', users);

//SET PORT
const port = process.env.PORT || 8080;
//LISTEN METHOD
app.listen(port, () => {
  console.log(`Server started on port ${port}`)
});