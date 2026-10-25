// Offline state/animation regression tests. This DOM stub does not test rendering.
const { test } = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');

const root = path.resolve(__dirname, '..');
const data = JSON.parse(fs.readFileSync(path.join(root, 'web/gua-matrix.json'), 'utf8'));
const template = fs.readFileSync(path.join(root, 'web/index.template.html'), 'utf8');

function site() {
  const elements = new Map();
  const timers = new Map();
  const animations = new Set();
  let timerId = 0;
  let guaIndex = 0;

  class Element {
    constructor(id) {
      this.id = id;
      this.hidden = false;
      this.disabled = false;
      this.style = {};
      this.dataset = {};
      this.children = [];
      this.listeners = {};
      this.textContent = '';
      const classes = new Set();
      this.classList = {
        add: (...names) => names.forEach(name => classes.add(name)),
        remove: (...names) => names.forEach(name => classes.delete(name)),
        contains: name => classes.has(name),
      };
    }
    set innerHTML(value) {
      this.html = value;
      this.children = [];
      // Result buttons are recreated by the real innerHTML assignment.
      for (const match of value.matchAll(/\bid="([^"]+)"/g)) {
        elements.set(match[1], new Element(match[1]));
      }
    }
    get innerHTML() { return this.html || ''; }
    appendChild(child) { this.children.push(child); }
    addEventListener(name, listener) {
      (this.listeners[name] ||= []).push(listener);
    }
    click() {
      if (this.disabled) return Promise.resolve();
      return Promise.all((this.listeners.click || []).map(listener => listener({})));
    }
    getBoundingClientRect() { return { left: 0, top: 0, width: 250, height: 110 }; }
    scrollIntoView() { this.scrollCount = (this.scrollCount || 0) + 1; }
    animate() {
      let finish;
      const finished = new Promise(resolve => { finish = resolve; });
      const animation = { finished, cancel() {}, finish };
      animations.add(animation);
      return animation;
    }
  }
  const get = id => {
    if (!elements.has(id)) elements.set(id, new Element(id));
    return elements.get(id);
  };
  const modeButtons = ['breakfast', 'all_day'].map(mode => {
    const button = new Element(mode);
    button.dataset.mode = mode;
    return button;
  });
  // Start with the same hidden sections as the document.
  for (const id of ['ritual', 'result', 'headMode', 'backHome']) get(id).hidden = true;
  const random = Object.create(Math);
  random.random = () => (guaIndex + 0.5) / data.gua.length;
  const context = {
    window: { scrollTo() {} },
    document: {
      getElementById: get,
      querySelectorAll: () => modeButtons,
      createElement: () => new Element(),
      body: get('body'),
    },
    navigator: {},
    matchMedia: () => ({ matches: false }),
    Math: random,
    Promise,
    setTimeout(callback) { const id = ++timerId; timers.set(id, callback); return id; },
    clearTimeout(id) { timers.delete(id); },
  };
  vm.createContext(context);
  const html = template.replace('/*__GUA_DATA__*/null', JSON.stringify(data));
  for (const match of html.matchAll(/<script>([\s\S]*?)<\/script>/g)) {
    vm.runInContext(match[1], context, { filename: 'index.template.html' });
  }

  const microtasks = async () => { for (let i = 0; i < 20; i++) await Promise.resolve(); };
  async function nextTimer() {
    const first = timers.entries().next().value;
    assert.ok(first, 'expected a pending timer');
    timers.delete(first[0]);
    first[1]();
    await microtasks();
  }
  async function finishAnimations() {
    for (const animation of animations) animation.finish();
    animations.clear();
    await microtasks();
  }
  async function settle() {
    for (let i = 0; i < 30; i++) {
      await microtasks();
      if (animations.size) await finishAnimations();
      else if (timers.size) await nextTimer();
      else return;
    }
    assert.fail('page did not settle');
  }
  return {
    get, nextTimer, finishAnimations, settle,
    setGua(index) { guaIndex = index; },
    choose(mode) { return modeButtons.find(button => button.dataset.mode === mode).click(); },
  };
}

for (const mode of ['breakfast', 'all_day']) {
  test(`${mode}: produces its own meal and restores button state`, async () => {
    const page = site();
    await page.choose(mode);
    const pending = page.get('cast').click();
    assert.equal(page.get('cast').disabled, true);
    await page.settle();
    await pending;
    assert.equal(page.get('result').hidden, false);
    assert.ok(page.get('result').innerHTML.includes(data.gua[0][mode].main));
    assert.equal(page.get('cast').disabled, false);
    assert.equal(page.get('guaName').textContent, `${data.gua[0].symbol}  ${data.gua[0].name}`);
  });
}

test('home during shake wait cancels the result without an async error', async () => {
  const page = site();
  await page.choose('breakfast');
  const pending = page.get('cast').click();
  await page.get('backHome').click();
  await page.settle();
  await pending;
  assert.equal(page.get('landing').hidden, false);
  assert.equal(page.get('ritual').hidden, true);
  assert.equal(page.get('result').hidden, true);
  assert.equal(page.get('guaName').textContent, '签未落');
  assert.equal(page.get('pieces').children.length, 0);
});

test('old draw animations cannot overwrite a newly selected meal', async () => {
  const page = site();
  await page.choose('breakfast');
  const oldCast = page.get('cast').click();
  await page.nextTimer(); // The initial shake completed; piece animations are pending.
  assert.equal(page.get('pieces').children.length, 3);
  await page.get('backHome').click();
  await page.choose('all_day');
  page.setGua(7);
  const newCast = page.get('cast').click();
  await page.finishAnimations(); // Complete the detached pieces from the old cast.
  await oldCast;
  assert.equal(page.get('result').hidden, true);
  assert.equal(page.get('guaName').textContent, '签未落');
  assert.equal(page.get('guaBoard').classList.contains('landed'), false);
  assert.equal(page.get('cast').disabled, true);
  await page.settle();
  await newCast;
  assert.ok(page.get('result').innerHTML.includes(data.gua[7].all_day.main));
  assert.equal(page.get('pieces').children.length, 6);
  assert.equal(page.get('headMode').textContent, '正餐签 · 午晚');
});

test('again replaces the previous pieces and meal', async () => {
  const page = site();
  await page.choose('all_day');
  const first = page.get('cast').click();
  await page.settle();
  await first;
  page.setGua(7);
  await page.get('againBtn').click();
  await page.settle();
  assert.equal(page.get('result').hidden, false);
  assert.equal(page.get('pieces').children.length, 6);
  assert.ok(page.get('result').innerHTML.includes(data.gua[7].all_day.main));
  assert.equal(page.get('cast').disabled, false);
});

const pieceCounts = { qian: 3, dui: 4, li: 4, zhen: 5, xun: 4, kan: 5, gen: 5, kun: 6 };
for (const [index, gua] of data.gua.entries()) {
  test(`${gua.id}: expected piece count and matching result`, async () => {
    const page = site();
    page.setGua(index);
    await page.choose('breakfast');
    const pending = page.get('cast').click();
    await page.settle();
    await pending;
    assert.equal(page.get('pieces').children.length, pieceCounts[gua.id]);
    assert.equal(page.get('guaName').textContent, `${gua.symbol}  ${gua.name}`);
    assert.ok(page.get('result').innerHTML.includes(gua.breakfast.main));
  });
}
