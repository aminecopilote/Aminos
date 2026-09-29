const assert = require('assert'), { pickSkills, buildSystem, loadSkills } = require('./server');
const sk = loadSkills(); assert(sk.length > 100, 'skills not loaded: ' + sk.length);
assert(pickSkills('use humanizer to rewrite this text').some(s => s.name.includes('humanizer')), 'humanizer not matched');
const { system } = buildSystem('audit accessibility wcag of my react app', []); assert(system.includes('Active skills'));
console.log('OK', sk.length, 'skills');
process.exit(0);
