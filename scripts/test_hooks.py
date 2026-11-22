import json, os, subprocess, sys, tempfile

root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
hooks = os.path.join(root, 'hooks')
fails = []

def run(script, payload):
    return subprocess.run([sys.executable, '-I', os.path.join(hooks, script)], input=json.dumps(payload), capture_output=True, text=True).stdout

with tempfile.TemporaryDirectory() as t:
    for name, text, expect in [
        ('영어 보고', "Two workers are building the payment and repo gates. I'll build the agent-behavior hooks myself while they run.", True),
        ('한국어 보고', "결제 관문을 만들고 있어요. `app/deploy/deploy.sh` 에 npm test 와 build 를 넣었고 PR #2730 을 열었어요.", False),
        ('코드 블록', "고쳤어요.\n```python\nprint('a long english code block that should not count')\n```\n검사도 통과했어요.", False),
        ('짧은 영어', "Done.", False),
        ('일본어 보고', "これはテストです。全部完了しました。次の作業に進みます。", True),
        ('중국어 보고', "我已经完成了所有的修改 测试都通过了 接下来继续处理剩下的任务", True),
        ('영어 섞인 짧은 상태 줄', "Waiting on the last two writers.", True),
        ('영어 식별자 섞임', "devkit 0.3.0 에 신뢰 피라미드를 넣었고 check.py 가 mode SKILL autonomous-run correct 를 검사해요.", False),
    ]:
        p = os.path.join(t, 'tx.jsonl')
        open(p, 'w').write(json.dumps({'type': 'assistant', 'message': {'content': [{'type': 'text', 'text': text}]}}) + '\n')
        if ('block' in run('korean-stop.py', {'transcript_path': p})) != expect:
            fails.append(f'korean-stop: {name}')
    p = os.path.join(t, 'tx.jsonl')
    if run('korean-stop.py', {'transcript_path': p, 'stop_hook_active': True}):
        fails.append('korean-stop: 이미 한 번 막았으면 놓아줘야 함')

    def tool(name, inp, tid='toolu_x'):
        return {'type': 'assistant', 'message': {'content': [{'type': 'tool_use', 'id': tid, 'name': name, 'input': inp}]}}
    plan = tool('mcp__ccd_turn__update_plan', {'items': [{'content': '원인 찾기', 'status': 'in_progress'}, {'content': '고치기', 'status': 'pending'}]})
    advance = tool('mcp__ccd_turn__update_plan', {'advance': True})
    wrap = tool('mcp__ccd_turn__wrap_up', {'recap': '고쳤어요.'})
    bg = tool('Bash', {'command': 'sleep 99', 'run_in_background': True}, 'toolu_bg1')
    note = {'type': 'user', 'message': {'content': '<task-notification>\n<tool-use-id>toolu_bg1</tool-use-id>\n</task-notification>'}}
    side = dict(plan, isSidechain=True)
    wait_for_human = tool('mcp__ccd_turn__wrap_up', {'recap': '47건을 보였어요.', 'ask': '어느 쪽부터 할까요?', 'blocked': True})
    human_decides = {'type': 'user', 'message': {'content': '1번으로 가자'}}
    for name, entries, expect in [
        ('미완료를 두고 멈춤', [plan, advance], True),
        ('다 끝내고 wrap_up', [plan, advance, advance, wrap], False),
        ('미완료여도 wrap_up 으로 마무리', [plan, wrap], False),
        ('백그라운드 작업을 기다림', [plan, bg], False),
        ('기다리던 작업이 끝났는데 멈춤', [plan, bg, note], True),
        ('작업 목록 없음', [], False),
        ('서브에이전트의 목록', [side], False),
        ('TodoWrite 미완료', [tool('TodoWrite', {'todos': [{'content': 'a', 'status': 'pending'}]})], True),
        ('사람 차례라 기다림', [plan, wait_for_human], False),
        ('사람이 정했는데 남은 단계 없이 끝냄', [plan, wait_for_human, human_decides], True),
        ('사람이 정했는데 한 단계도 안 하고 wrap_up', [plan, wait_for_human, human_decides, wrap], True),
        ('사람이 정한 뒤 이어서 끝까지', [plan, wait_for_human, human_decides, advance, advance, wrap], False),
        ('사람이 정한 뒤 또 사람에게 물음', [plan, wait_for_human, human_decides, wait_for_human], False),
    ]:
        open(p, 'w').write(''.join(json.dumps(e) + '\n' for e in entries))
        if ('block' in run('open-plan-stop.py', {'transcript_path': p})) != expect:
            fails.append(f'open-plan-stop: {name}')
    if run('open-plan-stop.py', {'transcript_path': p, 'stop_hook_active': True}):
        fails.append('open-plan-stop: 이미 한 번 막았으면 놓아줘야 함')

