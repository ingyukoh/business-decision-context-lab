"""Closed display contract. Model prose never becomes a business recommendation."""
import json
FIELDS = {
 'metric':['sales'], 'unit':['thousands_of_units','unavailable'],
 'interpretation':['association','unavailable'], 'evidence':['isl_advertising','unavailable'],
 'review':['human_review','training_range_review'], 'action':['none'],
 'context_status':['present','unavailable']}
SCHEMA = {'type':'object','properties':{k:{'type':'string','enum':v} for k,v in FIELDS.items()},
          'required':list(FIELDS),'additionalProperties':False}

def expected_decision(result, include_context=True):
    return {'metric':'sales','unit':'thousands_of_units' if include_context else 'unavailable',
     'interpretation':'association' if include_context else 'unavailable',
     'evidence':'isl_advertising' if include_context else 'unavailable',
     'review':'human_review' if result['within_marginal_training_bounds'] else 'training_range_review',
     'action':'none','context_status':'present' if include_context else 'unavailable'}

def reject_duplicates(pairs):
    obj={}
    for k,v in pairs:
        if k in obj:raise ValueError('Duplicate JSON key')
        obj[k]=v
    return obj

def validate_decision(raw, result, include_context=True):
    try:
        if not isinstance(raw,str) or len(raw.encode())>8192:raise ValueError('Output size/type')
        obj=json.loads(raw,object_pairs_hook=reject_duplicates,parse_constant=lambda x:(_ for _ in ()).throw(ValueError(x)))
        if not isinstance(obj,dict) or set(obj)!=set(FIELDS):raise ValueError('Exact object required')
        if any(type(v) is not str or v not in FIELDS[k] for k,v in obj.items()):raise ValueError('Enum mismatch')
        if obj!=expected_decision(result,include_context):raise ValueError('Evidence mismatch')
        return {'checks_passed':True,'failures':[],'decision':obj,'human_review_required':True,
                'scope':'Exact schema, allowlisted fields and consistency with trusted tool results; free text excluded.'}
    except (ValueError,TypeError,KeyError):
        return {'checks_passed':False,'failures':['structured_output_or_evidence_mismatch'],
                'human_review_required':True,'scope':'Model output rejected; trusted code supplies display.'}

def display_summary(result):
    return (f"Predicted sales: {result['prediction']:.2f} thousands of units. "
            'This is an association estimate from public advertising data. '
            'A human reviewer must assess applicability before a business decision.')

def structured_prompt(result, include_context=True):
    from lab import context
    facts={'metric':'sales','within_marginal_training_bounds':result['within_marginal_training_bounds'],
           'semantic_context':context() if include_context else [],'allowed_action':'none'}
    return ('Return only the JSON object described by this schema. Resolve definitions from the supplied '
            'semantic context; use unavailable when it is absent. Use training_range_review if outside '
            'individual training ranges, otherwise human_review. Select association only if the evidence '
            'states it. Do not generate numbers, recommendations, or extra text. Schema: '+json.dumps(SCHEMA)+
            '\nTrusted tool facts: '+json.dumps(facts))
