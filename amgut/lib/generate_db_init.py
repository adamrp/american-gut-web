#!/usr/bin/env python

from amgut.lib.human_survey_supp import (
    question_map, responses_map, key_map, question_group, group_order,
    supplemental_map, question_type)
from amgut.lib.locale_data.american_gut import _HUMAN_SURVEY
from amgut.lib.data_access.sql_connection import SQLConnectionHandler

conn = SQLConnectionHandler()

# Rows must be inserted into the tables in this order to avoid FK violations
order = [
    'survey_group',
    'surveys',
    'survey_question',
    'group_questions',
    'survey_response_types',
    'survey_question_response_type',
    'survey_response',
    'survey_question_response',
    'survey_question_triggered_by']

# Keeps track of insert statements by table name, so that the output file can
# be nicely formatted
lines = {table: [] for table in order}

# Set up the dictionary of insert statements
inserts = {}
inserts['survey_group'] = (
    'INSERT INTO survey_group (group_order, american_name, british_name) '
    'VALUES (%s, %s, %s);')

inserts['surveys'] = (
    'INSERT INTO surveys (survey_id, survey_group) VALUES (%s, %s);')

inserts['survey_question'] = (
    'INSERT INTO survey_question (american, british) '
    'VALUES (%s, %s);')

inserts['group_questions'] = (
    'INSERT INTO group_questions '
    '(survey_group, survey_question_id, display_index) '
    'VALUES (%s, %s, %s);')

inserts['survey_response_types'] = (
    'INSERT INTO survey_response_types (survey_response_type) VALUES (%s);')

inserts['survey_question_response_type'] = (
    'INSERT INTO survey_question_response_type '
    '(survey_question_id, survey_response_type) '
    'VALUES (%s, %s);')

inserts['survey_response'] = (
    'INSERT INTO survey_response (american, british) VALUES (%s, %s);')

inserts['survey_question_response'] = (
    'INSERT INTO survey_question_response '
    '(survey_question_id, response, display_index) '
    'VALUES (%s, %s, %s);')

inserts['survey_question_triggered_by'] = (
    'INSERT INTO survey_question_triggered_by '
    '(survey_question_id, trigger_question, trigger_response) '
    'VALUES (%s, %s, %s);')

# Go through the structures from human_survey_supp to fill the tables

# reverse lookup the question index from the question_key
qkey_to_idx = {qkey: idx for idx, qkey in key_map.iteritems()}

# reverse lookup the group index from the group_key
gkey_to_idx = {gkey: group_order.index(gkey) for gkey in group_order}

for i, gkey in enumerate(group_order):
    title_key = gkey + '_TITLE'
    lines['survey_group'].append((i, _HUMAN_SURVEY[title_key],
                                  _HUMAN_SURVEY[title_key]))
    lines['surveys'].append((1, i))

# need to keep track of idx to survey_question_id in DB
qidx_to_qid = {}

# enumeration here is to keep track of display order -- the serial starts at 1
for i, (idx, question_text) in enumerate(question_map.items(), start=1):
    qidx_to_qid[idx] = i
    lines['survey_question'].append((question_text, question_text))

# Add supplemental questions to survey_questions, keep track of qid, but no
# correspondance with qidx
# begin enumeration where the last one left off.  Haha.
supp_qkey_to_qid = {}
supp = {qkey: question_text
        for qkey, question_text in _HUMAN_SURVEY.items()
        if qkey.startswith('SUPPLEMENTAL_')}
for i2, (qkey, question_text) in enumerate(supp.items(), start = i):
    supp_qkey_to_qid[qkey] = i2
    lines['survey_question'].append((question_text, question_text))

# Add personal questions to survey questions, same as supp above begin
# enumeration where the last one left off.  Hahaha.
personal = {qkey: question_text
            for qkey, question_text in _HUMAN_SURVEY.items()
            if qkey.startswith('PERSONAL_PROMPT_')
            and not qkey.endswith('_TITLE')}
personal_qkey_to_qid = {}
for i3, (qkey, question_text) in enumerate(personal.items(), start = i2):
    personal_qkey_to_qid[qkey] = i3
    lines['survey_question'].append((question_text, question_text))

for gkey, question_indices in question_group.iteritems():
    gidx = gkey_to_idx[gkey]
    # enumeration here is to keep track of display order
    for i, qidx in enumerate(question_indices):
        qid = qidx_to_qid[qidx]
        lines['group_questions'].append((gidx, qid, i))

response_types_set = set()
for qkey, response_type in question_type.iteritems():
    qidx = qkey_to_idx[qkey]
    qid = qidx_to_qid[qidx]
    response_types_set.add(response_type)
    lines['survey_question_response_type'].append((qid, response_type))

for qkey, qid in personal_qkey_to_qid.iteritems():
    response_types_set.add('TEXT')
    lines['survey_question_response_type'].append((qid, 'TEXT'))

for qkey, qid in supp_qkey_to_qid.iteritems():
    response_types_set.add('TEXT')
    lines['survey_question_response_type'].append((qid, 'TEXT'))

for response_type in response_types_set:
    lines['survey_response_types'].append((response_type,))

responses_set = set()
for qidx, responses in responses_map.iteritems():
    qid = qidx_to_qid[qidx]

    # keep track of unique responses to add to survey_response table
    for response in responses:
        responses_set.add(response)
    # enumeration here is to keep track of display order
    for i, response in enumerate(responses):
        lines['survey_question_response'].append((qid , response, i))

for response in responses_set:
    lines['survey_response'].append((response, response))

for qkey, (trigger_indices, supp_qkey) in supplemental_map.iteritems():
    qidx = qkey_to_idx[qkey]
    qid = qidx_to_qid[qidx]
    supp_qid = supp_qkey_to_qid[supp_qkey]

    for trigger_index in trigger_indices:
        response = responses_map[qidx][trigger_index]
        lines['survey_question_triggered_by'].append((supp_qid, qid, response))

# write all the things
with conn.get_postgres_cursor() as cur:
    for table in order:
        print '----------------------------------------------------------'
        print '--', table
        print '----------------------------------------------------------'
        for line in lines[table]:
            print cur.mogrify(inserts[table], line)
        print