for name, tool, inp, expect in [
    ('한국어 recap', 'mcp__ccd_turn__wrap_up', {'recap': '빈 PR 머지를 막는 훅을 넣었어요. `check.py` 가 통과했고 CI 는 아직 돌고 있어요.', 'actions': [{'label': 'PR 머지'}]}, False),
    ('영어 recap', 'mcp__ccd_turn__wrap_up', {'recap': 'Added the empty PR merge gate. check.py passes and CI is still running.'}, True),
    ('짧은 영어 버튼', 'mcp__ccd_turn__wrap_up', {'recap': '고쳤어요.', 'actions': [{'label': 'Yes, fix 1'}]}, True),
    ('한 낱말 영어 버튼', 'mcp__ccd_turn__wrap_up', {'recap': '고쳤어요.', 'actions': [{'label': 'OK'}]}, False),
    ('한글 섞인 짧은 버튼', 'mcp__ccd_turn__wrap_up', {'recap': '고쳤어요.', 'ask': 'PR 을 머지할까요?', 'actions': [{'label': '1번 fix'}, {'action': 'commit'}]}, False),
    ('빈 필드', 'mcp__ccd_turn__wrap_up', {}, False),
    ('영어 작업 목록', 'mcp__ccd_turn__update_plan', {'items': [{'content': 'check.py 돌리기', 'status': 'pending'}, {'content': 'Push and watch CI', 'status': 'pending'}]}, True),
    ('한국어 작업 목록', 'mcp__ccd_turn__update_plan', {'items': [{'content': 'hooks.json 에 등록', 'status': 'in_progress'}]}, False),
    ('진행 표시만', 'mcp__ccd_turn__update_plan', {'advance': True}, False),
    ('영어 캡션', 'SendUserFile', {'caption': 'Settings screen after the fix'}, True),
    ('영어 명령 설명', 'Bash', {'command': 'git status', 'description': 'Show working tree status'}, True),
    ('한국어 명령 설명', 'Bash', {'command': 'git status', 'description': '작업 트리 상태 보기'}, False),
    ('설명 없는 명령', 'Bash', {'command': 'ls'}, False),
    ('질문 하나', 'AskUserQuestion', {'questions': [{'question': '버튼 색은 어느 쪽이 좋아요?', 'header': '버튼 색', 'options': [{'label': '파랑', 'description': '지금 앱 색'}, {'label': '초록'}]}]}, False),
    ('질문 둘', 'AskUserQuestion', {'questions': [{'question': '버튼 색은?', 'header': '색'}, {'question': '글꼴은?', 'header': '글꼴'}]}, True),
    ('영어 선택지', 'AskUserQuestion', {'questions': [{'question': '어느 쪽으로 할까요?', 'header': '방식', 'options': [{'label': 'Keep both'}, {'label': '하나만'}]}]}, True),
    ('다른 도구', 'Read', {'file_path': '/a/b'}, False),
]:
    if ('deny' in run('tool-text.py', {'tool_name': tool, 'tool_input': inp})) != expect:
        fails.append(f'tool-text: {name}')

for cmd, expect in [
    ('cd x && pytest -q | tail -3 && gh pr merge 12 --squash', True),
    ('pytest -q tests/ && git commit -m x', False),
    ('ls -la', False),
]:
    if ('deny' in run('guard-bash.py', {'tool_input': {'command': cmd}})) != expect:
        fails.append(f'guard-bash: {cmd[:40]}')

