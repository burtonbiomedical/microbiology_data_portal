const mongoose = require('mongoose');
const {Schema} = mongoose;

const UserSchema = new Schema({
  email: {
    type: String,
    required: true
  },
  firstName: {
    type: String,
    required: true
  },
  lastName: {
    type: String,
    requires: true
  },
  admin: {
    type: Boolean,
    required: true
  },
  date:{
    type: Date,
    default: Date.now
  }
});

mongoose.model('users', UserSchema);