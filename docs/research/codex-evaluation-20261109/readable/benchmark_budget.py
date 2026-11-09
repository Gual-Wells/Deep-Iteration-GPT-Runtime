"""Exploratory artifact-performance follow-up, declared after code inspection.

This does not change the frozen primary acceptance score. Input objects are
allocated before timing/tracing; peak memory is additional Python allocation.
"""
import gc
import importlib.util
import json
from pathlib import Path
import random
import statistics
import sys
import time
import tracemalloc

sys.dont_write_bytecode=True
ROOT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT/'support'))
import suite
LABELS=('b01','b05','b03','b04')
CATEGORIES=['food','travel','books']

def load(label):
    path=ROOT/'native_subjects'/label/'portfolio/task2_budget/output/budget.py'
    spec=importlib.util.spec_from_file_location('budget_'+label,path)
    module=importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
    return module.summarize

def dataset(expenses, refunds, unique_ids, orphan=False):
    items=[{'id':f'e{i%unique_ids}','type':'expense','amount':1+i%101,
            'category_candidates':[CATEGORIES[i%3]]} for i in range(expenses)]
    items += [{'id':f'r{i}','type':'refund','amount':1+i%17,
               'refund_of':('missing' if orphan else 'e'+str(i%unique_ids)),
               'category_candidates':['books']} for i in range(refunds)]
    return items

def benchmark():
    funcs={label:load(label) for label in LABELS}
    scenarios=[('mostly_unique',30000,15000,30000,False),
               ('many_duplicate_ids',80000,20000,10,False),
               ('mostly_orphan_refunds',100,100000,100,True)]
    rows=[]
    rng=random.Random(20261109)
    for name,nexp,nrefund,nunique,orphan in scenarios:
        items=dataset(nexp,nrefund,nunique,orphan)
        expected=suite._expected_budget(items,CATEGORIES)
        for label,fn in funcs.items():
            assert fn(items,CATEGORIES)==expected,(name,label,'benchmark correctness')
        elapsed={label:[] for label in LABELS}
        for repeat in range(5):
            order=list(LABELS); rng.shuffle(order)
            for label in order:
                gc.collect(); start=time.perf_counter()
                result=funcs[label](items,CATEGORIES)
                duration=time.perf_counter()-start
                assert result==expected
                elapsed[label].append(duration)
        measurements=[]
        for label in LABELS:
            gc.collect(); tracemalloc.start()
            result=funcs[label](items,CATEGORIES)
            current,peak=tracemalloc.get_traced_memory(); tracemalloc.stop()
            assert result==expected
            measurements.append({'label':label,'correct':True,
                'median_ms':statistics.median(elapsed[label])*1000,
                'all_ms':[value*1000 for value in elapsed[label]],
                'peak_auxiliary_python_bytes':peak})
        rows.append({'scenario':name,'expenses':nexp,'refunds':nrefund,
                     'distinct_expense_ids':nunique,'measurements':measurements})
    result={'status':'posthoc exploratory, not preregistered primary efficacy',
            'reason':'Full-profile D returned a bounded per-id index; compare all accepted artifacts rather than ignore a concrete improvement because binary acceptance is tied.',
            'python':sys.version,'method':'Five timed runs per artifact/scenario, shuffled order, warmup, gc.collect before runs; separate tracemalloc peak allocation; input construction, oracle, imports and input storage excluded.',
            'scope':'Synthetic in-process functions, not agent latency, monetary cost, actual user workload or a repeated causal trial of the protocol.',
            'rows':rows}
    (ROOT/'artifact_performance.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps(result,ensure_ascii=False,indent=2))

if __name__=='__main__':benchmark()
