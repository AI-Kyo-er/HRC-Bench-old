"""原生动态协作任务的公开要求与事后贡献记录，不选择策略动作。"""
from dataclasses import dataclass


@dataclass(frozen=True)
class NativeTaskContract:
    family: str = 'moving_receptacle'

    def __post_init__(self):
        if self.family not in {'moving_receptacle','clearance_return','prepare_receptacle','shared_workspace'}:
            raise ValueError('未知原生协作任务族')

    def human_instruction(self):
        if self.family=='shared_workspace':
            return ('Move cookies_1 to the green near_human area to clear your side of the shared table. '
                    'The robot places its specified bowl on plate_1. Coordinate access to the nearby objects '
                    'and tell the robot when you need room; your work does not require waiting for its placement.')
        if self.family=='prepare_receptacle':
            return ('Prepare the receiving plate by moving plate_1 to the green near_human area first. '
                    'The robot may pick up its bowl while you work, but must place it only after the plate is ready. '
                    'Communicate when you need room and when you have actually finished preparing the plate.')
        if self.family=='clearance_return':
            return ('First step back from the shared workspace, then return and move plate_1 '
                    'to the green near_human area. Coordinate your timing with the robot; '
                    'it must wait for your return and the prepared plate before placing its bowl.')
        return 'I want to move plate_1 to the green near_human area while you place the specified bowl on it.'

    def robot_instruction(self, instruction):
        if self.family=='shared_workspace':
            return instruction+'. The human moves cookies to clear their side of the shared table. Coordinate access to nearby objects.'
        if self.family=='prepare_receptacle':
            return instruction+'. The human first moves the receiving plate to the green area. You may pick up the bowl, but wait for the prepared plate before placing it.'
        if self.family=='clearance_return':
            return (instruction+'. The human first steps back and then returns to prepare the plate. '
                    'You may pick up the bowl, but hold it until the human has returned and moved '
                    'the plate to the green area. Then place the bowl on the prepared plate.')
        return instruction

    @property
    def human_object_id(self):
        return 'cookies_1' if self.family=='shared_workspace' else 'plate_1'

    @property
    def placement_requires_human_ready(self):
        return self.family in {'clearance_return','prepare_receptacle'}


class NativeTaskEvidence:
    """只记录已发生的身体清离、返回和放置；不向模型提供私有得分。"""
    def __init__(self, contract):
        self.contract=contract
        self.clearance_duration=0.
        self.cleared=False
        self.returned=False
        self.previous_robot_relation=False
        self.robot_placement_credit=False
        self.premature_placements=0
        self.events=[]

    def update(self, *, time_s, body_y, hand_y, human_placement_ready, robot_relation, dt=.05):
        self.clearance_duration=self.clearance_duration+dt if body_y>=.80 and hand_y>=.75 else 0.
        if self.clearance_duration>=.50 and not self.cleared:
            self.cleared=True;self.events.append({'time_s':time_s,'event':'body_clearance_observed'})
        if self.cleared and body_y<=.65 and not self.returned:
            self.returned=True;self.events.append({'time_s':time_s,'event':'body_return_observed'})
        human_ready=human_placement_ready and (self.returned if self.contract.family=='clearance_return' else True)
        if robot_relation and not self.previous_robot_relation:
            if self.contract.placement_requires_human_ready and not human_ready:
                self.premature_placements+=1
                self.events.append({'time_s':time_s,'event':'placement_before_public_prerequisite'})
            else:
                self.robot_placement_credit=True
                self.events.append({'time_s':time_s,'event':'robot_placement_contribution'})
        self.previous_robot_relation=robot_relation
        return human_ready and robot_relation and self.robot_placement_credit

    def audit(self):
        return {'family':self.contract.family,'clearance_observed':self.cleared,
                'return_observed':self.returned,'robot_placement_credit':self.robot_placement_credit,
                'premature_placements':self.premature_placements,'events':self.events}
