from scripts.audit_native_scene_integrity import audit


def test_other_object_loss_is_preserved_even_when_target_object_stays_on_table():
    trace=[{'time_s':t,'objects':{'target':[0.,0.,.92],'bottle':[x,0.,z]},'contacts':[]}
           for t,x,z in [(0.,0.,.9),(.1,.2,.7),(.2,.3,.4),(.3,.4,.02)]]
    result=audit(trace,['target','bottle'],.9)
    assert result['sustained_below_table_object_count']==1
    target,bottle=result['objects']
    assert target['first_below_table_clearance_s'] is None
    assert bottle['first_below_table_clearance_s']==.1
    assert bottle['terminal_below_table_clearance']