import datetime, stat
with tempfile.TemporaryDirectory() as t:
    def fake_gh(checks_out, code, age_sec, files=1):
        created = (datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(seconds=age_sec)).strftime('%Y-%m-%dT%H:%M:%SZ')
        path = os.path.join(t, 'gh')
        open(path, 'w').write(f"""#!/bin/sh
if [ "$2" = "view" ]; then echo '{{"createdAt":"{created}","headRefOid":"abc","files":{json.dumps([{"path": "a"}] * files)}}}'; exit 0; fi
echo '{checks_out}'; exit {code}
""")
        os.chmod(path, os.stat(path).st_mode | stat.S_IEXEC)
    env = dict(os.environ, PATH=t + os.pathsep + os.environ['PATH'])
    for name, out, code, age, files, expect in [
        ('체크가 아직 안 붙은 새 PR', 'no checks reported on the branch', 1, 20, 1, True),
        ('도는 체크', 'test\tpending\t0', 8, 600, 1, True),
        ('실패한 체크', 'test\tfail\t1m', 1, 600, 1, True),
        ('모두 통과', 'test\tpass\t1m', 0, 600, 1, False),
        ('체크 없는 경로의 오래된 PR', 'no checks reported on the branch', 1, 600, 1, False),
        ('바뀐 파일 0개', 'test\tpass\t1m', 0, 600, 0, True),
    ]:
        fake_gh(out, code, age, files)
        r = subprocess.run([sys.executable, '-I', os.path.join(hooks, 'guard-bash.py')], input=json.dumps({'tool_input': {'command': 'gh pr merge 42 --squash'}, 'cwd': t}), capture_output=True, text=True, env=env).stdout
        if ('deny' in r) != expect:
            fails.append(f'머지 관문: {name}')

    sub = os.path.join(t, 'other'); os.makedirs(sub)
    open(os.path.join(t, 'gh'), 'w').write(f"""#!/bin/sh
case "$*" in *"-R o/r"*) ok=1;; esac
[ "$(pwd -P)" = "$(cd {sub} && pwd -P)" ] && ok=1
[ -z "$ok" ] && {{ echo 'GraphQL: Could not resolve to a PullRequest with the number of 42.' >&2; exit 1; }}
if [ "$2" = "view" ]; then echo '{{"createdAt":"2020-01-01T00:00:00Z","files":[{{"path":"a"}}]}}'; exit 0; fi
echo 'test	pass	1m'; exit 0
""")
    for name, cmd, expect, word in [
        ('--repo 로 다른 저장소', 'M 42 --repo o/r --squash', False, ''),
        ('-R 로 다른 저장소', 'M 42 -R o/r --squash', False, ''),
        ('맨 앞 cd 로 다른 저장소', f'cd {sub} && M 42 --squash', False, ''),
        ('이 폴더에 없는 PR', 'M 42 --squash', True, '못 찾았다'),
    ]:
        r = subprocess.run([sys.executable, '-I', os.path.join(hooks, 'guard-bash.py')], input=json.dumps({'tool_input': {'command': cmd.replace('M ', 'gh pr ' + 'merge ')}, 'cwd': t}), capture_output=True, text=True, env=env).stdout
        if ('deny' in r) != expect or word not in r:
            fails.append(f'머지 관문: {name}')

