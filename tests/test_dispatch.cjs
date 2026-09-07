const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const test = require('node:test');

const workflow = fs.readFileSync(
  path.join(__dirname, '..', '.github', 'workflows', 'check-updates.yml'), 'utf8',
);
const lines = workflow.split(/\r?\n/);
const start = lines.findIndex(line => line === '          script: |');
assert.notEqual(start, -1, 'Check workflow must contain the dispatch script');
const scriptLines = [];
for (const line of lines.slice(start + 1)) {
  if (line.trim() && !line.startsWith('            ')) break;
  scriptLines.push(line.slice(12));
}
// Execute the workflow's actual script, not a second implementation of dispatch.
const AsyncFunction = Object.getPrototypeOf(async function () {}).constructor;
const dispatch = new AsyncFunction('github', 'context', 'core', 'process', scriptLines.join('\n'));

function fixture(version, uuid, status = 404) {
  const calls = [];
  const reports = [];
  const summary = {
    addHeading() { return this; },
    addCodeBlock(value) { reports.push(JSON.parse(value)); return this; },
    async write() {},
  };
  return {
    calls,
    reports,
    env: {
      BUILD_VERSION: version,
      BUILD_UUID: uuid,
      BUILD_TITLE: `Windows ${version}`,
      BUILD_ARTIFACT: 'iso',
      BUILD_ARCH: 'amd64',
      BUILD_RING: 'rp',
      BUILD_PACK: 'zh-cn',
      BUILD_EDITION: 'professional',
      BUILD_REF: 'main',
    },
    github: { rest: {
      repos: {
        async getReleaseByTag(params) {
          calls.push({ type: 'release', params });
          if (status !== 200) {
            throw Object.assign(new Error(`HTTP ${status}`), { status });
          }
          return { data: { tag_name: version } };
        },
      },
      actions: {
        async createWorkflowDispatch(params) {
          calls.push({ type: 'dispatch', params });
        },
      },
    } },
    core: { info() {}, summary },
  };
}

async function runFixture(data) {
  await dispatch(data.github, { repo: { owner: 'owner', repo: 'repo' } }, data.core, { env: data.env });
}

test('both unpublished branches dispatch independent pinned versions', async () => {
  const builds = [
    fixture('26200.9278', 'c1c737c2-f2d9-4824-bb5b-1af515179099'),
    fixture('26100.9278', 'd922b79f-142d-4cf8-896b-515abfd01e66'),
  ];
  for (const data of builds) {
    await runFixture(data);
    assert.equal(data.calls[0].params.tag, data.env.BUILD_VERSION);
    assert.deepEqual(data.calls[1], { type: 'dispatch', params: {
      owner: 'owner', repo: 'repo', workflow_id: 'build.yml', ref: 'main',
      inputs: {
        artifact: 'iso', arch: 'amd64', ring: 'rp', pack: 'zh-cn', edition: 'professional',
        uuid: data.env.BUILD_UUID, version: data.env.BUILD_VERSION,
      },
    } });
    assert.equal(data.reports[0].buildDispatched, true);
  }
});

test('published 25H2 does not suppress unpublished 24H2', async () => {
  const newer = fixture('26200.9278', '25h2-uuid', 200);
  const older = fixture('26100.9278', '24h2-uuid');
  await runFixture(newer);
  await runFixture(older);
  assert.equal(newer.calls.length, 1);
  assert.equal(newer.reports[0].buildDispatched, false);
  assert.equal(older.calls[1].params.inputs.version, '26100.9278');
});

test('both published branches are skipped', async () => {
  for (const version of ['26200.9278', '26100.9278']) {
    const data = fixture(version, `${version}-uuid`, 200);
    await runFixture(data);
    assert.equal(data.calls.length, 1);
    assert.equal(data.reports[0].releaseExists, true);
  }
});

test('GitHub permission and server errors are not mistaken for missing releases', async () => {
  for (const status of [401, 403, 429, 500]) {
    const data = fixture('26100.9278', 'uuid', status);
    await assert.rejects(runFixture(data), { status });
    assert.equal(data.calls.length, 1);
  }
});

test('dispatch errors are propagated, never reported as success', async () => {
  const data = fixture('26100.9278', 'uuid');
  data.github.rest.actions.createWorkflowDispatch = async () => { throw new Error('dispatch failed'); };
  await assert.rejects(runFixture(data), /dispatch failed/);
  assert.equal(data.reports.length, 0);
});

test('a failed branch does not prevent dispatching another branch', async () => {
  const failed = fixture('26200.9278', '25h2-uuid', 500);
  const other = fixture('26100.9278', '24h2-uuid');
  const results = await Promise.allSettled([runFixture(failed), runFixture(other)]);
  assert.equal(results[0].status, 'rejected');
  assert.equal(results[1].status, 'fulfilled');
  assert.equal(other.calls[1].params.inputs.uuid, '24h2-uuid');
  assert.match(workflow, /fail-fast: false/);
  assert.match(workflow, /build: \$\{\{ fromJSON\(needs\.check\.outputs\.builds\) \}\}/);
});

test('titles containing code remain summary data', async () => {
  const data = fixture('26100.9278', 'uuid');
  data.env.BUILD_TITLE = '$(exit 1) "; throw new Error(); //';
  await runFixture(data);
  assert.equal(data.reports[0].title, data.env.BUILD_TITLE);
});
