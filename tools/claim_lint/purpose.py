# -*- coding: utf-8 -*-
"""claim_lint purpose and mechanism rules (#18): L11-L14.

**These rules check that the declarations agree with each other, nothing more.** Whether a consumer really checks what
its enforced_at says, or really refuses a nested act as the current actor, cannot be decided statically; the runtime
tests of #8 do that (RULES.md pairs L11 and L12 with the negative tests by ID). An error here never means "guaranteed
by the machine".

Inputs: claims.yaml (answers, does_not_answer, usage, consumers, enforced_at, path, refs, spec_version,
revisit_trigger), token_types.yaml, templates/registry/questions.yaml (not_this, mechanisms) and the `questions` section
of catalog_answers.yaml (which questions the use case needs: {q-id: {needed: true|false, reason, channel}}).
"""
import os
import re

from .semantic import ADOPTED, ERROR, WARN, INFO, _F, _empty

SEV = {'L11': ERROR, 'L12': ERROR, 'L13': ERROR, 'L14': WARN}  # RULES.md: error only with opportunities and no false positive on scenario A
ASVS_CLAIMS = ('sub', 'scope', 'authorization_details')  # ASVS 5.0.0 10.3.2: present means part of the decision
DRAFT_RX = re.compile(r'draft-[a-z0-9-]+-\d{2}\b|preview|プレビュー|experimental|早期アクセス', re.I)
DRAFT_KINDS = {'txn_token', 'id_jag', 'status_list_token'}
DRAFT_CLAIMS = {'txn', 'tctx', 'rctx', 'req_wl', 'purp', 'azd', 'status'}
DRAFT_BEHAVIOUR = {'purp', 'azd'}  # slide:p06-transaction-tokens: do not rely on the draft's purp / azd


class X:
    def __init__(self, docs, root):
        self.claims = (docs.get('claims') or {}).get('claims') or []
        self.tts = (docs.get('token_types') or {}).get('token_types') or []
        self.tt = {t.get('id'): t for t in self.tts}
        self.answers = docs.get('catalog_answers') or {}
        from .core import load_yaml
        q = load_yaml(os.path.join(root, 'templates', 'registry', 'questions.yaml')) or {}
        self.questions = {x['id']: x for x in q.get('questions') or []}
        self.findings, self.checked = [], {}

    def add(self, rule, target, message, severity=None):
        self.findings.append(_F(rule, severity or SEV[rule], target, message))

    def count(self, rule):
        self.checked[rule] = self.checked.get(rule, 0) + 1

    def adopted(self):
        return [c for c in self.claims if c.get('decision') in ADOPTED]


def _refs_text(row):
    return ' '.join(f"{r.get('id', '')} {r.get('url', '')}" for r in row.get('refs') or [])


# ------------------------------------------------------------------ L11: a claim used for a decision has enforced_at
def rule_l11(x):
    for c in x.adopted():
        cid = c.get('id')
        if c.get('usage') in ('authz', 'identifier') and c.get('consumers'):
            x.count('L11')
            have = {str(e.get('service')) for e in c.get('enforced_at') or []}
            for s in c['consumers']:
                if s not in have:
                    x.add('L11', cid, f"usage {c['usage']} のクレームを読む受け手 {s} の enforced_at（何と何を照合するか）がない")
        if c.get('name') == 'tctx':
            x.count('L11')
            items = list((c.get('value_vocabulary') or {}).get('values') or [])
            text = ' '.join(e.get('check', '') for e in c.get('enforced_at') or [])
            if not c.get('enforced_at'):
                x.add('L11', cid, 'tctx に照合の規則（enforced_at）がない（本文と tctx の照合。仕様では MAY なので、規則は筆者の提案）')
            for it in items:
                if str(it) not in text:
                    x.add('L11', cid, f'tctx の項目 {it} を照合する規則が enforced_at にない')
        if c.get('namespace') is None and c.get('name') in ASVS_CLAIMS and \
                any(x.tt.get(t, {}).get('kind') == 'access_token' for t in c.get('carried_in') or []):
            x.count('L11')
            if not c.get('enforced_at'):
                x.add('L11', cid, f"AT に {c['name']} を載せるのに、認可の判断に使う宣言（enforced_at）がない。載せるなら判断に使い、使わないなら"
                                  '載せない（OWASP ASVS 5.0.0 10.3.2）', WARN)


# ------------------------------------------------------------------ L12: answers against does_not_answer
def _nested_act(c):
    """A row under a nested act (a past actor): two or more act in its path, whatever its name (act.act, act.act.sub)."""
    p = [str(v) for v in c.get('path') or [] if v is not None]
    return p.count('act') >= 2


