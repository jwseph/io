/// <reference path="./jquery.min.js" />
/// <reference path="./socket.io.min.js" />

const TYPING_DELAY = 400  // ms


const $window = $(window);
const $messages = $('.messages');
const $inputMessage = $('.inputMessage');
var $currentInput = $inputMessage.focus();

// Templates
const t$message = args =>
$('<li>')
  .addClass('message')
  .text(' '+args.message)
  .prepend(t$nickname(args.user))
;
const t$nickname = user =>
$('<div>')
  .addClass('nickname')
  .text(user.nickname)
  .css({
    background: user.color+'22',
    color: user.color
  })
;
const t$broadcast = message =>
$('<li>')
  .addClass('broadcast')
  .text(message)
;
const t$broadcastUser = args =>
t$broadcast(' '+args.message)
  .prepend(t$nickname(args.user))
;
const t$broadcastUserList = () => {
  const $broadcast = t$broadcast(`Online users (${Object.keys(users).length}): `);
  Object.values(users).forEach(user => $broadcast.append(t$nickname(user)).append(' '));
  return $broadcast;
}


var nickname = prompt('Enter your name').trim();
const socket = io('wss://kamiak.herokuapp.com/', {query: `nickname=${nickname}&seed=${localStorage.seed || (localStorage.seed = btoa(Math.random().toString()).substring(10, 15))}`});
// const socket = io({query: `nickname=${nickname}&seed=${localStorage.seed || (localStorage.seed = btoa(Math.random().toString()).substring(10, 15))}`});


var sid;  // Client ID
var color;
var typing;  // Bool
var lastTyping;  // Unix timestamp (ms)
var disconnected = false;
var userListCountdown = -1;

var users = {};   // (Obj) Data of users
const typingUsers = new Set();  // List of typing users


const log = ($element, forceScroll) => {
  $messages.append($element);
  if ($messages[0].scrollHeight-$messages.scrollTop() <= 2*$messages.outerHeight() || forceScroll) {  // User has not scrolled up past page height
    $messages.scrollTop($messages[0].scrollHeight);
  }
}

const sendMessage = () => {
  var message = $inputMessage.val();
  socket.emit('send', {message: message});
  $inputMessage.val('');
  log(t$message({message: message, user: {nickname: nickname, color: color}}), true);
}

const updateTyping = () => {
  if (!typing) {
    typing = true;
    socket.emit('typing_start');
  }
  lastTyping = Date.now();
  setTimeout(() => {
    if (Date.now()-lastTyping >= TYPING_DELAY && typing) {  // User may have typed another key
      typing = false;
      socket.emit('typing_stop');
    }
  }, TYPING_DELAY);
}

const updateTypingUsers = () => {
  const tua = [...typingUsers];  // typing users array
  var message;
  switch (typingUsers.size) {
    case 0:
      message = 'No one is typing';
      break;
    case 1:
      message = `${users[tua[0]].nickname} is typing...`;
      break;
    case 2:
      message = `${users[tua[0]].nickname} and ${users[tua[1]].nickname} are typing...`;
      break;
    case 3:
      message = `${users[tua[0]].nickname}, ${users[tua[1]].nickname}, and ${users[tua[2]].nickname} are typing...`;
      break;
    default:
      message = 'Several users are typing...';
      break;
  }
  // log(message);
}


$window.keydown(event => {
  if (!(event.ctrlKey || event.metaKey || event.altKey)) {
    $currentInput.focus();
  }
  if (event.which === 13) {
    if (nickname) {
      sendMessage();
      typing = false;
      socket.emit('typing_stop');
    } else {
      nickname = 'ANONYMOUS TEST';
    }
  }
});

$inputMessage.on('input', () => {
  updateTyping();
});


socket.on('connect', () => {
  console.log('connected');
  // sid = socket.io.engine.id;
});

socket.on('data', (data) => {
  console.log('data')
  sid = data.sid;
  nickname = data.nickname;
  color = data.color;
  users = data.users;
});

socket.on('disconnect', () => {
  console.log('disconnected');
  if (!disconnected) {
    disconnected = true;
    log(t$broadcastUser({message: 'left', user: {nickname: nickname, color: color}}));
    log(t$broadcast('Connection lost. Trying to reconnect...'));
    typingUsers.clear();
    updateTypingUsers();
  }
});

socket.on('join', (data) => {
  console.log('join');
  users[data.sid] = data.user;
  if (disconnected) log(t$broadcast('Reconnected to server'));
  log(t$broadcastUser({message: 'joined', user: users[data.sid]}));
  if (!disconnected) log(t$broadcast('Welcome to the chat!'));
  else disconnected = false;
  if (data.sid === sid || --userListCountdown <= 0) {
    log(t$broadcastUserList());
    userListCountdown = 4;
  }
});

socket.on('leave', (data) => {
  console.log('leave');
  log(t$broadcastUser({message: 'left', user: users[data.sid]}));
  delete users[data.sid];
  if (--userListCountdown <= 0) {
    log(t$broadcastUserList());
    userListCountdown = 4;
  }
});


socket.on('receive', (data) => {
  console.log('received', data.message, 'from', data.sid);
  if (data.sid !== sid) log(t$message({message: data.message, user: users[data.sid]}));
  userListCountdown -= 0.02;
  if (userListCountdown <= 0) {
    log(t$broadcastUserList());
    userListCountdown = 4;
  }
});

socket.on('typing_start', (data) => {
  typingUsers.add(data.sid);
  updateTypingUsers();
});

socket.on('typing_stop', (data) => {
  if (!typingUsers.has(data.sid)) return;
  typingUsers.delete(data.sid);
  updateTypingUsers();
});