with tempfile.TemporaryDirectory() as t:
    env = dict(os.environ, HOME=t)
    py = os.path.join(t, 'a.py')
    open(py, 'w').write('# Copyright 2026\nx = 1  # 있던 주석\n')
    def gate(payload):
        return 'deny' in subprocess.run([sys.executable, '-I', os.path.join(hooks, 'no-new-comments.py')], input=json.dumps(payload), capture_output=True, text=True, env=env).stdout
    edit = {'tool_name': 'Edit', 'tool_input': {'file_path': py, 'old_string': 'x = 1  # 있던 주석', 'new_string': 'x = 2  # 있던 주석\n# 값을 2로 바꾼다\ny = x'}}
    for name, payload, expect in [
        ('새 서술 주석', edit, True),
        ('같은 편집을 다시 보내면 통과', edit, False),
        ('있던 주석을 옮기기만', {'tool_name': 'Edit', 'tool_input': {'file_path': py, 'old_string': 'x = 1  # 있던 주석', 'new_string': 'x = 3  # 있던 주석'}}, False),
        ('링크 주석', {'tool_name': 'Edit', 'tool_input': {'file_path': py, 'old_string': 'x', 'new_string': '# https://example.com/spec\nx'}}, False),
        ('새 파일의 docstring', {'tool_name': 'Write', 'tool_input': {'file_path': os.path.join(t, 'b.py'), 'content': 'def f():\n    """하는 일."""\n    return 1\n'}}, True),
        ('기존 파일 덮어쓰기에 남은 주석', {'tool_name': 'Write', 'tool_input': {'file_path': py, 'content': '# Copyright 2026\nx = 5  # 있던 주석\n'}}, False),
        ('ts 새 주석', {'tool_name': 'Edit', 'tool_input': {'file_path': os.path.join(t, 'c.ts'), 'old_string': 'a', 'new_string': 'a // 왜냐하면'}}, True),
        ('마크다운은 보지 않음', {'tool_name': 'Write', 'tool_input': {'file_path': os.path.join(t, 'd.md'), 'content': '# 제목\n'}}, False),
    ]:
        if gate(payload) != expect:
            fails.append(f'새 주석 관문: {name}')

def stop_scripts():
    spec = json.load(open(os.path.join(hooks, 'hooks.json')))
    return [h['command'].split('/')[-1] for g in spec['hooks']['Stop'] for h in g['hooks']]

