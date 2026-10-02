"""Verify saved evidence, counts, API arithmetic and packaged hashes offline.

Input: a project directory supplied with --project. Output: JSON on stdout.
No files are changed and no model or network service is called. This verifies
recorded labels and arithmetic, not semantic answer correctness or human review.
"""
from pathlib import Path
import argparse
from collections import Counter
import hashlib
import json
import math


def verify(project):
    def read(rel):
        return json.loads((project / rel).read_text(encoding='utf-8'))
    cases=read('data/evaluation_40.json')['cases']
    rows=[json.loads(x) for x in (project/'results/formal/raw_vs_rag_results.jsonl').read_text(encoding='utf8').splitlines() if x.strip()]
    reviews=read('results/formal/ai_review_20261001/reviewed_answers.json')
    summary=read('results/formal/ai_review_20261001/review_summary.json')
    experiment=read('results/formal/experiment_summary.json')
    settings=read('config/model_settings.json')
    assert len(cases)==40 and len(rows)==len(reviews)==80
    pairs={(c['id'],mode) for c in cases for mode in ('raw','rag')}
    assert len(pairs)==80
    assert Counter((r['case_id'],r['condition']) for r in rows)==Counter(pairs)
    assert Counter((r['case_id'],r['condition']) for r in reviews)==Counter(pairs)
    originals={(r['case_id'],r['condition']):r for r in rows}
    assert not summary['human_review_completed']
    for r in reviews:
        assert r['original_answer']==originals[r['case_id'],r['condition']]['answer']
        assert not r['human_confirmed']
        assert r['strict_complete_and_cited']==r['strict_completeness_score']*r['page_citation_support_score']
    recomputed={}
    for mode in ('raw','rag'):
        rr=[r for r in reviews if r['condition']==mode]
        for key in ('strict_completeness_score','page_citation_support_score','strict_complete_and_cited','original_answer_score'):
            assert sum(r[key] for r in rr)==summary['overall'][mode][key]
        for category in ('requirements','deadlines','submission_information','concepts'):
            cr=[r for r in rr if r['category']==category]
            assert len(cr)==10
            assert sum(r['strict_completeness_score'] for r in cr)==summary['by_category'][mode][category]['strict_completeness_score']
        records=[r for r in rows if r['condition']==mode]
        for r in records:
            cost=(r['prompt_tokens']*settings['input_price_usd_per_million_tokens']+r['completion_tokens']*settings['output_price_usd_per_million_tokens'])/1e6
            assert math.isclose(cost,r['cost_usd'],abs_tol=1e-12)
        cost=sum(r['cost_usd'] for r in records)
        latency=sum(r['latency_seconds'] for r in records)/40
        assert math.isclose(cost,experiment['conditions'][mode]['total_cost_usd'],abs_tol=1e-12)
        assert math.isclose(latency,experiment['conditions'][mode]['average_latency_seconds'],abs_tol=1e-9)
        recomputed[mode]={'strict':sum(r['strict_completeness_score'] for r in rr),'cost_usd':cost,'input_tokens':sum(r['prompt_tokens'] for r in records),'output_tokens':sum(r['completion_tokens'] for r in records),'mean_api_seconds':latency}
    verified=0
    for filename in ('FILES_SHA256_CODE.json','FILES_SHA256_DATA.json'):
        if not (project/filename).exists():continue
        for rel,expected in read(filename).items():
            path=(project/rel).resolve()
            assert path.is_relative_to(project.resolve())
            with path.open('rb') as f: actual=hashlib.file_digest(f,'sha256').hexdigest()
            assert actual==expected, f'Hash mismatch: {rel}'
            verified+=1
    return {'passed':True,'cases':40,'paired_outputs':80,'ai_review_records':80,'human_validation':False,'recomputed':recomputed,'packaged_hashes_verified':verified,'network_calls':0}


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--project',type=Path,required=True)
    print(json.dumps(verify(parser.parse_args().project.resolve()),indent=2))
