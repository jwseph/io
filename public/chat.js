/// <reference path="./jquery.min.js" />
/// <reference path="./socket.io.min.js" />
$(()=>{

//#region JQuery Vars
const $window = $(window);
const $nicknameInput = $('.nicknameInput');
const $messageInput = $('.messageInput');
const $messages = $('.messages');
const $typing = $('.typing');
var $currentInput = $nicknameInput.focus();
//#endregion JQuery Vars


const randomHue = seed => {
  var hash = 7;
  for (let i = 0; i < seed.length; ++i)
    hash = (seed.charCodeAt(i)+(hash<<5)-(hash>>2))%47160;
  return hash%360;
}
const refreshnicknameInputColor = () => {
  const hue = randomHue($nicknameInput.text().trim().replace('\n', '')+(localStorage.seed || (localStorage.seed = btoa(Math.random().toString()).substring(10, 15))));
  $nicknameInput.attr('style', `color:hsl(${hue}, 100%, 40%); background:hsla(${hue}, 100%, 40%, 0.133); --placeholder-color:hsla(${hue}, 100%, 40%, 0.3)`);
  if ($nicknameInput.text().includes('\n')) {
    $nicknameInput.text() = $nicknameInput.text().replace('\n', '');
    submitNickname();
  }
}
refreshnicknameInputColor();
$nicknameInput.on('input', refreshnicknameInputColor);
$nicknameInput.on('keydown', function (e) {
  console.log(e);
  if (e.which == 13) {
    e.preventDefault();
    console.log('submit');
    submitNickname();
  }
});
$nicknameInput.on('paste', e => {
  e.preventDefault();
  const text = (e.originalEvent || e).clipboardData.getData('text/plain').replace('\n', '');
  document.execCommand('insertText', false, text.substring(0, 24-$nicknameInput.text().length));
  refreshnicknameInputColor();
});
const submitNickname = () => {
  nickname = $nicknameInput.text().trim().replace('\n', '');
  if (!$nicknameInput.prop('contenteditable') || nickname.length < 2) return;
  $nicknameInput.prop('contenteditable', false);
  setupSocket();
}




//#region Templates
const t$message = args =>
$('<li>')
  .addClass('message')
  .html(
    ' '+args.message
    .replace(/[&<>"'`=]/g, function(s) {return ENTITY_MAP[s]})
    .replace(/((http|https|ftp):\/\/[\w?=&.\/-;#~%-]+(?![\w\s?&.\/;#~%"=-]*>))/g, '<a href="$1" target="_blank" rel="nofollow noopener noreferrer">$1</a>')
  )
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
//#endregion Templates

const TYPING_DELAY = 400  // ms
const ENTITY_MAP = {'&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;', '`': '&#x60;', '=': '&#x3D;'};  // For escaping strings

let sid;  // Client ID
let color;
var typing;  // Bool
var lastTyping;  // Unix timestamp (ms)
var disconnected = false;

var users = {};   // (Obj) Data of users
const typingUsers = new Set();  // List of typing users
let socket;


const viewingNewMessages = () => ($messages[0].scrollHeight-$messages.scrollTop() <= 2*$messages.outerHeight());

const scrollToBottom = forceScroll => { if (viewingNewMessages() || forceScroll) $messages.scrollTop($messages[0].scrollHeight); };

const log = ($element, forceScroll) => {
  $messages.append($element);
  scrollToBottom(forceScroll);
}

const sendMessage = () => {
  var message = $messageInput.val();
  message = message.trim();
  if (message.length == 0) return;
  socket.emit('send message', {message: message});
  $messageInput.val('');
  log(t$message({message: message, user: {nickname: nickname, color: color}}), true);
}

const updateTyping = () => {
  if (!typing) {
    typing = true;
    socket.emit('start typing');
  }
  lastTyping = Date.now();
  setTimeout(() => {
    if (Date.now()-lastTyping >= TYPING_DELAY && typing) {  // User may have typed another key
      typing = false;
      socket.emit('stop typing');
    }
  }, TYPING_DELAY);
}

const updateTypingUsers = () => {
  const tua = [...typingUsers];  // typing users Array
  switch (typingUsers.size) {
    case 0:
      $typing.html('&nbsp');
      break;
    case 1:
      $typing
        .text(' is typing...')
        .prepend(t$nickname(users[tua[0]]))
      ;
      break;
    case 2:
      $typing
        .text(' and ')
        .prepend(t$nickname(users[tua[0]]))
        .append(t$nickname(users[tua[1]]))
        .append(' are typing...')
      ;
      break;
    case 3:
      $typing
        .text(' ')
        .prepend(t$nickname(users[tua[0]]))
        .append(t$nickname(users[tua[1]]))
        .append(' and ')
        .append(t$nickname(users[tua[1]]))
        .append(' are typing...')
      ;
      break;
    default:
      $typing.text('Several users are typing...');
      break;
  }
}


const autoFocus = e => {
  if (!(e.ctrlKey || e.metaKey || e.altKey)) {
    $currentInput.focus();
  }
  if (e.which == 13) {
    if (nickname) {
      sendMessage();
      typing = false;
      socket.emit('stop typing');
    } else {
      nickname = 'ANONYMOUS TEST';
    }
  }
}

$window.on('resize', scrollToBottom);

$window.on('keydown', autoFocus);
$('.login.page').on('click', autoFocus);

$messageInput.on('input', () => {
  updateTyping();
});

const setupSocket = () => {

  socket = io({path: '/chat/socket.io', query: `nickname=${encodeURIComponent(nickname)}&seed=${encodeURIComponent(localStorage.seed || (localStorage.seed = btoa(Math.random().toString()).substring(10, 15)))}`});
  $('.login.page').hide();
  $('.chat.page').show();

  socket.on('connect', () => {
    console.log('connected');
  });

  socket.on('login', (data) => {
    console.log('login')
    sid = data.sid;
    nickname = data.nickname;
    color = data.color;
    users = data.users;

    if (disconnected) {
      log(t$broadcast('Reconnected to server'));
      log(t$broadcastUser({message: 'joined', user: users[data.sid]}));
      disconnected = false;
    } else {
      $currentInput = $messageInput.prop('disabled', false).focus();
      log(t$broadcastUser({message: 'joined', user: users[data.sid]}));
      log(t$broadcast('Welcome to the chat!'));
    }
    log(t$broadcastUserList());
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

  socket.on('add user', (data) => {
    console.log('add user');
    users[data.sid] = data.user;
    log(t$broadcastUser({message: 'joined', user: users[data.sid]}));
    log(t$broadcastUserList());
  });

  socket.on('remove user', (data) => {
    console.log('remove user');
    log(t$broadcastUser({message: 'left', user: users[data.sid]}));
    delete users[data.sid];
    typingUsers.delete(data.sid);
    log(t$broadcastUserList());
    updateTypingUsers();
  });


  socket.on('new message', (data) => {
    console.log('received', data.message, 'from', data.sid);
    if (data.sid != sid) log(t$message({message: data.message, user: users[data.sid]}));
  });

  socket.on('start typing', (data) => {
    typingUsers.add(data.sid);
    updateTypingUsers();
  });

  socket.on('stop typing', (data) => {
    typingUsers.delete(data.sid);
    updateTypingUsers();
  });

}


});