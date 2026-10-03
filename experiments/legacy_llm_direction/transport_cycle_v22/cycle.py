"""公开请求、单调编号和逐行程事件；不读取任务目标或未来政策。"""
import copy


class CycleLedger:
    def __init__(self):
        self.legs=[];self.events=[];self.requests=[];self.active=None

    def snapshot(self):
        return copy.deepcopy(dict(legs=self.legs,events=self.events,requests=self.requests,active=self.active))

    def request(self,direction,facts):
        assert direction in ('forward','return')
        result=dict(sequence=len(self.requests),direction=direction,tick=facts['tick'],decision=None,leg_id=None)
        if self.active is not None:
            result['leg_id']=self.active
            result['decision']='already_running' if self.legs[self.active-1]['direction']==direction else 'rejected_motion'
        elif not facts['far' if direction=='forward' else 'near']:
            result['decision']='rejected_endpoint'
        else:
            ident=len(self.legs)+1
            leg=dict(id=ident,direction=direction,start_tick=facts['tick'],origin=facts['joint'],target=0.0 if direction=='forward' else 0.6,
                     loaded_at_start=facts['payload_stable'],carrier_event=None,payload_event=None,completed_tick=None)
            self.legs.append(leg);self.active=ident
            result.update(decision='accepted',leg_id=ident)
        self.requests.append(copy.deepcopy(result))
        return copy.deepcopy(result)

    def sample(self,facts):
        if self.active is None:return
        leg=self.legs[self.active-1]
        arrived=facts['profile_finished'] and facts['near' if leg['direction']=='forward' else 'far']
        def emit(kind):
            event=dict(sequence=len(self.events),kind=kind,leg_id=leg['id'],direction=leg['direction'],first_tick=facts['tick'])
            self.events.append(event);return copy.deepcopy(event)
        if arrived and leg['carrier_event'] is None:leg['carrier_event']=emit('carrier_arrived')
        if arrived and facts['payload_stable'] and leg['loaded_at_start'] and leg['payload_event'] is None:
            leg['payload_event']=emit('payload_arrived')
        if leg['carrier_event'] is not None and (not leg['loaded_at_start'] or leg['payload_event'] is not None):
            leg['completed_tick']=facts['tick'];self.active=None