fixtures = os.path.join(root, 'scripts', 'fixtures', 'correction')
with tempfile.TemporaryDirectory() as t:
    home = os.path.join(t, 'home')
    os.makedirs(home)
    clean = {k: v for k, v in os.environ.items() if not k.startswith('GIT_')}
    def git(repo, *args, when=None):
        env = dict(clean, HOME=home, GIT_AUTHOR_NAME='t', GIT_AUTHOR_EMAIL='t@t', GIT_COMMITTER_NAME='t', GIT_COMMITTER_EMAIL='t@t')
        if when:
            env.update(GIT_AUTHOR_DATE=when, GIT_COMMITTER_DATE=when)
        subprocess.run(['git', '-C', repo, *args], check=True, capture_output=True, env=env)
    def stop(entries, commit=(), dirty=(), before=(), active=False, body='x\n'):
        repo = tempfile.mkdtemp(dir=t)
        git(repo, 'init', '-q')
        at = datetime.datetime.fromisoformat(entries[0]['timestamp'].replace('Z', '+00:00'))
        for files, when in ((before, at - datetime.timedelta(days=1)), (commit, at + datetime.timedelta(minutes=1))):
            if files:
                for f in files:
                    os.makedirs(os.path.dirname(os.path.join(repo, f)) or repo, exist_ok=True)
                    open(os.path.join(repo, f), 'w').write('x\n')
                git(repo, 'add', '-A')
                git(repo, 'commit', '-qm', 'x', when=when.isoformat())
        for f in dirty:
            os.makedirs(os.path.dirname(os.path.join(repo, f)) or repo, exist_ok=True)
            open(os.path.join(repo, f), 'w').write(body)
        tx = os.path.join(repo, '..', os.path.basename(repo) + '.jsonl')
        open(tx, 'w').write(''.join(json.dumps(e, ensure_ascii=False) + '\n' for e in entries))
        payload = {'transcript_path': tx, 'cwd': repo, 'stop_hook_active': active}
        outs = [subprocess.run([sys.executable, '-I', os.path.join(hooks, s)], input=json.dumps(payload), capture_output=True, text=True, env=dict(clean, HOME='/Users/u')).stdout for s in stop_scripts()]
        return next((json.loads(o)['reason'] for o in outs if '교정' in o and 'block' in o), None)
    def load(name):
        return [json.loads(l) for l in open(os.path.join(fixtures, name + '.jsonl'))]
    def said(text):
        return {'type': 'assistant', 'message': {'content': [{'type': 'text', 'text': text}]}}
    earlier = load('release-memory-only')[0]
    leak = [dict(earlier, message={'role': 'user', 'content': '/ 메뉴 고쳐서 main 에 올려'}), said('고쳐서 올렸고 CI 가 v0.3.1 을 자동으로 릴리스했어요.')] + load('release-memory-only')
    first = lambda text: [dict(earlier, message={'role': 'user', 'content': text}), said('PR 을 올렸어요.')]
    for name, entries, kw, expect in [
        ('샌 교정: 릴리스는 말할 때만, 메모리만 바뀜', leak, {}, True),
        ('장치로 남음: 검증 없이 커밋, commit-msg 관문', load('verify-commit-gate'), {'commit': ['.githooks/commit-msg', '.claude/skills/verify-app/verify.sh', 'CLAUDE.md']}, False),
        ('장치로 남음: 재발한 카드, 회귀 테스트', load('recurring-card-test'), {'commit': ['fill.go', 'serve.go', 'need_revive_test.go', 'blocked_test.go']}, False),
        ('장치로 남음: 문서 인용 검사 스크립트', load('citation-check'), {'commit': ['scripts/check-citations.mjs']}, False),
        ('커밋 안 한 테스트 파일도 장치', leak, {'dirty': ['release_test.go']}, False),
        ('자체 시험을 품은 스크립트를 고침', leak, {'dirty': ['skills/featuremap/scripts/featuremap.py'], 'body': 'def self_test():\n    assert build() == 1\n'}, False),
        ('자체 시험 없는 스크립트만 고침', leak, {'dirty': ['skills/featuremap/scripts/featuremap.py']}, True),
        ('턴 전에 있던 검사는 이번 장치가 아님', leak, {'before': ['scripts/check.py'], 'commit': ['README.md']}, True),
        ('장치화 불가 이유를 적음', leak + [said('판단이라 장치화 불가: 언제 릴리스할지는 사람이 그때 정하는 일이다.')], {}, False),
        ('교정 아닌 메시지', leak[:2] + [dict(leak[2], message={'role': 'user', 'content': '릴리스 노트도 같이 써 줘'})] + leak[3:], {}, False),
        ('한 번 되돌렸으면 놓아줌', leak, {'active': True}, False),
        ('첫 요청의 금지 지시는 교정이 아님', first('고치고 PR 만 올려, 머지하지 마'), {}, False),
        ('첫 요청이라도 지난 일을 가리키면 교정', first('아직도 재발하네, 제대로 고쳐'), {}, True),
        ('압축 요약은 사람 메시지가 아님', [dict(leak[0], message={'role': 'user', 'content': '식별만 하는 게 가능할까?'}), {'type': 'user', 'isCompactSummary': True, 'isVisibleInTranscriptOnly': True, 'timestamp': leak[0]['timestamp'], 'message': {'role': 'user', 'content': '<artifact-content-authored-by-others/>\n요약: 사용자가 「제대로 고쳐 아직도 재발하니까」라고 했다.'}}, said('식별은 할 수 있어요.')], {}, False),
    ]:
        reason = stop(entries, **kw)
        if bool(reason) != expect:
            fails.append(f'correction-stop: {name} (되돌림 {"있음" if reason else "없음"})')
        elif reason and 'SHOW_REASON' in os.environ:
            print(f'{name}\n  되돌림: {reason}')

def say(text):
    return {'type': 'assistant', 'message': {'content': [{'type': 'text', 'text': text}]}}

paused = [{'type': 'user', 'message': {'content': '47건 한번 보고 결정내리고 싶은데'}}, plan, say('47건 목록이에요. 사람이 고를 차례라 기다려요.'), wait_for_human]
with tempfile.TemporaryDirectory() as t:
    p = os.path.join(t, 'tx.jsonl')
    for name, entries, expect in [
        ('사람 차례로 멈춤', paused, False),
        ('사람이 정했는데 중간 결론만 말하고 멈춤', paused + [human_decides, say('1번으로 할게요.')], True),
        ('사람이 정한 뒤 끝까지 감', paused + [human_decides, advance, advance, say('보고와 프롬프트를 다 썼어요.'), wrap], False),
        ('사람 차례로 멈춘 뒤 압축 요약만 옴', paused + [{'type': 'user', 'isCompactSummary': True, 'message': {'content': '<artifact-content-authored-by-others/>\n요약'}}, say('47건 목록이에요.')], False),
    ]:
        open(p, 'w').write(''.join(json.dumps(e) + '\n' for e in entries))
        blocked = any('block' in run(s, {'transcript_path': p, 'cwd': t}) for s in stop_scripts())
        if blocked != expect:
            fails.append(f'Stop 훅 전체 여러 턴: {name}')

