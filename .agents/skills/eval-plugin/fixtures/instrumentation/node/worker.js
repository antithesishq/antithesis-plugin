const ms = require('ms');
let x = 1;
setInterval(() => {
  if (x % 3 === 0) x += 7; else if (x % 3 === 1) x *= 3; else x -= 1;
  x %= 100003;
}, ms('50ms'));
