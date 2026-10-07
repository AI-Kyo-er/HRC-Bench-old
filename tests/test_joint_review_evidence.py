import json

import pytest

from hrc_pilot.joint_review_evidence import pointer_value, verify_review


def case(tmp_path):
    (tmp_path / 'episode').mkdir()
    (tmp_path / 'episode/dialogue.jsonl').write_text(
        json.dumps({'time_s': 4., 'text': 'I will serve.', 'held': 'bowl'}) + '\n')
    for name in ['summary.json', 'interaction_verification.json', 'independent_video_verification.json']:
        (tmp_path / name).write_text(json.dumps({'status': 'verified'}))
    review = {'review_type': 'assistant_review_of_saved_records_not_human_study',
              'formal_benchmark_score': None, 'findings': [
                  {'interpretation': '话语不证明已经释放。', 'evidence': [
                      {'file': 'episode/dialogue.jsonl', 'row': 0, 'pointer': '/held', 'equals': 'bowl'}]}]}
    (tmp_path / 'public_request_response_review.json').write_text(json.dumps(review))
    return review


def test_record_binding_does_not_certify_semantics(tmp_path):
    case(tmp_path)
    result = verify_review(tmp_path)
    assert result['status'] == 'evidence_anchors_verified'
    assert result['formal_benchmark_score'] is None
    assert result['semantic_validity'] == 'assistant_interpretation_not_independently_validated'
    previous = result['source_sha256']
    (tmp_path / 'episode/dialogue.jsonl').write_text(
        json.dumps({'time_s': 5., 'text': 'I will serve.', 'held': 'bowl'}) + '\n')
    assert verify_review(tmp_path)['source_sha256'] != previous


def test_false_reference_rejected(tmp_path):
    review = case(tmp_path)
    review['findings'][0]['evidence'][0]['equals'] = None
    (tmp_path / 'public_request_response_review.json').write_text(json.dumps(review))
    with pytest.raises(ValueError, match='原始记录不符'):
        verify_review(tmp_path)


def test_unverified_terminal_rejected(tmp_path):
    case(tmp_path)
    (tmp_path / 'independent_video_verification.json').write_text('{"status":"failed"}')
    with pytest.raises(ValueError, match='独立'):
        verify_review(tmp_path)


def test_outside_source_rejected(tmp_path):
    review = case(tmp_path)
    review['findings'][0]['evidence'][0]['file'] = '../outside.json'
    (tmp_path / 'public_request_response_review.json').write_text(json.dumps(review))
    with pytest.raises(ValueError, match='本运行目录'):
        verify_review(tmp_path)


def test_json_pointer_escaped_keys_and_list():
    assert pointer_value({'a/b': [{'~': False}]}, '/a~1b/0/~0') is False


def test_boolean_physical_evidence_is_not_number(tmp_path):
    review = case(tmp_path)
    (tmp_path / 'episode/dialogue.jsonl').write_text('{"released":true}\n')
    evidence = review['findings'][0]['evidence'][0]
    evidence.update(pointer='/released', equals=1)
    (tmp_path / 'public_request_response_review.json').write_text(json.dumps(review))
    with pytest.raises(ValueError, match='原始记录不符'):
        verify_review(tmp_path)
