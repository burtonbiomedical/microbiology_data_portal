//DEPENDENCIES
const express = require('express');
const exphbs = require('express-handlebars');
const mongoose = require('mongoose');
const bodyParser = require('body-parser');
const flash = require('connect-flash');
const session = require('express-session');
const passport = require('passport');
const path = require('path');
const db = require('./config/database')

//Express app init
const app = express();

//SETUP MONGOOSE
mongoose.Promise = global.Promise;
mongoose.connect(db.mongoURL, {
  useMongoClient: true
})
  .then(() => console.log('MongoDB connected...'))
  .catch(err => console.log(err));

//MIDDLEWARE
app.engine('handlebars', exphbs({
  defaultLayout: 'main'
}));
app.set('view engine', 'handlebars');

app.use(bodyParser.urlencoded({encoded: false}));
app.use(bodyParser.json());

app.use(session({
  secret: 'secret',
  resave: true,
  saveUninitialized: true
}));
app.use(flash());

app.use(passport.initialize());
app.use(passport.session());

//Set static folder
app.use(express.static(path.join(__dirname, 'public')));
app.use(express.static(path.join(__dirname, 'user_data')));

//GLOBAL VARS
app.use(function(request, response, next){
  response.locals.success_msg = request.flash('success_msg');
  response.locals.error_msg = request.flash('error_msg');
  response.locals.error = request.flash('error');
  response.locals.user = request.user || null;
  next();
});

//ROUTES
//Index
app.get('/', (request, response) => {
  response.render('index');
})

//Vitek
const vitek = require('./routes/vitek');
app.use('/vitek', vitek);
//User
const users = require('./routes/users');
app.use('/users', users);
//About
app.get('/about', (request, response) => {
  response.send('UNDER DEV');
});


require('./config/passport')(passport);
//SET PORT
const port = process.env.PORT || 8080;
//LISTEN METHOD
app.listen(port, () => {
  console.log(`Server started on port ${port}`)
});