def rule_l12(x):
    for c in x.claims:
        ans, dna = set(c.get('answers') or []), set(c.get('does_not_answer') or [])
        if not ans and not dna:
            continue
        x.count('L12')
        cid = c.get('id')
        for q in sorted(ans & dna):
            x.add('L12', cid, f'問い {q} が answers と does_not_answer の両方にある')
        pairs = set()
        for q in sorted(ans):
            for other in (x.questions.get(q) or {}).get('not_this') or []:
                if other in ans:
                    pairs.add(frozenset((q, other)))  # not_this may be written in one direction only
        for pr in sorted(pairs, key=sorted):
            a, b = sorted(pr)
            x.add('L12', cid, f'取り違えやすい 2 つの問い（{a} と {b}。questions.yaml の not_this）に、同じクレームで答えている')
        if _nested_act(c) and 'q-actor' in ans:  # name: act or name: sub under act.act
            x.add('L12', cid, f"入れ子の act の下（path {'.'.join(map(str, c.get('path') or []))}、過去の実行者）を「誰が代理して実行しているか」（q-actor）の答えにしている。"
                              '今の代理者は最も外側の act だけ（RFC 8693 §4.1）')


# ------------------------------------------------------------------ L13: every question the use case needs has a mechanism
def rule_l13(x):
    qs = x.answers.get('questions')
    if not isinstance(qs, dict):
        x.add('L13', 'questions', 'catalog_answers.yaml に questions（問いの一覧のそれぞれを、このユースケースで要るか）がない')
        return
    answered = {q for c in x.adopted() for q in c.get('answers') or []}
    for qid in x.questions:
        x.count('L13')
        a = qs.get(qid)
        if not isinstance(a, dict) or not isinstance(a.get('needed'), bool):
            x.add('L13', qid, f'問い {qid}（{x.questions[qid]["text"]}）に、要るか（needed: true／false）の回答がない')
            continue
        if a['needed'] is False:
            if _empty(a.get('reason')):
                x.add('L13', qid, f'問い {qid} を不要とした理由（reason）がない')
            continue
        if qid not in answered and _empty(a.get('channel')):
            x.add('L13', qid, f'要るとした問い {qid}（{x.questions[qid]["text"]}）に答える仕組みが 1 つもない（answers にこの問いを持つ採用のクレームも、'
                              'channel（mTLS の相手など、クレームでない仕組み）もない）')
    for qid in qs:
        if qid not in x.questions:
            x.add('L13', qid, f'questions の {qid} が templates/registry/questions.yaml の questions にない')


# ------------------------------------------------------------------ L14: rows depending on drafts record version and revisit
def _draft_reason(x, c):
    if DRAFT_RX.search(_refs_text(c)):
        return 'refs が草案・preview を指す'
    if c.get('namespace') is None and c.get('name') in DRAFT_CLAIMS:
        return f"{c['name']} は草案が定めるクレーム"
    kinds = {x.tt.get(t, {}).get('kind') for t in c.get('carried_in') or []}
    if kinds & DRAFT_KINDS:
        return f"草案のトークン（{'・'.join(sorted(k for k in kinds & DRAFT_KINDS))}）に載る"
    return None


def rule_l14(x):
    for c in x.adopted():
        why = _draft_reason(x, c)
        if not why:
            continue
        x.count('L14')
        miss = [k for k in ('spec_version', 'revisit_trigger') if _empty(c.get(k))]
        if miss:
            x.add('L14', c.get('id'), f"草案に依存する行（{why}）に {'・'.join(miss)} がない")
        if c.get('namespace') is None and c.get('name') in DRAFT_BEHAVIOUR:
            x.add('L14', c.get('id'), f"草案の {c['name']} に依存している（slide:p06-transaction-tokens は使わないことを勧める）")
    for t in x.tts:
        if t.get('decision') not in ADOPTED:
            continue
        if t.get('kind') in DRAFT_KINDS or DRAFT_RX.search(_refs_text(t) + ' ' + str(t.get('note', ''))):
            x.count('L14')
            if not DRAFT_RX.search(_refs_text(t)) or _empty(t.get('revisit_trigger')):
                x.add('L14', f"token_type {t['id']}", '草案に依存する種別に、版を付けた草案の参照（refs の draft-…-NN）か revisit_trigger がない')


RULES = [rule_l11, rule_l12, rule_l13, rule_l14]


def run(docs, root):
    x = X(docs, root)
    for r in RULES:
        r(x)
    return x.findings, x.checked