PR = 'https://github.com/me/app/pull/7'
def bash(i, cmd, bg=False):
    return {'type': 'assistant', 'message': {'content': [{'type': 'tool_use', 'id': f'toolu_{i}', 'name': 'Bash', 'input': dict(command=cmd, **({'run_in_background': True} if bg else {}))}]}}
def result(i, text):
    return {'type': 'user', 'message': {'content': [{'type': 'tool_result', 'tool_use_id': f'toolu_{i}', 'content': text}]}}
asked = {'type': 'user', 'message': {'content': '로그인 버그 고쳐'}}
opened = [asked, bash(1, 'gh pr create --fill'), result(1, PR), say('PR 을 열었어요. CI 체크 1개는 아직 돌고 있어요.')]
with tempfile.TemporaryDirectory() as t:
    home, bin_ = os.path.join(t, 'home'), os.path.join(t, 'bin')
    os.makedirs(os.path.join(home, '.claude')); os.makedirs(bin_)
    json.dump({'personal': {'owners': ['me']}}, open(os.path.join(home, '.claude', 'devkit.json'), 'w'))
    gh = os.path.join(bin_, 'gh')
    p = os.path.join(t, 'tx.jsonl')
    for name, entries, state, active, expect in [
        ('개인 PR 을 열고 머지 없이 닫음', opened, 'OPEN', False, True),
        ('이미 머지됨', opened, 'MERGED', False, False),
        ('회사 저장소 PR', [asked, bash(1, 'gh pr create'), result(1, PR.replace('/me/', '/corp/')), say('PR 열었어요.')], 'OPEN', False, False),
        ('체크를 백그라운드로 기다리는 중', opened + [bash(2, 'gh pr checks 7 --watch', bg=True), result(2, 'Command running in background')], 'OPEN', False, False),
        ('머지 안 함 이유를 적음', opened + [say('머지 안 함: 화면 문구라 사람 승인이 필요해요.')], 'OPEN', False, False),
        ('사람이 머지하지 말라고 함', [{'type': 'user', 'message': {'content': '고치고 PR 만 올려, 머지하지 마'}}] + opened[1:], 'OPEN', False, False),
        ('한 번 되돌렸으면 놓아줌', opened, 'OPEN', True, False),
        ('통과 뒤 사람이 다른 걸 물음', opened + [say('머지 안 함: 사람 리뷰가 필요해요.'), {'type': 'user', 'message': {'content': '그 PR 은 두고 다른 거 물어볼게'}}, say('네, 말씀하세요.')], 'OPEN', False, False),
    ]:
        open(gh, 'w').write(f'#!/bin/sh\necho {state}\n'); os.chmod(gh, 0o755)
        open(p, 'w').write(''.join(json.dumps(e, ensure_ascii=False) + '\n' for e in entries))
        env = dict(os.environ, HOME=home, PATH=bin_ + os.pathsep + os.environ['PATH'])
        outs = [subprocess.run([sys.executable, '-I', os.path.join(hooks, s)], input=json.dumps({'transcript_path': p, 'cwd': t, 'stop_hook_active': active}), capture_output=True, text=True, env=env).stdout for s in stop_scripts()]
        blocked = any(('block' in o) if name.startswith('통과 뒤') else ('머지되지 않은' in o) for o in outs)
        if blocked != expect:
            fails.append(f'open-pr-stop: {name} (되돌림 {"있음" if blocked else "없음"}) {outs}')

if fails:
    sys.exit('훅 시험 실패:\n' + '\n'.join(fails))
print('훅 시험 OK')
